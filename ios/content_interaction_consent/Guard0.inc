import Foundation

public enum NagramiXArchiveStorageFailure: Equatable, Error {
    case noSpace
    case writeFailed
    case unreadable

    static func writing(_ error: Error) -> NagramiXArchiveStorageFailure {
        var current = error as NSError
        for _ in 0..<8 {
            if (current.domain == NSCocoaErrorDomain && current.code == NSFileWriteOutOfSpaceError)
                || (current.domain == NSPOSIXErrorDomain && current.code == 28) { return .noSpace }
            guard let underlying = current.userInfo[NSUnderlyingErrorKey] as? NSError else { break }
            current = underlying
        }
        return .writeFailed
    }
}

public enum NagramiXArchiveStorageStatus: Equatable {
    case ready
    case retrying
    case failed(NagramiXArchiveStorageFailure)
}

/// Queue-confined write coordinator. Only the latest desired snapshot is kept;
/// readers are advanced by committed() exclusively after an atomic write.
/// A failed burst gets at most three automatic retries, never one per message.
final class NagramiXArchivePersistence<State> {
    private let write: (State) throws -> Void
    private let schedule: (Double, @escaping () -> Void) -> (() -> Void)
    private let committed: (State) -> Void
    private let status: (NagramiXArchiveStorageStatus) -> Void
    private(set) var pending: State?
    private var cancelRetry: (() -> Void)?
    private var generation: UInt64 = 0
    private var failures = 0
    private let delays = [1.0, 5.0, 30.0]

    init(write: @escaping (State) throws -> Void, schedule: @escaping (Double, @escaping () -> Void) -> (() -> Void), committed: @escaping (State) -> Void, status: @escaping (NagramiXArchiveStorageStatus) -> Void) {
        self.write = write; self.schedule = schedule; self.committed = committed; self.status = status
    }

    @discardableResult
    func submit(_ value: State, retryNow: Bool = false) -> Bool {
        let hadPending = self.pending != nil
        self.pending = value
        if hadPending && !retryNow { return false }
        return self.retry()
    }

    @discardableResult
    func retry() -> Bool {
        self.invalidateRetry()
        self.failures = 0
        guard self.pending != nil else { return true }
        self.status(.retrying)
        return self.attempt()
    }

    private func attempt() -> Bool {
        guard let pending = self.pending else { return true }
        self.invalidateRetry()
        do {
            try self.write(pending)
            self.pending = nil
            self.invalidateRetry()
            self.committed(pending)
            self.status(.ready)
            return true
        } catch {
            self.status(.failed(.writing(error)))
            let failure = self.failures
            self.failures += 1
            if failure < self.delays.count {
                let token = self.generation
                self.cancelRetry = self.schedule(self.delays[failure], { [weak self] in
                    guard let self, self.generation == token else { return }
                    self.cancelRetry = nil
                    _ = self.attempt()
                })
            }
            return false
        }
    }

    private func invalidateRetry() {
        self.generation &+= 1
        self.cancelRetry?(); self.cancelRetry = nil
    }

    deinit { self.cancelRetry?() }
}
