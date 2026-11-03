@main
private struct RecipientCopyTests {
    static func main() throws {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) {
            checks += 1
            if !value() { FileHandle.standardError.write(Data(("FAIL: " + label + "\n").utf8)); exit(1) }
        }
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        var nativeOwnedPaths: Set<String> = []
        defer {
            try? FileManager.default.removeItem(at: root)
            for path in nativeOwnedPaths { try? FileManager.default.removeItem(atPath: path) }
        }
        func stagingPaths() -> Set<String> {
            Set((try! FileManager.default.contentsOfDirectory(atPath: NSTemporaryDirectory())).filter { $0.hasPrefix("nagramix-archive-copy-") }.map { NSTemporaryDirectory() + $0 })
        }
        let initialPaths = stagingPaths()
        let box = MediaBox(), account = Account(box)
        var originals: [Message] = []
        let emoji = MediaId(namespace: 20, id: 44)
        for index in 0..<4 {
            let name = "photo-\(index)"
            let path = root.appendingPathComponent(name)
            try Data([UInt8(index), 10, 20, 30]).write(to: path)
            box.paths[name] = path.path
            var message = Message()
            message.id.value = index + 1
            message.protected = true
            message.groupingKey = 500
            message.text = index == 0 ? "Полная подпись 😀\n\nВторой абзац" : ""
            message.attributes = index == 0 ? [TextEntitiesMessageAttribute(entities: [Entity(value: "bold+emoji", associatedMediaIds: [emoji])]), MediaSpoilerMessageAttribute()] : []
            message.associatedMedia[emoji] = TelegramMediaContact()
            message.media = [TelegramMediaImage(representations: [TelegramMediaImageRepresentation(dimensions: Dimensions(width: 800, height: 1200), resource: CloudResource(name))])]
            originals.append(message)
        }
        func resource(_ message: EnqueueMessage) -> LocalFileReferenceMediaResource {
            guard case let .standalone(media)? = message.mediaReference else { fatalError("copy must use standalone media") }
            if let image = media as? TelegramMediaImage { return image.representations[0].resource as! LocalFileReferenceMediaResource }
            return (media as! TelegramMediaFile).resource as! LocalFileReferenceMediaResource
        }
        var batch: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies(originals, account: account, recipientCount: 2, forceLocalMedia: true)
        check(batch != nil && batch!.recipientMessages.map(\.count) == [4, 4], "both recipients receive exactly four album elements")
        let batches = batch!.recipientMessages
        let keys = batches.map { Set($0.compactMap(\.localGroupingKey)) }
        check(keys[0].count == 1 && keys[1].count == 1 && keys[0].isDisjoint(with: keys[1]), "each recipient must have a separate pending group")
        let paths = batches.map { Set($0.map { resource($0).localFilePath }) }
        check(paths[0].count == 4 && paths[1].count == 4 && paths[0].isDisjoint(with: paths[1]), "movable staging files are independent per recipient")
        for recipient in 0..<2 {
            check(batches[recipient].map(\.text) == originals.map(\.text), "caption, blank album slots and message order preserved for every recipient")
            check(batches[recipient][0].inlineStickers[emoji] != nil && batches[recipient][0].attributes.contains { $0 is TextEntitiesMessageAttribute }, "custom emoji and caption entities preserved")
            check(batches[recipient][0].attributes.contains { $0 is MediaSpoilerMessageAttribute }, "spoiler preserved")
            for index in 0..<4 {
                let file = resource(batches[recipient][index])
                check(file.isUniquelyReferencedTemporaryFile && (try! Data(contentsOf: URL(fileURLWithPath: file.localFilePath))) == Data([UInt8(index), 10, 20, 30]), "full independent media bytes retain source order")
            }
        }
        let collector = PendingCollector()
        collector.add(batches[0], peer: 100)
        collector.add(batches[1], peer: 200)
        for index in 0..<2 {
            let group = collector.collect(batches[index][0].localGroupingKey!)!
            check(group.count == 4 && Set(group.map { $0.messageId.peerId.value }) == [index == 0 ? 100 : 200], "native pending collector must not mix destination peers")
        }
        collector.holdUpload(peer: 200)
        check(collector.collect(batches[0][0].localGroupingKey!)?.count == 4, "another recipient upload cannot block the first album")
        check(collector.collect(batches[1][0].localGroupingKey!) == nil, "unfinished album retains native waiting behavior")
        // Verify the old production call pattern reproduces the video: one
        // payload reused for two peers merges eight entries in the native code.
        let old = nagramiXCopyMessagesAsNew(originals, account: account, forceLocalMedia: true)!
        nativeOwnedPaths.formUnion(old.map { resource($0).localFilePath })
        let oldCollector = PendingCollector(); oldCollector.add(old, peer: 100); oldCollector.add(old, peer: 200)
        let mixed = oldCollector.collect(old[0].localGroupingKey!)!
        check(mixed.count == 8 && Set(mixed.map { $0.messageId.peerId.value }).count == 2, "previous native collector defect is reproduced")
        oldCollector.holdUpload(peer: 200)
        check(oldCollector.collect(old[0].localGroupingKey!) == nil, "old shared group stalls both peers when one waits")

