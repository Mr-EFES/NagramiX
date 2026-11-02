private final class ProxyServerItemContext {
    private var disposable: Disposable?

    init(queue: Queue, context: MTContext, datacenterId: Int, server: ProxyServerSettings, updated: @escaping (ProxyServerStatus) -> Void) {
        self.disposable = (Signal<ProxyServerStatus, NoError> { subscriber in
            let disposable = MTProxyConnectivity.pingProxy(with: context, datacenterId: datacenterId, settings: server.mtProxySettings).start(next: { value in
                if let value = value as? MTProxyConnectivityStatus {
                    subscriber.putNext((value.reachable && value.roundTripTime.isFinite && value.roundTripTime >= 0.0 && value.roundTripTime <= 60.0) ? .available(value.roundTripTime) : .notAvailable)
                    subscriber.putCompletion()
                }
            }, error: { _ in
                subscriber.putNext(.notAvailable)
                subscriber.putCompletion()
            }, completed: {
                subscriber.putNext(.notAvailable)
                subscriber.putCompletion()
            })
            return ActionDisposable { disposable?.dispose() }
        }
        |> take(1)
        |> timeout(12.0, queue: queue, alternate: .single(.notAvailable))
        |> deliverOn(queue)).start(next: updated)
    }

    deinit {
        self.disposable?.dispose()
    }
}

final class ProxyServersStatusesImpl {
    private let queue: Queue
    private let context: MTContext
    private let datacenterId: Int
    private var contexts: [ProxyServerSettings: ProxyServerItemContext] = [:]
    private var contextIds: [ProxyServerSettings: UInt64] = [:]
    private var nextContextId: UInt64 = 0
    private var serversDisposable: Disposable?
    private var refreshTimer: SwiftSignalKit.Timer?
    private var servers: [ProxyServerSettings] = []
    private var activeServer: ProxyServerSettings?
    private var pending: [ProxyServerSettings] = []
    private var refreshEnabled = false
    private var networkAvailable = false
    private var inForeground = true
    private var manualPass = false
    private var connectionIsOnline = false
    private var lastPassStarted: TimeInterval = -Double.greatestFiniteMagnitude
    private var foregroundObservers: [NSObjectProtocol] = []
    private var checkedAt: [ProxyServerSettings: TimeInterval] = [:]
    private var currentValues: [ProxyServerSettings: ProxyServerStatus] = [:] {
        didSet { self.values.set(.single(self.currentValues)) }
    }
    let values = Promise<[ProxyServerSettings: ProxyServerStatus]>([:])

    init(queue: Queue, network: Network, servers: Signal<[ProxyServerSettings], NoError>, refreshEnabled: Signal<Bool, NoError>, activeServer: Signal<ProxyServerSettings?, NoError>) {
        self.queue = queue
        self.context = network.context
        self.datacenterId = network.datacenterId
        // Observe application lifecycle without adding a UIKit dependency to
        // TelegramCore; these are UIKit's public notification names.
        for (name, foreground) in [("UIApplicationDidEnterBackgroundNotification", false), ("UIApplicationWillEnterForegroundNotification", true)] {
            self.foregroundObservers.append(NotificationCenter.default.addObserver(forName: Notification.Name(name), object: nil, queue: nil, using: { [weak self] _ in
                queue.async {
                    guard let self else { return }
                    self.inForeground = foreground
                    if foreground {
                        self.refreshIfNeeded()
                    } else {
                        self.manualPass = false
                        self.lastPassStarted = -Double.greatestFiniteMagnitude
                        self.cancelChecks()
                    }
                }
            }))
        }
        self.serversDisposable = (combineLatest(servers, refreshEnabled, network.connectionStatus, activeServer)
        |> deliverOn(queue)).start(next: { [weak self] servers, refreshEnabled, connectionStatus, activeServer in
            guard let self else { return }
            let previousServers = self.servers
            let previousActive = self.activeServer
            self.activeServer = activeServer
            let wasAvailable = self.networkAvailable
            let wasRefreshing = self.refreshEnabled
            let wasOnline = self.connectionIsOnline
            if case .online = connectionStatus { self.connectionIsOnline = true } else { self.connectionIsOnline = false }
            var seen = Set<ProxyServerSettings>()
            self.servers = servers.filter { seen.insert($0).inserted }
            self.refreshEnabled = refreshEnabled
            if case .waitingForNetwork = connectionStatus {
                self.networkAvailable = false
            } else {
                self.networkAvailable = true
            }
            let valid = Set(self.servers)
            for server in Array(self.contexts.keys) where !valid.contains(server) {
                self.contexts.removeValue(forKey: server)
                self.contextIds.removeValue(forKey: server)
            }
            self.pending.removeAll { !valid.contains($0) }
            self.checkedAt = self.checkedAt.filter { valid.contains($0.key) }
            var values = self.currentValues.filter { valid.contains($0.key) }
            for server in self.servers where values[server] == nil { values[server] = refreshEnabled ? .checking : .notAvailable }
            self.currentValues = values
            if !self.networkAvailable || !self.inForeground || (!refreshEnabled && !self.manualPass) {
                self.cancelChecks()
                if !self.networkAvailable { self.checkedAt.removeAll() }
                return
            }
            if !wasAvailable || (!wasRefreshing && refreshEnabled) || previousActive != activeServer {
                self.recheckAll(servers: self.servers, showChecking: false)
            } else {
                for server in self.servers where !previousServers.contains(server) {
                    self.pending.append(server)
                }
                self.startPending()
            }
            if wasOnline && !self.connectionIsOnline {
                self.refreshTimer?.invalidate()
                self.refreshTimer = nil
                self.refreshIfNeeded()
            }
        })
    }

