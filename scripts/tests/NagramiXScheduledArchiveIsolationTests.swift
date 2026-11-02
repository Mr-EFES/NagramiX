import Foundation

private enum ChatControllerSubject: Equatable { case scheduledMessages, message, pinnedMessages }
private struct ChatLocation {
    let peerId: PeerId?
    let threadId: Int64?
}
private struct MutableMessageHistoryEntryAttributes { let authorIsContact: Bool }
private struct MessageHistoryEntry {
    let message: Message
    let isRead: Bool
    let location: Int?
    let monthLocation: Int?
    let attributes: MutableMessageHistoryEntryAttributes
}
private struct MessageHistoryView {
    let entries: [MessageHistoryEntry]
    let earlierId: MessageId?
    let laterId: MessageId?
}
private final class HistoryArchive {
    let archive: ArchiveHarness
    var snapshotCalls = 0
    var listCalls = 0
    init(_ archive: ArchiveHarness) { self.archive = archive }
    func snapshotForExpiredMessage(id: MessageId) -> Message? {
        self.snapshotCalls += 1
        return self.archive.snapshotForExpiredMessage(id: id)
    }
    func deletedMessages(peerId: PeerId, threadId: Int64?, minIndex: MessageIndex?, maxIndex: MessageIndex?) -> [Message] {
        self.listCalls += 1
        return self.archive.deletedMessages(peerId: peerId, threadId: threadId, minIndex: minIndex, maxIndex: maxIndex)
    }
    func reset() { self.snapshotCalls = 0; self.listCalls = 0 }
}
private struct HistoryAccount { let nagramiXMessageArchive: HistoryArchive }
private struct HistoryContext { let account: HistoryAccount }

private func renderedSources(context: HistoryContext, location: ChatLocation, subject: ChatControllerSubject?, view: MessageHistoryView) -> [MessageHistoryEntry] {
    // PRODUCTION_SOURCE_ENTRIES
    return sourceEntries
}

