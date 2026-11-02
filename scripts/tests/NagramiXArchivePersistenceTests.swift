import Foundation

private final class Scheduled {
    let delay: Double
    let action: () -> Void
    var cancelled = false
    init(_ delay: Double, _ action: @escaping () -> Void) { self.delay = delay; self.action = action }
}
private final class Scheduler {
    var tasks: [Scheduled] = []
    func schedule(_ delay: Double, _ action: @escaping () -> Void) -> (() -> Void) {
        let task = Scheduled(delay, action); self.tasks.append(task)
        return { task.cancelled = true }
    }
    func fire() { self.tasks.first(where: { !$0.cancelled }).map { $0.cancelled = true; $0.action() } }
    var active: Int { self.tasks.filter { !$0.cancelled }.count }
}

@main struct ArchivePersistenceTests {
    static func main() throws {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ description: String) {
            checks += 1; if !value() { fatalError("FAIL: " + description) }
        }
        let noSpace = NSError(domain: NSCocoaErrorDomain, code: NSFileWriteOutOfSpaceError)
        check(NagramiXArchiveStorageFailure.writing(noSpace) == .noSpace, "Cocoa ENOSPC is reported")
        check(NagramiXArchiveStorageFailure.writing(NSError(domain: NSPOSIXErrorDomain, code: 28)) == .noSpace, "POSIX ENOSPC is reported")
        check(NagramiXArchiveStorageFailure.writing(NSError(domain: NSCocoaErrorDomain, code: 512, userInfo: [NSUnderlyingErrorKey: noSpace])) == .noSpace, "underlying ENOSPC is reported")
        check(NagramiXArchiveStorageFailure.writing(NSError(domain: NSPOSIXErrorDomain, code: 13)) == .writeFailed, "permission error remains a write failure")
        let clock = Scheduler()
        var writes: [Int] = [], committed: [Int] = [], statuses: [NagramiXArchiveStorageStatus] = []
        var failing = false
        var writer: NagramiXArchivePersistence<Int>? = NagramiXArchivePersistence(write: { value in
            writes.append(value); if failing { throw noSpace }
        }, schedule: clock.schedule, committed: { committed.append($0) }, status: { statuses.append($0) })
        check(writer!.submit(1) && committed == [1] && writer!.pending == nil, "only successful write publishes committed state")
        failing = true
        check(!writer!.submit(2) && committed == [1] && writer!.pending == 2, "failure preserves committed state and dirty snapshot")
        check(statuses.last == .failed(.noSpace) && clock.active == 1, "failure reaches caller and schedules one retry")
        for value in 3...200 { check(!writer!.submit(value), "new messages coalesce while failed") }
        check(writes == [1, 2] && writer!.pending == 200 && clock.active == 1, "burst does not issue one failed write/timer per message")
        let stale = clock.tasks.last!
        clock.fire()
        check(writes.last == 200 && committed == [1], "retry writes latest snapshot, never the first failed version")
        let attempts = writes.count; stale.action()
        check(writes.count == attempts, "late previous timer cannot write again")
        clock.fire(); clock.fire()
        check(clock.active == 0 && writes.count == 5, "initial attempt plus exactly three automatic retries")
        check(clock.tasks.map { $0.delay } == [1, 5, 30], "bounded backoff is retained")
        for value in 201...300 { _ = writer!.submit(value) }
        check(writes.count == 5 && clock.active == 0 && writer!.pending == 300, "exhausted burst keeps latest state without an endless retry loop")
        failing = false
        check(writer!.retry() && committed == [1, 300] && writer!.pending == nil, "explicit recovery commits latest snapshot")
        check(statuses.last == .ready && clock.active == 0, "success clears failed state and timer")
        stale.action(); check(committed == [1, 300], "late timer cannot resurrect obsolete snapshot after recovery")
        failing = true; _ = writer!.submit(301)
        let pendingTimer = clock.tasks.last!
        check(!writer!.submit(302, retryNow: true) && writes.last == 302, "explicit user mutation can request immediate retry")
        let beforeLate = writes.count; pendingTimer.action()
        check(writes.count == beforeLate, "superseded explicit retry invalidates previous callback")
        weak var weakWriter = writer; writer = nil
        check(weakWriter == nil && clock.active == 0, "deinit cancels timer without a retain cycle")
        let otherClock = Scheduler(); var other: [Int] = []
        let independent = NagramiXArchivePersistence<Int>(write: { _ in }, schedule: otherClock.schedule, committed: { other.append($0) }, status: { _ in })
        check(independent.submit(9) && other == [9], "another archive has independent state and retry budget")
        print("PASS: \(checks) real persistence coordinator checks")
    }
}
