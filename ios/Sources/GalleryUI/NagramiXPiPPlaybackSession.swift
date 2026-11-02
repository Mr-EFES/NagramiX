// One explicit request owns readiness, native start and gallery transfer.
// AVKit is injected so the real lifecycle can also run without an Apple SDK.
final class NagramiXPiPPlaybackSession {
    enum Phase { case idle, waiting, starting, active }
    private(set) var phase: Phase = .idle
    private var completion: ((Bool) -> Void)?
    private var validate: (() -> Bool)?
    private let prepare: () -> Void
    private let possible: () -> Bool
    private let active: () -> Bool
    private let start: () -> Void
    private let stop: () -> Void
    private let transfer: () -> Bool
    private let release: () -> Void
    private let ended: () -> Void

    init(prepare: @escaping () -> Void, possible: @escaping () -> Bool,
         active: @escaping () -> Bool, start: @escaping () -> Void,
         stop: @escaping () -> Void, transfer: @escaping () -> Bool,
         release: @escaping () -> Void, ended: @escaping () -> Void) {
        self.prepare = prepare; self.possible = possible; self.active = active
        self.start = start; self.stop = stop; self.transfer = transfer
        self.release = release; self.ended = ended
    }

    @discardableResult
    func request(validate: @escaping () -> Bool, completion: @escaping (Bool) -> Void) -> Bool {
        guard self.phase == .idle, validate() else { return false }
        self.validate = validate
        self.completion = completion
        self.phase = .waiting
        self.prepare()
        self.readinessChanged()
        return true
    }

    func readinessChanged() {
        guard self.phase == .waiting else { return }
        guard self.validate?() == true else { self.fail(); return }
        if self.possible() {
            // Set state before invoking AVKit: its callbacks may be synchronous.
            self.phase = .starting
            self.start()
        }
    }

    func didStart() {
        guard self.phase == .starting else { return }
        guard self.validate?() == true else { self.fail(stopNative: true); return }
        // Reentrant gallery visibility callbacks must see an active owner.
        self.phase = .active
        let transferred = self.transfer()
        guard self.phase == .active else { return }
        guard transferred else { self.fail(stopNative: true); return }
        self.validate = nil
        let completion = self.completion
        self.completion = nil
        completion?(true)
    }

    func timedOut() {
        if self.phase == .starting, self.active() { self.didStart(); return }
        if self.phase == .waiting || self.phase == .starting { self.fail(stopNative: true) }
    }

    func failedToStart() {
        guard self.phase == .waiting || self.phase == .starting else { return }
        self.fail()
    }

    func cancelPreparation() {
        // A foreground transition can occur while iOS is presenting PiP.
        // Once start() was issued, its delegate/timeout owns the outcome.
        if self.phase == .waiting { self.fail() }
    }

    func stopRequested() {
        if self.phase == .waiting { self.fail(); return }
        if self.phase == .starting || self.phase == .active { self.stop() }
    }

    func didStop() {
        guard self.phase != .idle else { return }
        self.fail()
    }

    private func fail(stopNative: Bool = false) {
        let hadTransfer = self.phase == .active
        let completion = self.completion
        self.phase = .idle
        self.completion = nil
        self.validate = nil
        if stopNative { self.stop() }
        self.release()
        if hadTransfer { self.ended() }
        completion?(false)
    }
}