@main private struct ScheduledArchiveIsolationTests {
    static func main() throws {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ message: String) {
            checks += 1
            if !condition() {
                FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8))
                exit(1)
            }
        }
        let base = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString).path
        defer { try? FileManager.default.removeItem(atPath: base) }
        let own = PeerId(Int32(1)), peer = PeerId(Int32(200)), other = PeerId(Int32(300))
        let peers: [PeerId: Peer] = [own: TestPeer(own), peer: TestPeer(peer), other: TestPeer(other)]
        let transaction = Transaction(peers), box = MediaBox(base + "/cache")
        let archive = ArchiveHarness(base + "/state", mediaBox: box)
        func settings(_ enabled: Bool, _ temporary: Bool) {
            UserDefaults.standard.set(enabled, forKey: "nagramix.messages.showDeletedMessages")
            UserDefaults.standard.set(temporary, forKey: "nagramix.messages.saveTemporaryMessages")
            UserDefaults.standard.set(false, forKey: "nagramix.messages.editHistory")
            archive.refresh()
        }
        func message(_ number: Int32, namespace: Int32 = Namespaces.Message.Cloud, timestamp: Int32 = 100,
                     thread: Int64? = nil, inPeer: PeerId? = nil, media: [Media] = [], temporary: Bool = false) -> StoreMessage {
            StoreMessage(id: .Id(MessageId(peerId: inPeer ?? peer, namespace: namespace, id: number)), customStableId: nil,
                         globallyUniqueId: nil, groupingKey: nil, threadId: thread, timestamp: timestamp, flags: [],
                         tags: [], globalTags: [], localTags: [], forwardInfo: nil, authorId: own, text: "message \(number)",
                         attributes: temporary ? [AutoclearTimeoutMessageAttribute()] : [], media: media)
        }
        func id(_ item: StoreMessage) -> MessageId { if case let .Id(id) = item.id { return id }; fatalError() }
        func entry(_ item: StoreMessage) -> MessageHistoryEntry {
            MessageHistoryEntry(message: Message(item, peers: peers), isRead: false, location: 8, monthLocation: 9,
                                attributes: MutableMessageHistoryEntryAttributes(authorIsContact: true))
        }
        settings(true, true)
        var archivedIds = Set<MessageId>()
        for (offset, kind) in ["voice", "round", "photo"].enumerated() {
            let resource = TestResource(kind), path = base + "/" + kind
            try Data([1, 2, 3, 4]).write(to: URL(fileURLWithPath: path))
            box.sources[resource.id] = path
            let media: Media = kind == "photo" ? TelegramMediaImage(resource) : TelegramMediaFile(resource, kind: kind)
            let item = message(Int32(offset + 1), timestamp: Int32(100 + offset), thread: 9, media: [media], temporary: true)
            archive.captureSent(item, transaction: transaction); archive.queue.drain()
            archive.markTemporaryExpired(id: id(item), expiredAt: 150); archive.queue.drain()
            archivedIds.insert(id(item))
        }
        let deleted = message(4, timestamp: 104, thread: 9)
        archive.captureSent(deleted, transaction: transaction); archive.queue.drain()
        archive.archiveServerDeletion(messageIds: [id(deleted)], deletedAt: 150); archive.queue.drain()
        archivedIds.insert(id(deleted))
        let outside = message(5, timestamp: 105, thread: 10)
        archive.captureSent(outside, transaction: transaction); archive.queue.drain()
        archive.archiveServerDeletion(messageIds: [id(outside)], deletedAt: 150); archive.queue.drain()
        let foreign = message(6, inPeer: other)
        archive.captureSent(foreign, transaction: transaction); archive.queue.drain()
        archive.archiveServerDeletion(messageIds: [id(foreign)], deletedAt: 150); archive.queue.drain()
        let seededWrites = archive.writes
        let adapter = HistoryArchive(archive), context = HistoryContext(account: HistoryAccount(nagramiXMessageArchive: adapter))
        let location = ChatLocation(peerId: peer, threadId: 9)
        let scheduled = entry(message(100, namespace: Namespaces.Message.ScheduledCloud, timestamp: 500_000))
        let pending = entry(message(101, namespace: Namespaces.Message.ScheduledLocal, timestamp: 600_000))
        let live = entry(message(20, timestamp: 200, thread: 9))
        for enabled in [true, false] {
            for temporary in [true, false] {
                settings(enabled, temporary)
                // The screenshot: future scheduled text plus older archived
                // voice/round/photo. The view must keep only the native text.
                for boundary in [false, true] {
                    adapter.reset()
                    let view = MessageHistoryView(entries: [scheduled], earlierId: boundary ? live.message.id : nil,
                                                  laterId: boundary ? pending.message.id : nil)
                    let result = renderedSources(context: context, location: location, subject: .scheduledMessages, view: view)
                    check(result.count == 1 && result[0].message === scheduled.message,
                          "scheduled list must contain only native scheduled message")
                    check(!result[0].isRead && result[0].location == 8 && result[0].monthLocation == 9 && result[0].attributes.authorIsContact,
                          "scheduled entry metadata must be unchanged")
                    check(adapter.listCalls == 0 && adapter.snapshotCalls == 0, "scheduled list never queries archive")
                }
                adapter.reset()
                let empty = renderedSources(context: context, location: location, subject: .scheduledMessages,
                                            view: MessageHistoryView(entries: [], earlierId: nil, laterId: nil))
                check(empty.isEmpty && adapter.listCalls == 0, "empty scheduled view remains empty")
                let ordinary = renderedSources(context: context, location: location, subject: nil,
                                               view: MessageHistoryView(entries: [live], earlierId: nil, laterId: nil))
                let expected = enabled ? (temporary ? archivedIds : Set([id(deleted)])) : []
                check(Set(ordinary.map { $0.message.id }) == expected.union([live.message.id]),
                      "ordinary history retains existing archive settings and thread filter")
            }
        }
        settings(true, true)
        let subjects: [ChatControllerSubject?] = [nil, .message, .pinnedMessages]
        for subject in subjects {
            adapter.reset()
            let normal = renderedSources(context: context, location: location, subject: subject,
                                         view: MessageHistoryView(entries: [live], earlierId: nil, laterId: nil))
            check(normal.count == 5 && adapter.listCalls == 1, "other subject behavior is preserved")
            check(normal.map { $0.message.index } == normal.map { $0.message.index }.sorted(), "ordinary archive sorting remains native")
        }
        adapter.reset()
        let multiple = renderedSources(context: context, location: location, subject: .scheduledMessages,
                                       view: MessageHistoryView(entries: [pending, scheduled], earlierId: nil, laterId: nil))
        check(multiple.count == 2 && multiple[0].message === pending.message && multiple[1].message === scheduled.message,
              "scheduled merge does not change native order or deduplicate native entries")
        check(adapter.listCalls == 0 && adapter.snapshotCalls == 0, "multiple scheduled entries bypass archive")
        adapter.reset()
        let placeholder = entry(message(1, timestamp: 100, thread: 9, media: [TelegramMediaExpiredContent()]))
        let expiredView = MessageHistoryView(entries: [placeholder], earlierId: nil, laterId: nil)
        let hidden = renderedSources(context: context, location: location, subject: .scheduledMessages, view: expiredView)
        check(hidden.count == 1 && hidden[0].message === placeholder.message && adapter.snapshotCalls == 0,
              "scheduled view cannot restore ordinary expired placeholder by ID")
        let restored = renderedSources(context: context, location: location, subject: nil, view: expiredView)
        check(restored.contains { $0.message.id == placeholder.message.id && $0.message !== placeholder.message
            && $0.message.media.first is TelegramMediaFile }, "ordinary expired media restoration remains available")
        for namespace in [Namespaces.Message.ScheduledCloud, Namespaces.Message.ScheduledLocal] {
            let draft = message(1000 + namespace, namespace: namespace)
            archive.captureSent(draft, transaction: transaction); archive.queue.drain()
            check(!archive.hasSnapshot(id(draft)), "scheduled template must not be captured as sent archive")
        }
        let reopened = ArchiveHarness(base + "/state", mediaBox: box)
        check(reopened.deletedMessages(peerId: peer, threadId: 9, minIndex: nil, maxIndex: nil).count == 4,
              "view isolation does not delete persisted archived messages")
        archive.queue.drain()
        check(archive.writes == seededWrites, "view isolation must not rewrite or remove persisted archive")
        print("PASS: \(checks) scheduled/ordinary history integration checks; real archive methods and file store; UI/Postbox boundaries")
    }
}
