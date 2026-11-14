import Foundation
import SwiftSignalKit
import TelegramCore
import AccountContext

// Explicit message actions have their own lifetime; they do not enable a chat.
public enum NagramiXInlineTranslationRuntime {
    private struct Key: Hashable {
        let account: Int64
        let message: EngineMessage.Id
    }
    private struct Job {
        let token: UUID
        let revision: String
        let disposable: MetaDisposable
    }
    private static let lock = NSLock()
    private static var jobs: [Key: Job] = [:]

    private static func current(_ key: Key, _ token: UUID) -> Bool {
        self.lock.lock(); defer { self.lock.unlock() }
        return self.jobs[key]?.token == token
    }
    private static func finish(_ key: Key, _ token: UUID) {
        self.lock.lock()
        let job = self.jobs[key]?.token == token ? self.jobs.removeValue(forKey: key) : nil
        self.lock.unlock()
        job?.disposable.dispose()
    }
    private static func cancel(_ key: Key) {
        self.lock.lock(); let job = self.jobs.removeValue(forKey: key); self.lock.unlock()
        job?.disposable.dispose()
    }
    private static func entities(_ message: EngineRawMessage) -> [MessageTextEntity] {
        return (message.attributes.first { $0 is TextEntitiesMessageAttribute } as? TextEntitiesMessageAttribute)?.entities ?? []
    }
    private static func report(context: AccountContext, message: EngineRawMessage, configuration: NagramiXTranslationConfiguration, error: NagramiXTranslationFailure) {
        guard error != .cancelled else { return }
        DispatchQueue.main.async {
            let current = NagramiXTranslationSettings.current
            guard current.revision == configuration.revision else { return }
            NotificationCenter.default.post(name: NagramiXTranslationRuntime.failed, object: nil, userInfo: [
                "account": context.account.peerId.toInt64(),
                "chat": nagramiXTranslationChatKey(context: context, peerId: message.id.peerId, threadId: message.threadId),
                "error": error
            ])
        }
    }

    public static func translate(context: AccountContext, messageId: EngineMessage.Id) {
        let configuration = NagramiXTranslationSettings.current
        guard messageId.peerId.namespace != Namespaces.Peer.SecretChat else { return }
        let key = Key(account: context.account.peerId.toInt64(), message: messageId)
        let token = UUID(), disposable = MetaDisposable()
        self.lock.lock()
        // Share a repeated tap; a newly chosen service supersedes the old request.
        let previous = self.jobs[key]
        guard previous?.revision != configuration.revision else { self.lock.unlock(); return }
        self.jobs[key] = Job(token: token, revision: configuration.revision, disposable: disposable)
        self.lock.unlock()
        previous?.disposable.dispose()
        let interface = context.sharedContext.currentPresentationData.with { $0 }.strings.baseLanguageCode
        let signal: Signal<Bool, NoError> = context.engine.messages.nagramiXLocalMessages([messageId])
        |> mapToSignal { messages -> Signal<Bool, NoError> in
            guard let message = messages.first, !message.text.isEmpty, message.richText == nil, message.adAttribute == nil,
                  self.current(key, token) else { return .single(false) }
            let chatKey = nagramiXTranslationChatKey(context: context, peerId: message.id.peerId, threadId: message.threadId)
            let target = configuration.resolvedTarget(interface: interface, targetOverride: NagramiXTranslationSettings.chat(chatKey).target)
            guard let source = nagramiXTranslationSource(message.text, interface: target, ignored: configuration.effectiveIgnored(interface: interface, target: target)) else { return .single(false) }
            let fingerprint = nagramiXInlineTranslationFingerprint(message)
            return nagramiXTranslateText(context: context, text: message.text, entities: self.entities(message), source: source, target: target, configuration: configuration, manual: true)
            |> mapToSignal { translatedText, translatedEntities -> Signal<Bool, NagramiXTranslationFailure> in
                return context.engine.messages.nagramiXUpdateLocalMessageAttributes(messageId: messageId) { currentMessage in
                    let current = NagramiXTranslationSettings.current
                    let choice = NagramiXTranslationSettings.chat(chatKey)
                    guard self.current(key, token), current.revision == configuration.revision,
                          nagramiXInlineTranslationFingerprint(currentMessage) == fingerprint,
                          current.resolvedTarget(interface: interface, targetOverride: choice.target) == target else { return nil }
                    var attributes = currentMessage.attributes.filter { !($0 is TranslationMessageAttribute) }
                    attributes.append(TranslationMessageAttribute(text: translatedText, entities: translatedEntities, toLang: target,
                        nagramiXInlineRevision: configuration.revision, nagramiXInlineSource: fingerprint))
                    return attributes
                } |> castError(NagramiXTranslationFailure.self)
            }
            |> `catch` { error -> Signal<Bool, NoError> in
                self.report(context: context, message: message, configuration: configuration, error: error)
                return .single(false)
            }
        }
        disposable.set(signal.start(completed: { self.finish(key, token) }))
    }

    public static func showOriginal(context: AccountContext, messageId: EngineMessage.Id) {
        self.cancel(Key(account: context.account.peerId.toInt64(), message: messageId))
        let _ = context.engine.messages.nagramiXUpdateLocalMessageAttributes(messageId: messageId) { message in
            guard nagramiXInlineTranslationTarget(message) != nil,
                  let translation = message.attributes.first(where: { $0 is TranslationMessageAttribute }) as? TranslationMessageAttribute else { return nil }
            var attributes = message.attributes.filter { !($0 is TranslationMessageAttribute) }
            // Keep an explicit local original choice so automatic chat translation
            // cannot immediately replace it with a translation again.
            attributes.append(TranslationMessageAttribute(text: message.text, entities: self.entities(message), toLang: translation.toLang,
                nagramiXInlineRevision: translation.nagramiXInlineRevision, nagramiXInlineSource: translation.nagramiXInlineSource, nagramiXInlineHidden: true))
            return attributes
        }.startStandalone()
    }
}
