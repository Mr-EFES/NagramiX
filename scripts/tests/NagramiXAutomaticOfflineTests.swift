import Foundation

// The entire production presence manager is compiled with these boundary
// doubles. Only time, serial queue delivery and RPC responses are simulated.
enum NoError {}
struct MTRpcError: Error {}
protocol Disposable { func dispose() }
final class ActionDisposable: Disposable {
    let action: () -> Void
    init(_ action: @escaping () -> Void) { self.action = action }
    func dispose() { self.action() }
}
final class MetaDisposable: Disposable {
    private var current: Disposable?
    func set(_ value: Disposable?) { self.current?.dispose(); self.current = value }
    func dispose() { self.set(nil) }
}
final class Subscriber<T, E> {
    let next: (T) -> Void; let error: (E) -> Void; let completed: () -> Void
    init(next: @escaping (T) -> Void, error: @escaping (E) -> Void, completed: @escaping () -> Void) { self.next = next; self.error = error; self.completed = completed }
    func putNext(_ value: T) { self.next(value) }
    func putCompletion() { self.completed() }
}
final class Signal<T, E> {
    let generate: (Subscriber<T, E>) -> Disposable
    init(_ generate: @escaping (Subscriber<T, E>) -> Disposable) { self.generate = generate }
    func start(next: @escaping (T) -> Void = { _ in }, error: @escaping (E) -> Void = { _ in }, completed: @escaping () -> Void = {}) -> Disposable { self.generate(Subscriber(next: next, error: error, completed: completed)) }
    static func single(_ value: T) -> Signal<T, E> { Signal { $0.putNext(value); $0.putCompletion(); return ActionDisposable({}) } }
}
final class ValuePromise<T: Equatable> {
    var value: T
    var subscribers: [UUID: (T) -> Void] = [:]
    init(_ value: T, ignoreRepeated: Bool = false) { self.value = value }
    func set(_ value: T) { self.value = value; for callback in Array(self.subscribers.values) { callback(value) } }
    func get() -> Signal<T, NoError> {
        Signal { subscriber in
            let id = UUID(); self.subscribers[id] = subscriber.putNext; subscriber.putNext(self.value)
            return ActionDisposable { self.subscribers[id] = nil }
        }
    }
}
precedencegroup PipeRight {
    associativity: left
    higherThan: DefaultPrecedence
}
infix operator |> : PipeRight
func |> <T, U>(value: T, function: (T) -> U) -> U { function(value) }
func distinctUntilChanged<T: Equatable, E>(_ source: Signal<T, E>) -> Signal<T, E> {
    Signal { subscriber in
        var previous: T?
        return source.start(next: { if previous != $0 { previous = $0; subscriber.putNext($0) } }, error: subscriber.error, completed: subscriber.putCompletion)
    }
}
func combineLatest<A, B, E>(_ a: Signal<A, E>, _ b: Signal<B, E>) -> Signal<(A, B), E> {
    Signal { subscriber in
        var lastA: A?; var lastB: B?
        func emit() { if let a = lastA, let b = lastB { subscriber.putNext((a, b)) } }
        let da = a.start(next: { lastA = $0; emit() })
        let db = b.start(next: { lastB = $0; emit() })
        return ActionDisposable { da.dispose(); db.dispose() }
    }
}
final class Queue {
    static var pending: [() -> Void] = []
    func isCurrent() -> Bool { true }
    func async(_ action: @escaping () -> Void) { Self.pending.append(action) }
    static func drain() { while !pending.isEmpty { pending.removeFirst()() } }
}
func deliverOn<T, E>(_ queue: Queue) -> (Signal<T, E>) -> Signal<T, E> { { $0 } }
func `catch`<T, E, U>(_ transform: @escaping (E) -> Signal<T, U>) -> (Signal<T, E>) -> Signal<T, U> {
    { source in Signal { subscriber in source.start(next: subscriber.putNext, error: { _ = transform($0).start(next: subscriber.putNext, completed: subscriber.putCompletion) }, completed: subscriber.putCompletion) } }
}
final class TestClock {
    static let shared = TestClock()
    var now: Double = 0
    var timers: [SignalKitTimer] = []
    func reset() { for timer in timers { timer.invalidate() }; timers.removeAll(); now = 0 }
    func advance(_ delta: Double) {
        let target = now + delta
        while let timer = timers.filter({ !$0.invalidated && $0.due <= target }).min(by: { $0.due < $1.due }) {
            now = timer.due; timer.invalidated = true; timer.completion()
        }
        now = target
    }
}
final class SignalKitTimer {
    let interval: Double; let completion: () -> Void
    var due = Double.infinity
    var invalidated = false
    init(timeout: Double, repeat: Bool, completion: @escaping () -> Void, queue: Queue) { precondition(!`repeat`); self.interval = timeout; self.completion = completion }
    func start() { self.due = TestClock.shared.now + self.interval; TestClock.shared.timers.append(self) }
    func invalidate() { self.invalidated = true }
}
enum Api {
    enum Bool: Equatable { case boolTrue, boolFalse }
    enum functions { enum account { static func updateStatus(offline: Bool) -> Bool { offline } } }
}
final class TestActivityPipe {
    var subscribers: [UUID: () -> Void] = [:]
    func signal() -> Signal<Void, NoError> {
        Signal { subscriber in
            let id = UUID(); self.subscribers[id] = { subscriber.putNext(()) }
            return ActionDisposable { self.subscribers[id] = nil }
        }
    }
    func emit() { for callback in Array(subscribers.values) { callback() } }
}
enum ConnectionStatus: Equatable { case connecting, online }
final class Network {
    let activity = TestActivityPipe()
    let status = ValuePromise<ConnectionStatus>(.connecting)
    var connectionStatus: Signal<ConnectionStatus, NoError> { self.status.get() }
    var nagramiXOnlineActivity: Signal<Void, NoError> { self.activity.signal() }
    var requests: [(Double, Api.Bool)] = []
    var failNext = false
    var holdResponses = false
    var pending: [() -> Void] = []
    var inFlight = Set<UUID>()
    var cancelledRequests = 0
    func completeNext() { precondition(!pending.isEmpty); pending.removeFirst()() }
    func request(_ offline: Api.Bool) -> Signal<Api.Bool, MTRpcError> {
        Signal { subscriber in
            self.requests.append((TestClock.shared.now, offline))
            let id = UUID(); self.inFlight.insert(id)
            let complete: () -> Void = { [weak self] in
                guard let self, self.inFlight.remove(id) != nil else { return }
                if self.failNext { self.failNext = false; subscriber.error(MTRpcError()) }
                else { subscriber.putNext(.boolTrue); subscriber.putCompletion() }
            }
            if self.holdResponses { self.pending.append(complete) } else { complete() }
            return ActionDisposable { [weak self] in
                guard let self else { return }
                if self.inFlight.remove(id) != nil { self.cancelledRequests += 1 }
            }
        }
    }
}
func nagramiXGhostSettingsSignal() -> Signal<NagramiXGhostSettings, NoError> {
    Signal { subscriber in
        let observer = NotificationCenter.default.addObserver(forName: NagramiXPrivacySettings.changedNotification, object: nil, queue: nil) { _ in subscriber.putNext(.current) }
        subscriber.putNext(.current)
        return ActionDisposable { NotificationCenter.default.removeObserver(observer) }
    }
}

