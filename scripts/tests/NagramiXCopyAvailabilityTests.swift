@main private struct CopyAvailabilityTests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ label: String) {
        count += 1
        if !value() { fatalError("copy availability regression: " + label) }
    }
    static func poll(kind: TelegramMediaPollKind = .poll(multipleAnswers: false), correct: [Data]? = nil, voters: [TelegramMediaPollOptionVoters]? = nil, attached: Media? = nil, optionMedia: Media? = nil, solutionMedia: Media? = nil) -> TelegramMediaPoll {
        let options = [
            TelegramMediaPollOption(text: "Полностью согласен 😀", entities: [Entity(value: "bold")], opaqueIdentifier: Data([0]), media: optionMedia, date: 123, addedBy: PeerId(value: 55)),
            TelegramMediaPollOption(text: "Другая позиция", entities: [], opaqueIdentifier: Data([1]), date: 456, addedBy: PeerId(value: 66))
        ]
        let results = TelegramMediaPollResults(voters: voters, totalVoters: 19, recentVoters: [PeerId(value: 99)], solution: .init(text: "Объяснение", entities: [Entity(value: "italic")], media: solutionMedia), hasUnseenVotes: true, canViewStats: true)
        return TelegramMediaPoll(pollId: MediaId(namespace: 100, id: 777), publicity: .anonymous, kind: kind, text: "Выберите вариант ответа", textEntities: [Entity(value: "underline")], options: options, correctAnswers: correct, results: results, isClosed: true, deadlineTimeout: 60, deadlineDate: 1, pollHash: 888, openAnswers: true, revotingDisabled: true, shuffleAnswers: true, hideResultsUntilClose: true, isCreator: false, attachedMedia: attached, restrictToSubscribers: false, countries: [])
    }
    static func copiedPoll(_ m: EnqueueMessage) -> TelegramMediaPoll? {
        guard case let .standalone(media)? = m.mediaReference else { return nil }
        return media as? TelegramMediaPoll
    }
    static func main() throws {
        let box = MediaBox(), root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let account = Account(box), harness = CopyPolicyHarness(account)
        NagramiXPrivacySettings.current.bypassScreenshots = false
        harness.refreshSelection(); check(harness.rechecks == 0, "unchanged OFF needs no redundant selection lookup")
        NagramiXPrivacySettings.current.bypassScreenshots = true
        harness.refreshSelection(); check(harness.rechecks == 1, "ON refreshes an existing unchanged selection")
        harness.refreshSelection(); check(harness.rechecks == 1, "same ON value does not restart lookup")
        NagramiXPrivacySettings.current.bypassScreenshots = false
        harness.refreshSelection(); check(harness.rechecks == 2, "OFF invalidates old selection capability")
        let original = poll()
        var m = Message(); m.text = ""; m.media = [original]
        check(nagramiXCanCopyMessagesAsNew([m]), "anonymous poll from screenshot must be copyable")
        let payload = nagramiXCopyMessagesAsNew([m], account: account, forceLocalMedia: true)!
        let p = copiedPoll(payload[0])!
        check(p !== original && p.pollId.namespace == Namespaces.Media.LocalPoll && p.pollId != original.pollId, "new poll identity")
        check(p.text == original.text && p.textEntities.map { $0.value } == ["underline"], "question and formatting preserved")
        check(p.options.map { $0.text } == original.options.map { $0.text }, "option order and Unicode preserved")
        check(p.options[0].entities.map { $0.value } == ["bold"], "option formatting preserved")
        check(p.options.map { $0.opaqueIdentifier } == original.options.map { $0.opaqueIdentifier }, "answer identifiers preserved within new poll")
        check(p.options.allSatisfy { $0.addedBy == nil && $0.date == nil }, "old option-author metadata removed")
        check(p.results.totalVoters == nil && p.results.voters == nil && p.results.recentVoters.isEmpty && p.results.hasUnseenVotes == nil, "old votes and voter identities are not copied")
        check(!p.results.canViewStats && p.isCreator && !p.isClosed && p.deadlineDate == nil && p.deadlineTimeout == nil && p.pollHash == 0, "fresh poll has no expired deadline or old server state")
        check(p.openAnswers && p.revotingDisabled && p.shuffleAnswers && p.hideResultsUntilClose, "poll behavior flags preserved")
        check(p.results.solution?.text == "Объяснение", "quiz explanation payload preserved")
        check(original.results.totalVoters == 19 && original.options[0].addedBy?.value == 55 && original.isClosed, "source poll remains unchanged")
        let multi = poll(kind: .poll(multipleAnswers: true))
        m.media = [multi]
        let copiedMulti = copiedPoll(nagramiXCopyMessagesAsNew([m])![0])!
        if case let .poll(multipleAnswers) = copiedMulti.kind { check(multipleAnswers, "multiple-answer poll preserved") } else { check(false, "poll kind") }
        m.media = [original]
        for enabled in [false, true] {
            NagramiXPrivacySettings.current.bypassScreenshots = enabled
            for protected in [false, true] {
                m.protected = protected
                for native in [false, true] {
                    let menu = harness.menu([m], protected: protected, native: native)
                    check(menu.copy == (!protected || enabled), "protected copy menu follows Free Content; ordinary copy remains available")
                    check(menu.repost == (native && !protected), "Repost follows native rights independently")
                }
                check(nagramiXCanCopyMessagesAsNew([m]) == (!protected || enabled), "Core copy policy revalidates the live switch")
                check(harness.draft([m], hidden: true) == (!protected || enabled), "Send revalidates protected draft at current Free Content value")
                check(harness.commitAllowed([m]) == (!protected || enabled), "asynchronous commit cancels a protected copy after OFF")
                check(harness.selectionBlocked(secret: false, protected: protected, eligible: !protected || enabled) == (protected && !enabled), "bulk-selection buttons hidden for protected OFF")
                check(harness.draft([m], hidden: false) == !protected, "protected native Repost remains blocked")
            }
        }
        m.protected = false
        let channel = TelegramChannel(); m.peers[m.id.peerId] = channel
        for state: TelegramChannelParticipationStatus in [.member, .left, .kicked] {
            channel.participationStatus = state
            for username: String? in [nil, "public_channel"] {
                channel.username = username
                let allowed = state == .member || (state == .left && username != nil)
                for enabled in [false, true] {
                    NagramiXPrivacySettings.current.bypassScreenshots = enabled
                    let menu = harness.menu([m], protected: false, native: true)
                    check(menu.copy == (allowed || enabled), "closed source copy follows current Free Content")
                    check(menu.repost == allowed, "hide Repost for a private left/kicked channel")
                    check(harness.commitAllowed([m]) == (allowed || enabled), "recheck source access before asynchronous enqueue")
                }
            }
        }
        channel.participationStatus = .left; channel.username = nil
        channel.usernames = [ChannelUsername(flags: .isActive)]
        check(harness.menu([m], protected: false, native: true).repost, "active public alias permits native Repost")
        channel.usernames = [ChannelUsername(flags: [])]
        check(!harness.menu([m], protected: false, native: true).repost, "inactive username cannot restore access")
        m.peers = [:]
        let group = TelegramGroup(); m.peers[m.id.peerId] = group
        for membership: TelegramGroupMembership in [.Member, .Left, .Removed] {
            group.membership = membership
            for enabled in [false, true] {
                NagramiXPrivacySettings.current.bypassScreenshots = enabled
                let result = harness.menu([m], protected: false, native: true)
                check(result.copy == (membership == .Member || enabled), "basic-group access requires ON after leave/removal")
                check(result.repost == (membership == .Member), "basic-group native Repost follows membership")
            }
        }
        m.peers = [:]
        NagramiXPrivacySettings.current.bypassScreenshots = true
        var unknownChannel = m; unknownChannel.id.peerId.namespace = Namespaces.Peer.CloudChannel
        let unknownMenu = harness.menu([unknownChannel], protected: false, native: true)
        check(unknownMenu.copy && !unknownMenu.repost, "Free Content ON can copy a loaded message with unavailable source peer")
        check(harness.mode(transferMode: .forwardWithoutSource) == .copyToSingleRecipient, "single-recipient action must not send an inaccessible source ID")
        check(harness.mode(transferMode: .forwardWithSource) == .forwardWithSource, "native Repost route preserved")
        check(harness.mode(transferMode: .copyAsNew) == .copyAsNew, "broadcast route preserved")
        check(harness.mode(transferMode: .forwardWithoutSource).singleRecipient && harness.mode(transferMode: .forwardWithoutSource).copiesAsNew, "single-recipient copy retains destination contract")
        m.protected = true
        let batch = nagramiXPrepareRecipientCopies([m], account: account, recipientCount: 2, forceLocalMedia: true)!
        let first = copiedPoll(batch.recipientMessages[0][0])!, second = copiedPoll(batch.recipientMessages[1][0])!
        check(first.pollId != second.pollId && first !== second, "broadcast polls are independent for both recipients")
        check(first.text == second.text && first.options.count == second.options.count, "both recipients receive complete poll")
        var fetched: Bool?
        let simpleFetch = nagramiXFetchContentCopyMedia(mediaBox: box, messages: [m]).start(next: { fetched = $0 })
        check(fetched == true && box.fetched.isEmpty, "text-only poll needs no download")
        simpleFetch.dispose()
        let media = TelegramMediaFile(resource: CloudResource("poll-image"), mimeType: "image/jpeg", size: 4)
        let withMedia = poll(attached: media, optionMedia: media, solutionMedia: media)
        m.media = [withMedia]
        check(nagramiXCanCopyMessagesAsNew([m]), "native-supported cloud poll attachments are allowed")
        let copiedMedia = copiedPoll(nagramiXCopyMessagesAsNew([m], account: account)![0])!
        check(copiedMedia.attachedMedia != nil && copiedMedia.options[0].media != nil && copiedMedia.results.solution?.media != nil, "no poll attachment slot is omitted")
        fetched = nil
        let mediaFetch = nagramiXFetchContentCopyMedia(mediaBox: box, messages: [m]).start(next: { fetched = $0 })
        check(fetched == nil && box.activeFetches == 1, "all embedded poll slots share one complete resource fetch")
        box.emit("poll-image", ResourceData(complete: true))
        check(fetched == true, "embedded media preparation completes before send")
        mediaFetch.dispose(); check(box.activeKeeps == 0 && box.activeFetches == 0, "embedded resource leases released")
        m.media = [poll(attached: UnsupportedMedia())]
        check(!nagramiXCanCopyMessagesAsNew([m]), "native-unrepresentable poll media is never silently dropped")
        m.media = [poll(kind: .quiz(multipleAnswers: false), correct: [Data([1])])]
        check(copiedPoll(nagramiXCopyMessagesAsNew([m])![0])!.correctAnswers == [Data([1])], "known quiz answer preserved")
        m.media = [poll(kind: .quiz(multipleAnswers: false), voters: [.init(selected: true, opaqueIdentifier: Data([0]), count: 7, isCorrect: false), .init(selected: false, opaqueIdentifier: Data([1]), count: 12, isCorrect: true)])]
        let knownQuiz = copiedPoll(nagramiXCopyMessagesAsNew([m])![0])!
        check(knownQuiz.correctAnswers == [Data([1])] && knownQuiz.results.voters == nil, "derive known correct answer without old votes")
        m.media = [poll(kind: .quiz(multipleAnswers: false))]
        check(!nagramiXCanCopyMessagesAsNew([m]), "unknown quiz answer is never fabricated")
        m.media = [poll(kind: .quiz(multipleAnswers: false), correct: [Data([9])])]
        check(!nagramiXCanCopyMessagesAsNew([m]), "invalid correct-answer mapping rejected")
        var text = Message(); text.text = "Подпись"; text.id.value = 2
        m.media = [original]
        let ordered = nagramiXCopyMessagesAsNew([text, m, text])!
        check(ordered.count == 3 && ordered[0].text == "Подпись" && copiedPoll(ordered[1]) != nil && ordered[2].text == "Подпись", "mixed text and poll order preserved")
        for blocked: Media in [TelegramMediaAction(), TelegramMediaPaidContent(), TelegramMediaExpiredContent(), UnsupportedMedia()] {
            var invalid = m; invalid.media = [blocked]
            check(nagramiXCopyMessagesAsNew([text, invalid]) == nil, "unsupported selection is never partially sent")
        }
        var secret = m; secret.protected = false; secret.id.peerId.namespace = Namespaces.Peer.SecretChat
        for enabled in [false, true, false] {
            NagramiXPrivacySettings.current.bypassScreenshots = enabled
            check(nagramiXCanCopyMessagesAsNew([secret]) == enabled, "secret-chat copy follows Free Content, including revocation")
            let menu = harness.menu([secret], protected: false, native: false)
            check(menu.copy == enabled && !menu.repost, "secret-chat custom commands appear only with ON")
            check(harness.draft([secret], hidden: true) == enabled, "secret-chat draft revalidates current switch")
            check(harness.commitAllowed([secret]) == enabled, "secret source is checked again before enqueue")
            check(harness.selectionBlocked(secret: true, protected: false, eligible: enabled) == !enabled, "secret-chat bulk actions visible only with ON")
        }
        var ephemeral = m; ephemeral.protected = false
        ephemeral.attributes = [EphemeralMessageAttribute(isForwardingDisabled: true)]
        for enabled in [false, true, false] {
            NagramiXPrivacySettings.current.bypassScreenshots = enabled
            check(nagramiXCanCopyMessagesAsNew([ephemeral]) == enabled, "per-message forwarding restriction requires Free Content")
            check(harness.commitAllowed([ephemeral]) == enabled, "ephemeral restriction rechecked at commit")
        }
        NagramiXPrivacySettings.current.bypassScreenshots = true
        let secretPath = root.appendingPathComponent("decrypted-secret.bin")
        let secretBytes = Data([1, 2, 3, 4]); try secretBytes.write(to: secretPath)
        let secretResource = CloudResource("secret-decrypted")
        box.paths[secretResource.id.stringRepresentation] = secretPath.path
        box.complete.insert(secretResource.id.stringRepresentation)
        secret.media = [TelegramMediaFile(resource: secretResource, mimeType: "application/octet-stream", size: 4)]
        let secretPayload = nagramiXCopyMessagesAsNew([secret], account: account, forceLocalMedia: true)!
        guard case let .standalone(localMedia)? = secretPayload[0].mediaReference,
              let localFile = localMedia as? TelegramMediaFile,
              let resource = localFile.resource as? LocalFileReferenceMediaResource else { fatalError("copy availability regression: secret file must use new local upload") }
        defer { try? FileManager.default.removeItem(atPath: resource.localFilePath) }
        let localSecretBytes = try Data(contentsOf: URL(fileURLWithPath: resource.localFilePath))
        check(localSecretBytes == secretBytes, "copied secret attachment uses complete decrypted MediaBox bytes")
        check(localFile.partialReference == nil && localFile.fileId.namespace == Namespaces.Media.LocalFile, "new upload has no original secret resource reference")
        NagramiXPrivacySettings.current.bypassScreenshots = false
        check(!harness.commitAllowed([secret]), "disabling Free Content cancels secret send after staging")
        check(nagramiXCopyMessagesAsNew([secret], account: account, forceLocalMedia: true) == nil, "OFF refuses rebuilding staged secret bytes")
        NagramiXPrivacySettings.current.bypassScreenshots = true
        var codes = m; codes.id.peerId.isVerificationCodes = true
        check(!nagramiXCanCopyMessagesAsNew([codes]), "verification-code boundary preserved")
        var incomingOnce = m; incomingOnce.minAutoremoveOrClearTimeout = viewOnceTimeout
        check(!nagramiXCanCopyMessagesAsNew([incomingOnce]), "incoming view-once lifetime preserved")
        print("PASS: \(count) poll/menu/free-content/draft/recipient checks; native API/network/UIKit are explicit boundaries")
    }
}
