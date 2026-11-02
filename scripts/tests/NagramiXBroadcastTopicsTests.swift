import Foundation

// UIKit, Postbox and network are boundaries. Selection handoff and both enqueue
// update methods in Production.swift are extracted from the native overlay.
struct Channel: Equatable {
    let id: Int; var isForum = false; var isMonoForum = false
    var isForumOrMonoForum: Bool { isForum || isMonoForum }
}
enum EnginePeer: Equatable {
    case user(Int), channel(Channel), community(Int)
    var id: Int { switch self { case let .user(id), let .community(id): return id; case let .channel(c): return c.id } }
}
struct Mode { let copiesAsNew: Bool }
struct MessageId: Equatable { let peerId: Int; let namespace: Int; let id: Int32 }
enum Namespaces { enum Message { static let Cloud = 0 } }
struct EngineMessageReplySubject: Equatable { let messageId: MessageId; let quote: Int?; let innerSubject: Int? }
enum EnqueueMessage: Equatable {
    case message(text: String, attributes: [Int], inlineStickers: [Int:Int], mediaReference: Int?, threadId: Int64?, replyToMessageId: EngineMessageReplySubject?, replyToStoryId: Int?, localGroupingKey: Int64?, correlationId: Int64?, bubbleUpEmojiOrStickersets: [Int])
    case forward(source: MessageId, threadId: Int64?, grouping: Int, attributes: [Int], correlationId: Int64?)
    var topic: Int64? {
        switch self { case let .message(_,_,_,_,topic,_,_,_,_,_): return topic; case let .forward(_,topic,_,_,_): return topic }
    }
    var reply: EngineMessageReplySubject? {
        if case let .message(_,_,_,_,_,reply,_,_,_,_) = self { return reply }; return nil
    }
}
struct SelectionState {
    var editing = false
    var selectedPeerIds = Set<Int>()
    var selectedPeerMap: [Int:EnginePeer] = [:]
    var foundPeers: [EnginePeer] = []
    var folderLocalValue = 0
}
final class ListNode {
    var currentState = SelectionState()
    var selectionCountChanged: ((Int) -> Void)?
    func updateState(_ f: (SelectionState) -> SelectionState) {
        currentState = f(currentState); selectionCountChanged?(currentState.selectedPeerIds.count)
    }
    func select(_ peer: EnginePeer) {
        updateState { old in
            var state = old; state.editing = true
            state.selectedPeerIds.insert(peer.id); state.selectedPeerMap[peer.id] = peer
            state.foundPeers.append(peer); return state
        }
    }
    func deselect(_ peer: EnginePeer) { currentState.selectedPeerIds.remove(peer.id) }
    var recipients: [EnginePeer] { currentState.selectedPeerIds.compactMap { currentState.selectedPeerMap[$0] } }
}
final class Folder { let listNode = ListNode() }
final class FolderContainer {
    var nagramiXPreserveCopyRecipients = false
    var currentItemNodeValue: Folder? = Folder()
}

