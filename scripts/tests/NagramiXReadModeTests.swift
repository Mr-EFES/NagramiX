import Foundation

@main struct ReadModeTests {
    static func main() throws {
        if CommandLine.arguments.count == 4 && CommandLine.arguments[1] == "--set-cold" {
            let defaults = UserDefaults(suiteName: CommandLine.arguments[2])!
            NagramiXReadModeSettings.set(.local, enabled: CommandLine.arguments[3] == "local", in: defaults)
            defaults.synchronize()
            return
        }
        if CommandLine.arguments.count == 4 && CommandLine.arguments[1] == "--cold" {
            let defaults = UserDefaults(suiteName: CommandLine.arguments[2])!
            precondition(NagramiXReadModeSettings.read(from: defaults).rawValue == CommandLine.arguments[3])
            return
        }
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ name: String) { precondition(condition(), name); checks += 1 }
        let suite = "nagramix.read.mode.tests." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        check(NagramiXReadModeSettings.read(from: defaults) == .standard, "first launch: normal read mode")
        check(defaults.object(forKey: "nagramix.privacy.individual.v2") == nil, "reading defaults does not write preferences")
        for previous in NagramiXReadMode.allCases {
            for option in [NagramiXReadMode.local] {
                for enabled in [false, true] {
                    let mode = previous.setting(option, enabled: enabled)
                    check(!enabled || mode == option, "ON selects just the requested mode")
                    check(enabled || mode == (previous == option ? .standard : previous), "OFF only affects its own selection")
                    check(NagramiXReadMode.allCases.count == 2, "no server mode exists")
                }
            }
        }
        NagramiXPrivacySettings.update(in: defaults) { $0[.typing] = true; $0[.readOnAction] = true }
        for mode in [NagramiXReadMode.local, .standard, .local] {
            if mode == .standard { NagramiXReadModeSettings.set(.local, enabled: false, in: defaults) }
            else { NagramiXReadModeSettings.set(mode, enabled: true, in: defaults) }
            check(NagramiXReadModeSettings.read(from: UserDefaults(suiteName: suite)!) == mode, "new defaults instance preserves selection")
            let full = NagramiXPrivacySettings.read(from: defaults)
            check(full[.typing] && full[.readOnAction], "reading mode never rewrites another checkbox")
            check(full.readsOnAction, "action mode remains independent of local toggle")
            defaults.synchronize()
            check(NagramiXReadModeSettings.read(from: UserDefaults(suiteName: suite)!) == mode, "persisted preferences preserve the exact selected mode")
        }
        defaults.set(["readMode": "unknown-future-mode"], forKey: "nagramix.privacy.individual.v2")
        check(NagramiXReadModeSettings.read(from: defaults) == .standard, "unknown canonical value leaves controls OFF")
        NagramiXReadModeSettings.set(.local, enabled: true, in: defaults)
        NagramiXPrivacySettings.update(in: defaults) { $0[.storyReads] = true }
        check(NagramiXReadModeSettings.read(from: defaults) == .local, "story switch never resets read mode")
        check(NagramiXGhostSettings.preservesPrivateRead(privateMaxId: 80, localMaxId: 80, serverMaxId: 40), "partial server acknowledgement keeps private remainder")
        print("PASS: \(checks) unified reading-mode checks; cold-process reads run by the Python validator")
    }
}
