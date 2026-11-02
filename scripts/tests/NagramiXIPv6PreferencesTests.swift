import Foundation

final class Notifications: @unchecked Sendable {
    private let lock = NSLock(); private var storage: [String] = []
    func append(_ value: String) { lock.lock(); storage.append(value); lock.unlock() }
    var values: [String] { lock.lock(); defer { lock.unlock() }; return storage }
}
@main struct IPv6PreferencesTests {
    static func main() {
        let defaults = UserDefaults.standard
        let ipv6 = "nagramix.network.preferIPv6", auto = "nagramix.network.proxyAutoSwitchEnabled", timeout = "nagramix.network.proxyAutoSwitchTimeout", vpn = "nagramix.network.avoidProxyWithVPN", dns = "nagramix.network.dnsProvider"
        if CommandLine.arguments.count > 1 {
            let command = CommandLine.arguments[1], enabled = CommandLine.arguments[2] == "true"
            if command == "set" { NagramiXProxyPreferences.setPreferIPv6(enabled); _ = defaults.synchronize() }
            else {
                precondition(NagramiXProxyPreferences.preferIPv6 == enabled, "saved IPv6 setting survives cold launch")
                if command == "fresh" { precondition(defaults.object(forKey:ipv6) == nil, "fresh getter never writes synthetic OFF") }
            }
            print("PASS cold " + command + " " + String(enabled)); return
        }
        let keys = [ipv6,auto,timeout,vpn,dns]
        keys.forEach(defaults.removeObject(forKey:))
        defer { keys.forEach(defaults.removeObject(forKey:)); _ = defaults.synchronize() }
        var count = 0
        func check(_ value: @autoclosure () -> Bool, _ message: String) { precondition(value(),message); count += 1 }
        check(!NagramiXProxyPreferences.preferIPv6 && defaults.object(forKey:ipv6) == nil, "fresh OFF, read only")
        NagramiXProxyPreferences.initializeIfNeeded(proxyEnabled:false,serverCount:0)
        check(defaults.object(forKey:ipv6) == nil, "opening empty proxy list does not change default")
        NagramiXProxyPreferences.initializeIfNeeded(proxyEnabled:true,serverCount:1)
        check(!NagramiXProxyPreferences.preferIPv6 && defaults.object(forKey:ipv6) == nil, "adding first proxy does not enable IPv6")
        check(NagramiXProxyPreferences.autoSwitchEnabled && NagramiXProxyPreferences.autoSwitchTimeout == 30, "existing first-proxy defaults retained")
        let events = Notifications()
        let changed = NotificationCenter.default.addObserver(forName:NagramiXProxyPreferences.changedNotification,object:nil,queue:nil) { notification in events.append(notification.name.rawValue) }
        let reconnect = NotificationCenter.default.addObserver(forName:Notification.Name("NagramiXDnsSettingsChanged"),object:nil,queue:nil) { notification in events.append(notification.name.rawValue) }
        defer { NotificationCenter.default.removeObserver(changed); NotificationCenter.default.removeObserver(reconnect) }
        for enabled in [false,true,false,true] {
            let start = events.values.count
            NagramiXProxyPreferences.setPreferIPv6(enabled)
            check(NagramiXProxyPreferences.preferIPv6 == enabled, "explicit choice retained")
            check(Array(events.values.dropFirst(start)) == ["NagramiXSettingsChanged","NagramiXDnsSettingsChanged"], "refresh proxy row then reuse native per-account reconnect")
            defaults.set(false,forKey:auto); defaults.set(15,forKey:timeout); defaults.set(false,forKey:vpn); defaults.set(0,forKey:dns)
            NagramiXProxyPreferences.initializeIfNeeded(proxyEnabled:true,serverCount:2)
            check(NagramiXProxyPreferences.preferIPv6 == enabled, "proxy reactivation preserves saved IPv6 choice")
            check(!NagramiXProxyPreferences.autoSwitchEnabled && NagramiXProxyPreferences.autoSwitchTimeout == 15 && !defaults.bool(forKey:vpn) && defaults.integer(forKey:dns) == 0, "IPv6 does not overwrite DNS/auto-switch/timeout/VPN user settings")
            NagramiXProxyPreferences.setAutoSwitch(true); NagramiXProxyPreferences.setAvoidVPN(true)
            check(NagramiXProxyPreferences.preferIPv6 == enabled, "other proxy switches do not alter IPv6")
        }
        print("PASS: \(count) actual Swift proxy preference/reconnect/default checks")
    }
}
