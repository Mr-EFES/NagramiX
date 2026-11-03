private final class FreeContentWeakReference {
    weak var value: AnyObject?
}

@main
private struct FreeContentTests {
    static func main() {
        let defaults = UserDefaults.standard
        let key = "nagramix.privacy.individual.v2"
        let args = CommandLine.arguments
        if args.count == 3, args[1] == "--write" {
            NagramiXPrivacySettings.update { $0[.screenshotBypass] = args[2] == "true" }
            _ = defaults.synchronize()
            return
        }
        if args.count == 3, args[1] == "--read" {
            guard NagramiXPrivacySettings.current.allowsFreeContent == (args[2] == "true") else { exit(3) }
            return
        }
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ text: String) {
            checks += 1
            if !value() { FileHandle.standardError.write(Data(("FAIL: " + text + "\n").utf8)); exit(1) }
        }
        func enabled(_ value: Bool) { NagramiXPrivacySettings.update { $0[.screenshotBypass] = value } }
        for name in [key, "nagramix.privacy.ghost.v1", "nagramix.privacy.messageReadMode.v1", "nagramix.stories.anonymousViewing"] {
            defaults.removeObject(forKey: name)
        }
        check(!NagramiXPrivacySettings.current.allowsFreeContent, "fresh launch must be OFF")
        defaults.set(["enabled": true], forKey: "nagramix.privacy.ghost.v1")
        check(!NagramiXPrivacySettings.current.allowsFreeContent, "legacy master must not enable free content")
        for old: [String: Any] in [["typing": true], ["screenshotBypass": false], ["screenshotBypass": true], ["screenshotBypass": "true"]] {
            defaults.set(old, forKey: key)
            check(NagramiXPrivacySettings.current.allowsFreeContent == (old["screenshotBypass"] as? Bool ?? false), "existing saved choice must migrate without reset")
        }
        enabled(false)
        let settings = ContentSettings(ignoreContentRestrictionReasons: ["ignored"], addContentRestrictionReasons: ["extra"])
        let savedSettings = settings
        check(!settings.nagramiXAllowsFreeContent, "cached settings start OFF")
        for platform in ["ios", "all", "android", "extra"] {
            for reason in ["copyright", "other", "sensitive", "ignored"] {
                let rule = RestrictionRule(platform: platform, reason: reason, text: "notice-\(platform)-\(reason)")
                let user = TelegramUser([rule]), channel = TelegramChannel([rule])
                let message = Message(1, rules: [rule])
                let expected = reason != "sensitive" && reason != "ignored" && platform != "android" ? rule.text : nil
                enabled(false)
                check(user.restrictionText(platform: "ios", contentSettings: settings) == expected, "OFF restores native bot/user restriction")
                check(channel.restrictionText(platform: "ios", contentSettings: settings) == expected, "OFF restores native channel restriction")
                check(message.restrictionReason(platform: "ios", contentSettings: settings) == expected, "OFF restores native message restriction")
                enabled(true)
                check(user.restrictionText(platform: "ios", contentSettings: settings) == nil, "enabled content must remove platform notice from peer")
                check(channel.restrictionText(platform: "ios", contentSettings: settings) == nil, "enabled content must remove platform notice from channel")
                check(message.restrictionReason(platform: "ios", contentSettings: settings) == nil, "enabled content must remove platform notice from message")
                check(!message.isRestricted(platform: "ios", contentSettings: settings), "message isRestricted uses the same switch")
                check(settings == savedSettings && settings.ignoreContentRestrictionReasons == ["ignored"] && settings.addContentRestrictionReasons == ["extra"], "switch never mutates server content settings")
            }
        }
        enabled(false)
        let multiple = [RestrictionRule(platform: "android", reason: "other", text: "skip"), RestrictionRule(platform: "ios", reason: "ignored", text: "skip"), RestrictionRule(platform: "all", reason: "copyright", text: "first"), RestrictionRule(platform: "ios", reason: "other", text: "second")]
        check(TelegramUser(multiple).restrictionText(platform: "ios", contentSettings: settings) == "first", "OFF preserves rule order")
        check(Message(2, rules: multiple).restrictionReason(platform: "ios", contentSettings: settings) == "first", "message rule order remains native")
        for value in [false, true] {
            enabled(value)
            check(OrdinaryPeer().restrictionText(platform: "ios", contentSettings: settings) == nil && TelegramUser(nil).restrictionText(platform: "ios", contentSettings: settings) == nil, "unrestricted peers stay unrestricted")
            check(!Message(3).isRestricted(platform: "ios", contentSettings: settings), "unrestricted messages stay unrestricted")
            check(settings.nagramiXAllowsFreeContent == value, "cached ContentSettings reads current switch immediately")
            check(NagramiXPrivacySettings.current.bypassScreenshots == value, "capture/export compatibility API follows free content")
            check(nagramiXShouldNotifyScreenCapture() != value, "capture notification producer follows the same switch")
            for paid in [false, true] {
                for codes in [false, true] {
                    let message = Message(4, paid: paid, codes: codes)
                    let eligible = message.nagramiXAllowsScreenshotBypass
                    check(eligible == (!paid && !codes), "paid media and verification codes retain capture eligibility rules")
                    check(NagramiXPrivacySettings.current.requiresScreenshotProtection(true, allowsBypass: eligible) == !(value && eligible), "capture protection follows one checkbox and keeps exceptions")
                }
            }
        }
        enabled(false)
        var controller: ControllerHarness? = ControllerHarness()
        let a = Message(10), b = Message(11)
        controller!.chatDisplayNode.historyNode.nodes = [ChatMessageItemView([a]), ChatMessageItemView([a, b]), ItemNode(), ChatMessageItemView(nil)]
        enabled(true)
        check(controller!.forcedUpdates == 1 && Set(controller!.chatDisplayNode.historyNode.updated) == [a.id, b.id], "toggle refreshes existing peer panels and grouped message rows")
        check(controller!.chatDisplayNode.historyNode.updated.count == 2, "refresh deduplicates album and repeated IDs")
        NagramiXPrivacySettings.update { $0[.typing] = !$0[.typing] }
        check(controller!.forcedUpdates == 1, "unrelated privacy changes do not relayout content")
        enabled(true)
        check(controller!.forcedUpdates == 1, "same setting value does not trigger another refresh")
        enabled(false)
        check(controller!.forcedUpdates == 2, "OFF refreshes an already open chat")
        controller!.isNodeLoaded = false
        enabled(true)
        check(controller!.forcedUpdates == 2, "unloaded controller never forces node loading")
        let weakController = FreeContentWeakReference()
        weakController.value = controller
        controller = nil
        check(weakController.value == nil, "notification observer never retains the controller")
        enabled(false)
        let otherSettings = NagramiXPrivacySettings.current
        enabled(true)
        let after = NagramiXPrivacySettings.current
        for option in NagramiXPrivacySettings.Option.allCases where option != .screenshotBypass {
            check(after[option] == otherSettings[option], "unification leaves other privacy options unchanged")
        }
        check(after.readMode == otherSettings.readMode, "unification leaves read mode unchanged")
        let values = defaults.dictionary(forKey: key)!
        check(values["screenshotBypass"] as? Bool == true && values["freeContent"] == nil, "one old storage key, no second toggle or reset key")
        print("PASS: \(checks) actual free-content policy, capture compatibility, defaults and live chat refresh checks; UI/Postbox DTO boundaries")
    }
}
