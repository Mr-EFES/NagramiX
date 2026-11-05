import Foundation
import CoreFoundation

private var checks = 0
private func check(_ value: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    if !value() { fatalError("Archive deletion visibility regression: " + label) }
}
@main struct ArchiveDeletionVisibilityTests {
    static func message(_ id: Int32, _ stable: UInt32, peer: Int64 = 1, namespace: Int32 = 0) -> Message {
        Message(stableId: stable, id: MessageId(peerId: PeerId(value: peer), namespace: namespace, id: id))
    }
    static func row(_ m: Message) -> ChatHistoryEntry { .MessageEntry(m, 0, true, nil, 0, 0) }
    static func group(_ messages: [Message], _ key: Int64 = 77) -> ChatHistoryEntry { .MessageGroupEntry(key, messages.map { ($0, true, 0, 0, nil) }, 0) }
    static func main() {
        // The four-element post in the video keeps its logical IDs/group key,
        // but all native stable IDs change when the local archive renders it.
        for size in [1, 2, 4] {
            for animated in [false, true] {
                let old = (1...size).map { message(Int32($0), UInt32($0)) }
                let copies = (1...size).map { message(Int32($0), UInt32(100 + $0)) }
                let list = TransitionHarness(), node = ChatMessageBubbleItemNode(old)
                list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: size == 1 ? [row(old[0])] : [group(old)])
                list.context.engine.messages.deleted = Set(old.map { $0.id })
                list.process(size == 1 ? [row(copies[0])] : [group(copies)], animated: animated)
                check(!node.isHidden, "retained post keeps its visible cell")
                check(node.snapshotCalls == 0, "retained replacement never burns the whole row")
                check(list.applied.isEmpty, "retained row has no phantom 0.8s collapse")
                check(list.context.engine.messages.tested.isEmpty, "retained logical IDs are not deletion candidates")
                check(list.hiddenCount == 0, "retained replacement needs no visibility ownership")
            }
        }
        // A surviving component means the album cell is still displayed.
        let a = message(1, 1), b = message(2, 2), localA = message(1, 101)
        do {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a, b])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: [group([a, b])])
            list.context.engine.messages.deleted = [a.id, b.id]
            list.process([group([localA])]); check(!node.isHidden && node.snapshotCalls == 0, "partial retained album must not disappear")
        }
        // True native deletion and explicit second deletion still use dust.
        for archivePurge in [false, true] {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a, b])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: [group([a, b])])
            if archivePurge { list.ignoreMessageIds = [a.id, b.id] } else { list.context.engine.messages.deleted = [a.id, b.id] }
            list.process([])
            check(node.isHidden && node.snapshotCalls == 1, "actual deletion snapshots/hides the cell once")
            check(list.applied == [a.stableId], "actual dust reserves only its candidate")
            check(list.dustEffectLayer?.frames.count == 1 && list.hiddenCount == 1, "one dust image per album")
        }
        // Multiple matching IDs in a cell must not create duplicate snapshots.
        do {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a, b])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: [group([a, b])])
            list.forceCandidates([a.stableId, b.stableId]); list.process([])
            check(node.snapshotCalls == 1 && list.dustEffectLayer?.frames.count == 1, "deduplicated album snapshot")
            check(list.applied == [a.stableId, b.stableId], "deduplication preserves every applied correlation")
        }
        // The archive can publish later than native deletion, including during
        // Undo, or in a transition without insertion animation/Reduce Motion.
        for animated in [false, true] {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a, b])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: [group([a, b])]); list.context.engine.messages.deleted = [a.id, b.id]
            list.process([]); check(node.isHidden, "fixture owns the hidden dust cell")
            list.forceCandidates([a.stableId, b.stableId])
            list.process([group([localA, message(2, 102)])], animated: animated)
            check(!node.isHidden, "delayed retained copy/Undo restores visible reused cell")
            check(list.hiddenCount == 0 && list.pending.isEmpty, "delayed return clears dust ownership and stale candidates")
            check(list.applied.isEmpty && node.snapshotCalls == 1, "return is not hidden a second time")
        }
        // Do not undo visibility changes belonging to gallery/context preview.
        do {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a]); node.isHidden = true
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: [row(a)])
            list.process([row(localA)]); check(node.isHidden, "external hidden ownership is preserved")
        }
        // A true delete with no snapshot must collapse normally, never reserve
        // space for a dust effect that was not actually started.
        for mode in 0..<4 {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a])
            list.itemNodes = [node]; list.historyView = HistoryView(filteredEntries: [row(a)]); list.context.engine.messages.deleted = [a.id]
            if mode == 0 { node.snapshotAvailable = false }
            if mode == 1 { node.bounds.size.height = 1801 }
            if mode == 2 { node.service = true }
            if mode == 3 { list.allowDustEffect = false }
            list.process([])
            check(!node.isHidden && list.applied.isEmpty && list.hiddenCount == 0, "snapshot/height/service/killswitch fallback leaves no blank slot")
        }
        do {
            let list = TransitionHarness(), failed = ChatMessageBubbleItemNode([a]), good = ChatMessageBubbleItemNode([b]); failed.snapshotAvailable = false
            list.itemNodes = [failed, good]; list.historyView = HistoryView(filteredEntries: [row(a), row(b)]); list.context.engine.messages.deleted = [a.id, b.id]
            list.process([])
            check(!failed.isHidden && good.isHidden, "mixed snapshot result affects only captured cell")
            check(list.applied == [b.stableId], "failed snapshot never receives dust duration")
        }
        do {
            NagramiXDeletionEffectSettings.enabled = false
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a]); list.itemNodes = [node]
            list.historyView = HistoryView(filteredEntries: [row(a)]); list.context.engine.messages.deleted = [a.id]; list.process([])
            check(!node.isHidden && list.pending.isEmpty && list.applied.isEmpty, "effect OFF keeps native non-dust deletion")
            NagramiXDeletionEffectSettings.enabled = true
        }
        // Same numeric ID in another peer or namespace cannot keep a removed
        // original alive. Scheduled deletion keeps its native dust exclusion.
        for other in [message(1, 100, peer: 99), message(1, 100, namespace: 2)] {
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([a]); list.itemNodes = [node]
            list.historyView = HistoryView(filteredEntries: [row(a)]); list.context.engine.messages.deleted = [a.id]; list.process([row(other)])
            check(node.isHidden, "logical identity includes peer and namespace")
        }
        do {
            let scheduled = message(3, 3, namespace: Namespaces.Message.ScheduledCloud)
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([scheduled]); list.itemNodes = [node]
            list.historyView = HistoryView(filteredEntries: [row(scheduled)]); list.context.engine.messages.deleted = [scheduled.id]; list.process([])
            check(!node.isHidden && list.applied.isEmpty, "native scheduled exclusion preserved")
        }
        do {
            var expiring = a; expiring.autoremoveAttribute = AutoremoveAttribute(countdownBeginTime: Int32(CFAbsoluteTimeGetCurrent()) - 2, timeout: 2)
            let list = TransitionHarness(), node = ChatMessageBubbleItemNode([expiring]); list.itemNodes = [node]
            list.historyView = HistoryView(filteredEntries: [row(expiring)]); list.process([])
            check(node.isHidden && list.applied == [a.stableId], "actual native expiry still animates")
        }
        // Tracking cannot extend a deleted item's lifetime; stale weak entries
        // are removed at the next transition.
        do {
            let list = TransitionHarness(); var node: ChatMessageBubbleItemNode? = ChatMessageBubbleItemNode([a]); let probe = WeakNodeProbe(node)
            list.itemNodes = [node!]; list.historyView = HistoryView(filteredEntries: [row(a)]); list.context.engine.messages.deleted = [a.id]; list.process([])
            node = nil; list.itemNodes.removeAll(); check(probe.node == nil, "dust tracking does not retain cell")
            list.process([]); check(list.hiddenCount == 0, "dead weak entries cleaned")
        }
        print("PASS: \(checks) archive deletion visibility checks; UIKit/CA/engine answers are explicit boundaries")
    }
}