        let comment = EnqueueMessage.message(text: "Комментарий", attributes: [NotificationInfoMessageAttribute(muted: true)], inlineStickers: [:], mediaReference: nil, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: nil, bubbleUpEmojiOrStickersets: [])
        let configured = batches[0].map { message in message.withUpdatedAttributes { $0 + [NotificationInfoMessageAttribute(muted: true), OutgoingScheduleInfoMessageAttribute(time: 1234)] } }
        for index in 0..<2 {
            let prepared = batch!.messages(forRecipientAt: index, template: [comment] + configured)!
            check(prepared.count == 5 && prepared[0].text == "Комментарий" && prepared[0].localGroupingKey == nil, "comment remains separate and precedes each album")
            check(prepared.dropFirst().map(\.text) == originals.map(\.text), "silent/scheduled transform never changes caption")
            check(prepared.dropFirst().allSatisfy { $0.attributes.contains { ($0 as? OutgoingScheduleInfoMessageAttribute)?.time == 1234 } }, "chosen schedule preserved in each destination")
            check(prepared.dropFirst().allSatisfy { $0.attributes.contains { ($0 as? NotificationInfoMessageAttribute)?.muted == true } }, "silent mode preserved in each destination")
            check(Set(prepared.dropFirst().map { resource($0).localFilePath }) == paths[index], "template cannot substitute another recipient's resources")
        }
        check(batch!.messages(forRecipientAt: 2, template: configured) == nil && batch!.messages(forRecipientAt: 0, template: []) == nil, "invalid recipient or incomplete template cannot produce a partial post")
        batch = nil
        check(paths.flatMap { $0 }.allSatisfy { !FileManager.default.fileExists(atPath: $0) }, "cancelled schedule/payment removes all uncommitted files")

        var committed: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies(originals, account: account, recipientCount: 2, forceLocalMedia: true)
        let committedMessages = committed!.recipientMessages
        let committedPaths = committedMessages.map { $0.map { resource($0).localFilePath } }
        committed!.commit(); committed!.commit(); committed = nil
        nativeOwnedPaths.formUnion(committedPaths.flatMap { $0 })
        check(committedPaths.flatMap { $0 }.allSatisfy { FileManager.default.fileExists(atPath: $0) }, "accepted batch transfers file ownership to native send")
        // Native Fetch.swift moves uniquely-referenced files. Moving the first
        // peer's paths must leave the second peer's complete byte sources intact.
        for (i, path) in committedPaths[0].enumerated() { try FileManager.default.moveItem(atPath: path, toPath: root.appendingPathComponent("uploaded-\(i)").path) }
        check(committedPaths[1].allSatisfy { FileManager.default.fileExists(atPath: $0) }, "one destination consuming its temp files cannot stall another")
        for (i, path) in committedPaths[1].enumerated() { check((try! Data(contentsOf: URL(fileURLWithPath: path))) == Data([UInt8(i), 10, 20, 30]), "second recipient still owns full bytes after first upload") }

        var hidden: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies(originals, account: account, recipientCount: 2, hideCaptions: true, forceLocalMedia: true)
        check(hidden!.recipientMessages.flatMap { $0 }.allSatisfy { $0.text.isEmpty && $0.inlineStickers.isEmpty && !$0.attributes.contains { $0 is TextEntitiesMessageAttribute } }, "explicit hide captions still applies to every recipient")
        hidden = nil
        var text = Message(); text.text = "Просто текст"; text.protected = true
        var textBatch: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies([text], account: account, recipientCount: 3, forceLocalMedia: true)
        check(textBatch!.recipientMessages.map { $0[0].text } == Array(repeating: text.text, count: 3), "text-only broadcast remains complete")
        textBatch = nil
        check(nagramiXPrepareRecipientCopies([], account: account, recipientCount: 2) == nil && nagramiXPrepareRecipientCopies(originals, account: account, recipientCount: 0) == nil, "empty recipients/source are rejected")
        let beforeFailure = stagingPaths()
        var unavailable = originals; unavailable[3].media = [TelegramMediaImage(representations: [TelegramMediaImageRepresentation(dimensions: Dimensions(width: 1, height: 1), resource: CloudResource("missing"))])]
        check(nagramiXPrepareRecipientCopies(unavailable, account: account, recipientCount: 2, forceLocalMedia: true) == nil, "missing attachment prevents preparation of all recipients")
        check(stagingPaths() == beforeFailure, "failed album staging rolls back already copied files")
        var lookups = 0
        box.lookupHook = { resource in
            lookups += 1
            return lookups > 4 ? nil : box.paths[resource.id.stringRepresentation]
        }
        check(nagramiXPrepareRecipientCopies(originals, account: account, recipientCount: 2, forceLocalMedia: true) == nil, "second recipient preparation failure rejects the whole operation")
        box.lookupHook = nil
        check(stagingPaths() == beforeFailure, "failure in a later recipient rolls back the first recipient's files too")

