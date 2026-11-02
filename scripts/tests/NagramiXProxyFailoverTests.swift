import Foundation

private let a = ProxyServerSettings(host: "proxy.example", port: 443, connection: .socks5(username: nil, password: nil))
private let b = ProxyServerSettings(host: "reserve.example", port: 8443, connection: .mtp(secret: Data([1])))
private let sameHost = ProxyServerSettings(host: a.host, port: 1080, connection: .socks5(username: "test", password: "test"))

private final class Fixture {
    let controller: NagramiXProxyFailoverController
    let manager: AccountManager<TelegramAccountManagerTypes>
    let network: Network
    var monitor: ProxyServersStatuses { self.network.nagramiXProxyStatuses.with { $0 }! }
    private var closed = false
    init(status: ConnectionStatus = .online(proxyAddress: a.host), servers: [ProxyServerSettings] = [a, b], enabled: Bool = true, auto: Bool = true, timeout: Int? = nil) {
        Clock.reset()
        let defaults = UserDefaults.standard
        for key in ["nagramix.network.proxyAutoSwitchEnabled", "nagramix.network.proxyAutoSwitchTimeout", "nagramix.network.avoidProxyWithVPN"] { defaults.removeObject(forKey: key) }
        defaults.set(auto, forKey: "nagramix.network.proxyAutoSwitchEnabled")
        defaults.set(false, forKey: "nagramix.network.avoidProxyWithVPN")
        if let timeout { defaults.set(timeout, forKey: "nagramix.network.proxyAutoSwitchTimeout") }
        NagramiXProxyVPNPolicy.set(false)
        self.controller = NagramiXProxyFailoverController()
        self.manager = AccountManager(ProxySettings(enabled: enabled, servers: servers, activeServer: servers.first, useForCalls: true))
        self.network = Network(status)
        self.controller.start(accountManager: self.manager, network: self.network)
        Queue.drain()
    }
    func checking() { self.network.publish(.connecting(proxyAddress: self.manager.settings.activeServer?.host, proxyHasConnectionIssues: true)) }
    func manual(_ server: ProxyServerSettings) {
        NotificationCenter.default.post(name: Notification.Name("NagramiXProxySelectionRequested"), object: nil)
        var settings = self.manager.settings; settings.activeServer = server; self.manager.publish(settings); Queue.drain()
    }
    func close() {
        guard !self.closed else { return }; self.closed = true
        self.controller.stop(); Queue.drain()
    }
    deinit { self.close() }
}

