private var checks = 0
private func expect(_ value: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    precondition(value(), label)
}

@main private enum Tests {
    static func main() throws {
        let base = NSTemporaryDirectory() + "/outgoing-archive-" + UUID().uuidString
        defer { try? FileManager.default.removeItem(atPath: base) }
        let own = PeerId(Int32(1)), other = PeerId(Int32(100))
        let peers: [PeerId: Peer] = [own: TestPeer(own), other: TestPeer(other)]
        let transaction = Transaction(peers)
        func settings(_ deleted: Bool, _ temporary: Bool, _ archive: ArchiveHarness) {
            UserDefaults.standard.set(deleted, forKey: "nagramix.messages.showDeletedMessages")
            UserDefaults.standard.set(temporary, forKey: "nagramix.messages.saveTemporaryMessages")
            UserDefaults.standard.set(false, forKey: "nagramix.messages.editHistory")
            archive.refresh()
        }
        func message(_ number: Int32, incoming: Bool = false, temporary: Bool = false,
                     media: [Media] = [], peer: PeerId? = nil, namespace: Int32 = 0,
                     extra: [MessageAttribute] = [], flags: StoreMessageFlags = []) -> StoreMessage {
            StoreMessage(id: .Id(MessageId(peerId: peer ?? other, namespace: namespace, id: number)),
                customStableId: nil, globallyUniqueId: nil, groupingKey: 42, threadId: 9,
                timestamp: 1000 + number, flags: incoming ? flags.union(.Incoming) : flags,
                tags: [], globalTags: [], localTags: [], forwardInfo: nil,
                authorId: incoming ? other : own, text: "caption \(number)",
                attributes: (temporary ? [AutoclearTimeoutMessageAttribute()] : []) + extra,
                media: media)
        }
        func id(_ message: StoreMessage) -> MessageId { if case let .Id(id) = message.id { return id }; fatalError() }
        let box = MediaBox(base + "/cache")
        let archive = ArchiveHarness(base + "/state", mediaBox: box)
        settings(true, true, archive)
        expect(!archive.legacyAccepts(message(1), peers: peers), "reproduce former outgoing rejection")
        expect(archive.legacyAccepts(message(1, incoming: true), peers: peers), "legacy incoming control")

        // All four switch states: no outgoing/incoming ingestion while disabled.
        for deleted in [false, true] {
            for temporarySetting in [false, true] {
                let unit = ArchiveHarness(base + "/matrix-\(deleted)-\(temporarySetting)", mediaBox: box)
                settings(deleted, temporarySetting, unit)
                for incoming in [false, true] {
                    for temporary in [false, true] {
                        let item = message(Int32(10 + (incoming ? 2 : 0) + (temporary ? 1 : 0)), incoming: incoming, temporary: temporary)
                        if incoming { unit.captureIncoming(item, peers: peers) }
                        else { unit.captureSent(item, transaction: transaction) }
                        unit.queue.drain()
                        expect(unit.hasSnapshot(id(item)) == (deleted && (!temporary || temporarySetting)), "capture switch matrix")
                    }
                }
            }
        }
        settings(true, true, archive)
        var retained: [(MessageId, Data)] = []
        for incoming in [false, true] {
            for (offset, kind) in ["voice", "round", "video", "photo"].enumerated() {
                let number = Int32(100 + offset + (incoming ? 10 : 0))
                let resource = TestResource("resource-\(number)")
                let path = box.cache + "/source-\(number)"
                let bytes = Data("complete attachment \(number)".utf8)
                try bytes.write(to: URL(fileURLWithPath: path))
                box.sources[resource.id] = path
                let media: Media = kind == "photo" ? TelegramMediaImage(resource) : TelegramMediaFile(resource, kind: kind)
                let item = message(number, incoming: incoming, temporary: true, media: [media])
                if incoming { archive.captureIncoming(item, peers: peers) }
                else { archive.captureSent(item, transaction: transaction) }
                expect(archive.cacheResourcesToRemove([resource.id]).isEmpty, "reserve before async capture")
                archive.queue.drain()
                expect(archive.wasIncoming(id(item)) == incoming, "stored actual direction")
                archive.archiveTemporaryExpiration(message: Message(item, peers: peers), expiredAt: 2000)
                archive.queue.drain()
                let rendered = archive.snapshotForExpiredMessage(id: id(item))!
                expect(rendered.flags.contains(.Incoming) == incoming, "render actual direction")
                expect(TagSpy.incoming.last == incoming, "tag actual direction")
                expect(rendered.author?.id == (incoming ? other : own), "preserve author")
                expect(rendered.threadId == 9 && rendered.groupingKey == 42, "preserve thread and group")
                expect(rendered.text == item.text, "preserve caption")
                expect(!rendered.attributes.contains { $0 is AutoclearTimeoutMessageAttribute || $0 is AutoremoveTimeoutMessageAttribute }, "local copy has no native expiration")
                expect(archive.cacheResourcesToRemove([resource.id]) == [resource.id], "independent copy permits native cache cleanup")
                _ = box.removeCachedResources([resource.id], force: true).start()
                expect(!FileManager.default.fileExists(atPath: path), "native cache bytes removed")
                let local = (rendered.media.first as? TelegramMediaFile)?.resource ?? (rendered.media.first as! TelegramMediaImage).representations[0].resource
                let localPath = (local as! LocalFileReferenceMediaResource).localFilePath
                expect(try! Data(contentsOf: URL(fileURLWithPath: localPath)) == bytes, "archive bytes survive cache purge")
                if kind != "photo" { expect((rendered.media.first as? TelegramMediaFile)?.kind == kind, "voice/round/video shape preserved") }
                retained.append((id(item), bytes))
            }
        }
        archive.queue.drain()
        let ordinary = message(200)
        archive.captureSent(ordinary, transaction: transaction)
        archive.queue.drain()
        archive.archiveServerDeletion(messageIds: [id(ordinary)], deletedAt: 3000)
        archive.queue.drain()
        expect(archive.deletedMessage(id: id(ordinary))?.text == ordinary.text, "ordinary outgoing deletion retained")
        expect(archive.deletedMessage(id: id(ordinary))?.flags.contains(.Incoming) == false, "ordinary outgoing side retained")

        // Reload real JSON/index/files; Postbox codec remains a controlled boundary.
        let loaded = ArchiveHarness(base + "/state", mediaBox: box)
        loaded.refresh(); loaded.queue.drain()
        for (key, bytes) in retained {
            let rendered = loaded.deletedMessage(id: key)!
            let local = (rendered.media.first as? TelegramMediaFile)?.resource ?? (rendered.media.first as! TelegramMediaImage).representations[0].resource
            expect(try! Data(contentsOf: URL(fileURLWithPath: (local as! LocalFileReferenceMediaResource).localFilePath)) == bytes, "reload actual archived bytes without cache")
            expect(loaded.wasIncoming(key) == (key.id >= 110), "JSON reload direction")
        }
        settings(true, false, loaded)
        for (key, _) in retained {
            expect(loaded.deletedMessage(id: key) == nil, "temporary off hides deleted snapshot")
            expect(loaded.snapshotForExpiredMessage(id: key) == nil, "temporary off hides expired replacement")
            expect(!loaded.containsArchivedMessage(id: key), "temporary off hides menu marker")
            expect(loaded.hasSnapshot(key), "temporary off retains approved metadata")
        }
        let visible = loaded.deletedMessages(peerId: other, threadId: 9, minIndex: nil, maxIndex: nil, limit: 1)
        expect(visible.count == 1 && visible.first?.id == id(ordinary), "filter before limit keeps ordinary deletion")
        expect(loaded.deletedMessages(peerId: other, threadId: 8, minIndex: nil, maxIndex: nil).isEmpty, "different topic excluded")
        settings(false, false, loaded)
        expect(loaded.deletedMessage(id: id(ordinary)) == nil, "deleted off hides ordinary copy")
        expect(loaded.deletedMessages(peerId: other, threadId: nil, minIndex: nil, maxIndex: nil).isEmpty, "deleted off hides history")
        expect(loaded.cacheResourcesToRemove([TestResource("missing").id]).count == 1, "disabled native cache cleanup")
        settings(true, true, loaded)
        expect(loaded.deletedMessage(id: retained[0].0) != nil, "reenable retained temporary copy")
        let countdown = message(250, extra: [AutoremoveTimeoutMessageAttribute()])
        loaded.archiveTemporaryExpiration(message: Message(countdown, peers: peers), expiredAt: 4000)
        loaded.queue.drain()
        expect(loaded.deletedMessage(id: id(countdown))?.flags.contains(.Incoming) == false, "capture outgoing autoremove before expiry when enabled later")
        settings(true, false, loaded)
        expect(loaded.deletedMessage(id: id(countdown)) == nil, "autoremove is gated by temporary setting")
        settings(true, true, loaded)
        let notSent = message(251, incoming: true)
        loaded.captureSent(notSent, transaction: transaction); loaded.queue.drain()
        expect(!loaded.hasSnapshot(id(notSent)), "send acknowledgment entry rejects incoming messages")
        let absent = MessageId(peerId: other, namespace: 0, id: 999)
        expect(loaded.snapshotForExpiredMessage(id: absent) == nil, "cannot invent already expired bytes")

        let excluded = [
            message(400, namespace: Namespaces.Message.Local),
            message(401, peer: PeerId(Int32(100), namespace: Namespaces.Peer.SecretChat)),
            message(402, peer: PeerId(Int32(777000))),
            message(403, media: [TelegramMediaPaidContent()]),
            message(404, flags: .CopyProtected),
            message(405, peer: own),
            message(406, extra: [EphemeralMessageAttribute()]),
            message(407, extra: [EphemeralOutgoingMessageAttribute()]),
            message(408, media: [TelegramMediaExpiredContent()])
        ]
        for item in excluded {
            loaded.captureSent(item, transaction: transaction); loaded.queue.drain()
            expect(!loaded.hasSnapshot(id(item)), "preserve native exclusion \(id(item).id)")
        }
        let protectedPeer = PeerId(Int32(300))
        let protectedItem = message(409, peer: protectedPeer)
        loaded.captureSent(protectedItem, transaction: Transaction([protectedPeer: TestPeer(protectedPeer, protected: true), own: TestPeer(own)]))
        loaded.queue.drain()
        expect(!loaded.hasSnapshot(id(protectedItem)), "protected peer exclusion")
        print("\(checks) bidirectional archive checks passed")
    }
}
