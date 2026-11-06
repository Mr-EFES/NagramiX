@main enum RepostCopyIntegrityTests {
    static var checks = 0
    static func check(_ value: @autoclosure () -> Bool, _ label: String) {
        if !value() { fatalError("Repost integrity regression: " + label) }
        checks += 1
    }
    static func require<T>(_ value: T?, _ label: String) -> T {
        guard let value else { fatalError("Repost integrity regression: " + label) }
        return value
    }
    static func main() throws {
        let defaults = UserDefaults.standard
        defaults.set(false, forKey: "nagramix.messages.saveTemporaryMessages")
        defaults.set(false, forKey: "nagramix.messages.replayViewOnce")
        let box = MediaBox(), account = Account(box)
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        var staged = Set<String>()
        defer {
            staged.forEach { try? FileManager.default.removeItem(atPath: $0) }
            try? FileManager.default.removeItem(at: root)
        }
        var expectedBytes: [String: Data] = [:]
        for i in 1 ... 8 {
            let key = "part\(i)", data = Data([UInt8(i), 2, 3, 4]), path = root.appendingPathComponent("part\(i)")
            try data.write(to: path); box.paths[key] = path.path; expectedBytes[key] = data
        }
        func message(_ id: Int, text: String, group: Int64? = nil, parts: [Int] = [], paid: Bool = false) -> Message {
            var result = Message(); result.id.value = id; result.text = text; result.groupingKey = group
            result.attributes = [TextEntitiesMessageAttribute(entities: [Entity(value: "bold/url")])]
            let media: [Media] = parts.map { TelegramMediaFile(resource: CloudResource("part\($0)"), size: 4, attributes: ["video"]) }
            result.media = paid ? [TelegramMediaPaidContent(extendedMedia: media.map { .full($0) })] : media
            return result
        }
        func bytes(_ value: EnqueueMessage) throws -> Data? {
            guard let file = value.mediaReference?.media as? TelegramMediaFile else { return nil }
            if let resource = file.resource as? LocalFileReferenceMediaResource {
                staged.insert(resource.localFilePath)
                return try Data(contentsOf: URL(fileURLWithPath: resource.localFilePath))
            }
            return expectedBytes[file.resource.id.stringRepresentation]
        }
        func assembled(_ composer: SourceComposer, _ label: String) -> [EnqueueMessage] {
            require(composer.output, label)
        }

        // Real reproduction: all primary bytes exist, but one source expands.
        let paid = message(10, text: "Bundle 😀 https://example.org", parts: [1, 2, 3], paid: true)
        let composer = SourceComposer(account: account, hideNames: true)
        composer.assemble([paid.id], resolved: [paid.id: paid], thread: 77)
        let complete = assembled(composer, "complete bundle must assemble")
        check(complete.count == 3, "one paid source retains every attachment")
        check(complete.map { $0.text } == [paid.text, "", ""], "caption belongs to its first attachment")
        check(complete.allSatisfy { $0.threadId == 77 }, "every expanded part inherits destination topic")
        check(complete[0].localGroupingKey != nil && Set(complete.map { $0.localGroupingKey }).count == 1, "expanded post keeps one album")
        check(complete[0].attributes.contains { $0 is TextEntitiesMessageAttribute }, "caption entities retained")
        check(complete.dropFirst().allSatisfy { !$0.attributes.contains { $0 is TextEntitiesMessageAttribute } }, "caption entities do not leak to other attachments")
        for (i, item) in complete.enumerated() {
            let actual = try bytes(item)
            check(actual == expectedBytes["part\(i + 1)"], "full bytes and attachment order retained")
        }

        // Unequal output counts must not shift later source IDs or their text.
        let first = message(20, text: "First", parts: [4, 5], paid: true)
        let text = message(25, text: "Between the albums")
        let last = message(30, text: "Last", parts: [6, 7], paid: true)
        let mixed = SourceComposer(account: account, hideNames: true)
        mixed.assemble([last.id, text.id, first.id], resolved: [last.id: last, text.id: text, first.id: first], thread: 88)
        let ordered = assembled(mixed, "mixed input must assemble")
        check(ordered.count == 5, "unequal source cardinalities preserve all outputs")
        check(ordered.map { $0.text } == ["First", "", text.text, "Last", ""], "later IDs never receive an earlier source's content")
        check(ordered.allSatisfy { $0.threadId == 88 }, "mixed outputs keep selected topic")
        check(ordered[0].localGroupingKey == ordered[1].localGroupingKey && ordered[3].localGroupingKey == ordered[4].localGroupingKey, "each expanded source retains its album")
        check(ordered[0].localGroupingKey != ordered[3].localGroupingKey, "independent posts never merge")
        for (i, key) in [(0, "part4"), (1, "part5"), (3, "part6"), (4, "part7")] {
            let actual = try bytes(ordered[i]); check(actual == expectedBytes[key], "source/media correspondence preserved")
        }

        // One conversion pass preserves groups spanning archive/live categories.
        var archived = message(40, text: "Archived", group: 777, parts: [1])
        archived.attributes += [NagramiXArchivedMessageAttribute()]
        let live = message(41, text: "", group: 777, parts: [2])
        account.nagramiXMessageArchive.messages = [archived.id: archived]
        let joined = SourceComposer(account: account, hideNames: true)
        joined.assemble([live.id, archived.id], resolved: [live.id: live])
        let joinedParts = assembled(joined, "mixed archive/live album")
        check(joinedParts.count == 2, "archive and live items retained")
        check(joinedParts[0].localGroupingKey != nil && joinedParts[0].localGroupingKey == joinedParts[1].localGroupingKey, "one album survives crossing copy categories")
        for item in joinedParts { _ = try bytes(item) }

        var stale = paid; stale.text = "Stale archive"; stale.attributes += [NagramiXArchivedMessageAttribute()]
        account.nagramiXMessageArchive.messages = [paid.id: stale]
        let overlap = SourceComposer(account: account, hideNames: true)
        overlap.assemble([paid.id], resolved: [paid.id: paid])
        let current = assembled(overlap, "overlapping lookups")
        check(current.count == 3 && current[0].text == paid.text, "existing resolved-source precedence is preserved without duplicate preparation")
        for item in current { _ = try bytes(item) }
        account.nagramiXMessageArchive.messages = [:]

        let native = SourceComposer(account: account)
        native.assemble([text.id], resolved: [text.id: text], thread: 99)
        let nativeOutput = assembled(native, "native repost")
        check(nativeOutput.count == 1 && nativeOutput[0].nativeForwardSource == text.id, "ordinary author-preserving repost remains a native forward")
        check(nativeOutput[0].threadId == 99, "native repost topic unchanged")
        var protected = text; protected.protected = true
        let denied = SourceComposer(account: account)
        denied.assemble([protected.id], resolved: [protected.id: protected])
        check(denied.output == nil && denied.interfaceInteraction?.errors == 1, "existing native protection guard still aborts the whole assembly")

        let hidden = SourceComposer(account: account, hideNames: true, hideCaptions: true)
        hidden.assemble([paid.id], resolved: [paid.id: paid])
        let noCaptions = assembled(hidden, "hidden captions")
        check(noCaptions.count == 3 && noCaptions.allSatisfy { $0.text.isEmpty }, "hiding captions does not discard attachments")
        for item in noCaptions { _ = try bytes(item) }

        var round = message(50, text: "Visible author caption", parts: [8])
        round.media = [TelegramMediaFile(resource: CloudResource("part8"), size: 4, attributes: ["round"])]
        let roundNext = message(51, text: "Following source")
        let roundComposer = SourceComposer(account: account, hideNames: true)
        roundComposer.assemble([roundNext.id, round.id], resolved: [round.id: round, roundNext.id: roundNext], thread: 66)
        let roundParts = assembled(roundComposer, "round expansion")
        check(roundParts.count == 3 && roundParts.map { $0.text } == [round.text, "", roundNext.text], "separate round caption cannot steal the next source ID")
        check(roundParts[0].mediaReference == nil && (roundParts[1].mediaReference?.media as? TelegramMediaFile)?.isInstantVideo == true, "round caption and media both survive")
        check(roundParts.allSatisfy { $0.threadId == 66 }, "round caption and media inherit the same topic")
        _ = try bytes(roundParts[1])

        let bySource = require(nagramiXCopyMessagesAsNewBySource([first, text, last]), "source ranges")
        check(bySource[first.id]?.count == 2 && bySource[text.id]?.count == 1 && bySource[last.id]?.count == 2, "every source owns its full range")
        check(bySource[text.id]?.first?.text == text.text, "range after an expanded source starts at its own output")
        check(nagramiXCopyMessagesAsNewBySource([]) == nil, "empty input rejected")
        check(nagramiXCopyMessagesAsNewBySource([text, text]) == nil, "duplicate source IDs rejected before staging")
        check(nagramiXCopyMessagesAsNew([text, text])?.count == 2, "legacy flat copier keeps duplicate-input behavior")

        let prefix = EnqueueMessage.message(text: "Comment", attributes: [], inlineStickers: [:], mediaReference: nil, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: nil, bubbleUpEmojiOrStickersets: [])
        let prefixed = SourceComposer(account: account, hideNames: true)
        prefixed.assemble([paid.id], resolved: [paid.id: paid], prefix: [prefix])
        let withComment = assembled(prefixed, "comment plus expanded post")
        check(withComment.count == 4 && withComment[0].text == "Comment", "composer comment remains before the entire copied post")
        for item in withComment { _ = try bytes(item) }

        var unavailable = paid; unavailable.id.value = 60
        unavailable.media = [TelegramMediaPaidContent(extendedMedia: [.full(TelegramMediaFile(resource: CloudResource("missing"), attributes: ["video"]))])]
        let failed = SourceComposer(account: account, hideNames: true)
        failed.assemble([first.id, unavailable.id], resolved: [first.id: first, unavailable.id: unavailable])
        check(failed.output == nil && failed.interfaceInteraction?.errors == 1, "failure in a later source cannot send an earlier partial result")
        var preview = paid; preview.media = [TelegramMediaPaidContent(extendedMedia: [.full(first.media[0]), .preview])]
        check(nagramiXCopyMessagesAsNewBySource([preview]) == nil, "unavailable paid content is never fabricated")

        let paidSend = SourceComposer(account: account, hideNames: true)
        paidSend.assemble([paid.id], resolved: [paid.id: paid])
        let chargedParts = assembled(paidSend, "paid destination")
        for item in chargedParts { _ = try bytes(item) }
        paidSend.submitPrepared(paid: true)
        check(paidSend.controller?.quotes == [3], "native fee confirmation uses every output, not one source ID")
        check(paidSend.sentModes.isEmpty, "no enqueue before native confirmation")
        paidSend.controller?.confirmation?(true)
        check(paidSend.sentModes == [true], "native postponement choice reaches submission")
        check(paidSend.sentCounts == [3], "confirmed fee and submitted complete payload have the same count")
        paidSend.controller?.confirmation?(false)
        check(paidSend.sentModes == [true], "a repeated native purchase callback cannot enqueue twice")
        for item in chargedParts {
            let data = try bytes(item); check(data != nil, "committed files survive release of the preparation lease")
        }
        let cancelled = SourceComposer(account: account, hideNames: true)
        cancelled.assemble([paid.id], resolved: [paid.id: paid])
        let cancelledParts = assembled(cancelled, "cancelled paid destination")
        let cancelledPaths = cancelledParts.compactMap { ($0.mediaReference?.media as? TelegramMediaFile)?.resource as? LocalFileReferenceMediaResource }.map { $0.localFilePath }
        cancelled.submitPrepared(paid: true)
        check(cancelledPaths.count == 3 && cancelledPaths.allSatisfy { FileManager.default.fileExists(atPath: $0) }, "preparation files remain pinned while the alert is open")
        cancelled.cancel()
        check(cancelled.sentModes.isEmpty && cancelledPaths.allSatisfy { !FileManager.default.fileExists(atPath: $0) }, "cancelling confirmation rolls back all staged files without sending")

        var plainModes: [Bool] = [], unexpectedQuotes = 0
        nagramiXSubmitComposerForwardMessages(messageCount: 1, requiresPayment: false, postpone: true, present: { _, _ in unexpectedQuotes += 1 }, send: { plainModes.append($0) })
        check(plainModes == [true] && unexpectedQuotes == 0, "ordinary native sends retain their existing postponement without another alert")
        var invalidSubmits = 0
        for count in [0, -1, Int(Int32.max) + 1] {
            nagramiXSubmitComposerForwardMessages(messageCount: count, requiresPayment: true, postpone: false, present: { _, _ in unexpectedQuotes += 1 }, send: { _ in invalidSubmits += 1 })
        }
        check(invalidSubmits == 0 && unexpectedQuotes == 0, "invalid paid counts cannot be underquoted or submitted")
        print("Repost copy integrity checks: \(checks)")
    }
}
