import Foundation

@main struct PrivacyMigrationTests {
    static func main() throws {
        if CommandLine.arguments.count == 5 && CommandLine.arguments[1] == "--seed-online" {
            let defaults = UserDefaults(suiteName: CommandLine.arguments[2])!
            defaults.set(["online": CommandLine.arguments[3] == "true", "automaticOffline": CommandLine.arguments[4] == "true"], forKey: "nagramix.privacy.individual.v2")
            defaults.synchronize()
            return
        }
        if CommandLine.arguments.count == 4 && CommandLine.arguments[1] == "--set-online" {
            let defaults = UserDefaults(suiteName: CommandLine.arguments[2])!
            NagramiXPrivacySettings.update(in: defaults) { $0[.online] = CommandLine.arguments[3] == "true" }
            defaults.synchronize()
            return
        }
        if CommandLine.arguments.count == 4 && CommandLine.arguments[1] == "--cold-online" {
            let value = NagramiXPrivacySettings.read(from: UserDefaults(suiteName: CommandLine.arguments[2])!)
            let expected = CommandLine.arguments[3] == "true"
            precondition(value.hidesOnline == expected && value.automaticOffline == expected)
            return
        }
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ name: String) { precondition(value(), name); checks += 1 }
        let suite = "nagramix.privacy.migration.tests." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let currentKey = "nagramix.privacy.individual.v2"
        let ghostKey = "nagramix.privacy.ghost.v1"
        let modeKey = "nagramix.privacy.messageReadMode.v1"
        let storyKey = "nagramix.stories.anonymousViewing"
        let fresh = NagramiXPrivacySettings.read(from: defaults)
        check(fresh == NagramiXPrivacySettings(), "fresh defaults are empty")
        check(fresh.readMode == .standard && fresh.hidesTyping && NagramiXPrivacySettings.Option.allCases.filter { fresh[$0] } == [.typing], "only activity hiding ON on first launch")
        check(defaults.object(forKey: currentKey) == nil, "read-only access does not save artificial choices")

        let oldOptions = ["messageReads", "storyReads", "online", "typing", "automaticOffline", "readOnAction"]
        for mask in 0..<128 {
            for explicit in [nil, "standard", "local", "server"] as [String?] {
                for story in [nil, false, true] {
                    defaults.removePersistentDomain(forName: suite)
                    var legacy: [String: Bool] = ["enabled": mask & 64 != 0]
                    for (index, name) in oldOptions.enumerated() { legacy[name] = mask & (1 << index) != 0 }
                    defaults.set(legacy, forKey: ghostKey)
                    if let explicit { defaults.set(explicit, forKey: modeKey) }
                    if let story { defaults.set(story, forKey: storyKey) }
                    let actual = NagramiXPrivacySettings.read(from: defaults)
                    let oldMode = explicit ?? "standard"
                    let oldReadWasHidden = oldMode == "local" || (oldMode == "standard" && mask & 65 == 65)
                    check(actual.hidesMessageReads == oldReadWasHidden, "migration preserves actual message receipt behavior")
                    check(actual.readMode == (oldReadWasHidden ? .local : .standard), "retired server choice becomes standard without activating old hiding")
                    check(actual.hidesStoryReads == (mask & 66 == 66 || story == true), "the two story settings merge without disabling an active choice")
                    check(actual.hidesOnline == (mask & 64 != 0 && mask & 20 != 0), "either active legacy online protection enables the merged switch; OFF master stays OFF")
                    check(actual.hidesTyping == (mask & 72 == 72), "typing migrates independently")
                    check(actual.automaticOffline == actual.hidesOnline, "both online protections use the merged choice")
                    check(!actual.bypassScreenshots, "a legacy ON master must not activate the newly added screenshot bypass")
                    check(actual.readsOnAction == (oldMode == "standard" && mask & 97 == 97), "migration does not silently enable a reply exception")
                    check(defaults.dictionary(forKey: ghostKey) as? [String: Bool] == legacy, "legacy data remains intact")
                    check(defaults.object(forKey: currentKey) == nil, "migration is a read until the user edits")
                }
            }
        }
        defaults.removePersistentDomain(forName: suite)
        defaults.set(["enabled": true], forKey: ghostKey)
        check(NagramiXPrivacySettings.read(from: defaults).readMode == .local, "missing old suboptions use the old ON defaults only under an ON master")
        NagramiXPrivacySettings.update(in: defaults) { value in
            value.readMode = .standard
            for option in NagramiXPrivacySettings.Option.allCases { value[option] = false }
        }
        check(NagramiXPrivacySettings.read(from: UserDefaults(suiteName: suite)!) == NagramiXPrivacySettings(options: [:]), "turning every option OFF saves that choice")
        defaults.set(true, forKey: storyKey)
        check(NagramiXPrivacySettings.read(from: defaults) == NagramiXPrivacySettings(options: [:]), "stale legacy master/story cannot resurrect after canonical OFF")