    deinit {
        self.serversDisposable?.dispose()
        self.refreshTimer?.invalidate()
        for observer in self.foregroundObservers { NotificationCenter.default.removeObserver(observer) }
    }

    func stop() {
        assert(self.queue.isCurrent())
        self.serversDisposable?.dispose()
        self.serversDisposable = nil
        self.refreshEnabled = false
        self.networkAvailable = false
        for observer in self.foregroundObservers { NotificationCenter.default.removeObserver(observer) }
        self.foregroundObservers.removeAll()
        self.cancelChecks()
    }

    private func cancelChecks() {
        self.contexts.removeAll()
        self.contextIds.removeAll()
        self.pending.removeAll()
        var values = self.currentValues
        for (server, value) in values {
            if case .checking = value { values[server] = .notAvailable }
        }
        self.currentValues = values
        self.refreshTimer?.invalidate()
        self.refreshTimer = nil
    }

    func recheckAll(servers: [ProxyServerSettings], showChecking: Bool = true) {
        assert(self.queue.isCurrent())
        self.cancelChecks()
        self.manualPass = showChecking
        self.lastPassStarted = ProcessInfo.processInfo.systemUptime
        var seen = Set<ProxyServerSettings>()
        let servers = servers.filter { self.servers.contains($0) && seen.insert($0).inserted }
        if showChecking {
            var values = self.currentValues
            for server in servers {
                values[server] = .checking
                self.checkedAt.removeValue(forKey: server)
            }
            self.currentValues = values
        }
        if self.networkAvailable && self.inForeground && (self.refreshEnabled || self.manualPass) {
            // Check the selected server first, before the 15-second deadline.
            self.pending = servers.filter { $0 == self.activeServer } + servers.filter { $0 != self.activeServer }
        } else if showChecking {
            var values = self.currentValues
            for server in servers { values[server] = .notAvailable }
            self.currentValues = values
        }
        self.startPending()
    }

    private func startPending() {
        assert(self.queue.isCurrent())
        // Two native probes at most, regardless of saved-list length.
        while self.networkAvailable && self.inForeground && (self.refreshEnabled || self.manualPass) && self.contexts.count < 2 && !self.pending.isEmpty {
            let server = self.pending.removeFirst()
            self.nextContextId &+= 1
            let contextId = self.nextContextId
            self.contextIds[server] = contextId
            let queue = self.queue
            self.contexts[server] = ProxyServerItemContext(queue: queue, context: self.context, datacenterId: self.datacenterId, server: server, updated: { [weak self] value in
                // Also defers synchronous completion until the context is stored.
                queue.async {
                    guard let self, self.contextIds[server] == contextId else { return }
                    self.contexts.removeValue(forKey: server)
                    self.contextIds.removeValue(forKey: server)
                    self.checkedAt[server] = ProcessInfo.processInfo.systemUptime
                    self.currentValues[server] = value
                    self.startPending()
                }
            })
        }
        if self.pending.isEmpty && self.contexts.isEmpty { self.manualPass = false }
        if self.pending.isEmpty && self.contexts.isEmpty && self.refreshEnabled && self.networkAvailable && self.inForeground && !self.servers.isEmpty && self.refreshTimer == nil {
            // Two minutes while connected, faster recovery while connecting.
            let timer = SwiftSignalKit.Timer(timeout: self.connectionIsOnline ? 120.0 : 30.0, repeat: false, completion: { [weak self] in
                guard let self else { return }
                self.refreshTimer = nil
                self.recheckAll(servers: self.servers, showChecking: false)
            }, queue: self.queue)
            self.refreshTimer = timer
            timer.start()
        }
    }

    func refreshIfNeeded() {
        assert(self.queue.isCurrent())
        guard self.refreshEnabled, self.networkAvailable, self.inForeground,
              self.contexts.isEmpty, self.pending.isEmpty else { return }
        if ProcessInfo.processInfo.systemUptime - self.lastPassStarted >= 30.0 {
            self.recheckAll(servers: self.servers, showChecking: false)
        } else {
            self.startPending()
        }
    }

    func availableServers(maxAge: Double) -> Set<ProxyServerSettings> {
        assert(self.queue.isCurrent())
        let now = ProcessInfo.processInfo.systemUptime
        return Set(self.servers.filter { server in
            guard self.networkAvailable, let checkedAt = self.checkedAt[server], now - checkedAt <= maxAge,
                  let status = self.currentValues[server], case .available = status else { return false }
            return true
        })
    }

    func markUnavailable(_ server: ProxyServerSettings) {
        assert(self.queue.isCurrent())
        self.contexts.removeValue(forKey: server)
        self.contextIds.removeValue(forKey: server)
        self.pending.removeAll { $0 == server }
        self.checkedAt.removeValue(forKey: server)
        if self.currentValues[server] != nil { self.currentValues[server] = .notAvailable }
        self.startPending()
    }

    func recordAvailable(_ server: ProxyServerSettings, roundTripTime: Double) {
        assert(self.queue.isCurrent())
        guard self.servers.contains(server), self.networkAvailable, roundTripTime.isFinite,
              roundTripTime >= 0.0 && roundTripTime <= 60.0 else { return }
        self.contexts.removeValue(forKey: server)
        self.contextIds.removeValue(forKey: server)
        self.pending.removeAll { $0 == server }
        self.checkedAt[server] = ProcessInfo.processInfo.systemUptime
        self.currentValues[server] = .available(roundTripTime)
        self.startPending()
    }
}