@main struct ProxyFailoverTests {
    static func main() {
        var checks = 0
        var failures = 0
        func check(_ value: @autoclosure () -> Bool, _ description: String) {
            checks += 1
            if !value() { failures += 1; print("FAIL: " + description) }
        }
        func run(_ action: (Fixture) -> Void) { let f = Fixture(); action(f); f.close() }
        // The regression that used to arm a deadline and disconnect ONLINE.
        run { f in
            check(Clock.active.isEmpty, "ONLINE with no ping result does not arm a failover")
            f.monitor.publish([a: .notAvailable, b: .available(0.05)])
            Clock.advance(90)
            check(f.manager.settings.activeServer == a && f.manager.automaticWrites.isEmpty, "failed independent ping must not switch a live connection")
            check(Clock.active.isEmpty, "failed ping cannot leave a deadline armed for ONLINE")
        }
        if CommandLine.arguments.contains("--regression-only") {
            print("Regression checks: \(checks), failures: \(failures)")
            exit(failures == 0 ? 0 : 1)
        }
        for state in [ProxyServerStatus.checking, .notAvailable, .available(0.01)] {
            let addresses: [String?] = [a.host, b.host, nil]
            for address in addresses {
                let f = Fixture(status: .online(proxyAddress: address))
                f.monitor.publish([a: state, b: .available(0.02)])
                Clock.advance(65)
                check(f.manager.automaticWrites.isEmpty, "probe/address labels are not a reason to disconnect ONLINE")
                check(Clock.active.isEmpty, "ONLINE never creates a probe-dependent timer")
                f.close()
            }
        }
        // Native connection failures still use the user's one continuous deadline.
        for timeout in [15, 30, 60] {
            let f = Fixture(timeout: timeout)
            f.monitor.publish([a: .notAvailable, b: .available(0.05)])
            f.checking()
            check(Clock.active.count == 1, "one native failure deadline")
            Clock.advance(Double(timeout) - 1)
            check(f.manager.settings.activeServer == a, "no early reserve switch")
            f.network.publish(.updating(proxyAddress: a.host))
            f.monitor.publish([a: .checking, b: .available(0.05)])
            Clock.advance(1)
            check(f.manager.settings.activeServer == b && f.manager.automaticWrites.count == 1, "native failure switches to checked reserve at original timeout")
            f.network.publish(.online(proxyAddress: b.host))
            f.monitor.publish([a: .available(0.1), b: .notAvailable])
            Clock.advance(Double(timeout) * 2)
            check(f.manager.settings.activeServer == b && f.manager.automaticWrites.count == 1, "recovered reserve remains selected even when its ping fails")
            check(f.manager.settings.useForCalls, "call-proxy preference retained")
            f.close()
        }
        run { f in
            check(NagramiXProxyPreferences.autoSwitchTimeout == 30, "absent interval remains 30 seconds")
            f.monitor.publish([b: .available(0.01)]); f.checking(); Clock.advance(29)
            f.network.publish(.online(proxyAddress: a.host)); Clock.advance(40)
            check(f.manager.automaticWrites.isEmpty, "recovery before deadline cancels switch")
        }
        run { f in
            f.monitor.publish([a: .notAvailable, b: .notAvailable]); f.checking(); Clock.advance(30)
            check(f.manager.automaticWrites.isEmpty && f.monitor.refreshes > 0, "no unchecked reserve is selected")
            f.monitor.publish([a: .notAvailable, b: .available(0.05)])
            check(f.manager.settings.activeServer == b, "a later verified reserve completes failover without another full deadline")
        }
        run { f in
            f.monitor.publish([b: .available(0.05)]); f.checking(); Clock.advance(30)
            f.network.publish(.connecting(proxyAddress: b.host, proxyHasConnectionIssues: true))
            f.monitor.publish([a: .available(0.02), b: .notAvailable]); Clock.advance(30)
            check(f.manager.settings.activeServer == a && f.manager.automaticWrites.count == 2, "failed reserve retries another checked server after the next deadline")
        }
        // Queued native/health/timer/transaction events cannot override recovery.
        run { f in
            f.monitor.publish([b: .available(0.05)]); f.checking()
            let expired = Clock.active.first
            Clock.advance(10); f.network.publish(.online(proxyAddress: a.host))
            expired?.lateCallback(); Queue.drain()
            check(f.manager.automaticWrites.isEmpty, "late cancelled timer cannot switch recovered connection")
        }
        for replacement in [b, sameHost] {
            let f = Fixture(servers: [a, replacement])
            f.manager.holdTransactions = true
            f.monitor.publish([replacement: .available(0.05)]); f.checking(); Clock.advance(30)
            check(f.manager.pendingTransactions.count == 1, "deferred failover transaction prepared")
            f.network.publish(.online(proxyAddress: a.host)); f.manager.commitPending()
            check(f.manager.settings.activeServer == a && f.manager.automaticWrites.isEmpty, "recovery cancels queued switch even for same hostname/different port")
            f.close()
        }
        for replacement in [b, sameHost] {
            let f = Fixture(servers: [a, replacement])
            f.monitor.publish([replacement: .available(0.05)]); f.checking()
            let oldTimer = Clock.active.first
            Clock.advance(5); f.manual(replacement)
            oldTimer?.lateCallback(); Queue.drain()
            check(f.manager.settings.activeServer == replacement && f.manager.automaticWrites.isEmpty, "manual full server selection outranks stale deadline")
            f.network.publish(.online(proxyAddress: a.host))
            Clock.advance(40)
            check(f.manager.settings.activeServer == replacement && f.manager.automaticWrites.isEmpty, "old ONLINE never selects a different proxy")
            f.network.publish(.connecting(proxyAddress: replacement.host, proxyHasConnectionIssues: true))
            f.monitor.publish([a: .available(0.02), replacement: .notAvailable]); Clock.advance(30)
            check(f.manager.settings.activeServer == a, "subsequent native failure of manually selected server still triggers failover")
            f.close()
        }
        run { f in
            f.manager.holdTransactions = true; f.monitor.publish([b: .available(0.05)])
            f.checking(); Clock.advance(30); f.manual(b); f.manager.commitPending()
            check(f.manager.settings.activeServer == b && f.manager.automaticWrites.isEmpty, "queued automatic write cannot overwrite manual choice")
        }
        run { f in
            f.manager.holdTransactions = true; f.monitor.publish([b: .available(0.05)])
            f.checking(); Clock.advance(30)
            var settings = f.manager.settings; settings.servers = [a]; f.manager.publish(settings); Queue.drain(); f.manager.commitPending()
            check(f.manager.settings.activeServer == a && f.manager.automaticWrites.isEmpty, "deleted reserve cannot be applied by queued transaction")
        }
        for reason in ["auto", "proxy", "vpn", "background", "network", "stop"] {
            let f = Fixture(); f.manager.holdTransactions = true
            f.monitor.publish([b: .available(0.05)]); f.checking(); Clock.advance(30)
            switch reason {
            case "auto": NagramiXProxyPreferences.setAutoSwitch(false); Queue.drain()
            case "proxy": var value = f.manager.settings; value.enabled = false; f.manager.publish(value); Queue.drain()
            case "vpn": NagramiXProxyVPNPolicy.set(true)
            case "background": NotificationCenter.default.post(name: Notification.Name("UIApplicationDidEnterBackgroundNotification"), object: nil); Queue.drain()
            case "network": f.network.publish(.waitingForNetwork)
            default: f.close()
            }
            f.manager.commitPending(); Clock.advance(65)
            check(f.manager.automaticWrites.isEmpty, "queued transaction cancelled for " + reason)
            check(Clock.active.isEmpty, "no timer remains for " + reason)
            f.close()
        }
        for reason in ["auto", "proxy", "vpn", "background", "network"] {
            let f = Fixture(); f.monitor.publish([b: .available(0.05)]); f.checking(); Clock.advance(5)
            switch reason {
            case "auto": NagramiXProxyPreferences.setAutoSwitch(false); Queue.drain(); Clock.advance(40); NagramiXProxyPreferences.setAutoSwitch(true); Queue.drain()
            case "proxy": var value = f.manager.settings; value.enabled = false; f.manager.publish(value); Queue.drain(); Clock.advance(40); value.enabled = true; f.manager.publish(value); Queue.drain()
            case "vpn": NagramiXProxyVPNPolicy.set(true); Clock.advance(40); NagramiXProxyVPNPolicy.set(false)
            case "background": NotificationCenter.default.post(name: Notification.Name("UIApplicationDidEnterBackgroundNotification"), object: nil); Queue.drain(); Clock.advance(40); NotificationCenter.default.post(name: Notification.Name("UIApplicationWillEnterForegroundNotification"), object: nil); Queue.drain()
            default: f.network.publish(.waitingForNetwork); Clock.advance(40); f.checking()
            }
            check(f.manager.automaticWrites.isEmpty, "disabled period never switches for " + reason)
            Clock.advance(29); check(f.manager.settings.activeServer == a, "resume restarts full deadline for " + reason)
            Clock.advance(1); check(f.manager.settings.activeServer == b, "failover resumes for " + reason)
            f.close()
        }
        for servers in [[a], [a, a]] {
            let f = Fixture(status: .connecting(proxyAddress: a.host, proxyHasConnectionIssues: true), servers: servers)
            Clock.advance(120)
            check(f.manager.automaticWrites.isEmpty && Clock.active.isEmpty, "one unique server never cycles")
            f.close()
        }
        run { f in
            f.monitor.publish([b: .available(0.05)]); f.checking(); Clock.advance(10)
            UserDefaults.standard.set(60, forKey: "nagramix.network.proxyAutoSwitchTimeout")
            NotificationCenter.default.post(name: Notification.Name("NagramiXSettingsChanged"), object: nil); Queue.drain()
            Clock.advance(59); check(f.manager.settings.activeServer == a, "changed interval restarts the configured deadline")
            Clock.advance(1); check(f.manager.settings.activeServer == b, "saved 60-second interval applied")
        }
        run { f in
            f.monitor.publish([b: .available(0.05)]); f.checking(); Clock.advance(20)
            NagramiXProxyPreferences.setPreferIPv6(true); Queue.drain(); Clock.advance(10)
            check(f.manager.settings.activeServer == b, "unrelated preference notification does not reset failure deadline")
            check(NagramiXProxyPreferences.preferIPv6, "failover preserves saved IPv6 choice")
        }
        print("PASS checks: \(checks); failures: \(failures); real failover controller, virtual time/transactions/network boundaries")
        exit(failures == 0 ? 0 : 1)
    }
}
