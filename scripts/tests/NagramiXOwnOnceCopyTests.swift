import Foundation

// Real production ownership policy, new-message builder, file staging, local
// preflight and preparation UI are compiled alongside existing boundary doubles.
@main struct OwnOnceCopyTests {
    static func main() throws {
        try ContentCopyTests.main()
        var checks = 0
        func check(_ result: @autoclosure () -> Bool, _ label: String) { precondition(result(), label); checks += 1 }
        let accountId = PeerId(value: 100)
        let targetId = PeerId(value: 200)
        let folder = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        var staged: [String] = []
        defer {
            try? FileManager.default.removeItem(at: folder)
            staged.forEach { try? FileManager.default.removeItem(atPath: $0) }
        }
        let bytes = Data([3, 1, 4, 1, 5, 9])
        let path = folder.appendingPathComponent("recording.bin")
        try bytes.write(to: path)
        let box = MediaBox(); box.paths["own"] = path.path
        var voice = Message()
        voice.id.peerId = targetId
        voice.author = TestUser(id: accountId)
        voice.text = ""
        voice.containsSecretMedia = true
        voice.minAutoremoveOrClearTimeout = viewOnceTimeout
        voice.attributes = [AutoremoveTimeoutMessageAttribute(timeout: viewOnceTimeout, countdownBeginTime: 123)]
        voice.media = [TelegramMediaFile(resource: CloudResource("own"), mimeType: "audio/ogg", size: Int64(bytes.count), attributes: ["voice", "duration=3", "waveform"])]
        var round = voice
        round.media = [TelegramMediaFile(resource: CloudResource("own"), size: Int64(bytes.count), attributes: ["round", "duration=3", "size=1080"])]
        for recording in [voice, round] {
            check(recording.nagramiXAllowsOwnViewOnceCopy(accountPeerId: accountId), "own sent voice/round accepted")
            check(!recording.nagramiXAllowsOwnViewOnceCopy(accountPeerId: nil), "missing account cannot grant ownership")
            check(!recording.nagramiXAllowsContentCopy, "general export must still exclude one-shot media")
            check(!nagramiXAllowsProtectedContentExport(recording), "saving rights not expanded")
            check(!nagramiXCanCopyMessagesAsNew([recording]), "legacy caller without identity cannot copy view-once")
            check(nagramiXCanCopyMessagesAsNew([recording], accountPeerId: accountId), "account-aware capability accepted")
            for protected in [false, true] {
                let menu = productionMenu([recording], accountPeerId: accountId, native: false, isCopyProtected: protected)
                check(menu.0 && !menu.1, "own one-shot adds copy actions but no Repost")
                check(!productionMenu([recording], accountPeerId: PeerId(value: 101), native: false, isCopyProtected: protected).0, "another account cannot open copy actions")
            }
            for mode in [NagramiXMessageTransferMode.forwardWithoutSource, .copyAsNew, .copyToSingleRecipient] {
                let needsCopy = productionProtectedCopy(mode, [recording], false, targetId, accountPeerId: accountId)
                check(needsCopy, "both own view-once actions use preparation and local upload")
                let effective = productionEffectiveMode(mode, needsCopy)
                check(effective.copiesAsNew && effective.singleRecipient == mode.singleRecipient, "recipient contract preserved")
                check(!productionPickerHasSourceIds(effective, needsCopy), "no server forward IDs in own view-once picker")
                check(productionPickerLimit(effective, needsCopy) == (mode.singleRecipient ? 1 : nil), "single selection limit preserved")
            }
            check(!productionProtectedCopy(.forwardWithSource, [recording], false, targetId, accountPeerId: accountId), "Repost does not enter copy fallback")
            var values: [Bool] = []
            let operation = nagramiXFetchContentCopyMedia(mediaBox: box, messages: [recording], accountPeerId: accountId).start(next: { values.append($0) })
            check(values == [true] && box.fetched.isEmpty, "local preflight completes without opening or fetching original")
            operation.dispose()
            let copy = nagramiXCopyMessagesAsNew([recording], mediaBox: box, accountPeerId: accountId)!
            let once = copy[0].attributes.compactMap { $0 as? AutoremoveTimeoutMessageAttribute }
            check(once.count == 1 && once[0].timeout == viewOnceTimeout && once[0].countdownBeginTime == nil, "fresh one-shot lifetime without old countdown")
            let stored = outgoingMessageAttributes(requestedAttributes: copy[0].attributes, isSecretChat: false, peerAutoremoveTimeout: 60)
            let mediaTimers = stored.compactMap { $0 as? AutoclearTimeoutMessageAttribute }
            check(mediaTimers.count == 1 && mediaTimers[0].timeout == viewOnceTimeout && mediaTimers[0].countdownBeginTime == nil, "native enqueue produces the one-shot cloud media timer")
            check(stored.compactMap { $0 as? AutoremoveTimeoutMessageAttribute }.first?.timeout == 60, "destination chat auto-delete timer stays separate")
            check(copy[0].threadId == nil && copy[0].replyToMessageId == nil, "source reply/thread not copied")
            guard case let .standalone(media)? = copy[0].mediaReference,
                  let file = media as? TelegramMediaFile,
                  let resource = file.resource as? LocalFileReferenceMediaResource else { fatalError("must stage local bytes") }
            staged.append(resource.localFilePath)
            check(file.fileId.namespace == Namespaces.Media.LocalFile && file.partialReference == nil, "independent file identity")
            check(file.attributes == (recording.media[0] as! TelegramMediaFile).attributes, "voice/round attributes preserved")
            let copiedBytes = try Data(contentsOf: URL(fileURLWithPath: resource.localFilePath))
            check(copiedBytes == bytes, "full recording bytes preserved")
            let context = AccountContext(box); let chat = ChatControllerImpl(context); var prepared = 0
            chat.nagramiXPrepareProtectedCopy(messages: [recording]) { prepared += 1 }; Queue.flush()
            check(prepared == 1 && context.presented.isEmpty, "actual UI preparation passes account ID and opens without loader flash")
        }
        // Refuse every unsupported ownership/lifecycle/media combination as a
        // whole selection. No incoming view-once copy is introduced.
        var rejected: [Message] = []
        var bad = voice; bad.author = TestUser(id: targetId); rejected.append(bad)
        bad = voice; bad.author = nil; rejected.append(bad)
        bad = voice; bad.flags = [.Incoming]; rejected.append(bad)
        for flag in [MessageFlags.sending, .Failed] { bad = voice; bad.flags = flag; rejected.append(bad) }
        bad = voice; bad.forwardInfo = 1; rejected.append(bad)
        bad = voice; bad.id.namespace = 100; rejected.append(bad)
        bad = voice; bad.id.peerId.namespace = Namespaces.Peer.SecretChat; rejected.append(bad)
        bad = voice; bad.id.peerId.namespace = 2; rejected.append(bad)
        bad = voice; bad.id.peerId = accountId; rejected.append(bad)
        bad = voice; bad.id.peerId.isVerificationCodes = true; rejected.append(bad)
        for timeout in [Optional<Int32>.none, Optional<Int32>(60)] { bad = voice; bad.minAutoremoveOrClearTimeout = timeout; rejected.append(bad) }
        for media in [[Media](), [TelegramMediaPaidContent()], [TelegramMediaExpiredContent()], [TelegramMediaAction()], [TelegramMediaContact()], [TelegramMediaFile(resource: CloudResource("own"))], [voice.media[0], TelegramMediaContact()]] {
            bad = voice; bad.media = media; rejected.append(bad)
        }
        for item in rejected {
            check(!item.nagramiXAllowsOwnViewOnceCopy(accountPeerId: accountId), "invalid own-view-once policy rejected")
            check(nagramiXCopyMessagesAsNew([voice, item], mediaBox: box, accountPeerId: accountId) == nil, "mixed invalid batch never copies a permitted subset")
            var values: [Bool] = []
            _ = nagramiXFetchContentCopyMedia(mediaBox: box, messages: [item], accountPeerId: accountId).start(next: { values.append($0) })
            check(values == [false] && box.fetched.isEmpty, "invalid media rejected before remote fetch")
        }
        // Destination validation is shared by both copy actions, and happens
        // again after native contacts/search selection and current fee lookup.
        check(nagramiXAllowsOwnViewOnceDestination(.user(TestUser(id: targetId)), accountPeerId: accountId, requiresPayment: false), "ordinary private recipient accepted")
        for peer in [EnginePeer.user(TestUser(id: accountId)), .user(TestUser(id: targetId, botInfo: 1)), .group, .channel, .secretChat] {
            check(!nagramiXAllowsOwnViewOnceDestination(peer, accountPeerId: accountId, requiresPayment: false), "unsupported one-shot destination rejected")
        }
        check(!nagramiXAllowsOwnViewOnceDestination(.user(TestUser(id: targetId)), accountPeerId: accountId, requiresPayment: true), "paid destination rejected")
        check(productionAllowsMode(.generic) && productionAllowsMode(.silent), "ordinary and silent send keep one-shot")
        check(!productionAllowsMode(.schedule) && !productionAllowsMode(.whenOnline), "unsupported schedule does not downgrade one-shot")
        // No remote refetch, indefinite progress or empty upload after eviction.
        try FileManager.default.removeItem(at: path)
        for item in [voice, round] {
            var values: [Bool] = []
            _ = nagramiXFetchContentCopyMedia(mediaBox: box, messages: [item], accountPeerId: accountId).start(next: { values.append($0) })
            check(values == [false] && box.fetched.isEmpty, "evicted original fails promptly without fetch")
            check(nagramiXCopyMessagesAsNew([item], mediaBox: box, accountPeerId: accountId) == nil, "send rechecks file existence")
        }
        for stagedPath in staged {
            let retained = try Data(contentsOf: URL(fileURLWithPath: stagedPath))
            check(retained == bytes, "staged new upload survives original deletion")
        }
        for contents in [Data(), Data([1])] {
            try contents.write(to: path)
            check(!voice.nagramiXHasLocalViewOnceRecording(mediaBox: box), "zero/truncated recording rejected")
            check(nagramiXCopyMessagesAsNew([voice], mediaBox: box, accountPeerId: accountId) == nil, "no upload of truncated bytes")
        }
        try FileManager.default.removeItem(at: path)
        try FileManager.default.createDirectory(at: path, withIntermediateDirectories: true)
        check(!voice.nagramiXHasLocalViewOnceRecording(mediaBox: box), "directory cannot be uploaded as recording")
        let missingContext = AccountContext(box); let missingChat = ChatControllerImpl(missingContext); var ready = 0
        missingChat.nagramiXPrepareProtectedCopy(messages: [voice]) { ready += 1 }; Queue.flush()
        check(ready == 0 && missingContext.presented.last is TestAlert, "actual UI shows error and cannot open picker without bytes")
        // Existing text and normal recording paths remain ordinary.
        let text = Message()
        let normalCopy = nagramiXCopyMessagesAsNew([text], accountPeerId: accountId)!
        check(normalCopy[0].attributes.allSatisfy { !($0 is AutoremoveTimeoutMessageAttribute) }, "ordinary text does not become one-shot")
        check(box.fetched.isEmpty && box.activeFetches == 0, "own recordings never remotely fetched or consumed")
        print("PASS: \(checks) own view-once ownership/voice/round/menu/recipient/local-upload/lifetime checks")
    }
}
