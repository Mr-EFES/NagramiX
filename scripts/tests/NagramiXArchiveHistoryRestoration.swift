
private struct TestDisposable {}
struct TelegramMediaAction: Media {}
private let EmptyDisposable = TestDisposable()
private struct ArchiveSubscriber<Value> {
    let putCompletion: () -> Void
    func putNext(_ value: Value) {}
}
extension Signal {
    fileprivate init(_ start: @escaping (ArchiveSubscriber<V>) -> TestDisposable) {
        self.init(perform: { completion in _ = start(ArchiveSubscriber(putCompletion: completion)) })
    }
}
extension ReadState {
    mutating func modify(_ update: (Value) -> Value) -> Value {
        value = update(value)
        return value
    }
}

enum TestActionType { case genericAction, destructiveAction }
struct TextAlertAction {
    let type: TestActionType
    let title: String
    let action: () -> Void
}
struct TestAlert { let text: String; let actions: [TextAlertAction] }
func textAlertController(context: Context, title: String, text: String, actions: [TextAlertAction], parseMarkdown: Bool) -> TestAlert {
    TestAlert(text: text, actions: actions)
}

@main enum ArchiveHistoryRestorationChecks {
    static func main() throws {
        let peer = PeerId(value: 10), other = PeerId(value: 20)
        func id(_ n: Int32, _ peerId: PeerId = peer) -> MessageId { MessageId(peerId: peerId, namespace: Namespaces.Message.Cloud, id: n) }
        let mine = id(10), theirs = id(11), oldLive = id(12), fresh = id(13)
        let archive = Archive()
        for key in [mine, theirs, oldLive, id(4, other)] { archive.addRecord(.init(messageId: key)) }
        func record(_ id: MessageId) -> NagramiXArchivedRecord { archive.state.value.records[Archive.key(id)]! }
        archive.removeLocal(messageIds: [mine])
        precondition(record(mine).hiddenFromChat && record(mine).deletedAt != nil)
        precondition(!record(theirs).hiddenFromChat)
        let chat = ChatControllerImpl(archive: archive)
        func plan(_ ids: Set<MessageId>, candidates: Set<MessageId>, live: [MessageId: Message] = [:]) -> NagramiXArchivePostDeletionPlan {
            archive.postDeletionPlan(transaction: Transaction(live: live), messageIds: ids, localCandidates: candidates)
        }
        let first = plan([theirs], candidates: [theirs])
        precondition(first.permanentLocalIds.isEmpty && first.nativeMessageIds.isEmpty && first.localMessageIds == [theirs])
        chat.confirm(plan: first, type: .forLocalPeer)
        precondition(chat.alerts.isEmpty && chat.chatDisplayNode.historyNode.ignoreMessageIds == [theirs])
        precondition(chat.overlays.last!.action(.undo) && !record(theirs).hiddenFromChat)
        chat.confirm(plan: first, type: .forLocalPeer)
        precondition(chat.overlays.last!.action(.commit) && record(theirs).hiddenFromChat)
        precondition(archive.purges.isEmpty && chat.context.engine.messages.calls.isEmpty)

        let oldFormat = Data("{\"records\":{}}".utf8)
        precondition((try? JSONDecoder().decode(NagramiXMessageArchiveState.self, from: oldFormat))?.pendingHistories == nil)
        archive.state.value.suspendHistory(peerId: peer, topCloudId: 12, clearedAt: 500)
        archive.state.value = try JSONDecoder().decode(NagramiXMessageArchiveState.self, from: JSONEncoder().encode(archive.state.value))
        precondition([mine, theirs, oldLive].allSatisfy { record($0).historyVisibility == .awaitingNewMessage })
        precondition(record(id(4, other)).historyVisibility == nil)
        precondition(!archive.state.value.resumeHistory(id: oldLive, timestamp: 501))
        precondition(!archive.state.value.resumeHistory(id: id(14, other), timestamp: 501))
        archive.receivedNewHistoryMessage(id: fresh, timestamp: 500, media: [TelegramMediaAction()])
        NagramiXMessageArchiveSettings.current.showDeletedMessages = false
        archive.receivedNewHistoryMessage(id: fresh, timestamp: 500, media: [])
        precondition(record(mine).hiddenFromChat)
        NagramiXMessageArchiveSettings.current.showDeletedMessages = true
        archive.receivedNewHistoryMessage(id: fresh, timestamp: 500, media: [])
        precondition(record(mine).historyVisibility == .restored)
        precondition(!archive.state.value.resumeHistory(id: fresh, timestamp: 501))
        precondition([mine, theirs, oldLive].allSatisfy { record($0).historyVisibility == .restored && !record($0).hiddenFromChat })

        let mixed = plan([theirs, fresh], candidates: [theirs], live: [theirs: Message(id: theirs), fresh: Message(id: fresh)])
        precondition(mixed.permanentLocalIds == [theirs] && mixed.nativeMessageIds == [fresh] && mixed.liveMessageIds == [fresh])
        let permanent = plan([mine], candidates: [mine])
        chat.confirm(plan: permanent, type: .forLocalPeer)
        precondition(chat.alerts.last!.text.contains("Cannot undo") && archive.purges.isEmpty)
        chat.alerts.last!.actions[0].action()
        precondition(record(mine).historyVisibility == .restored && archive.purges.isEmpty)
        chat.confirm(plan: permanent, type: .forLocalPeer)
        chat.alerts.last!.actions[1].action()
        precondition(chat.overlays.last!.action(.undo) && archive.purges.isEmpty)
        chat.confirm(plan: permanent, type: .forLocalPeer)
        chat.alerts.last!.actions[1].action()
        precondition(chat.overlays.last!.action(.commit) && archive.purges == [[mine]])
        precondition(chat.context.engine.messages.calls.isEmpty)
        precondition(archive.state.value.purgedMessageKeys == [Archive.key(mine)])
        precondition(archive.purgedKeys.value.contains(Archive.key(mine)))
        archive.state.value = try JSONDecoder().decode(NagramiXMessageArchiveState.self, from: JSONEncoder().encode(archive.state.value))
        archive.state.value.suspendHistory(peerId: peer, topCloudId: 13, clearedAt: 510)
        precondition(archive.state.value.resumeHistory(id: id(14), timestamp: 510))
        precondition(archive.usesLocalHistoryVisibility(mine, timestamp: 500) && archive.state.value.records[Archive.key(mine)] == nil)
        precondition(record(theirs).historyVisibility == .restored)
        print("PASS archive hide, undo, durable suspension, fresh traffic, restored-only confirmation and purge")
    }
}
