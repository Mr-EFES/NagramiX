@main private enum CallsPreferenceTests {
    static func main() throws {
        let suite = ProcessInfo.processInfo.environment["NAGRAMIX_TEST_SUITE"]!
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        defer { defaults.removePersistentDomain(forName: suite) }

        // Pre-upgrade native records did not have the migration marker.
        for native in [nil, false, true] as [Bool?] {
            let encoded = native.map { $0 ? "1" : "0" } ?? "null"
            let previous = try JSONDecoder().decode(CallListSettings.self, from: Data("{\"showTab\":\(encoded)}".utf8))
            for hidden in [nil, false, true] as [Bool?] {
                let migrated = previous.migratingCallsTabVisibility(legacyHidden: hidden)
                let expected = hidden.map { !$0 } ?? native ?? false
                check(migrated.showTab == expected, "upgrade resolves legacy and native settings")
                let saved = try JSONEncoder().encode(migrated)
                let restarted = try JSONDecoder().decode(CallListSettings.self, from: saved)
                check(restarted == migrated, "migration persists atomically with native value")
                check(restarted.migratingCallsTabVisibility(legacyHidden: expected) == migrated, "stale legacy choice cannot override a later launch")
            }
        }

        NagramiXTabSettings.update { $0.wideTabBar = false }
        check(NagramiXTabSettings.storedHideCalls == nil, "unrelated edit preserves absence of a saved legacy choice")
        for wide in [false, true] {
            NagramiXTabSettings.update { $0.wideTabBar = wide }
            var preference = CallListSettings.defaultSettings.migratingCallsTabVisibility(legacyHidden: nil)
            NagramiXTabSettings.reflectCallsTabVisibility(preference.showTab)
            let root = Root(Strings(actionCatalog))
            let promise = ValuePromise(NagramiXTabSettings.current, ignoreRepeated: false)
            var hiddenValues: [Bool] = []
            let updates = nagramiXLiveTabSettings(promise).start(next: { hiddenValues.append($0.hideCalls) })
            defer { updates.dispose() }
            func assertUI(_ visible: Bool) {
                RunLoop.current.run(until: Date().addingTimeInterval(0.02))
                check(hiddenValues.last == !visible, "open settings shows the inverse native value")
                check(count(CallsController.self, root) == (visible ? 1 : 0), "panel follows committed visibility")
                check(NagramiXTabSettings.current.wideTabBar == wide, "panel mode remains selected")
            }
            assertUI(false)
            preference = settingChange(preference, hidden: false)
            NagramiXTabSettings.reflectCallsTabVisibility(preference.showTab)
            assertUI(true)
            let index = root.bar.controllers.firstIndex(where: { $0 === root.callListController })!
            root.bar.selectedIndex = index
            root.bar.dispatchContext(index: index, view: ContextExtractedContentContainingView(), gesture: ContextGesture())
            check(root.callListController!.nativeContexts == 1, "long press routes to Telegram's own menu")
            preference = hideFromMenu(preference)
            NagramiXTabSettings.reflectCallsTabVisibility(preference.showTab)
            assertUI(false)
            check(root.bar.currentController === root.chatListController, "hiding the active Calls tab selects Chats")
            preference = nativeSwitchChange(preference, visible: true)
            NagramiXTabSettings.reflectCallsTabVisibility(preference.showTab)
            assertUI(true)
            let eventCount = hiddenValues.count
            NagramiXTabSettings.reflectCallsTabVisibility(true)
            assertUI(true)
            check(hiddenValues.count == eventCount, "repeated native acknowledgement does not redraw")
            preference = settingChange(preference, hidden: true)
            NagramiXTabSettings.reflectCallsTabVisibility(preference.showTab)
            assertUI(false)

            let restored = try JSONDecoder().decode(CallListSettings.self, from: JSONEncoder().encode(preference))
            let afterRestart = restored.migratingCallsTabVisibility(legacyHidden: false)
            NagramiXTabSettings.reflectCallsTabVisibility(afterRestart.showTab)
            check(count(CallsController.self, Root(Strings(actionCatalog))) == 0, "selected visibility survives restart")
        }
        print("Calls tab: migration, both controls, long press, both panel modes and restart passed.")
    }
}
