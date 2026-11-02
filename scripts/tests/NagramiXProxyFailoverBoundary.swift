// Deterministic boundaries for the real queue-confined failover controller.
// No socket, native transport or Apple SDK is replaced by these test results.
import Foundation

protocol Disposable { func dispose() }
final class ActionDisposable: Disposable {
    private var action: (() -> Void)?
    init(_ action: @escaping () -> Void) { self.action = action }
    func dispose() { let action = self.action; self.action = nil; action?() }
}
final class MetaDisposable: Disposable {
    private var current: Disposable?
    private var disposed = false
    func set(_ value: Disposable?) {
        if self.disposed { value?.dispose(); return }
        let old = self.current; self.current = value; old?.dispose()
    }
    func dispose() { self.disposed = true; let old = self.current; self.current = nil; old?.dispose() }
}
final class Subscriber<T, E> {
    var active = true
    let next: (T) -> Void
    let completed: () -> Void
    init(next: @escaping (T) -> Void, completed: @escaping () -> Void) { self.next = next; self.completed = completed }
    func putNext(_ value: T) { if self.active { self.next(value) } }
    func putCompletion() { if self.active { self.active = false; self.completed() } }
}
enum NoError: Error {}
final class Signal<T, E> {
    let generator: (Subscriber<T, E>) -> Disposable
    init(_ generator: @escaping (Subscriber<T, E>) -> Disposable) { self.generator = generator }
    static func single(_ value: T) -> Signal<T, E> {
        Signal { $0.putNext(value); $0.putCompletion(); return ActionDisposable({}) }
    }
    func start(next: @escaping (T) -> Void = { _ in }, completed: @escaping () -> Void = {}) -> Disposable {
        let subscriber = Subscriber<T, E>(next: next, completed: completed)
        let disposable = self.generator(subscriber)
        return ActionDisposable { subscriber.active = false; disposable.dispose() }
    }
}
final class ValuePromise<T> {
    private var value: T
    private var subscribers: [UUID: Subscriber<T, NoError>] = [:]
    init(_ value: T) { self.value = value }
    func set(_ value: T) {
        self.value = value
        for subscriber in Array(self.subscribers.values) { subscriber.putNext(value) }
    }
    func get() -> Signal<T, NoError> {
        Signal { subscriber in
            let id = UUID(); self.subscribers[id] = subscriber; subscriber.putNext(self.value)
            return ActionDisposable { self.subscribers.removeValue(forKey: id) }
        }
    }
}
precedencegroup PipeRight {
    associativity: left
    higherThan: DefaultPrecedence
}
infix operator |> : PipeRight
func |> <T, U>(value: T, function: (T) -> U) -> U { function(value) }
func map<T, U, E>(_ transform: @escaping (T) -> U) -> (Signal<T, E>) -> Signal<U, E> {
    { source in Signal { subscriber in source.start(next: { subscriber.putNext(transform($0)) }, completed: subscriber.putCompletion) } }
}
func take<T, E>(_ count: Int) -> (Signal<T, E>) -> Signal<T, E> {
    { source in Signal { subscriber in
        var remaining = count
        return source.start(next: { value in
            guard remaining > 0 else { return }; remaining -= 1; subscriber.putNext(value)
            if remaining == 0 { subscriber.putCompletion() }
        }, completed: subscriber.putCompletion)
    } }
}
func distinctUntilChanged<T: Equatable, E>(_ source: Signal<T, E>) -> Signal<T, E> {
    Signal { subscriber in
        var previous: T?
        var emitted = false
        return source.start(next: { value in
            if !emitted || previous != value { emitted = true; previous = value; subscriber.putNext(value) }
        }, completed: subscriber.putCompletion)
    }
}
func combineLatest<A, B>(_ a: Signal<A, NoError>, _ b: Signal<B, NoError>) -> Signal<(A, B), NoError> {
    Signal { subscriber in
        var lastA: A?, lastB: B?
        func emit() { if let lastA, let lastB { subscriber.putNext((lastA, lastB)) } }
        let da = a.start(next: { lastA = $0; emit() })
        let db = b.start(next: { lastB = $0; emit() })
        return ActionDisposable { da.dispose(); db.dispose() }
    }
}
final class Atomic<T> {
    private var value: T
    init(value: T) { self.value = value }
    func with<U>(_ action: (T) -> U) -> U { action(self.value) }
    func swap(_ value: T) -> T { let old = self.value; self.value = value; return old }
    func modify(_ action: (T) -> T) -> T { self.value = action(self.value); return self.value }
}
final class Queue {
    private static var pending: [() -> Void] = []
    init(name: String) {}
    func async(_ action: @escaping () -> Void) { Self.pending.append(action) }
    static func drain() {
        var turns = 0
        while !self.pending.isEmpty {
            turns += 1; precondition(turns < 10000, "unbounded controller callback loop")
            self.pending.removeFirst()()
        }
    }
}
func deliverOn<T, E>(_ queue: Queue) -> (Signal<T, E>) -> Signal<T, E> {
    { source in Signal { subscriber in
        source.start(next: { value in queue.async { subscriber.putNext(value) } }, completed: { queue.async { subscriber.putCompletion() } })
    } }
}
enum SwiftSignalKit {
    final class Timer {
        let timeout: Double
        let repeats: Bool
        let completion: () -> Void
        let queue: Queue
        var due = 0.0
        var invalidated = false
        init(timeout: Double, repeat repeats: Bool, completion: @escaping () -> Void, queue: Queue) {
            self.timeout = timeout; self.repeats = repeats; self.completion = completion; self.queue = queue
        }
        func start() { self.due = Clock.now + self.timeout; Clock.timers.append(self) }
        func invalidate() { self.invalidated = true }
        func lateCallback() { self.queue.async(self.completion) }
    }
}
enum Clock {
    static var now = 0.0
    static var timers: [SwiftSignalKit.Timer] = []
    static var active: [SwiftSignalKit.Timer] { self.timers.filter { !$0.invalidated } }
    static func reset() { self.now = 0; self.timers.removeAll() }
    static func advance(_ delta: Double) {
        let target = self.now + delta
        var turns = 0
        while let timer = self.active.filter({ $0.due <= target }).min(by: { $0.due < $1.due }) {
            turns += 1; precondition(turns < 10000, "unbounded failover timer loop")
            self.now = timer.due
            if timer.repeats { timer.due += timer.timeout } else { timer.invalidated = true }
            timer.queue.async(timer.completion); Queue.drain()
        }
        self.now = target; Queue.drain()
    }
}

