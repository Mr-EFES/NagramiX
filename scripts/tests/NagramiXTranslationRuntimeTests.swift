import Foundation

@main struct TranslationRuntimeTests {
    static var count = 0
    static func check(_ condition: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !condition() { FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1) }
    }
    static func main() {
        let context = AccountContext(), service = LocalService()
        engineExperimentalInternalTranslationService = service
        let peer = PeerId(value: 42)
        func fixture(_ id: Int32, _ text: String = "Hello world") -> Message {
            let message = Message(id: MessageId(peerId: peer, id: id), text: text)
            context.account.postbox.store.messages[message.id] = message
            return message
        }
        func translate(_ message: Message, target: String = "ru") -> Disposable {
            NagramiXTranslationRuntime.translate(context: context, messageIds: [message.id], target: target).startStandalone()
        }
        func result(_ message: Message) -> TranslationMessageAttribute? { message.attributes.first { $0 is TranslationMessageAttribute } as? TranslationMessageAttribute }
        NagramiXTranslationSettings.update { $0.enabled = true; $0.automatic = true; $0.provider = .apple }
        let key = nagramiXTranslationChatKey(context: context, peerId: peer, threadId: nil)
        let message = fixture(1)
        let request = translate(message)
        check(service.requests.count == 1 && service.requests[0].source == "en" && service.requests[0].target == "ru", "actual local translation dispatch")
        service.finish("Привет мир")
        check(result(message)?.text == "Привет мир" && message.text == "Hello world", "actual store adds translated attribute without altering original")
        check(context.account.postbox.store.updates == 1, "store metadata preserved by actual write body")
        check(NagramiXTranslationRuntime.hasTranslation(context: context, message: message, target: "ru"), "actual cache stamp matches provider and content")
        _ = translate(message)
        check(service.requests.count == 1, "translated message does not charge/translate again")
        request.dispose()
        let stale = fixture(2)
        _ = translate(stale)
        NagramiXTranslationSettings.credentialsChanged(); service.finish()
        check(result(stale) == nil, "provider/key revision change rejects an in-flight write")
        let edited = fixture(3)
        _ = translate(edited)
        let replacement = Message(id: edited.id, text: "New text after editing")
        context.account.postbox.store.messages[edited.id] = replacement
        service.finish()
        check(result(replacement) == nil && replacement.text == "New text after editing", "edit during translation is never overwritten")
        let disabled = fixture(4)
        _ = translate(disabled)
        NagramiXTranslationSettings.updateChat(key) { $0.enabled = false }; service.finish()
        check(result(disabled) == nil, "chat OFF rejects an in-flight write")
        NagramiXTranslationSettings.updateChat(key) { $0.enabled = true }
        let retargeted = fixture(5)
        _ = translate(retargeted)
        NagramiXTranslationSettings.updateChat(key) { $0.target = "de" }; service.finish()
        check(result(retargeted) == nil, "new target rejects a result for the old target")
        NagramiXTranslationSettings.updateChat(key) { $0.target = nil }
        let cancelled = fixture(6)
        let cancel = translate(cancelled); cancel.dispose(); service.finish()
        check(result(cancelled) == nil, "disposed subscription cannot update storage")
        let calls = service.requests.count
        for (id, text) in [(7,"Привет мир"),(8,"🙂 123"),(9,"https://example.com")] {
            let original = fixture(Int32(id), text)
            _ = translate(original)
            check(result(original)?.text == text, "identity translation avoids native indefinite loading")
        }
        check(service.requests.count == calls, "same-language and non-prose text never sent to cloud/local translator")
        let ad = fixture(10); ad.adAttribute = 1
        let own = fixture(11); own.author = Peer(id: context.account.peerId)
        let rich = fixture(12); rich.richText = "rich-document"
        let secret = Message(id: MessageId(peerId: PeerId(namespace: Namespaces.Peer.SecretChat, value: 99), id: 12), text: "Secret message")
        context.account.postbox.store.messages[secret.id] = secret
        for value in [ad, own, rich, secret] { _ = translate(value); check(result(value) == nil, "ad/own/rich/secret exclusions preserved") }
        check(service.requests.count == calls, "excluded messages never dispatched")
        let foreignAccount = AccountContext(2)
        check(!NagramiXTranslationRuntime.hasTranslation(context: foreignAccount, message: message, target: "ru"), "translation stamp isolated by account")
        let changed = Message(id: message.id, text: "Edited again")
        check(!NagramiXTranslationRuntime.hasTranslation(context: context, message: changed, target: "ru"), "edited source invalidates old stamp")
        let failed = fixture(14)
        _ = translate(failed)
        service.requests.last!.subscriber.putNext(nil); service.requests.last!.subscriber.putCompletion()
        let failedCount = service.requests.count
        _ = translate(failed)
        check(service.requests.count == failedCount, "automatic repeated failure has bounded backoff")
        NagramiXTranslationSettings.credentialsChanged()
        _ = translate(failed)
        check(service.requests.count == failedCount + 1, "a corrected key/provider revision can retry immediately")
        service.requests.last!.subscriber.putNext(nil); service.requests.last!.subscriber.putCompletion()
        NagramiXTranslationRuntime.clearFailure(chat: key)
        _ = translate(failed)
        check(service.requests.count == failedCount + 2, "explicit retry clears only its current chat/revision backoff")
        service.finish()
        check(result(failed) != nil, "retry after failure can commit a complete translation")
        let masterOff = fixture(13)
        _ = translate(masterOff); NagramiXTranslationSettings.update { $0.enabled = false }; service.finish()
        check(result(masterOff) == nil, "master OFF rejects an in-flight result")
        print("PASS: \(count) actual runtime dispatch/store/cache/stale/cancel/identity checks; Apple ML, signal delivery and Postbox are boundaries")
    }
}
