import Foundation

private let a = ProxyServerSettings(host: "primary.example", port: 443, connection: .socks5(username: nil, password: nil))
private let b = ProxyServerSettings(host: "reserve.example", port: 8443, connection: .mtp(secret: Data([1])))
private let dns = Notification.Name("NagramiXDnsSettingsChanged")
private final class Fixture {
    let path = UUID().uuidString
    let manager: AccountManager<TelegramAccountManagerTypes>
    let network = Network(.connecting(proxyAddress: a.host, proxyHasConnectionIssues: true))
    var recovery: NagramiXNetworkRecovery?
    init(keep: Bool = true, failover: Bool = true) {
        Queue.drain(); Clock.reset()
        UserDefaults.standard.set(true, forKey: "nagramix.network.proxyAutoSwitchEnabled")
        UserDefaults.standard.set(30, forKey: "nagramix.network.proxyAutoSwitchTimeout")
        NagramiXProxyVPNPolicy.set(false)
        self.manager = AccountManager(ProxySettings(enabled: true, servers: [a, b], activeServer: a, useForCalls: true))
        self.network.shouldKeepConnection.set(keep)
        self.recovery = NagramiXNetworkRecovery.attach(basePath: self.path, accountManager: self.manager, network: self.network, allowsFailover: failover)
        Queue.drain()
    }
    var monitor: ProxyServersStatuses? { self.network.nagramiXProxyStatuses.with { $0 } }
    func reserve() { self.monitor!.publish([a: .notAvailable, b: .available(0.01)]) }
    func replacement(keep: Bool = true, failover: Bool = true) -> (Network, NagramiXNetworkRecovery) {
        let network = Network(.connecting(proxyAddress: a.host, proxyHasConnectionIssues: true))
        network.shouldKeepConnection.set(keep)
        return (network, NagramiXNetworkRecovery.attach(basePath: self.path, accountManager: self.manager, network: network, allowsFailover: failover))
    }
    func close() { self.recovery?.dispose(); self.recovery = nil; Queue.drain() }
    deinit { self.close() }
}

