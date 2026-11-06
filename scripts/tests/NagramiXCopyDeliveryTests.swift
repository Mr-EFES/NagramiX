import Foundation

@main struct CopyDeliveryTests {
    static func main() throws {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) {
            if !value() { fatalError("Copy delivery regression: " + label) }; checks += 1
        }
        let box = MediaBox(), account = Account(box)
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let bytes = Data([1, 2, 3, 4])
        let source = root.appendingPathComponent("video"); try bytes.write(to: source)
        box.paths["video"] = source.path
        var post = Message(); post.text = "Caption 😀 https://example.org"; post.groupingKey = 44
        post.attributes = [TextEntitiesMessageAttribute(entities: [Entity(value: "bold/url")])]
        post.media = [TelegramMediaFile(resource: CloudResource("video"), size: 4, attributes: ["video"])]
        for free in [false, true] {
            NagramiXPrivacySettings.current.bypassScreenshots = free
            for protected in [false, true] {
                post.protected = protected
                check(nagramiXCanCopyMessagesAsNew([post]), "copy eligibility is independent of Free Content")
                check(post.nagramiXCopyNeedsLocalMedia == protected, "only protected/archive sources require preparation")
                let batch = nagramiXPrepareRecipientCopies([post, post], account: account, recipientCount: 2)!
                check(batch.recipientMessages.count == 2, "all recipients prepared")
                let a = batch.recipientMessages[0], b = batch.recipientMessages[1]
                check(a.count == 2 && a.map { $0.text } == [post.text, post.text], "whole post and captions preserved")
                check(a[0].localGroupingKey == a[1].localGroupingKey && a[0].localGroupingKey != b[0].localGroupingKey, "album keys independent per recipient")
                check(a[0].attributes.contains { $0 is TextEntitiesMessageAttribute }, "entities retained")
                if protected {
                    let af = a[0].mediaReference!.media as! TelegramMediaFile
                    let bf = b[0].mediaReference!.media as! TelegramMediaFile
                    let ar = af.resource as! LocalFileReferenceMediaResource, br = bf.resource as! LocalFileReferenceMediaResource
                    check(ar.localFilePath != br.localFilePath, "recipient temporary paths independent")
                    let copied = try Data(contentsOf: URL(fileURLWithPath: br.localFilePath))
                    check(copied == bytes, "full attachment bytes preserved")
                } else {
                    check(a.allSatisfy { if case .message? = $0.mediaReference { return true }; return false }, "ordinary media uses server references without staging")
                }
                let configured = a.map { $0.withUpdatedAttributes { $0 + [NotificationInfoMessageAttribute(muted: true), OutgoingScheduleInfoMessageAttribute(time: 123)] } }
                let scheduled = batch.messages(forRecipientAt: 1, template: configured)!
                check(scheduled.allSatisfy { $0.attributes.contains { ($0 as? NotificationInfoMessageAttribute)?.muted == true } }, "silent mode preserved")
                check(scheduled.allSatisfy { $0.attributes.contains { ($0 as? OutgoingScheduleInfoMessageAttribute)?.time == 123 } }, "schedule preserved")
                check(scheduled.map { $0.text } == a.map { $0.text }, "mode transform preserves content")
            }
        }
        post.protected = false
        var paid = post; paid.media = [TelegramMediaPaidContent(extendedMedia: [.full(post.media[0]), .full(post.media[0])])]
        let paidBatch = nagramiXPrepareRecipientCopies([paid], account: account, recipientCount: 2)!
        check(paidBatch.recipientMessages.allSatisfy { $0.count == 2 && $0[1].text.isEmpty }, "full paid bundle becomes complete own media")
        check(paidBatch.recipientMessages[0][0].localGroupingKey != paidBatch.recipientMessages[1][0].localGroupingKey, "paid albums never share recipient group IDs")
        paid.media = [TelegramMediaPaidContent(extendedMedia: [.full(post.media[0]), .preview])]
        check(nagramiXCopyMessagesAsNew([paid], account: account) == nil, "unavailable paid bytes not fabricated")
        var round = post; round.media = [TelegramMediaFile(resource: CloudResource("video"), attributes: ["round"])]
        let roundCopy = nagramiXCopyMessagesAsNew([round])!
        check(roundCopy.count == 2 && roundCopy[0].text == post.text && roundCopy[1].text.isEmpty, "round video caption remains visible as adjacent text")
        var text = post; text.media = []
        let noPreview = nagramiXCopyMessagesAsNew([text])![0]
        check(noPreview.attributes.contains { ($0 as? OutgoingContentInfoMessageAttribute)?.flags.contains(.disableLinkPreviews) == true }, "bare links never expand")
        let option = TelegramMediaPollOption(text: "Answer", entities: [], opaqueIdentifier: Data([1]), media: post.media[0], date: nil, addedBy: nil)
        let results = TelegramMediaPollResults(voters: nil, totalVoters: 50, recentVoters: [], solution: nil, hasUnseenVotes: nil, canViewStats: false)
        let poll = TelegramMediaPoll(pollId: MediaId(namespace: 0, id: 333), publicity: .anonymous, kind: .quiz(multipleAnswers: false), text: "Question", textEntities: [], options: [option], correctAnswers: [Data([1])], results: results, isClosed: true, deadlineTimeout: nil, deadlineDate: nil, pollHash: 0, openAnswers: false, revotingDisabled: false, shuffleAnswers: false, hideResultsUntilClose: false, isCreator: false, attachedMedia: nil, restrictToSubscribers: false, countries: [])
        var pollMessage = post; pollMessage.media = [poll]
        let copiedPoll = nagramiXCopyMessagesAsNew([pollMessage])![0].mediaReference!.media as! TelegramMediaPoll
        check(copiedPoll.pollId != poll.pollId && copiedPoll.results.totalVoters == nil && !copiedPoll.isClosed, "quiz gets own identity without foreign votes")
        check(copiedPoll.correctAnswers == [Data([1])] && copiedPoll.options[0].media != nil, "quiz answer and option attachment preserved")
        var unknown = post; unknown.media = [UnsupportedMedia()]
        check(nagramiXCanCopyMessagesAsNew([unknown]), "special objects reach resolver rather than disappear from menu")
        check(nagramiXCopyMessagesAsNew([unknown]) == nil, "unresolved unsupported object cannot silently lose media")
        var copy = post; copy.attributes += [OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy])]
        for code in ["CHAT_FORWARDS_RESTRICTED", "MEDIA_EMPTY", "MEDIA_INVALID"] { check(nagramiXCopyShouldReupload(copy, error: code), "definitive reference rejection triggers upload") }
        check(!nagramiXCopyShouldReupload(post, error: "MEDIA_INVALID"), "ordinary/native messages unaffected")
        copy.attributes += [ForwardSourceInfoAttribute()]
        check(!nagramiXCopyShouldReupload(copy, error: "CHAT_FORWARDS_RESTRICTED"), "native repost never converted into anonymous copy")
        copy.media = [TelegramMediaGame()]; copy.attributes = [OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy], nagramiXCopyFallbackText: "Original card")]
        check(nagramiXCopyServerFallbackText(copy, error: "GAME_ID_INVALID") == "Original card", "special fallback uses original prepared card")
        check(nagramiXCopyServerFallbackText(copy, error: "TIMEOUT") == nil, "lost acknowledgement must not create another send")
        check(nagramiXCopyServerFallbackText(copy, error: "USER_BANNED_IN_CHANNEL") == nil, "destination rights errors remain errors")
        var pending = post; pending.flags = [.Unsent]
        check(nagramiXCopiedMessageDeliveryState(pending, acknowledged: false) == .queued, "enqueue is not server acknowledgement")
        pending.flags = [.sending]
        check(nagramiXCopiedMessageDeliveryState(pending, acknowledged: false) == .queued, "upload is not server acknowledgement")
        check(nagramiXCopiedMessageDeliveryState(nil, acknowledged: false) == .queued, "missing pending record does not prove delivery")
        check(nagramiXCopiedMessageDeliveryState(nil, acknowledged: true) == .accepted, "native correlation proves server acceptance")
        pending.flags = [.Failed]
        check(nagramiXCopiedMessageDeliveryState(pending, acknowledged: false) == .failed, "recipient error retained")
        check(nagramiXCopiedMessageDeliveryState(pending, acknowledged: true) == .accepted, "acknowledged message never offered for duplicate retry")
        pending.flags = []
        check(nagramiXCopiedMessageDeliveryState(pending, acknowledged: false) == .accepted, "sent/scheduled native record accepted")
        print("Copy delivery payload checks: \(checks)")
    }
}
