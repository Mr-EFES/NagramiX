@main private struct Tests {
    static func main() {
        let contacts = Contacts(); contacts.refresh()
        expect(contacts.tabBarItem.image?.renderingMode == .alwaysTemplate, "Contacts icon must follow theme tint")
        expect(contacts.tabBarItem.selectedImage?.renderingMode == .alwaysTemplate, "Contacts selected icon must follow accent tint")
        contacts.isTab = false; contacts.tabBarItem.image = nil; contacts.refresh()
        expect(contacts.tabBarItem.image == nil, "pushed Contacts does not get tab appearance")

        let a = ViewController(), b = ViewController(), c = ViewController(), d = ViewController()
        let all = [a, b, c, d]
        for selected in 0 ..< 4 {
            for removed in 0 ..< 4 {
                let host = Controller(); host.setControllers(all, selectedIndex: selected)
                let previous = all[selected]
                host.tabBarControllerNode.resetEvidence()
                let before = host.switches
                let remaining = all.enumerated().filter { $0.offset != removed }.map { $0.element }
                let fallback = previous === all[removed] ? remaining.firstIndex(where: { $0 === c }) ?? 0 : nil
                host.setControllers(remaining, selectedIndex: fallback)
                let expected = fallback.map { remaining[$0] } ?? previous
                expect(host.currentController === expected, "controller identity survives removal or uses explicit Chats fallback")
                expect(host.tabBarControllerNode.committedSelections.allSatisfy { $0 == ObjectIdentifier(expected.tabBarItem) }, "items and selection commit atomically")
                expect(host.tabBarControllerNode.springUpdates == 0, "structural removal must not start selection spring")
                expect(host.switches - before == (previous === expected ? 0 : 1), "structural removal swaps child at most once")
                host.tabBarControllerNode.flush()
                expect(host.tabBarControllerNode.committedCounts.allSatisfy { $0 == remaining.count }, "deferred pass cannot resurrect old count")
                host.setControllers(all, selectedIndex: nil)
                expect(host.currentController === expected, "show again preserves selected controller")
            }
        }
        let host = Controller(); host.setControllers(all, selectedIndex: 0)
        host.setControllers([d, c, b, a], selectedIndex: nil)
        expect(host.currentController === a && host.selectedIndex == 3, "same-count reorder resolves identity")
        host.tabBarControllerNode.resetEvidence()
        host.complete(b)
        expect(host.currentController === b && host.selectedIndex == 2, "ready callback resolves moved tab identity")
        expect(host.tabBarControllerNode.springUpdates == 1, "ordinary selection keeps native spring")
        host.setControllers([a, c, d], selectedIndex: 1)
        host.complete(b)
        expect(host.currentController === c, "removed ready callback cannot select replacement at old index")
        host.setControllers([], selectedIndex: nil)
        expect(host.currentController == nil && host._selectedIndex == nil, "empty root clears selection and child")
        host.setControllers(all, selectedIndex: 999)
        expect(host.currentController === d, "explicit selection clamps safely")

        // Force the deferred onLayout path, without a root updateLayout call.
        let node = Node()
        node.updateTabBarItems(items: all.map { TabBarNodeItem(item: $0.tabBarItem, contextActionType: .none) }, selectedIndex: 3)
        _ = node.containerLayoutUpdated(ContainerViewLayout(version: 1), toolbar: nil, transition: .immediate)
        node.updateTabBarItems(items: [TabBarNodeItem(item: a.tabBarItem, contextActionType: .none)], selectedIndex: 0)
        NagramiXTabSettings.current.showSearchButton = false
        node.flush()
        expect(node.committedCounts.last == 1 && node.committedSearch.last == false, "deferred layout rebuilds model and settings together")
        let before = node.updates
        node.updateTabBarItems(items: [TabBarNodeItem(item: d.tabBarItem, contextActionType: .none)], selectedIndex: 0)
        _ = node.containerLayoutUpdated(ContainerViewLayout(version: 1), toolbar: nil, transition: .immediate)
        expect(node.updates == before + 1 && node.committedSelections.last! == ObjectIdentifier(d.tabBarItem), "same params cannot hide pending model update")
        let cached = node.updates
        _ = node.containerLayoutUpdated(ContainerViewLayout(version: 1), toolbar: nil, transition: .immediate)
        expect(node.updates == cached, "unchanged completed layout still uses cache")

        func model(_ ids: [Int], _ selected: Int, search: Bool = true) -> TabBarComponent {
            TabBarComponent(items: ids.map { .init(id: AnyHashable($0)) }, selectedId: AnyHashable(selected), search: search ? .init() : nil)
        }
        let view = ComponentViewHost()
        _ = view.apply(model([0, 1, 2, 3], 1), .immediate)
        view.overrideSelectedItemId = 0
        view.selectionGestureState = (0, 90, 60, 0)
        view.itemWithActiveContextGesture = 0
        let timer = TimerHost(); view.pendingDoubleTapItem = (0, 1, timer)
        let removal = view.apply(model([1, 2, 3], 2), .spring)
        expect(removal == .immediate, "structural change cannot interpolate old item geometry")
        expect(view.overrideSelectedItemId == nil && view.selectionGestureState == nil, "removed selection and drag coordinates cleared in same pass")
        expect(timer.invalidated && view.pendingDoubleTapItem == nil && view.itemWithActiveContextGesture == nil, "removed gesture context and pending double tap cancelled")
        expect(view.tabSelectionRecognizer?.isEnabled == true, "recognizer remains usable after cancellation")
        expect(view.tabSelectionRecognizer?.cancellations == 1, "structural change cancels old gesture before new frames")
        view.overrideSelectedItemId = 1
        let normal = view.apply(model([1, 2, 3], 3), .spring)
        expect(normal == .spring && view.overrideSelectedItemId == nil, "external selection clears optimistic override and keeps animation")
        view.overrideSelectedItemId = 1
        let searchHidden = view.apply(model([1, 2, 3], 3, search: false), .spring)
        expect(searchHidden == .immediate && view.overrideSelectedItemId == nil, "hide search reconciles capsule geometry")
        var wide = model([1, 2, 3], 3, search: false); wide.nagramiXWidePanelSnapshot = true
        expect(view.apply(wide, .spring) == .immediate, "wide mode reconciles geometry atomically")
        print("Tab bar visual consistency: \(assertions) actual-body checks passed")
    }
}