@main struct NetworkRecoveryTests {
    static func main() {
        var checks = 0, failures = 0
        func check(_ value: @autoclosure () -> Bool, _ description: String) {
            checks += 1
            if !value() { failures += 1; print("FAIL: " + description) }
        }
        // Exactly the same runtime is attached to UnauthorizedAccount and Account.
        do {
            let f = Fixture(); f.reserve()
            check(f.monitor != nil, "login network owns a health monitor")
            Clock.advance(29.9)
            check(f.manager.automaticWrites.isEmpty, "login respects saved 30-second deadline")
            Clock.advance(0.1)
            check(f.manager.settings.activeServer == b, "login can fail over before authorization")
            let drops = f.network.drops
            NotificationCenter.default.post(name: dns, object: nil); Queue.drain()
            check(f.network.drops == drops + 1 && !f.network.mainSession.paused, "login DNS/IPv6 change reconnects active main session once")
            f.close()
        }
        // A DC change / authorization promotion retires the old account even
        // when its caller still retains it and its native final RPC can finish.
        for _ in 0..<3 {
            let f = Fixture(); f.reserve()
            let oldMonitor = f.monitor!
            f.manager.holdTransactions = true; Clock.advance(30)
            check(f.manager.pendingTransactions.count == 1, "old runtime has a queued proxy transaction")
            let (next, owner) = f.replacement()
            // Deliberately commit before any queued cleanup/start callback.
            f.manager.commitPending()
            check(f.manager.automaticWrites.isEmpty, "replaced login network cannot commit before async stop")
            check(oldMonitor.stopped && f.monitor == nil, "old monitor is detached at replacement")
            check(next.nagramiXProxyStatuses.with { $0 } != nil, "new network receives recovery ownership")
            let oldDrops = f.network.drops, newDrops = next.drops
            NotificationCenter.default.post(name: dns, object: nil); Queue.drain()
            check(f.network.drops == oldDrops && next.drops == newDrops + 1, "only current network receives DNS reconnect")
            check(!f.network.mainSession.paused, "handoff does not interrupt old native finishing requests")
            f.recovery?.dispose(); Queue.drain()
            check(next.nagramiXProxyStatuses.with { $0 } != nil, "late dispose of old owner does not unregister replacement")
            f.manager.holdTransactions = false
            next.nagramiXProxyStatuses.with { $0 }!.publish([a: .notAvailable, b: .available(0.01)])
            Clock.advance(30)
            check(f.manager.settings.activeServer == b, "new owner can still switch proxy")
            owner.dispose(); Queue.drain(); f.close()
            check(next.nagramiXProxyStatuses.with { $0 } == nil && Clock.active.isEmpty, "replacement teardown cancels monitor and deadline")
        }
        do {
            let f = Fixture()
            NotificationCenter.default.post(name: dns, object: nil)
            // Execute observer callback: schedules native reconnect, but do not
            // execute the native queue yet. Replacement must reject that work.
            Queue.runNext()
            let oldDrops = f.network.drops
            let (next, owner) = f.replacement()
            Queue.drain()
            check(f.network.drops == oldDrops, "already enqueued DNS callback checks owner at execution")
            let drops = next.drops
            NotificationCenter.default.post(name: dns, object: nil); Queue.drain()
            check(next.drops == drops + 1, "new DNS observer remains alive")
            owner.dispose(); Queue.drain(); f.close()
        }
        do {
            let f = Fixture(keep: false)
            check(f.monitor == nil && Clock.active.isEmpty, "paused login does not start proxy probes")
            NotificationCenter.default.post(name: dns, object: nil); Queue.drain()
            check(f.network.drops == 1 && f.network.mainSession.paused, "DNS change never wakes paused session")
            f.network.shouldKeepConnection.set(true); Queue.drain(); f.reserve()
            check(f.monitor != nil, "native connection demand starts login recovery")
            f.manager.holdTransactions = true; Clock.advance(30)
            f.network.shouldKeepConnection.set(false); Queue.drain(); f.manager.commitPending()
            check(f.manager.automaticWrites.isEmpty && f.monitor == nil, "native pause cancels monitor and pending proxy transaction")
            check(Clock.active.isEmpty, "paused network leaves no failover deadline")
            f.network.shouldKeepConnection.set(true); Queue.drain()
            check(f.monitor != nil, "reopening can restart recovery")
            f.close()
        }
        // The actual native keep callback and reconnect method, not replicas.
        do {
            let network = Network(.waitingForNetwork); Queue.drain()
            network.shouldKeepConnection.set(true); Queue.drain()
            network.shouldKeepConnection.set(false) // queued BEFORE reconnect
            let work = network.reconnectForNagramiXDnsChange(); Queue.drain()
            check(network.mainSession.paused && network.drops == 1, "reconnect uses latest queue-applied pause state")
            work.dispose()
            network.shouldKeepConnection.set(true); Queue.drain()
            let cancelled = network.reconnectForNagramiXDnsChange(); cancelled.dispose(); Queue.drain()
            check(network.drops == 1, "cancelled reconnect has no transport effect")
            let valid = Atomic(value: true)
            let obsolete = network.reconnectForNagramiXDnsChange(shouldApply: { valid.with { $0 } })
            _ = valid.swap(false); Queue.drain(); obsolete.dispose()
            check(network.drops == 1, "revoked lease prevents queued native restart")
        }
        do {
            let f = Fixture(failover: false)
            check(f.monitor == nil && Clock.active.isEmpty, "supplementary network never owns failover")
            NotificationCenter.default.post(name: dns, object: nil); Queue.drain()
            check(f.network.drops == 1, "supplementary DNS applies without failover")
            let (main, owner) = f.replacement()
            Queue.drain()
            check(main.nagramiXProxyStatuses.with { $0 } != nil, "main and supplementary roles do not revoke one another")
            f.close()
            let drops = main.drops
            NotificationCenter.default.post(name: dns, object: nil); Queue.drain()
            check(main.drops == drops + 1, "disposing supplementary leaves main DNS handler alive")
            owner.dispose(); Queue.drain()
        }
        do {
            let f = Fixture(); let second = Fixture()
            let drops1 = f.network.drops, drops2 = second.network.drops
            NotificationCenter.default.post(name: dns, object: nil); Queue.drain()
            check(f.network.drops == drops1 + 1 && second.network.drops == drops2 + 1, "different account directories retain independent DNS handlers")
            second.close(); f.close()
        }
        do {
            let f = Fixture(); f.reserve()
            NagramiXProxyVPNPolicy.set(true); Clock.advance(90)
            check(f.manager.automaticWrites.isEmpty, "VPN bypass prevents login auto-switch")
            NagramiXProxyVPNPolicy.set(false)
            f.network.publish(.waitingForNetwork); Clock.advance(90)
            check(f.manager.automaticWrites.isEmpty && Clock.active.isEmpty, "no route does not cycle login proxies")
            f.network.publish(.online(proxyAddress: a.host)); Clock.advance(90)
            check(f.manager.automaticWrites.isEmpty, "ONLINE still outranks failed ping after lifecycle change")
            f.close()
        }
        do {
            let f = Fixture()
            var owners: [NagramiXNetworkRecovery] = []
            var networks: [Network] = []
            for _ in 0..<25 {
                let (network, owner) = f.replacement()
                owners.append(owner); networks.append(network)
            }
            Queue.drain()
            check(networks.dropLast().allSatisfy { $0.nagramiXProxyStatuses.with { $0 } == nil }, "rapid replacements never start obsolete monitors")
            check(networks.last!.nagramiXProxyStatuses.with { $0 } != nil, "last rapid replacement owns recovery")
            NotificationCenter.default.post(name: dns, object: nil); Queue.drain()
            check(networks.dropLast().allSatisfy { $0.drops == 0 } && networks.last!.drops == 1, "rapid replacement leaves exactly one observer")
            for owner in owners { owner.dispose(); owner.dispose() }; Queue.drain(); f.close()
            check(Clock.active.isEmpty, "repeated disposal is idempotent")
        }
        do {
            let f = Fixture()
            weak var weakOwner = f.recovery
            f.recovery = nil; Queue.drain()
            check(weakOwner == nil && f.monitor == nil, "deinit fallback releases helper and stops monitor without resurrection")
            let drops = f.network.drops
            NotificationCenter.default.post(name: dns, object: nil); Queue.drain()
            check(f.network.drops == drops, "deinit fallback removes observer")
            f.close()
        }
        check(Clock.active.isEmpty, "suite leaves no active deadlines")
        print("Network recovery checks: \(checks), failures: \(failures)")
        exit(failures == 0 ? 0 : 1)
    }
}
