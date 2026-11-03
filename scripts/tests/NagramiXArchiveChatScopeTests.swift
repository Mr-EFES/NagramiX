@main
private struct ArchiveScopeTests {
    static func main() throws {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ message: String) {
            checks += 1
            if !value() { FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1) }
        }
        let defaults = UserDefaults.standard
        func settings(_ enabled: Bool) {
            defaults.set(enabled, forKey: "nagramix.messages.showDeletedMessages")
            defaults.set(false, forKey: "nagramix.messages.saveTemporaryMessages")
            defaults.set(false, forKey: "nagramix.messages.replayViewOnce")
            defaults.set(false, forKey: "nagramix.messages.editHistory")
        }
        let base = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: base) }
        let peer = PeerId(20), other = PeerId(30)
        func message(_ number: Int32, peerId: PeerId? = nil, thread: Int64? = nil,
                     timestamp: Int32 = 100, incoming: Bool = true, namespace: Int32 = 0) -> Message {
            Message(MessageId(peerId: peerId ?? peer, namespace: namespace, id: number), timestamp: timestamp,
                    thread: thread, grouping: 44, text: "message \(number)", incoming: incoming,
                    bytes: [Data([UInt8(truncatingIfNeeded: number), 2, 3])])
        }
        let postbox = Postbox()
        let archive = ArchiveHarness(path: base.appendingPathComponent("archive.json").path, postbox: postbox)
        let second = ArchiveHarness(path: base.appendingPathComponent("second.json").path, postbox: Postbox())
        check(ArchiveHarness.forMediaBox(postbox.mediaBox) === archive, "MediaBox resolves its own account archive")
        check(ArchiveHarness.forMediaBox(second.postbox.mediaBox) === second, "accounts remain isolated")
        check(ArchiveHarness.forMediaBox(MediaBox()) == nil, "unregistered MediaBox has no archive")
        settings(true)

        let incoming = message(1), outgoing = message(2, incoming: false)
        let transaction = Transaction([incoming, outgoing])
        performDelete(transaction: transaction, mediaBox: postbox.mediaBox, ids: [incoming.id, outgoing.id])
        check(archive.mediaStore.reserved.count == 2, "reserve media before native removal")
        check(transaction.messages.isEmpty, "native local/global deletion is preserved")
        Queue.drain()
        check(archive.records.count == 2, "deletion retains both directions")
        check(archive.record(incoming.id)?.deletedAt != nil && archive.record(outgoing.id)?.deletedAt != nil, "both messages marked deleted")
        check(archive.record(outgoing.id)?.incoming == false, "outgoing direction retained")
        check(archive.record(incoming.id)?.groupingKey == 44 && archive.record(incoming.id)?.content.media == incoming.bytes, "album and complete content retained")

        archive.removeLocal(messageIds: [incoming.id]); Queue.drain()
        check(archive.record(incoming.id) != nil, "individual delete must retain archived message")
        archive.clear(peerId: peer); Queue.drain()
        check(archive.records.count == 2 && archive.mediaStore.removed.isEmpty, "chat deletion never purges archive/media")
        let deletionDate = archive.record(incoming.id)?.deletedAt
        let edited = Message(incoming.id, text: "late edit", bytes: incoming.bytes)
        archive.recordIncomingEdit(previousMessage: incoming, replacementMessage: edited, peers: [:], receivedAt: 500)
        Queue.drain()
        check(archive.record(incoming.id)?.deletedAt == deletionDate && archive.record(incoming.id)?.content.text == "late edit", "late edit cannot unmark deleted snapshot")

        let previouslyCaptured = message(11, thread: 77)
        let replacement = Message(previouslyCaptured.id, thread: 77, text: "captured before clear")
        archive.recordIncomingEdit(previousMessage: previouslyCaptured, replacementMessage: replacement, peers: [:], receivedAt: 501)
        Queue.drain()
        check(archive.record(previouslyCaptured.id) != nil && archive.record(previouslyCaptured.id)?.deletedAt == nil, "previously captured live record starts unmarked")
        let absentFromPostbox = Transaction([])
        performClear(transaction: absentFromPostbox, mediaBox: postbox.mediaBox, peerId: peer, threadId: 77,
                     minTimestamp: nil, maxTimestamp: nil, namespaces: .all)
        Queue.drain()
        check(archive.record(previouslyCaptured.id)?.deletedAt != nil, "clearing marks retained records even after Postbox evicted them")

        var all = [message(3, thread: 9, timestamp: 101), message(4, thread: 9, timestamp: 102),
                   message(5, thread: 10, timestamp: 101), message(6, peerId: other, thread: 9)]
        let scoped = Transaction(all)
        performClear(transaction: scoped, mediaBox: postbox.mediaBox, peerId: peer, threadId: 9,
                     minTimestamp: 102, maxTimestamp: 102, namespaces: .all)
        Queue.drain()
        check(archive.record(all[1].id)?.deletedAt != nil, "range clear captures exact target")
        check(archive.record(all[0].id) == nil && archive.record(all[2].id) == nil && archive.record(all[3].id) == nil, "range/thread/peer isolation")
        check(scoped.messages.count == 3, "native range clear remains exact")
        performClear(transaction: scoped, mediaBox: postbox.mediaBox, peerId: peer, threadId: nil,
                     minTimestamp: nil, maxTimestamp: nil, namespaces: .all)
        Queue.drain()
        check(archive.record(all[0].id) != nil && archive.record(all[2].id) != nil, "whole-chat removal keeps all topics")
        check(scoped.messages.count == 1 && scoped.messages[0].id.peerId == other, "other dialog is untouched")

        let globalMessage = message(7)
        let global = Transaction([globalMessage])
        performGlobalDelete(transaction: global, postbox: postbox, ids: [7]); Queue.drain()
        check(global.messages.isEmpty && archive.record(globalMessage.id)?.deletedAt != nil, "server global deletion captures existing message before removal")
        let rangeMessages = [message(8), message(9), message(10)]
        let range = Transaction(rangeMessages)
        performRangeDelete(transaction: range, postbox: postbox, id: rangeMessages[1].id); Queue.drain()
        check(archive.record(rangeMessages[0].id) != nil && archive.record(rangeMessages[1].id) != nil && archive.record(rangeMessages[2].id) == nil, "server min-available deletion keeps exact ID range")

        let scheduled = message(90, namespace: Namespaces.Message.ScheduledCloud)
        let scheduledTransaction = Transaction([scheduled])
        performClear(transaction: scheduledTransaction, mediaBox: postbox.mediaBox, peerId: peer, threadId: nil,
                     minTimestamp: nil, maxTimestamp: nil, namespaces: .just([Namespaces.Message.ScheduledCloud]))
        Queue.drain()
        check(scheduledTransaction.enumerations == 0 && archive.record(scheduled.id) == nil, "scheduled clear never captures ordinary archive")

        let native = message(1000)
        let nativeEntry = MessageHistoryEntry(message: native, isRead: false, location: 8, monthLocation: 9,
                                             attributes: MutableMessageHistoryEntryAttributes(authorIsContact: true))
        func render(_ subject: ChatControllerSubject?, view: MessageHistoryView? = nil,
                    location: ChatLocation? = nil, music: Bool = false, recent: Bool = false) -> [MessageHistoryEntry] {
            renderHistory(context: TestContext(account: TestAccount(nagramiXMessageArchive: archive)),
                          subject: subject, view: view ?? MessageHistoryView(entries: [nativeEntry]),
                          location: location ?? ChatLocation(peerId: peer, threadId: nil), isMusicPlaylist: music,
                          associatedData: AssociatedData(isRecentActions: recent))
        }
        let archived = render(nil)
        check(archived.count > 1 && archived.contains { $0.message.isDeleted }, "original chat shows archive")
        let calls = archive.listCalls
        for subject in [ChatControllerSubject.pinnedMessages(id: nil), .pinnedMessages(id: 3), .scheduledMessages, .messageOptions, .customChatContents] {
            let result = render(subject)
            check(result.count == 1 && result[0].message === native, "pinned/scheduled/custom view must contain only native messages")
            check(!result[0].isRead && result[0].location == 8 && result[0].monthLocation == 9, "native metadata unchanged")
        }
        check(archive.listCalls == calls, "non-chat views do not even query archive")
        check(render(.message(id: 1)).count > 1, "jump to original chat message keeps archive")
        for view in [MessageHistoryView(entries: [nativeEntry], tag: "pinned"),
                     MessageHistoryView(entries: [nativeEntry], namespaces: .just([Namespaces.Message.ScheduledCloud])),
                     MessageHistoryView(entries: [nativeEntry], namespaces: .just([Namespaces.Message.ScheduledLocal]))] {
            check(render(nil, view: view).count == 1, "filtered/non-cloud view is native only")
        }
        check(render(nil, music: true).count == 1 && render(nil, recent: true).count == 1, "playlist/recent actions excluded")
        check(render(nil, location: ChatLocation(peerId: other, threadId: nil)).count == 1, "archive never leaks into another peer")
        let topic = render(nil, location: ChatLocation(peerId: peer, threadId: 9))
        check(topic.filter { $0.message.isDeleted }.allSatisfy { $0.message.threadId == 9 }, "topic archive stays within its thread")

        settings(false)
        let beforeOff = archive.records.count
        let off = Transaction([message(2000)])
        performDelete(transaction: off, mediaBox: postbox.mediaBox, ids: off.messages.map { $0.id }); Queue.drain()
        check(off.messages.isEmpty && archive.records.count == beforeOff, "OFF keeps native deletion without new capture")
        check(render(nil).count == 1, "OFF hides previous archive")
        let offClear = Transaction([message(2001)])
        performClear(transaction: offClear, mediaBox: postbox.mediaBox, peerId: peer, threadId: nil,
                     minTimestamp: nil, maxTimestamp: nil, namespaces: .all); Queue.drain()
        check(offClear.messages.isEmpty && offClear.enumerations == 0 && archive.records.count == beforeOff, "OFF clear neither captures nor purges approved data")
        settings(true)
        let reopened = ArchiveHarness(path: archive.path, postbox: Postbox()); reopened.load()
        check(reopened.records == archive.records, "real JSON reload retains full archive")

        all = (3000..<3340).map { message(Int32($0), timestamp: Int32($0)) }
        let large = Transaction(all)
        performClear(transaction: large, mediaBox: postbox.mediaBox, peerId: peer, threadId: nil,
                     minTimestamp: nil, maxTimestamp: nil, namespaces: .all); Queue.drain()
        let full = render(nil, view: MessageHistoryView(entries: []))
        check(full.count == archive.records.count && full.count > 200, "cleared chat shows every retained message, beyond old 200-row cap")
        check(zip(full, full.dropFirst()).allSatisfy { $0.message.index <= $1.message.index }, "archive order retained")
        archive.clearAll(); Queue.drain()
        check(archive.records.isEmpty && archive.mediaStore.clears == 1, "explicit full clear is the purge")
        let empty = ArchiveHarness(path: archive.path, postbox: Postbox()); empty.load()
        check(empty.records.isEmpty, "full clear persists an empty archive")
        print("PASS: \(checks) actual archive/history/native deletion bridge checks; JSON IO real; Postbox/UI/media boundaries")
    }
}
