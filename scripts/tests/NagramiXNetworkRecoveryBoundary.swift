// Substitutes only Network/MTProto at the framework boundary. The validator
// inserts the actual final native keep callback and reconnect method below.
final class RecoverySession {
    var pauses: [Bool] = []
    var paused = true
    func setPaused(_ value: Bool) { self.paused = value; self.pauses.append(value) }
}
final class Network {
    let queue = Queue(name: "network")
    let shouldKeepConnection = ValuePromise(false)
    let mainSession = RecoverySession()
    var drops = 0
    private var nagramiXKeepsMainConnection = false
    private let shouldKeepConnectionDisposable = MetaDisposable()
    let status: ValuePromise<ConnectionStatus>
    var connectionStatus: Signal<ConnectionStatus, NoError> { self.status.get() |> distinctUntilChanged }
    let nagramiXProxyStatuses = Atomic<ProxyServersStatuses?>(value: nil)
    init(_ status: ConnectionStatus) {
        self.status = ValuePromise(status)
        let queue = self.queue
        // NATIVE_KEEP_SUBSCRIPTION
    }
    func dropConnectionStatus() { self.drops += 1 }
    func publish(_ status: ConnectionStatus) { self.status.set(status); Queue.drain() }
    // NATIVE_RECONNECT_METHOD
    deinit { self.shouldKeepConnectionDisposable.dispose() }
}
