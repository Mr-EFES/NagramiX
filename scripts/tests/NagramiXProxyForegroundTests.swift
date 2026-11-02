import Foundation

@main struct ProxyForegroundTests {
    static func main() {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ message: String) {
            checks += 1
            precondition(condition(), message)
        }
        let a = ProxyServerSettings(host: "a.example", port: 443, connection: .socks5(username: nil, password: nil))
        let b = ProxyServerSettings(host: "b.example", port: 443, connection: .socks5(username: nil, password: nil))
        func defaults() {
            Clock.reset()
            UIApplication.shared.applicationState = .active
            UserDefaults.standard.set(true, forKey: "nagramix.network.proxyAutoSwitchEnabled")
            UserDefaults.standard.set(15, forKey: "nagramix.network.proxyAutoSwitchTimeout")
            UserDefaults.standard.set(false, forKey: "nagramix.network.avoidProxyWithVPN")
            NagramiXProxyVPNPolicy.set(false)
        }
        func manager() -> AccountManager<TelegramAccountManagerTypes> {
            AccountManager(ProxySettings(enabled: true, servers: [a, b], activeServer: a, useForCalls: false))
        }
        func event(_ state: UIApplication.State) {
            UIApplication.shared.applicationState = state
            NotificationCenter.default.post(name: Notification.Name(state == .background
                ? "UIApplicationDidEnterBackgroundNotification" : "UIApplicationWillEnterForegroundNotification"), object: nil)
            Queue.drain()
        }
        func fail(_ network: Network) {
            network.nagramiXProxyStatuses.with { $0 }!.publish([a: .notAvailable, b: .available(0.01)])
            network.publish(.connecting(proxyAddress: a.host, proxyHasConnectionIssues: true))
        }
        for stoppedForeground in [true, false] {
            defaults()
            let manager = manager(), network = Network(.online(proxyAddress: a.host))
            let controller = NagramiXProxyFailoverController()
            controller.start(accountManager: manager, network: network); Queue.drain()
            event(.background)
            controller.stop(); Queue.drain()
            if stoppedForeground { event(.active) }
            controller.start(accountManager: manager, network: network); Queue.drain()
            fail(network); Clock.advance(90)
            check(manager.settings.activeServer == (stoppedForeground ? b : a),
                  "restart must sample current state, including foreground missed while stopped")
            if !stoppedForeground {
                check(Clock.active.isEmpty, "restart in background must not arm failover")
                event(.inactive); Clock.advance(15)
                check(manager.settings.activeServer == b, "foreground transition rearms reserve selection")
            }
            controller.stop(); Queue.drain()
        }
        defaults()
        do {
            UIApplication.shared.applicationState = .background
            let manager = manager(), network = Network(.online(proxyAddress: a.host))
            let controller = NagramiXProxyFailoverController()
            controller.start(accountManager: manager, network: network); Queue.drain()
            fail(network); Clock.advance(90)
            check(manager.automaticWrites.isEmpty && Clock.active.isEmpty, "cold background start stays inactive")
            event(.active); Clock.advance(15)
            check(manager.settings.activeServer == b, "cold background controller recovers on foreground")
            controller.stop(); Queue.drain()
        }
        defaults()
        do {
            let manager = manager(), network = Network(.online(proxyAddress: a.host))
            let controller = NagramiXProxyFailoverController()
            controller.start(accountManager: manager, network: network)
            Queue.drain(excludingMain: true)
            network.nagramiXProxyStatuses.with { $0 }!.values = [b: .available(0.01)]
            network.status.set(.connecting(proxyAddress: a.host, proxyHasConnectionIssues: true))
            Queue.drain(excludingMain: true)
            check(Clock.active.isEmpty, "do not assume foreground before UIKit snapshot arrives")
            // Retire the first run with its snapshot still on the main queue.
            controller.stop(); controller.start(accountManager: manager, network: network)
            Queue.drain(excludingMain: true)
            network.nagramiXProxyStatuses.with { $0 }!.values = [b: .available(0.01)]
            Queue.drain(excludingMain: true)
            check(Queue.runNext(named: "main"), "old foreground snapshot exists")
            Queue.drain(excludingMain: true)
            check(Clock.active.isEmpty, "retired snapshot cannot enable replacement run")
            check(Queue.runNext(named: "main"), "replacement foreground snapshot exists")
            Queue.drain(excludingMain: true)
            check(!Clock.active.isEmpty, "current snapshot enables replacement")
            Clock.advance(15)
            check(manager.settings.activeServer == b, "replacement still selects reserve")
            controller.stop(); Queue.drain()
        }
        defaults()
        do {
            let manager = manager(), network = Network(.online(proxyAddress: a.host))
            let controller = NagramiXProxyFailoverController()
            var current = true
            controller.start(accountManager: manager, network: network, isCurrentNetwork: { current })
            Queue.drain(excludingMain: true)
            current = false
            Queue.drain()
            fail(network); Clock.advance(90)
            check(manager.automaticWrites.isEmpty && Clock.active.isEmpty, "snapshot cannot restore a revoked network lease")
            controller.stop(); Queue.drain()
        }
        defaults()
        do {
            let manager = manager(), network = Network(.online(proxyAddress: a.host))
            let controller = NagramiXProxyFailoverController()
            controller.start(accountManager: manager, network: network)
            Queue.drain(excludingMain: true)
            check(Queue.runNext(named: "main"), "capture active snapshot")
            UIApplication.shared.applicationState = .background
            NotificationCenter.default.post(name: Notification.Name("UIApplicationDidEnterBackgroundNotification"), object: nil)
            Queue.drain()
            fail(network); Clock.advance(90)
            check(manager.automaticWrites.isEmpty && Clock.active.isEmpty, "newer background event outranks the snapshot")
            event(.active); Clock.advance(15)
            check(manager.settings.activeServer == b, "subsequent foreground event starts working failover")
            controller.stop(); Queue.drain()
        }
        print("PASS: \(checks) current-foreground/restart/stale-snapshot checks; full production controller, UIKit/network boundaries")
    }
}