// DTOs preserve native equality across host, port, transport and credentials.
enum ProxyServerConnection: Hashable { case socks5(username: String?, password: String?), mtp(secret: Data), web(secret: Data, path: String) }
struct ProxyServerSettings: Hashable {
    let host: String
    let port: Int32
    let connection: ProxyServerConnection
}
struct ProxySettings: Equatable {
    var enabled: Bool
    var servers: [ProxyServerSettings]
    var activeServer: ProxyServerSettings?
    var useForCalls: Bool
    static let defaultSettings = ProxySettings(enabled: false, servers: [], activeServer: nil, useForCalls: false)
}
enum ProxyServerStatus: Equatable { case checking, available(Double), notAvailable }
enum ConnectionStatus: Equatable {
    case connecting(proxyAddress: String?, proxyHasConnectionIssues: Bool)
    case updating(proxyAddress: String?)
    case online(proxyAddress: String?)
    case waitingForNetwork
}
enum SharedDataKeys { static let proxySettings = 1 }
struct PreferencesEntry {
    let value: Any
    func get<T>(_ type: T.Type) -> T? { self.value as? T }
}
struct SharedData { let entries: [Int: PreferencesEntry] }
enum TelegramAccountManagerTypes {}
final class AccountManager<T> {
    private let promise: ValuePromise<SharedData>
    var settings: ProxySettings
    var holdTransactions = false
    var pendingTransactions: [() -> Void] = []
    var automaticWrites: [ProxyServerSettings?] = []
    init(_ settings: ProxySettings) {
        self.settings = settings
        self.promise = ValuePromise(SharedData(entries: [SharedDataKeys.proxySettings: PreferencesEntry(value: settings)]))
    }
    func sharedData(keys: [Int]) -> Signal<SharedData, NoError> { self.promise.get() }
    func publish(_ settings: ProxySettings) {
        self.settings = settings
        self.promise.set(SharedData(entries: [SharedDataKeys.proxySettings: PreferencesEntry(value: settings)]))
    }
    func commitPending() { let actions = self.pendingTransactions; self.pendingTransactions.removeAll(); actions.forEach { $0() }; Queue.drain() }
}
func updateProxySettingsInteractively(accountManager: AccountManager<TelegramAccountManagerTypes>, _ transform: @escaping (ProxySettings) -> ProxySettings) -> Signal<Bool, NoError> {
    Signal { subscriber in
        let commit = {
            // A transaction already queued in Postbox may still run after
            // disposal. The production cancellation guard must prevent writes.
            let previous = accountManager.settings
            let updated = transform(previous)
            let changed = previous != updated
            if changed { accountManager.automaticWrites.append(updated.activeServer); accountManager.publish(updated) }
            subscriber.putNext(changed); subscriber.putCompletion()
        }
        if accountManager.holdTransactions { accountManager.pendingTransactions.append(commit) }
        else { Queue(name: "transaction").async(commit) }
        return ActionDisposable({})
    }
}
enum NagramiXProxyVPNPolicy {
    static var bypassed = false
    static let promise = ValuePromise(false)
    static func bypassedSignal() -> Signal<Bool, NoError> { self.promise.get() }
    static func set(_ value: Bool) { self.bypassed = value; self.promise.set(value); Queue.drain() }
}
final class Network {
    let status: ValuePromise<ConnectionStatus>
    var connectionStatus: Signal<ConnectionStatus, NoError> { self.status.get() |> distinctUntilChanged }
    let nagramiXProxyStatuses = Atomic<ProxyServersStatuses?>(value: nil)
    init(_ status: ConnectionStatus) { self.status = ValuePromise(status) }
    func publish(_ status: ConnectionStatus) { self.status.set(status); Queue.drain() }
}
final class ProxyServersStatuses {
    private let promise = ValuePromise<[ProxyServerSettings: ProxyServerStatus]>([:])
    var values: [ProxyServerSettings: ProxyServerStatus] = [:]
    var refreshes = 0
    var stopped = false
    init(network: Network, servers: Signal<[ProxyServerSettings], NoError>, refreshEnabled: Signal<Bool, NoError>, activeServer: Signal<ProxyServerSettings?, NoError>) {}
    func statuses() -> Signal<[ProxyServerSettings: ProxyServerStatus], NoError> { self.promise.get() }
    func publish(_ values: [ProxyServerSettings: ProxyServerStatus]) { self.values = values; self.promise.set(values); Queue.drain() }
    func availableServers() -> Signal<Set<ProxyServerSettings>, NoError> {
        .single(Set(self.values.compactMap { if case .available = $0.value { return $0.key }; return nil }))
    }
    func markUnavailable(_ server: ProxyServerSettings) { self.values[server] = .notAvailable; self.promise.set(self.values) }
    func refreshIfNeeded() { self.refreshes += 1 }
    func stop() { self.stopped = true }
}
final class Logger {
    static let shared = Logger()
    func log(_ category: String, _ message: String) {}
}
