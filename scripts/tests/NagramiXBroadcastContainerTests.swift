import Foundation

// Telegram 13.1 exposes the same ID through EngineMessage in UI modules.
enum EngineMessage { typealias Id = MessageId }

struct RowResult {
    let enabled: Bool
    let selectable: Bool
    let opened: [Int]
    let threads: [Int64?]
    let toggled: [Int]
}
final class RowInteraction {
    var opened: [Int] = []
    var threads: [Int64?] = []
    var toggled: [Int] = []
    func peerSelected(_ peer: EnginePeer, _ unused: Int?, _ thread: Int64?, _ promo: Int?, _ flag: Bool) {
        self.opened.append(peer.id)
        self.threads.append(thread)
    }
    func togglePeerSelected(_ peer: EnginePeer, _ thread: Int64?) {
        self.toggled.append(peer.id)
    }
}
enum NagramiXMessageTransferMode { case copyAsNew, copyToSingleRecipient, forwardWithSource }

@main struct BroadcastContainerTests {
    static func main() {
        Tests.main() // Existing folder preservation and actual enqueue routing.
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ message: String) {
            precondition(condition(), message)
            checks += 1
        }
        let copy = makeBroadcastFilter(.copyAsNew, ownViewOnce: false).union(.includeCommunities)
        let normal: ChatListNodePeersFilter = [.onlyWriteable, .includeCommunities]
        let forum = EnginePeer.channel(Channel(id: 40, isForum: true))
        let mono = EnginePeer.channel(Channel(id: 60, isMonoForum: true))
        let community = EnginePeer.community(70)
        check(copy.contains(.nagramiXCopyDestinations), "broadcast opts in")
        check(!makeBroadcastFilter(.copyToSingleRecipient, ownViewOnce: false).contains(.nagramiXCopyDestinations), "single copy unchanged")
        check(!makeBroadcastFilter(.forwardWithSource, ownViewOnce: false).contains(.nagramiXCopyDestinations), "native forward unchanged")
        check(!makeBroadcastFilter(.copyAsNew, ownViewOnce: true).contains(.nagramiXCopyDestinations), "own view-once private-only path unchanged")
        for legacy in [legacyRowInsert, legacyRowUpdate] {
            let old = legacy(forum, true, false, nil, copy, true)
            check(!old.enabled && old.opened.isEmpty, "baseline reproduces disabled forum in multiple selection")
        }
        for row in [copyRowInsert, copyRowUpdate] {
            for peer in [forum, mono, community] {
                let value = row(peer, true, false, nil, copy, true)
                check(value.enabled && !value.selectable, "container is navigable without a recipient checkbox")
                check(value.opened == [peer.id] && value.toggled.isEmpty, "tap opens container instead of selecting root")
                let denied = row(peer, true, false, nil, copy, false)
                check(!denied.enabled && denied.opened.isEmpty && denied.toggled.isEmpty, "existing permission/filter denial retained")
                let legacy = row(peer, true, false, nil, normal, true)
                check(!legacy.enabled && legacy.opened.isEmpty, "other multiple-selection pickers unchanged")
            }
            for peer in [EnginePeer.user(10), .channel(Channel(id: 50))] {
                let value = row(peer, true, false, nil, copy, true)
                check(value.enabled && value.selectable && value.toggled == [peer.id] && value.opened.isEmpty,
                      "personal and ordinary group recipients still toggle normally")
            }
            let topic = row(forum, false, false, 900, copy, true)
            check(topic.opened == [forum.id] && topic.threads == [900] && topic.toggled.isEmpty, "explicit topic reaches native callback")
            check(!row(forum, false, false, 900, copy, false).enabled, "closed/unavailable topic stays disabled")
            let privacy = row(forum, true, true, nil, normal, true)
            check(privacy.enabled && privacy.selectable && privacy.toggled == [forum.id], "peer-ID privacy/folder pickers unchanged")
            let single = row(forum, false, false, nil, normal, true)
            check(single.enabled && single.opened == [forum.id], "native single-selection forum navigation retained")
        }
        // Selecting the actual topic remains the existing broadcast route;
        // comments/media all keep the same destination and other recipients.
        let a = EnginePeer.user(10), b = EnginePeer.user(20)
        let batch: [EnqueueMessage] = [.message(text: "video caption", attributes: [5], inlineStickers: [:],
            mediaReference: 90, threadId: nil, replyToMessageId: nil, replyToStoryId: nil,
            localGroupingKey: 123, correlationId: 456, bubbleUpEmojiOrStickersets: [])]
        for peer in [a, b, forum] {
            let result = route(batch, to: peer, topics: [forum.id: 900])
            check(result.count == 1, "each selected recipient retains its copy")
            check(result[0].topic == (peer.id == forum.id ? 900 : nil), "topic does not leak to personal recipients")
            if peer.id == forum.id {
                check(result[0].reply?.messageId == MessageId(peerId: forum.id, namespace: Namespaces.Message.Cloud, id: 900),
                      "forum RPC reply target is the explicit selected topic")
            }
        }
        check(rejects([a, forum], topics: [:]), "no fallback to General or first topic")
        print("PASS \(checks) broadcast container navigation/selection checks; UIKit and network are boundaries")
    }
}