        for option in NagramiXPrivacySettings.Option.allCases {
            NagramiXPrivacySettings.update(in: defaults) { $0[option] = true }
            let selected = NagramiXPrivacySettings.read(from: defaults)
            check(selected[option], "each switch works without a master")
            check(NagramiXPrivacySettings.Option.allCases.filter { selected[$0] } == [option], "no other checkbox is silently selected")
            NagramiXReadModeSettings.set(.local, enabled: true, in: defaults)
            check(NagramiXPrivacySettings.read(from: defaults)[option], "changing mode preserves the selected option")
            NagramiXReadModeSettings.set(.local, enabled: false, in: defaults)
            check(NagramiXPrivacySettings.read(from: defaults)[option], "normal reading preserves the raw option choice")
            NagramiXPrivacySettings.update(in: defaults) { $0[option] = false; $0.readMode = .standard }
        }
        check(NagramiXPrivacySettings.read(from: defaults) == NagramiXPrivacySettings(options: [:]), "all-OFF remains stable")
        let previousOptions = ["storyReads", "online", "typing", "automaticOffline", "readOnAction"]
        for raw in ["standard", "local", "server", "unknown"] {
            for mask in 0..<32 {
                var snapshot: [String: Any] = ["readMode": raw]
                for (i, option) in previousOptions.enumerated() { snapshot[option] = mask & (1 << i) != 0 }
                defaults.set(snapshot, forKey: currentKey)
                let actual = NagramiXPrivacySettings.read(from: defaults)
                check(actual.readMode == (raw == "local" ? .local : .standard), "old server/unknown becomes normal mode")
                for option in NagramiXPrivacySettings.Option.allCases {
                    let expected = option == .online ? mask & 10 != 0 : previousOptions.firstIndex(of: option.rawValue).map { mask & (1 << $0) != 0 } ?? false
                    check(actual[option] == expected, "saved choices are preserved; online merges with automatic offline")
                }
                check(actual.hidesMessageReads == (raw == "local" || mask & 16 != 0), "independent action mode hides automatic reads")
            }
        }
        func reopen(_ expected: Bool) {
            defaults.synchronize()
            let value = NagramiXPrivacySettings.read(from: UserDefaults(suiteName: suite)!)
            check(value.hidesOnline == expected && value.automaticOffline == expected, "reopening preferences preserves both parts of the merged setting")
        }
        for oldOnline in [false, true] {
            for oldAutomatic in [false, true] {
                defaults.set(["online": oldOnline, "automaticOffline": oldAutomatic, "typing": false], forKey: currentKey)
                let expected = oldOnline || oldAutomatic
                check(NagramiXPrivacySettings.read(from: defaults).hidesOnline == expected, "all four saved combinations migrate by OR")
                reopen(expected)
                NagramiXPrivacySettings.update(in: defaults) { $0[.online] = true }
                reopen(true)
                NagramiXPrivacySettings.update(in: defaults) { $0[.online] = false }
                check(defaults.dictionary(forKey: currentKey)?["automaticOffline"] == nil, "explicit OFF removes the retired field")
                reopen(false)
                NagramiXPrivacySettings.update(in: defaults) { $0[.storyReads].toggle() }
                reopen(false)
                check(!NagramiXPrivacySettings.read(from: defaults).hidesTyping, "saved activity OFF is preserved during online migration")
            }
        }
        print("PASS: \(checks) privacy default/migration/independence checks")
    }
}
