// The single owner of an explicit system PiP transition. AVKit and the gallery
// are injected so callback ordering, cancellation and restoration are testable.
final class NagramiXPiPLifecycle {
    enum Phase { case idle, preparing, starting, active, stopping, finished }
    enum Readiness { case waiting, ready, invalid }

    private(set) var phase: Phase = .idle {
        didSet { self.changed() }
    }
    private(set) var transferred = false
    private(set) var restored = false
    private var nativeStopped = false
    private var restoring = false
    private var restoreDeadline = 0.0
    private var deadline = 0.0
    private var startTimeout = 0.0
    private var result: ((Bool) -> Void)?
    private var restoreResults: [(Bool) -> Void] = []
    private var updating = false
    private var updateAgain = false

    private let now: () -> Double
    private let valid: () -> Bool
    private let prepare: () -> Void
    private let readiness: () -> Readiness
    private let nativeActive: () -> Bool
    private let start: () -> Void
    private let stop: () -> Void
    private let commit: () -> Bool
    private let restore: (@escaping (Bool) -> Void) -> Void
    private let release: () -> Void
    private let ended: (Bool) -> Void
    private let changed: () -> Void

    init(now: @escaping () -> Double, valid: @escaping () -> Bool,
         prepare: @escaping () -> Void, readiness: @escaping () -> Readiness,
         nativeActive: @escaping () -> Bool, start: @escaping () -> Void,
         stop: @escaping () -> Void, commit: @escaping () -> Bool,
         restore: @escaping (@escaping (Bool) -> Void) -> Void,
         release: @escaping () -> Void, ended: @escaping (Bool) -> Void,
         changed: @escaping () -> Void) {
        self.now = now; self.valid = valid; self.prepare = prepare
        self.readiness = readiness; self.nativeActive = nativeActive
        self.start = start; self.stop = stop; self.commit = commit
        self.restore = restore; self.release = release; self.ended = ended
        self.changed = changed
    }

    var needsTimer: Bool {
        self.phase == .preparing || self.phase == .starting || self.phase == .stopping || self.restoring
    }

    @discardableResult
    func begin(timeout: Double, completion: @escaping (Bool) -> Void) -> Bool {
        guard self.phase == .idle, timeout.isFinite, timeout > 0, self.valid() else { return false }
        self.result = completion
        self.startTimeout = timeout
        self.deadline = self.now() + timeout
        self.phase = .preparing
        self.prepare()
        self.update()
        return true
    }

    func update() {
        // A status/KVO callback or a synchronous test double may reenter here.
        if self.updating { self.updateAgain = true; return }
        self.updating = true
        repeat {
            self.updateAgain = false
            self.advance()
        } while self.updateAgain
        self.updating = false
    }

    private func advance() {
        if self.restoring, self.now() >= self.restoreDeadline { self.restorationCompleted(false) }
        switch self.phase {
        case .preparing:
            guard self.valid(), self.now() < self.deadline else { self.finish(); return }
            switch self.readiness() {
            case .invalid: self.finish()
            case .waiting: break
            case .ready:
                // Readiness may have delivered a reentrant cancellation.
                guard self.phase == .preparing, self.valid() else { return }
                self.deadline = self.now() + self.startTimeout
                self.phase = .starting
                self.start()
            }
        case .starting:
            if !self.valid() { self.stopRequested(); return }
            if self.nativeActive() { self.didStart(); return }
            if self.now() >= self.deadline { self.stopRequested() }
        case .stopping:
            if self.nativeStopped && !self.restoring { self.finish() }
            else if self.now() >= self.deadline && !self.nativeActive() && !self.restoring { self.finish() }
        case .idle, .active, .finished: break
        }
    }

    func didStart() {
        if self.phase == .stopping {
            // stop() can precede a late didStart. Close that native window too.
            self.stop()
            return
        }
        guard self.phase == .starting else { return }
        guard self.valid() else { self.stopRequested(); return }
        self.phase = .active
        // Commit owns all gallery side effects, after native success only.
        self.transferred = true
        guard self.commit() else {
            self.transferred = false
            self.stopRequested()
            return
        }
        guard self.phase == .active else { return }
        self.complete(true)
    }

    func failedToStart() {
        guard self.phase == .preparing || self.phase == .starting || self.phase == .stopping else { return }
        self.nativeStopped = true
        self.finish()
    }

    func cancelPreparation() {
        if self.phase == .preparing { self.finish() }
    }

    func stopRequested() {
        switch self.phase {
        case .idle, .finished, .stopping: return
        case .preparing: self.finish()
        case .starting, .active:
            self.deadline = self.now() + 4.0
            self.phase = .stopping
            self.complete(false)
            self.stop()
        }
    }

    func didStop() {
        guard self.phase != .idle && self.phase != .finished else { return }
        self.nativeStopped = true
        if !self.restoring { self.finish() }
        else { self.phase = .stopping }
    }

    func restoreInterface(completion: @escaping (Bool) -> Void) {
        if self.restored { completion(true); return }
        guard self.transferred, self.phase == .active || self.phase == .stopping else { completion(false); return }
        self.restoreResults.append(completion)
        guard !self.restoring else { return }
        self.restoring = true
        self.restoreDeadline = self.now() + 5.0
        self.changed()
        self.restore { [weak self] success in self?.restorationCompleted(success) }
    }

    private func restorationCompleted(_ success: Bool) {
        guard self.restoring else { return }
        self.restoring = false
        self.restored = success
        let callbacks = self.restoreResults
        self.restoreResults.removeAll()
        callbacks.forEach { $0(success) }
        self.changed()
        if self.nativeStopped { self.finish() }
    }

    private func complete(_ success: Bool) {
        let callback = self.result
        self.result = nil
        callback?(success)
    }

    private func finish() {
        guard self.phase != .finished else { return }
        self.restoring = false
        let restoreResults = self.restoreResults
        self.restoreResults.removeAll()
        self.phase = .finished
        let hadTransfer = self.transferred
        self.release()
        self.complete(false)
        restoreResults.forEach { $0(false) }
        if hadTransfer { self.ended(self.restored) }
    }
}

// ManagedAudioSession.isPlaybackActive includes ambient. That flag alone does
// not establish a playback-category session for silent/paused PiP sources.
enum NagramiXPiPAudioPolicy {
    enum Category { case ambient, playback, playAndRecord, other }

    static func isReady(managedPlaybackActive: Bool, category: Category) -> Bool {
        return managedPlaybackActive && (category == .playback || category == .playAndRecord)
    }

    static func needsPlaybackLease(managedPlaybackActive: Bool, category: Category,
                                   elapsed: Double, alreadyRequested: Bool) -> Bool {
        guard elapsed.isFinite, elapsed >= 0.5, !alreadyRequested, category != .playAndRecord else { return false }
        return !self.isReady(managedPlaybackActive: managedPlaybackActive, category: category)
    }
}
