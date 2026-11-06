import Foundation

private var effectChecks = 0
private func effectCheck(_ value: @autoclosure () -> Bool, _ label: String) {
    effectChecks += 1
    if !value() { fatalError("Archive deletion effect regression: " + label) }
}

@main struct ArchiveDeletionEffectTests {
    static func live(_ id: Int32, stable: UInt32? = nil, peer: Int64 = 1, namespace: Int32 = 0) -> Message {
        ArchiveDeletionVisibilityTests.message(id, stable ?? UInt32(id), peer: peer, namespace: namespace)
    }
    static func archived(_ message: Message, stable: UInt32? = nil) -> Message {
        var result = message
        if let stable { result.stableId = stable }
        result.attributes = [NagramiXArchivedMessageAttribute()]
        return result
    }
    static func entries(_ messages: [Message], album: Bool = false) -> [ChatHistoryEntry] {
        album ? [ArchiveDeletionVisibilityTests.group(messages)] : messages.map(ArchiveDeletionVisibilityTests.row)
    }
    static func main() {
        // Run the complete prior no-gap/weak ownership suite against this code.
        ArchiveDeletionVisibilityTests.main()
        for size in [1, 2, 5] {
            for album in [false, true] {
                for stableChanges in [false, true] {
                    for animated in [false, true] {
                        let originals = (1...size).map { live(Int32($0)) }
                        let copies = originals.map { archived($0, stable: stableChanges ? $0.stableId + 100 : nil) }
                        let list = TransitionHarness()
                        let nodes = album ? [ChatMessageBubbleItemNode(originals)] : originals.map { ChatMessageBubbleItemNode([$0]) }
                        list.itemNodes = nodes
                        list.historyView = HistoryView(filteredEntries: entries(originals, album: album))
                        // This also covers server updates: no interactive engine marker.
                        list.process(entries(copies, album: album), animated: animated)
                        effectCheck(nodes.allSatisfy { $0.snapshotCalls == 1 }, "first deletion snapshots each post exactly once")
                        effectCheck(list.dustEffectLayer?.frames.count == nodes.count, "first deletion starts dust")
                        effectCheck(nodes.allSatisfy { !$0.isHidden } && list.hiddenCount == 0, "retained copy stays visible without dust ownership")
                        effectCheck(list.applied.isEmpty && list.pending.isEmpty, "first deletion never reserves collapse or stale correlations")
                        effectCheck(nodes.allSatisfy { $0.bounds == CGRect(x: 0, y: 0, width: 300, height: 1100) }, "first deletion preserves row geometry")
                        // ListView may replace or reuse the node. The next update
                        // must not replay an already completed archive transition.
                        for (index, node) in nodes.enumerated() { node.item = MessageItem(album ? copies : [copies[index]]) }
                        list.process(entries(copies, album: album), animated: !animated)
                        effectCheck(nodes.allSatisfy { $0.snapshotCalls == 1 }, "archive refresh never repeats deletion")
                        // Explicit second deletion retains stock dust and collapse.
                        list.ignoreMessageIds = Set(copies.map { $0.id })
                        list.process([], animated: true)
                        effectCheck(nodes.allSatisfy { $0.snapshotCalls == 2 && $0.isHidden }, "second deletion animates too")
                        effectCheck(!list.applied.isEmpty, "second deletion uses actual removal duration")
                    }
                }
            }
        }
        let a = live(1), b = live(2)
        let copy = archived(a, stable: 101)
        // A node can already have received the new stable ID. Logical identity
        // still identifies the pending native-to-archive transition.
        do {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([copy])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: entries([a]))
            list.process(entries([copy]))
            effectCheck(node.snapshotCalls == 1 && !node.isHidden && list.applied.isEmpty, "already updated node supports first deletion")
        }
        // Initial loading, a reappearing archive after OFF, and restored cells
        // do not constitute a new deletion of a visible original.
        for hasPrevious in [false, true] {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([copy])
            list.itemNodes = [node]
            if hasPrevious { list.historyView = HistoryView(filteredEntries: []) }
            list.process(entries([copy]))
            effectCheck(node.snapshotCalls == 0 && list.dustEffectLayer == nil, "initial/reappearing archive does not burn")
        }
        for animated in [false, true] {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([copy])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: entries([copy]))
            list.process(entries([archived(a, stable: 201)]), animated: animated)
            effectCheck(node.snapshotCalls == 0 && !node.isHidden, "archived edit/revision/stable ID change is not deletion")
        }
        // OFF applies to the first deletion as well as true removals.
        do {
            NagramiXDeletionEffectSettings.enabled = false
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: entries([a]))
            list.forceCandidates([a.stableId]); list.process(entries([copy]))
            effectCheck(node.snapshotCalls == 0 && !node.isHidden && list.applied.isEmpty && list.pending.isEmpty, "effect OFF prevents first dust")
            NagramiXDeletionEffectSettings.enabled = true
            node.item = MessageItem([copy]); list.process(entries([copy]))
            effectCheck(node.snapshotCalls == 0, "enabling effect does not replay old deletion")
        }
        // Stock constraints and unavailable snapshots cannot hide a retained row.
        for mode in 0..<4 {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: entries([a]))
            if mode == 0 { node.snapshotAvailable = false }
            if mode == 1 { node.bounds.size.height = 1801 }
            if mode == 2 { node.service = true }
            if mode == 3 { list.allowDustEffect = false }
            list.process(entries([copy]))
            effectCheck(!node.isHidden && list.applied.isEmpty && list.hiddenCount == 0, "first-deletion fallback never creates gap")
        }
        // A mixed batch burns both originals, but only the genuinely removed
        // row becomes hidden and receives a custom delete duration.
        do {
            let list = TransitionHarness(), retained = ChatMessageBubbleItemNode([a]), removed = ChatMessageBubbleItemNode([b])
            list.itemNodes = [retained, removed]; list.historyView = HistoryView(filteredEntries: entries([a, b]))
            list.context.engine.messages.deleted = [b.id]
            list.process(entries([copy]))
            effectCheck(retained.snapshotCalls == 1 && removed.snapshotCalls == 1, "mixed deletion animates both")
            effectCheck(!retained.isHidden && removed.isHidden && list.hiddenCount == 1, "mixed deletion preserves only retained row")
            effectCheck(list.applied == [b.stableId], "mixed batch reserves only removed row duration")
        }
        // Logical identity includes peer/namespace; there is no unrelated
        // 'first deletion' when another conversation uses the same numeric ID.
        for other in [archived(live(1, peer: 99)), archived(live(1, namespace: 2))] {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: entries([a]))
            list.process(entries([other]))
            effectCheck(node.snapshotCalls == 0 && !node.isHidden, "unrelated peer/namespace does not trigger retained dust")
        }
        // Snapshot first deletion without stealing external visibility ownership.
        do {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a]); node.isHidden = true
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: entries([a]))
            list.process(entries([copy]))
            effectCheck(node.isHidden && list.hiddenCount == 0 && list.applied.isEmpty, "external hidden owner is unchanged")
        }
        // Re-delete after Undo is a new event, rather than a lifetime one-shot.
        do {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: entries([a]))
            list.process(entries([copy])); node.item = MessageItem([copy])
            list.process(entries([a])); node.item = MessageItem([a])
            list.process(entries([copy]))
            effectCheck(node.snapshotCalls == 2 && !node.isHidden, "each deletion after Undo animates")
        }
        print("PASS: \(effectChecks) archive deletion effect checks; plus prior visibility suite; UIKit/CA rendering are boundaries")
    }
}