@main struct Tests {
    static var checks = 0
    static func check(_ ok: @autoclosure () -> Bool, _ label: String) {
        checks += 1; precondition(ok(),label)
    }
    static func main() {
        let a = EnginePeer.user(10), b = EnginePeer.user(20)
        let forum = EnginePeer.channel(Channel(id: 40,isForum: true))
        let other = EnginePeer.channel(Channel(id: 50))
        let mono = EnginePeer.channel(Channel(id: 60,isMonoForum: true))
        let video = EnqueueMessage.message(text:"caption",attributes:[1,7],inlineStickers:[2:3],mediaReference:90,threadId:nil,replyToMessageId:nil,replyToStoryId:nil,localGroupingKey:123,correlationId:456,bubbleUpEmojiOrStickersets:[8])
        let comment = EnqueueMessage.message(text:"comment",attributes:[],inlineStickers:[:],mediaReference:nil,threadId:nil,replyToMessageId:nil,replyToStoryId:nil,localGroupingKey:nil,correlationId:457,bubbleUpEmojiOrStickersets:[])
        let batch = [comment,video,video]
        check(rejects([a,b,forum],topics:[:]),"missing forum topic rejects whole batch before async payment/enqueue")
        check(rejects([a,.community(70)],topics:[:]),"community container cannot become first channel")
        check(rejects([mono],topics:[:]),"monoforum requires explicit thread")
        check(!rejects([a,b,other],topics:[:]),"ordinary private/group/channel batch needs no topic")
        check(!rejects([a,b,forum],topics:[40:99]),"valid mixed batch accepted")
        let filtered = snapshotTopics([40:99,50:777],recipients:[10,20,40])
        check(filtered == [40:99],"snapshot excludes deselected destination topics")

        // Reproduce build114: a new/cached folder replaces the list that owns
        // a/b. The old test's one-list fixture could not detect this loss.
        let legacy = FolderContainer()
        legacy.currentItemNodeValue!.listNode.select(a); legacy.currentItemNodeValue!.listNode.select(b)
        let lostFolder = Folder(); legacy.legacyActivate(lostFolder); lostFolder.listNode.select(forum)
        check(Set(lostFolder.listNode.recipients.map(\.id)) == [40],"legacy folder switch loses both people")
        let oldRoute = legacyRoute(batch,to:forum,topics:[40:99])
        check(oldRoute.allSatisfy { $0.topic == 99 && $0.reply == nil },"legacy copies have local topic but no server reply target")

        let picker = Picker()
        check(!picker.nagramiXCopySelection && !picker.mainContainerNode!.nagramiXPreserveCopyRecipients,"opt-in off for native lists")
        picker.nagramiXCopySelection = true
        let folders = picker.mainContainerNode!
        check(folders.nagramiXPreserveCopyRecipients,"copy mode enables folder handoff")
        let first = folders.currentItemNodeValue!
        first.listNode.select(a); first.listNode.select(b)
        var count = 0
        first.listNode.selectionCountChanged = { count = $0 }
        let work = Folder(); work.listNode.currentState.folderLocalValue = 88
        folders.activate(work); work.listNode.select(forum)
        check(Set(work.listNode.recipients.map(\.id)) == [10,20,40],"all people plus selected forum retained")
        check(count == 3,"Send panel count follows current folder")
        check(work.listNode.currentState.folderLocalValue == 88,"folder-local state preserved")
        let snapshot = work.listNode.recipients
        var liveTopics: [Int:Int64] = [40:99]
        let topics = liveTopics
        liveTopics[40] = 1
        var delivered = Set<Int>()
        for peer in snapshot {
            let sent = route(batch,to:peer,topics:topics)
            check(sent.count == batch.count,"every recipient receives full batch")
            for (index,item) in sent.enumerated() {
                if peer == forum {
                    let reply = EngineMessageReplySubject(messageId:MessageId(peerId:40,namespace:0,id:99),quote:nil,innerSubject:nil)
                    check(item == batch[index].withUpdatedThreadId(99).withUpdatedReplyToMessageId(reply),"forum copy addresses exact topic, preserving all payload fields")
                } else { check(item == batch[index],"private copy carries no forum reply or topic") }
            }
            delivered.insert(peer.id)
        }
        check(delivered == [10,20,40],"three separate enqueue destinations, no first-topic fallback")
        check(batch[1] == video && video.reply == nil,"per-recipient transformation leaves original batch unchanged")
        work.listNode.deselect(a)
        folders.activate(first)
        check(Set(first.listNode.recipients.map(\.id)) == [20,40],"cached folder does not resurrect deselected recipient")
        check(count == 2,"cached folder updates count")
        first.listNode.deselect(forum); first.listNode.deselect(b)
        folders.activate(work)
        check(work.listNode.recipients.isEmpty && !work.listNode.currentState.selectedPeerMap.isEmpty,"empty selection stays empty even with stale peer map")
        check(count == 0,"no selected recipients disables native Send via existing count callback")
        work.listNode.select(a)
        folders.activate(work)
        check(work.listNode.recipients == [a],"same-node activation preserves selection")
        for index in 0..<30 {
            let next = Folder(); next.listNode.currentState.folderLocalValue = index
            folders.activate(next)
            check(next.listNode.recipients == [a],"recreated/late folder receives latest selection")
            check(next.listNode.currentState.folderLocalValue == index,"unrelated state survives folder handoff")
        }
        picker.nagramiXCopySelection = false
        let native = Folder(); native.listNode.select(other)
        folders.activate(native)
        check(native.listNode.recipients == [other],"non-copy picker keeps native per-folder behavior")

        for topic: Int64 in [1,99,456,Int64(Int32.max)] {
            let items = route(batch,to:forum,topics:[40:topic,10:999])
            check(items.allSatisfy { $0.topic == topic && $0.reply?.messageId == MessageId(peerId:40,namespace:0,id:Int32(topic)) },"explicit General/non-General/large topic uses correct peer and root")
            check(route(batch,to:a,topics:[40:topic]) == batch,"forum mapping does not leak to person")
            check(route(batch,to:other,topics:[40:topic]) == batch,"forum mapping does not leak to broadcast channel")
        }
        let monoTopic: Int64 = 8_000_000_000
        check(route(batch,to:mono,topics:[60:monoTopic]).allSatisfy { $0.topic == monoTopic && $0.reply == nil },"monoforum retains native 64-bit peer addressing, no Int32 reply conversion")
        check(route(batch,to:forum,topics:[40:99],copy:false) == batch,"ordinary server forwarding unchanged")
        print("PASS \(checks) checks; extracted native folder handoff and enqueue routing; no UIKit/network delivery")
    }
}