        var document = Message(); document.protected = true; document.id.value = 10; document.text = "Документ"
        document.media = [TelegramMediaFile(resource: CloudResource("photo-0"), mimeType: "application/pdf", size: 4, attributes: ["fileName=report.pdf"], fileName: "report.pdf")]
        var secondAlbum = Array(originals.prefix(2))
        for i in secondAlbum.indices { secondAlbum[i].groupingKey = 600; secondAlbum[i].id.value = 20 + i }
        var mixedBatch: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies(originals + [document, text] + secondAlbum, account: account, recipientCount: 2, forceLocalMedia: true)
        for copies in mixedBatch!.recipientMessages {
            check(copies.count == 8 && copies[4].text == document.text && copies[5].text == text.text, "mixed messages/files preserve position for each recipient")
            check(copies[4].localGroupingKey == nil && copies[5].localGroupingKey == nil && copies[0].localGroupingKey != copies[6].localGroupingKey, "separate albums and standalone messages remain separate")
            guard case let .standalone(media)? = copies[4].mediaReference, let file = media as? TelegramMediaFile else { fatalError("file copy missing") }
            check(file.mimeType == "application/pdf" && file.attributes == ["fileName=report.pdf"] && file.fileId.namespace == Namespaces.Media.LocalFile, "document payload and independent native identity preserved")
        }
        mixedBatch = nil
        let richPage = InstantPage(blocks: ["paragraph", "image"], rawMedia: [emoji: originals[0].media[0]], isComplete: true, rtl: false, url: "https://example.org/post", views: 20)
        var richPost = Message(); richPost.text = ""; richPost.protected = true
        richPost.attributes = [RichTextMessageAttribute(instantPage: richPage, fullInstantPage: nil)]
        var richBatch: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies([richPost], account: account, recipientCount: 2, forceLocalMedia: true)
        let richFirst = richBatch!.recipientMessages[0]
        let richSecond = richBatch!.messages(forRecipientAt: 1, template: richFirst)!
        let firstPage = (richFirst[0].attributes[0] as! RichTextMessageAttribute).instantPage
        let secondPage = (richSecond[0].attributes[0] as! RichTextMessageAttribute).instantPage
        let firstResource = (firstPage.rawMedia[emoji] as! TelegramMediaImage).representations[0].resource as! LocalFileReferenceMediaResource
        let secondResource = (secondPage.rawMedia[emoji] as! TelegramMediaImage).representations[0].resource as! LocalFileReferenceMediaResource
        check(firstPage.blocks == secondPage.blocks && firstPage.rawMedia.keys == secondPage.rawMedia.keys, "rich post blocks and embedded media keys preserved")
        check(firstResource.localFilePath != secondResource.localFilePath && FileManager.default.fileExists(atPath: secondResource.localFilePath), "send template cannot leak the first recipient's rich-media resources")
        richBatch = nil

        let sendBatch = nagramiXPrepareRecipientCopies(originals, account: account, recipientCount: 2, forceLocalMedia: true)!
        nativeOwnedPaths.formUnion(sendBatch.recipientMessages.flatMap { $0.map { resource($0).localFilePath } })
        let sender = RecipientSender(account)
        let firstQueue = ManualEnqueue(), secondQueue = ManualEnqueue()
        var confirmations = 0
        sender.start(sendBatch, signals: [firstQueue.signal, secondQueue.signal], counts: [4, 4]) { confirmations += 1 }
        check(firstQueue.starts == 1 && secondQueue.starts == 1 && confirmations == 0, "both native queues start before either recipient completes")
        firstQueue.accept(peer: 100, count: 4)
        check(confirmations == 0, "first recipient alone never confirms the entire broadcast")
        secondQueue.accept(peer: 200, count: 4)
        check(confirmations == 1 && sender.errors == 0, "confirmation follows acceptance of every full recipient batch")
        firstQueue.accept(peer: 100, count: 4); secondQueue.accept(peer: 200, count: 4)
        check(confirmations == 1 && firstQueue.starts == 1 && secondQueue.starts == 1, "repeated callbacks cannot enqueue or confirm another broadcast")
        check(account.pendingMessageManager.watched.count == 8 && Set(account.pendingMessageManager.watched.map { $0.peerId.value }) == [100, 200], "pending observers cover all recipients instead of replacing one another")
        let failedSender = RecipientSender(account), badFirst = ManualEnqueue(), badSecond = ManualEnqueue()
        failedSender.start(sendBatch, signals: [badFirst.signal, badSecond.signal], counts: [4, 4]) { confirmations += 1 }
        badFirst.accept(peer: 100, count: 4); badSecond.subscriber?.putNext([nil, nil, nil, nil])
        check(failedSender.errors == 1 && confirmations == 1, "missing native queue IDs show an error instead of a false success")
        check(initialPaths.isSubset(of: stagingPaths()), "unrelated staged files are untouched")
        print("PASS: \(checks) actual recipient copy/staging/native pending group checks; real Foundation IO; Postbox/API boundaries")
    }
}
