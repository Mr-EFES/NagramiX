// Only Postbox, queue/time and media ownership boundaries are substituted.
// Archive models, writer, mutation bodies and real Foundation IO are inserted
// by validate_archive_persistence.py from the final generated production source.
import Foundation
public enum NoError {}
public struct Signal<T, E> {}
final class ValuePromise<T> {
    var value: T
    init(_ value: T, ignoreRepeated: Bool) { self.value = value }
    func set(_ value: T) { self.value = value }
    func get() -> Signal<T, NoError> { Signal() }
}
final class Atomic<T> {
    var value: T
    init(value: T) { self.value = value }
    func with<R>(_ action: (T) -> R) -> R { action(self.value) }
    func swap(_ value: T) -> T { let old = self.value; self.value = value; return old }
}
final class Queue {
    static var pending: [() -> Void] = []
    func async(_ action: @escaping () -> Void) { Self.pending.append(action) }
    static func drain() { while !self.pending.isEmpty { self.pending.removeFirst()() } }
}
enum SwiftSignalKit {
    final class Timer {
        static var timers: [Timer] = []
        var invalidated = false
        let action: () -> Void
        init(timeout: Double, repeat: Bool, completion: @escaping () -> Void, queue: Queue) { self.action = completion }
        func start() { Self.timers.append(self) }
        func invalidate() { self.invalidated = true }
        static func fire() {
            if let timer = self.timers.first(where: { !$0.invalidated }) { timer.invalidated = true; timer.action(); Queue.drain() }
        }
    }
}
public struct MessageTextEntity: Codable, Equatable {}
struct PeerId: Hashable {
    let value: Int64
    init(_ value: Int64) { self.value = value }
    func toInt64() -> Int64 { self.value }
}
struct MessageId: Hashable { let peerId: PeerId; let namespace: Int32; let id: Int32 }
final class MediaStoreSpy {
    var sequence: Int64 = 0
    var removed: Set<String> = []
    var retained: Set<String> = []
    var clears = 0
    var beforeRemoval: ((Set<String>) -> Void)?
    func barrier() -> Int64 { self.sequence += 1; return self.sequence }
    func retain(key: String, requests: [Int], ticket: Int64) { self.retained.insert(key) }
    func remove(keys: Set<String>, before: Int64) { self.beforeRemoval?(keys); self.removed.formUnion(keys); self.retained.subtract(keys) }
    func clear(before: Int64) { self.beforeRemoval?(self.retained); self.clears += 1; self.removed.formUnion(self.retained); self.retained.removeAll() }
}
struct NagramiXMessageArchiveSettings {
    var messageEditHistory = true
}