@main struct AutomaticOfflineTests {
    static func main() {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ name: String) { precondition(condition(), name); checks += 1 }
        let key = "nagramix.privacy.individual.v2", saved = UserDefaults.standard.object(forKey: "nagramix.privacy.individual.v2")
        defer { if let saved { UserDefaults.standard.set(saved, forKey: key) } else { UserDefaults.standard.removeObject(forKey: key) } }
        func settings(_ hidden: Bool) { NagramiXPrivacySettings.update { $0[.online] = hidden } }
        let clock = TestClock.shared

        settings(false)
        do {
            clock.reset(); let foreground = ValuePromise(true), network = Network()
            let manager = AccountPresenceManagerImpl(queue: Queue(), shouldKeepOnlinePresence: foreground.get(), network: network)
            check(network.requests.map { $0.1 } == [.boolFalse], "OFF preserves native foreground online")
            clock.advance(30)
            check(network.requests.count == 2 && network.requests.last?.1 == .boolFalse, "OFF preserves native 30-second refresh")
            settings(true)
            check(network.requests.last?.0 == clock.now && network.requests.last?.1 == .boolTrue, "enabling immediately requests offline with no five-second delay")
            let before = network.requests.count
            NagramiXPrivacySettings.update { $0[.storyReads].toggle() }
            check(network.requests.count == before, "unrelated privacy settings send no status")
            for _ in 0..<20 { network.activity.emit() }
            check(network.requests.count == before + 20 && network.requests.suffix(20).allSatisfy { $0.0 == clock.now && $0.1 == .boolTrue }, "every acknowledged online-inducing event immediately reasserts offline")
            check(clock.timers.allSatisfy { $0.interval == 30 }, "no five-second or other artificial-delay timer exists")
            network.status.set(.online)
            check(network.requests.last?.1 == .boolTrue && network.requests.count == before + 21, "restored connection immediately reasserts offline")
            network.status.set(.online)
            check(network.requests.count == before + 21, "repeated identical connection state cannot loop")
            network.status.set(.connecting); network.status.set(.online)
            check(network.requests.count == before + 22, "next reconnection reasserts offline again")
            let refreshed = network.requests.count; clock.advance(90)
            check(network.requests.count == refreshed + 3 && network.requests.dropFirst(refreshed).allSatisfy { $0.1 == .boolTrue }, "native refresh never restores online while hidden")
            settings(false)
            check(network.requests.last?.1 == .boolFalse, "OFF immediately restores normal foreground online")
            let disabled = network.requests.count
            network.activity.emit(); network.status.set(.connecting); network.status.set(.online)
            check(network.requests.count == disabled, "OFF disables action and reconnect enforcement")
            withExtendedLifetime(manager) {}
        }
        settings(true)
        do {
            clock.reset(); let foreground = ValuePromise(true), network = Network()
            var manager: AccountPresenceManagerImpl? = AccountPresenceManagerImpl(queue: Queue(), shouldKeepOnlinePresence: foreground.get(), network: network)
            check(network.requests.map { $0.1 } == [.boolTrue], "saved ON opens offline immediately, without sending online first")
            foreground.set(false)
            check(network.requests.count == 2 && network.requests.last?.1 == .boolTrue, "background immediately remains offline")
            let background = network.requests.count; clock.advance(60)
            check(network.requests.count == background, "background cancels foreground refreshes")
            foreground.set(true)
            check(network.requests.count == background + 1 && network.requests.last?.0 == clock.now, "foreground reasserts offline without waiting")
            weak var weakManager = manager
            manager = nil
            check(weakManager == nil && network.activity.subscribers.isEmpty && network.status.subscribers.isEmpty, "all subscriptions release the manager")
            let ended = network.requests.count; clock.advance(60); network.activity.emit(); network.status.set(.online); Queue.drain()
            check(network.requests.count == ended, "deinit cannot issue later status requests")
        }
        settings(true)
        do {
            clock.reset(); let foreground = ValuePromise(true), network = Network(), otherAccount = Network()
            network.holdResponses = true
            let manager = AccountPresenceManagerImpl(queue: Queue(), shouldKeepOnlinePresence: foreground.get(), network: network)
            check(network.requests.count == 1 && manager.isPerformingUpdate.value, "offline remains in flight until acknowledgement")
            for _ in 0..<100 { network.activity.emit() }
            network.status.set(.online)
            check(network.requests.count == 1 && network.cancelledRequests == 0 && network.inFlight.count == 1, "busy actions and reconnect never cancel or starve the first offline request")
            network.completeNext()
            check(manager.isPerformingUpdate.value, "pending trailing request keeps the native network assertion active")
            Queue.drain()
            check(network.requests.count == 2 && network.inFlight.count == 1 && network.cancelledRequests == 0, "one immediate trailing offline covers the entire pending burst")
            network.completeNext(); Queue.drain()
            check(!manager.isPerformingUpdate.value && network.requests.count == 2, "acknowledgements do not cause an offline RPC loop")
            otherAccount.activity.emit(); otherAccount.status.set(.online); Queue.drain()
            check(network.requests.count == 2, "another account cannot trigger this account's status")
            network.activity.emit(); check(network.requests.count == 3, "new action after acknowledgement immediately starts a fresh offline request")
            network.completeNext(); Queue.drain()
            withExtendedLifetime(manager) {}
        }
        settings(true)
        do {
            clock.reset(); let foreground = ValuePromise(true), network = Network()
            network.holdResponses = true
            let manager = AccountPresenceManagerImpl(queue: Queue(), shouldKeepOnlinePresence: foreground.get(), network: network)
            network.activity.emit(); network.completeNext()
            check(!Queue.pending.isEmpty, "a trailing reassertion is queued without recursion")
            settings(false)
            let disabled = network.requests.count; Queue.drain()
            check(network.requests.count == disabled && network.requests.last?.1 == .boolFalse, "OFF rejects a queued stale offline reassertion")
            network.completeNext(); Queue.drain()
            check(!manager.isPerformingUpdate.value, "ordinary online completes after disabling")
            withExtendedLifetime(manager) {}
        }
        settings(true)
        do {
            clock.reset(); let foreground = ValuePromise(true), network = Network()
            network.failNext = true
            let manager = AccountPresenceManagerImpl(queue: Queue(), shouldKeepOnlinePresence: foreground.get(), network: network)
            check(network.requests.count == 1 && !manager.isPerformingUpdate.value, "failed offline completes without sticking or an immediate retry loop")
            network.status.set(.online)
            check(network.requests.count == 2 && network.requests.last?.1 == .boolTrue, "reconnection retries offline immediately after failure")
            clock.advance(30)
            check(network.requests.count == 3 && network.requests.last?.1 == .boolTrue, "native refresh remains an offline retry fallback")
            withExtendedLifetime(manager) {}
        }
        settings(false)
        do {
            clock.reset(); let foreground = ValuePromise(true), network = Network()
            let manager = AccountPresenceManagerImpl(queue: Queue(), shouldKeepOnlinePresence: foreground.get(), network: network)
            let stale = clock.timers.last!
            settings(true)
            let hidden = network.requests.count; stale.completion()
            check(network.requests.count == hidden && network.requests.last?.1 == .boolTrue, "an old online refresh cannot undo hidden mode")
            foreground.set(false)
            let background = network.requests.count; clock.advance(60)
            check(network.requests.count == background, "background invalidates all stale refresh generations")
            withExtendedLifetime(manager) {}
        }
        for name in ["messages.sendMessage", "messages.sendMedia", "messages.sendMultiMedia", "messages.sendEncrypted", "messages.sendEncryptedFile", "messages.sendEncryptedService", "messages.sendReaction", "messages.sendPaidReaction", "messages.forwardMessages", "messages.readHistory", "messages.readMessageContents", "messages.readEncryptedHistory", "channels.readHistory", "messages.setTyping", "messages.setEncryptedTyping", "stories.readStories", "stories.sendReaction", "phone.acceptCall"] {
            check(productionRPCMayRestoreOnline(name), "real network classifier catches online-inducing request " + name)
        }
        for name in ["account.updateStatus", "messages.getHistory", "updates.getDifference", "upload.saveFilePart", "upload.getFile", "help.getConfig", "ping", "messages.getMessagesReactions"] {
            check(!productionRPCMayRestoreOnline(name), "real network classifier excludes offline/keepalive/query loops " + name)
        }
        print("PASS: \(checks) real immediate-offline presence/coalescing/reconnection/cancellation/failure checks")
    }
}
