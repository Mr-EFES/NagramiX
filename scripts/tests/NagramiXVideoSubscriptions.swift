import Foundation

private struct RangeSet<Bound: Comparable> {}
private typealias MediaPlayerStatus = Int
private enum NoError {}
private struct UniversalVideoContent { let id: AnyHashable }
private struct Holder {
    var statusValue: MediaPlayerStatus?
    var bufferingStatusValue: (RangeSet<Int64>, Int64)?
    var isNativePictureInPictureActiveValue = false
}
private struct ActionDisposable {
    let dispose: () -> Void
    init(_ dispose: @escaping () -> Void) { self.dispose = dispose }
}
private final class Queue {
    static let shared = Queue()
    private var jobs: [() -> Void] = []
    static func mainQueue() -> Queue { self.shared }
    func isCurrent() -> Bool { true }
    func async(_ job: @escaping () -> Void) { self.jobs.append(job) }
    func drain() { let jobs = self.jobs; self.jobs = []; jobs.forEach { $0() } }
}
private struct Subscriber<T> { let putNext: (T) -> Void }
private struct Signal<T, E> {
    let subscribe: (Subscriber<T>) -> ActionDisposable
    init(_ subscribe: @escaping (Subscriber<T>) -> ActionDisposable) { self.subscribe = subscribe }
}
infix operator |>
private func |> <T>(value: T, function: (T) -> T) -> T { function(value) }
private func runOn<T>(_ queue: Queue) -> (T) -> T { { $0 } }

// PRODUCTION CALLBACK BAGS
private final class Manager {
    var holders: [AnyHashable: Holder] = [:]
    var holderCallbacks: [AnyHashable: UniversalVideoContentHolderCallbacks] = [:]
    // PRODUCTION SUBSCRIPTION METHODS
}

@main private enum CallbackTests {
    static func main() {
        let manager = Manager(), content = UniversalVideoContent(id: 45)
        var statusCount = 0
        let status = manager.statusSignal(content: content).subscribe(Subscriber { _ in statusCount += 1 })
        let registry = manager.holderCallbacks[content.id]!
        for _ in 0 ..< 10 {
            let finish = manager.addPlaybackCompleted(id: content.id) {}
            let buffer = manager.bufferingStatusSignal(content: content).subscribe(Subscriber { _ in })
            var events: [Bool] = []
            let pip = manager.isNativePictureInPictureActiveSignal(content: content).subscribe(Subscriber { events.append($0) })
            buffer.dispose()
            manager.removePlaybackCompleted(id: content.id, index: finish)
            Queue.shared.drain()
            precondition(manager.holderCallbacks[content.id] === registry)
            registry.isNativePictureInPictureActive.copyItems().forEach { $0(true) }
            precondition(events == [false, true])
            pip.dispose()
            Queue.shared.drain()
            precondition(registry.isNativePictureInPictureActive.isEmpty && registry.bufferingStatus.isEmpty)
            registry.status.copyItems().forEach { $0(7) }
        }
        precondition(statusCount == 11, "closing PiP must not disconnect playback status")
        status.dispose()
        Queue.shared.drain()
        precondition(manager.holderCallbacks[content.id] == nil)
        print("PASS: ten PiP subscriptions, buffering and completion cleanup preserve the active status listener")
    }
}
