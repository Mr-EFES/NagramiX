@main struct TransferRoutingTests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1; if !value() { fatalError(message) }
    }
    static func main() {
        let a = EnginePeer.user(User(id: 10)), b = EnginePeer.user(User(id: 20)), leaf = EnginePeer.channel(Channel(id: 30))
        // Reproduce build113: returning from a nested picker runs beginSelection
        // again and drops the contacts. Same native reset body, former guard.
        let old = SelectionNode(); old.contactListActive = true
        old.legacyBeginSelection(); old.nagramiXSelectCopyRecipient(a); old.nagramiXSelectCopyRecipient(b)
        old.legacyBeginSelection(); old.nagramiXSelectCopyRecipient(leaf)
        check(old.ids == [30], "build113 loss of original contacts reproduced")
        let node = SelectionNode(); node.nagramiXCopySelection = true; node.contactListActive = true
        node.beginSelection(); node.nagramiXSelectCopyRecipient(a); node.nagramiXSelectCopyRecipient(b)
        node.beginSelection(); node.nagramiXSelectCopyRecipient(leaf)
        check(node.ids == [10,20,30], "nested channel keeps selected contacts")
        node.beginSelection(); node.nagramiXSelectCopyRecipient(leaf)
        check(node.ids == [10,20,30], "repeated nested callback is idempotent")
        check(node.resets == 1, "copy selection native initialization runs once")
        node.switchTab(false)
        check(node.ids == [10,20,30], "contacts to chats preserves complete batch")
        node.mainContainerNode?.currentItemNode.updateState { s in var s = s; s.selectedPeerIds.remove(20); return s }
        node.switchTab(true)
        check(node.ids == [10,30], "deselection in chats is reflected in contacts")
        node.contactListNode?.updateSelectionState { $0?.withToggledPeerId(.peer(30)) }
        node.switchTab(false)
        check(node.ids == [10], "deselection in contacts is reflected in chats")
        node.switchTab(true); node.beginSelection(); node.nagramiXSelectCopyRecipient(b)
        check(node.ids == [10,20], "remaining selection survives repeated transitions")
        let plain = SelectionNode(); plain.beginSelection(); plain.beginSelection()
        check(plain.resets == 2, "unrelated native selectors keep previous initialization")
        for mode in [NagramiXMessageTransferMode.forwardWithSource, .forwardWithoutSource, .copyAsNew, .copyToSingleRecipient] {
            check(productionUsesCopyPicker(mode, protected: mode.copiesAsNew, own: true) == (mode == .copyAsNew), "one-shot single opens destination composer")
            check(productionUsesCopyPicker(mode, protected: mode.copiesAsNew, own: false) == mode.copiesAsNew, "other copy routes preserved")
        }
        check(productionLegacyUsesCopyPicker(.copyToSingleRecipient, protected:true), "build113 own-single broadcast UI regression reproduced")
        check(!productionUsesCopyPicker(.copyToSingleRecipient, protected: false, own: false), "archived single keeps native destination composer")
        check(!productionUsesCopyPicker(.copyToSingleRecipient, protected: true, own: true), "Переслать is not broadcast UI")
        check(productionUsesCopyPicker(.copyAsNew, protected: true, own: true), "Рассылка remains multi-recipient")
        check(productionPickerLimit(.copyToSingleRecipient, protected:true, own:true) == nil, "own single uses ordinary picker with no multi-select counter")
        check(productionPickerLimit(.copyToSingleRecipient, protected:true, own:false) == 1, "other local-copy fallback stays bounded")
        check(productionPickerLimit(.copyAsNew, protected:true, own:true) == nil, "broadcast remains unbounded by single limit")
        let forum = EnginePeer.channel(Channel(id: 40, isForumOrMonoForum: true))
        check(productionRejectsDestination([a,b,forum], threads: [:]), "missing forum topic never defaults to General")
        check(!productionRejectsDestination([a,b,forum], threads: [40:99]), "explicit forum topic accepted with private recipients")
        check(productionRejectsDestination([a, .community(50)], threads: [:]), "community container is not a send target")
        check(!productionRejectsDestination([a,b,leaf], threads: [:]), "ordinary group/channel has no topic requirement")
        var liveTopics: [Int:Int64] = [40:99, 55:100]
        let snapshot = productionSnapshot(liveTopics, recipients: [10,20,40])
        liveTopics[40] = 1
        check(snapshot == [40:99], "batch snapshots exact selected topic and omits stale destinations")
        check(!productionRejectsDestination([a,forum], threads: snapshot), "snapshot remains scoped to the selected forum")
        let video: [EnqueueMessage] = [.message(id:90, once:false, local:false, threadId:nil)]
        var destinations = Set<Int>()
        for target in [a,b,forum] {
            let routed = productionRoute(video, to:target, threads:snapshot)
            check(routed.count == 1, "normal video remains in every selected destination batch")
            if case let .message(id, once, _, topic) = routed[0] {
                check(id == 90 && !once && topic == (target.id == 40 ? 99 : nil), "topic applied only to its exact destination; ordinary video stays ordinary")
            } else { check(false, "broadcast must remain a new message") }
            destinations.insert(target.id)
        }
        check(destinations == [10,20,40], "all private recipients and the explicit forum are retained")
        // Real extracted native preflight; fake engine completions are manual.
        let send = DraftSender(); send.sendCurrentMessage()
        check(send.sent == 0 && send.context.engine.data.queries == 1, "waits for fresh originals and destination fees")
        send.sendCurrentMessage(); check(send.context.engine.data.queries == 1, "double tap does not issue duplicate send")
        send.context.engine.data.emit()
        check(send.sent == 1 && send.resolved?[1]?.ownOnce == true, "own one-shot draft reaches native composer send")
        send.finishForward()
        check(send.enqueued.count == 1, "exactly one output in ordinary Send")
        if case let .message(_, once, local, _) = send.enqueued[0] { check(once && local, "own one-shot dispatch is local new message") } else { check(false, "own recording must never be server-forwarded") }
        for variant in 0..<4 {
            let stale = DraftSender(); stale.sendCurrentMessage()
            if variant == 0 { stale.chatLocation.peerId = 99 }
            if variant == 1 { stale.chatLocation.threadId = 99 }
            if variant == 2 { stale.chatPresentationInterfaceState.interfaceState.version = 1 }
            if variant == 3 { stale.textInputPanelNode?.inputTextState = 2 }
            stale.context.engine.data.emit(); check(stale.sent == 0, "changed draft/location/input cancels old async send")
            check(!stale.nagramiXResolvingForwardSend, "stale callback releases send lock")
        }
        let blockedPeers: [EnginePeer?] = [nil, .user(User(id:100)), .user(User(id:200,botInfo:1)), forum, .community(50)]
        for peer in blockedPeers {
            let blocked = DraftSender(); blocked.sendCurrentMessage(); blocked.context.engine.data.emit(peer:peer)
            check(blocked.sent == 0 && blocked.interfaceInteraction?.alerts == 1, "unsupported fresh one-shot destination rejected")
        }
        for variant in 0..<5 {
            let blocked = DraftSender()
            if variant == 0 { blocked.chatPresentationInterfaceState.subject = .scheduledMessages }
            blocked.sendCurrentMessage(scheduleTime: variant == 1 ? 100 : nil, repeatPeriod: variant == 2 ? 10 : nil, postpone: variant == 3)
            blocked.context.engine.data.emit(stars: variant == 4 ? 1 : nil)
            check(blocked.sent == 0 && blocked.interfaceInteraction?.alerts == 1, "schedule/when-online/repeat/postpone/fees rejected before staging")
        }
        let ordinary = DraftSender(); ordinary.sendCurrentMessage(silentPosting:true); ordinary.context.engine.data.emit([Message(id:1)])
        ordinary.finishForward()
        check(ordinary.sent == 1 && ordinary.silent == true, "ordinary/silent native send preserved")
        if case .forward = ordinary.enqueued.first { check(true, "ordinary native forward preserved") } else { check(false, "ordinary message route changed") }
        let evicted = DraftSender(); evicted.sendCurrentMessage(); evicted.context.engine.data.emit()
        copyAvailable = false; evicted.finishForward(); copyAvailable = true
        check(evicted.enqueued.isEmpty && evicted.interfaceInteraction?.alerts == 1, "evicted local bytes never degrade to native forward")
        let cancelled = DraftSender(); cancelled.sendCurrentMessage(); cancelled.chatPresentationInterfaceState.interfaceState.forwardMessageIds = nil
        cancelled.context.engine.data.emit(); check(cancelled.sent == 0, "cancelled forward cannot enqueue late")
        let restored = DraftSender(); restored.sendCurrentMessage(); restored.context.engine.data.emit(); restored.finishForward()
        if case .message = restored.enqueued.first { check(true, "restored draft re-resolves own one-shot rather than requiring ephemeral payload") } else { check(false, "restored one-shot draft used server ID") }
        print("Transfer routing: \(count) checks passed; build113 contact-loss reproduced")
    }
}
