import Foundation

@main struct PrivacyPolicyTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ name: String) { precondition(value(), name); checks += 1 }
        for mode in NagramiXReadMode.allCases {
            for mask in 0..<32 {
                var value = NagramiXPrivacySettings(readMode: mode)
                for (index, option) in NagramiXPrivacySettings.Option.allCases.enumerated() { value[option] = mask & (1 << index) != 0 }
                check(value.hidesMessageReads == (mode == .local || mask & 8 != 0), "local reading or action reading hides automatic receipts")
                check(value.hidesStoryReads == (mask & 1 != 0), "story reads have their own switch")
                check(value.hidesOnline == (mask & 2 != 0), "online has its own switch")
                check(value.hidesTyping == (mask & 4 != 0), "typing has its own switch")
                check(value.automaticOffline == (mask & 2 != 0), "the online switch also enables delayed automatic offline")
                check(value.readsOnAction == (mask & 8 != 0), "action reading works independently")
                check(value.bypassScreenshots == (mask & 16 != 0), "screenshot bypass has its own default-OFF switch")
                check(value.requiresScreenshotProtection(true, allowsBypass: false), "mandatory protection is never bypassed")
                check(!value.requiresScreenshotProtection(false, allowsBypass: true), "unprotected layers stay unprotected")
                check(value.requiresScreenshotProtection(true, allowsBypass: true) == (mask & 16 == 0), "only an explicitly enabled eligible layer bypasses capture protection")
                check(value.presenceDirective(requestedOnline: false, forceOffline: true) == .offline, "background offline preserved")
                for force in [false, true] {
                    let expected: NagramiXPrivacySettings.PresenceDirective
                    expected = mask & 2 != 0 ? .offline : .online
                    check(value.presenceDirective(requestedOnline: true, forceOffline: force) == expected, "presence without a master")
                }
            }
        }
        let empty = NagramiXGhostSettings()
        check(!empty.hidesMessageReads && !empty.hidesStoryReads && !empty.hidesOnline && empty.hidesTyping && !empty.automaticOffline && !empty.readsOnAction, "only activity hiding defaults ON")
        check(NagramiXGhostSettings.preservesPrivateRead(privateMaxId: 80, localMaxId: 80, serverMaxId: 20), "private history survives turning an option OFF")
        check(!NagramiXGhostSettings.preservesPrivateRead(privateMaxId: 80, localMaxId: 81, serverMaxId: 20), "new native read can synchronize")
        check(!NagramiXGhostSettings.preservesPrivateRead(privateMaxId: 80, localMaxId: 80, serverMaxId: 80), "server catches up")
        check(!NagramiXGhostSettings.preservesPrivateRead(privateMaxId: nil, localMaxId: 80, serverMaxId: 20), "ordinary validation unchanged")
        check(NagramiXGhostSettings.preservesPrivateRead(privateMaxId: 80, localMaxId: 70, serverMaxId: 20), "partial history stays protected")
        check(!NagramiXGhostSettings.preservesPrivateRead(privateMaxId: 80, localMaxId: 10, serverMaxId: 20), "server-ahead state validates normally")
        print("PASS: \(checks) independent privacy/presence/private-boundary checks")
    }
}
