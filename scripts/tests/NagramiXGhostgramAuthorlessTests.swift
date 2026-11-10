import Foundation

private var checks = 0
private func check(_ value: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    if !value() { fputs("Authorless regression: \(label)\n", stderr); exit(97) }
}

@main struct GhostgramAuthorlessTests {
    static var serial = 10
    static func source(_ media: [Media] = []) -> Message {
        serial += 1
        var result = Message()
        result.id.value = serial; result.media = media
        result.author = TestUser(id: PeerId(value: 99))
        return result
    }
    static func forward(_ value: EnqueueMessage, original: Message, hiddenCaption: Bool = false) {
        guard case let .forward(id, thread, grouping, attributes, correlation) = value else {
            check(false, "ordinary objects retain the fast path"); return
        }
        check(id == original.id && thread == nil && correlation == nil, "live ID preserved without source destination state")
        if case .auto = grouping {} else { check(false, "native album grouping") }
        let options = attributes.compactMap { $0 as? ForwardOptionsMessageAttribute }
        check(options.count == 1 && options[0].hideNames, "fast route hides author")
        check(options[0].hideCaptions == hiddenCaption, "caption choice preserved")
        check(!attributes.contains { $0 is OutgoingContentInfoMessageAttribute }, "fast path never masquerades as a byte copy")
        check(!forwardKeepsSenderHeader(media: original.media), "fast route cannot retain an author header")
        let flags = productionForwardFlags(original, options: options[0])
        check(flags & (1 << 11) != 0, "native RPC receives drop_author")
        check((flags & (1 << 12) != 0) == hiddenCaption, "native RPC receives caption choice")
    }
    static func main() throws {
        let box = MediaBox(), account: Account
        account = Account(box)
        LocalCopyDefaultsBoundary.shared.enabled = true
        let kinds: [[Media]] = [[], [TelegramMediaFile(resource: CloudResource("video"), attributes: ["video"])],
            [TelegramMediaFile(resource: CloudResource("round"), attributes: ["round"])],
            [TelegramMediaFile(resource: CloudResource("voice"), attributes: ["voice"])],
            [TelegramMediaFile(resource: CloudResource("audio"), attributes: ["music"])],
            [TelegramMediaFile(resource: CloudResource("gif"), attributes: ["animated"])],
            [TelegramMediaFile(resource: CloudResource("document"))],
            [TelegramMediaFile(resource: CloudResource("sticker"), attributes: ["sticker"])],
            [TelegramMediaImage(representations: [.init(dimensions: .init(width: 640, height: 480), resource: CloudResource("photo"))])],
            [TelegramMediaContact()], [TelegramMediaMap()], [TelegramMediaDice()], [TelegramMediaInvoice()],
            [TelegramMediaStory()], [TelegramMediaGiveaway()], [TelegramMediaTodo()], [TelegramMediaGame()],
            [TelegramMediaWebpage()], [TelegramMediaPaidContent()]]
        for media in kinds {
            let message = source(media)
            check(nagramiXCanForwardWithoutAuthor(message), "ordinary objects retain the fast path")
            for hide in [false, true] {
                let batch = nagramiXPrepareRecipientCopies([message], account: account, recipientCount: 3, hideCaptions: hide)!
                for recipient in batch.recipientMessages {
                    check(recipient.count == 1, "one full object per destination")
                    forward(recipient[0], original: message, hiddenCaption: hide)
                }
                check(box.fetched.isEmpty && box.paths.isEmpty, "no cache download for native forward")
            }
        }
        // Received poll identity, results, option media and unknown quiz answers
        // are not rebuilt on the native route. The same ID is forwarded.
        let options = [TelegramMediaPollOption(text: "One", entities: [], opaqueIdentifier: Data([9]), media: nil, date: nil, addedBy: nil)]
        let video = TelegramMediaFile(resource: CloudResource("poll-video"), size: 4, attributes: ["video"])
        let poll = TelegramMediaPoll(pollId: MediaId(namespace: 55, id: 501), publicity: .anonymous, kind: .quiz(multipleAnswers: false),
            text: "Video quiz", textEntities: [], options: options, correctAnswers: nil,
            results: .init(voters: nil, totalVoters: 12, recentVoters: [], solution: nil, hasUnseenVotes: nil, canViewStats: false),
            isClosed: false, deadlineTimeout: nil, deadlineDate: nil, pollHash: 900, attachedMedia: video)
        let vote = source([poll])
        forward(nagramiXMessagesWithoutAuthor([vote], account: account)![0], original: vote)
        check(box.fetched.isEmpty, "video poll does not wait for bytes")
        check(nagramiXCopyMessagesAsNew([vote], account: account) == nil, "strict copy API never guesses unknown quiz answer")

        var temporary = source([video]); temporary.minAutoremoveOrClearTimeout = viewOnceTimeout; temporary.containsSecretMedia = true
        check(!nagramiXCanForwardWithoutAuthor(temporary), "temporary source ID never forwarded")
        var rawTemporary = source([video]); rawTemporary.attributes = [AutoremoveTimeoutMessageAttribute(timeout: viewOnceTimeout, countdownBeginTime: nil)]
        check(!nagramiXCanForwardWithoutAuthor(rawTemporary), "raw TTL blocks fast path independently of retention setting")
        var retained = source([video]); retained.attributes = [NagramiXArchivedMessageAttribute(isTemporary: true)]
        check(!nagramiXCanForwardWithoutAuthor(retained), "retained temporary never forwards old ID")
        var deleted = source(); deleted.attributes = [NagramiXArchivedMessageAttribute()]
        check(!nagramiXCanForwardWithoutAuthor(deleted), "deleted original ID excluded")
        var secret = source(); secret.id.peerId.namespace = Namespaces.Peer.SecretChat
        check(!nagramiXCanForwardWithoutAuthor(secret), "secret source becomes a copy")
        var protected = source([video]); protected.protected = true
        check(!nagramiXCanForwardWithoutAuthor(protected), "protected content does not call forward RPC")
        var pending = source(); pending.flags = [.sending]
        check(!nagramiXCanForwardWithoutAuthor(pending), "unfinished source excluded")
        pending.flags = [.Failed]
        check(!nagramiXCanForwardWithoutAuthor(pending), "failed source excluded")
        pending = source(); pending.id.namespace = 99
        check(!nagramiXCanForwardWithoutAuthor(pending), "local namespace excluded")
        pending = source(); pending.id.value = 0
        check(!nagramiXCanForwardWithoutAuthor(pending), "non-server ID excluded")
        check(!nagramiXCanForwardWithoutAuthor(source([TelegramMediaWidget()])), "widget cannot leak forced author header")
        check(!nagramiXCanForwardWithoutAuthor(source([TelegramMediaAction()])), "service message excluded")
        check(!nagramiXCanForwardWithoutAuthor(source([TelegramMediaExpiredContent()])), "expired placeholder excluded")
        var retry = source(); retry.flags = [.Failed]
        retry.attributes = [ForwardSourceInfoAttribute(), ForwardOptionsMessageAttribute(hideNames: true, hideCaptions: false)]
        check(nagramiXCanRetryWithoutAuthor(retry), "failed fast forward can retry same pending record")
        retry.attributes = [ForwardSourceInfoAttribute(), ForwardOptionsMessageAttribute(hideNames: false, hideCaptions: false)]
        check(!nagramiXCanRetryWithoutAuthor(retry), "ordinary repost stays outside custom retry")
        retry.attributes = [OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy])]
        check(nagramiXCanRetryWithoutAuthor(retry), "copy retry remains available")
        retry.flags = [.Failed, .Incoming]
        check(!nagramiXCanRetryWithoutAuthor(retry), "incoming messages cannot enter resend")

        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let path = root.appendingPathComponent("video.mp4"); let bytes = Data([1,2,3,4]); try bytes.write(to: path)
        box.paths["poll-video"] = path.path
        var plain = source(); plain.groupingKey = 100
        protected.groupingKey = 100
        let copySources = nagramiXMessagesRequiringCopy([plain, protected])
        check(copySources.map { $0.id } == [plain.id, protected.id], "selected album stays on one transport")
        var anotherPeer = source(); anotherPeer.groupingKey = 100; anotherPeer.id.peerId.value = 2
        check(nagramiXMessagesRequiringCopy([plain, protected, anotherPeer]).count == 2, "album key scoped to original peer")
        let before = source(), after = source([TelegramMediaContact()])
        var batch: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies([before, plain, protected, after], account: account, recipientCount: 2)
        check(batch != nil, "mixed native and local batch prepared")
        var paths: [String] = [], groups: [Int64] = []
        for (index, recipient) in batch!.recipientMessages.enumerated() {
            check(recipient.count == 4, "mixed source order and count")
            forward(recipient[0], original: before); forward(recipient[3], original: after)
            guard case let .message(_, _, _, reference, _, _, _, group, _, _) = recipient[2],
                  let file = reference?.media as? TelegramMediaFile,
                  let resource = file.resource as? LocalFileReferenceMediaResource else { check(false, "copy owns bytes"); return }
            paths.append(resource.localFilePath); groups.append(group!)
            let copiedBytes = try Data(contentsOf: URL(fileURLWithPath: resource.localFilePath))
            check(copiedBytes == bytes, "fallback preserves video bytes")
            let template = batch!.recipientMessages[0].map { $0.withUpdatedAttributes { $0 + [NotificationInfoMessageAttribute(muted: true), OutgoingScheduleInfoMessageAttribute(time: 777)] } }
            let configured = batch!.messages(forRecipientAt: index, template: template)!
            for item in configured {
                check(item.attributes.contains { ($0 as? NotificationInfoMessageAttribute)?.muted == true }, "silent choice applies to both transports")
                check(item.attributes.contains { ($0 as? OutgoingScheduleInfoMessageAttribute)?.time == 777 }, "schedule applies to both transports")
            }
            let topic = configured[0].withUpdatedThreadId(500).withUpdatedCorrelationId(Int64(index + 1))
            if case let .forward(_, thread, _, _, correlation) = topic {
                check(thread == 500 && correlation == Int64(index + 1), "native topic and correlation survive transforms")
            } else { check(false, "native transform stays forward") }
        }
        check(paths.count == 2 && paths[0] != paths[1], "recipient copy files remain independent")
        check(groups[0] != groups[1], "recipient album groups remain independent")
        batch = nil
        check(paths.allSatisfy { !FileManager.default.fileExists(atPath: $0) }, "cancel releases every uncommitted copy")
        var unavailable = protected; unavailable.media = [TelegramMediaFile(resource: CloudResource("missing"))]
        check(nagramiXPrepareRecipientCopies([before, unavailable], account: account, recipientCount: 2) == nil, "missing fallback stops whole batch before enqueue")

        let derived = nagramiXResolvedTransferMessage(source())!
        check(!nagramiXCanForwardWithoutAuthor(derived), "resolved card cannot forward original ID")
        check(nagramiXResolvedTransferMessage(nil) == nil, "failed resolution remains failed")
        check(nagramiXMessagesWithoutAuthor([before, before]) == nil, "duplicate source IDs rejected")
        check(nagramiXMessagesWithoutAuthor([]) == nil, "empty selection rejected")
        let strict = nagramiXCopyMessagesAsNew([before], account: account)!
        if case .message = strict[0] {} else { check(false, "explicit copy API stays strict") }
        print("GhostGram authorless checks: \(checks)")
    }
}
