@main enum RoundCaptionTransportTests {
    static var checks = 0
    static func check(_ value: @autoclosure () -> Bool, _ label: String) {
        if !value() { fatalError("Round caption regression: " + label) }
        checks += 1
    }
    static func info(_ message: EnqueueMessage) -> OutgoingContentInfoMessageAttribute? {
        return message.attributes.first { $0 is OutgoingContentInfoMessageAttribute } as? OutgoingContentInfoMessageAttribute
    }
    static func validate(_ copies: [EnqueueMessage], source: Message, emoji: MediaId) {
        check(copies.count == 2, "caption and round media are both present")
        check(copies[0].text == source.text && copies[0].mediaReference == nil, "caption remains adjacent text before the video")
        check(copies[1].text.isEmpty && (copies[1].mediaReference?.media as? TelegramMediaFile)?.isInstantVideo == true, "video remains a round recording without invisible caption")
        for part in copies {
            check(info(part)?.flags.contains(.nagramiXCopy) == true, "each part has persisted copy identity for retry")
            check(info(part)?.flags.contains(.disableLinkPreviews) == true, "bare links remain without an unsolicited preview")
            check(part.attributes.filter { $0 is OutgoingContentInfoMessageAttribute }.count == 1, "transport info is not duplicated")
        }
        check((copies[0].attributes.first { $0 is TextEntitiesMessageAttribute } as? TextEntitiesMessageAttribute)?.entities.map { $0.value } == ["bold/url/custom-emoji"], "caption formatting is preserved")
        check(copies[0].inlineStickers[emoji] is TelegramMediaContact, "caption retains its custom emoji resource")
        check(copies[1].inlineStickers.isEmpty && !copies[1].attributes.contains { $0 is TextEntitiesMessageAttribute }, "caption entities are not applied to the video")
        check(copies[0].attributes.allSatisfy { $0 is TextEntitiesMessageAttribute || $0 is OutgoingContentInfoMessageAttribute }, "caption does not inherit media spoiler, rich media or one-shot timer")
        check(copies.allSatisfy { $0.replyToMessageId == nil && $0.replyToStoryId == nil }, "original reply targets are not reused")
    }
    static func stored(_ output: EnqueueMessage, id: Int, flags: MessageFlags) -> Message {
        var result = Message()
        result.id.value = id
        result.flags = flags
        result.globallyUniqueId = Int64(1000 + id)
        result.groupingKey = output.localGroupingKey
        result.threadId = 77
        result.timestamp = 123
        result.author = TestUser(id: PeerId(value: 9))
        result.text = output.text
        result.media = output.mediaReference.map { [$0.media] } ?? []
        result.attributes = output.attributes + [RoundCaptionRandomId(value: Int64(9000 + id))]
        return result
    }
    static func main() throws {
        let box = MediaBox(), account = Account(box)
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let bytes = Data([0, 1, 2, 255])
        let file = root.appendingPathComponent("round.mp4")
        try bytes.write(to: file)
        box.paths["round"] = file.path
        let emoji = MediaId(namespace: 0, id: 999)
        var round = Message()
        round.text = "Автор 😀:\nПодпись https://example.org"
        round.media = [TelegramMediaFile(resource: CloudResource("round"), size: 4, attributes: ["round"])]
        round.attributes = [TextEntitiesMessageAttribute(entities: [Entity(value: "bold/url/custom-emoji", associatedMediaIds: [emoji])]), MediaSpoilerMessageAttribute(), AutoremoveTimeoutMessageAttribute(timeout: 60, countdownBeginTime: 1), UnrelatedAttribute()]
        round.associatedMedia[emoji] = TelegramMediaContact()
        let copies = nagramiXCopyMessagesAsNew([round])!
        validate(copies, source: round, emoji: emoji)
        let indexed = nagramiXCopyMessagesAsNewBySource([round])![round.id]!
        validate(indexed, source: round, emoji: emoji)
        for protected in [false, true] {
            round.protected = protected
            let batch = nagramiXPrepareRecipientCopies([round], account: account, recipientCount: 2)!
            for output in batch.recipientMessages { validate(output, source: round, emoji: emoji) }
            let configured = batch.recipientMessages[0].map { $0.withUpdatedAttributes { $0 + [NotificationInfoMessageAttribute(muted: true), OutgoingScheduleInfoMessageAttribute(time: 456)] } }
            let scheduled = batch.messages(forRecipientAt: 1, template: configured)!
            check(scheduled.allSatisfy { $0.attributes.contains { ($0 as? OutgoingScheduleInfoMessageAttribute)?.time == 456 } && $0.attributes.contains { ($0 as? NotificationInfoMessageAttribute)?.muted == true } }, "schedule and silent mode reach both parts")
            check(scheduled.allSatisfy { info($0)?.flags.contains([.nagramiXCopy, .disableLinkPreviews]) == true }, "send-mode configuration preserves caption transport")
            if protected {
                let resources = batch.recipientMessages.map { ($0[1].mediaReference!.media as! TelegramMediaFile).resource as! LocalFileReferenceMediaResource }
                check(resources[0].localFilePath != resources[1].localFilePath, "broadcast recipients retain independent media staging")
                let stagedBytes = try Data(contentsOf: URL(fileURLWithPath: resources[1].localFilePath))
                check(stagedBytes == bytes, "complete recording survives preparation")
            }
        }
        round.protected = false
        check(nagramiXCopyMessagesAsNew([round], hideCaptions: true)?.count == 1, "hidden caption does not create an extra text message")
        var captionless = round
        captionless.text = ""
        check(nagramiXCopyMessagesAsNew([captionless])?.count == 1, "empty caption does not create a blank text message")
        var ordinary = round
        ordinary.media = [TelegramMediaFile(resource: CloudResource("round"), attributes: ["video"])]
        check(nagramiXCopyMessagesAsNew([ordinary])?.count == 1, "ordinary video remains a single captioned message")

        // Retry the actual generated caption, the actual generated video, and
        // then both. An accepted part must never be sent a second time.
        for failed in [[0], [1], [0, 1]] {
            let db = account.postbox.storage
            db.messages = [:]; db.updates = []
            let original = copies.enumerated().map { stored($0.element, id: $0.offset + 1, flags: failed.contains($0.offset) ? [.Failed] : []) }
            for item in original { db.messages[item.id] = item }
            var unrelated = original[0]; unrelated.id.value = 3; unrelated.attributes = []; unrelated.flags = [.Failed]
            db.messages[unrelated.id] = unrelated
            var incoming = original[0]; incoming.id.value = 4; incoming.flags = [.Failed, .Incoming]
            db.messages[incoming.id] = incoming
            var pending = original[0]; pending.id.value = 5; pending.flags = [.Unsent]
            db.messages[pending.id] = pending
            let requested = original.map { $0.id } + [original[0].id, unrelated.id, incoming.id, pending.id]
            let disposable = nagramiXRetryCopiedMessages(account: account, messageIds: requested).start()
            disposable.dispose()
            check(Set(db.updates.map { $0.id.value }) == Set(failed.map { $0 + 1 }), "retry resumes exactly the failed generated parts")
            check(db.updates.count == failed.count, "duplicate selection does not duplicate retry")
            for update in db.updates {
                let source = original.first { $0.id == update.id }!
                check(update.globallyUniqueId == source.globallyUniqueId && (update.attributes.last as? RoundCaptionRandomId)?.value == (source.attributes.last as? RoundCaptionRandomId)?.value, "pending and RPC identities survive retry")
                check(update.text == source.text && update.media.count == source.media.count && update.threadId == source.threadId && update.groupingKey == source.groupingKey, "retry preserves caption, media, grouping and destination topic")
                check(update.flags == [.Unsent], "failed part returns to native outbox")
                check(update.attributes.contains { ($0 as? OutgoingContentInfoMessageAttribute)?.flags.contains([.nagramiXCopy, .disableLinkPreviews]) == true }, "retry preserves copy and preview policy")
            }
            let again = nagramiXRetryCopiedMessages(account: account, messageIds: original.map { $0.id }).start()
            again.dispose()
            check(db.updates.count == failed.count, "repeated retry cannot resend pending or accepted parts")
        }
        print("Round caption transport checks: \(checks)")
    }
}
