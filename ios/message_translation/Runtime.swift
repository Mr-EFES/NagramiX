import Foundation
import NaturalLanguage
import SwiftSignalKit
import Postbox
import TelegramCore
import AccountContext

public func nagramiXTranslationSettingsSignal() -> Signal<NagramiXTranslationConfiguration, NoError> {
    return Signal { subscriber in
        let observer = NotificationCenter.default.addObserver(forName: NagramiXTranslationSettings.changed, object: nil, queue: nil) { _ in
            subscriber.putNext(NagramiXTranslationSettings.current)
        }
        subscriber.putNext(NagramiXTranslationSettings.current)
        return ActionDisposable { NotificationCenter.default.removeObserver(observer) }
    }
}

public func nagramiXTranslationSource(_ text: String, interface: String, ignored: [String] = []) -> String? {
    let text = NagramiXTranslationLanguage.recognitionText(text)
    guard !text.isEmpty else { return nil }
    let recognizer = NLLanguageRecognizer()
    recognizer.processString(text)
    return NagramiXTranslationLanguage.accepted(recognizer.languageHypotheses(withMaximum: 3).map { ($0.key.rawValue, $0.value) }, interface: interface, ignored: ignored)
}

public func nagramiXTranslationChatKey(context: AccountContext, peerId: EnginePeer.Id, threadId: Int64?) -> String {
    return NagramiXTranslationSettings.chatKey(account: context.account.peerId.toInt64(), peer: peerId.toInt64(), thread: threadId)
}

public func nagramiXTranslationChatState(context: AccountContext, peerId: EnginePeer.Id, threadId: Int64?) -> Signal<ChatTranslationState?, NoError> {
    guard peerId.namespace != Namespaces.Peer.SecretChat else { return .single(nil) }
    let key = nagramiXTranslationChatKey(context: context, peerId: peerId, threadId: threadId)
    return combineLatest(nagramiXTranslationSettingsSignal(), context.sharedContext.presentationData)
    |> mapToSignal { configuration, presentation -> Signal<ChatTranslationState?, NoError> in
        guard configuration.enabled else { return .single(nil) }
        let choice = NagramiXTranslationSettings.chat(key)
        let interface = NagramiXTranslationLanguage.base(presentation.strings.baseLanguageCode)
        let target = choice.target ?? (configuration.target.isEmpty ? interface : configuration.target)
        return context.account.viewTracker.aroundMessageHistoryViewForLocation(.peer(peerId: peerId, threadId: threadId), index: .upperBound,
            anchorIndex: .upperBound, count: 32, fixedCombinedReadStates: nil)
        |> map { view, _, _ -> ChatTranslationState? in
            // Look at a bounded sample; detection is on the view-tracker queue.
            var weights: [String: Int] = [:]
            for entry in view.entries.suffix(32) {
                let message = entry.message
                guard message.adAttribute == nil, message.effectivelyIncoming(context.account.peerId),
                      let language = nagramiXTranslationSource(message.text, interface: interface, ignored: configuration.ignored) else { continue }
                weights[language, default: 0] += min(message.text.count, 512)
            }
            guard let dominant = weights.sorted(by: { $0.value == $1.value ? $0.key < $1.key : $0.value > $1.value }).first else { return nil }
            let source = dominant.value * 100 >= weights.values.reduce(0, +) * 60 ? dominant.key : "auto"
            return ChatTranslationState(baseLang: interface, fromLang: source, timestamp: nil, toLang: target,
                isEnabled: choice.enabled ?? configuration.automatic)
        }
    }
}

private func nagramiXTranslationSpans(_ entities: [MessageTextEntity]) -> [NagramiXTranslationSpan] {
    return entities.map { entity in
        let protected: Bool
        switch entity.type {
        case .Mention, .Hashtag, .BotCommand, .Url, .Email, .Code, .Pre, .TextMention, .PhoneNumber, .BankCard, .TonAddress, .CustomEmoji, .FormattedDate:
            protected = true
        default: protected = false
        }
        return NagramiXTranslationSpan(range: entity.range, protected: protected)
    }
}

private func nagramiXTranslateFragments(context: AccountContext, configuration: NagramiXTranslationConfiguration,
                                      texts: [String], source: String, target: String, chatKey: String?) -> Signal<[String], NagramiXTranslationFailure> {
    if texts.isEmpty { return .single([]) }
    if configuration.provider == .apple {
        guard #available(iOS 18.0, *), let service = engineExperimentalInternalTranslationService else { return .fail(.unavailable) }
        var requests: [AnyHashable: String] = [:]
        for (i, text) in texts.enumerated() { requests[i] = text }
        return service.translate(texts: requests, fromLang: source, toLang: target)
        |> castError(NagramiXTranslationFailure.self)
        |> mapToSignal { values -> Signal<[String], NagramiXTranslationFailure> in
            guard let values else { return .fail(.unsupportedLanguage) }
            let results = texts.indices.compactMap { values[$0] }
            guard results.count == texts.count else { return .fail(.invalidResponse) }
            return .single(results)
        }
    }
    guard let credentials = NagramiXTranslationKeys.read(configuration.provider), !credentials.key.isEmpty else { return .fail(.missingKey) }
    var groups: [[String]] = [], group: [String] = [], size = 0
    for text in texts {
        guard text.utf8.count <= 24000 else { return .fail(.tooLarge) }
        if group.count >= 32 || size + text.utf8.count > 24000 { groups.append(group); group = []; size = 0 }
        group.append(text); size += text.utf8.count
    }
    if !group.isEmpty { groups.append(group) }
    let signals = groups.map { texts -> Signal<[String], NagramiXTranslationFailure> in
        return Signal { subscriber in
            do {
                let request = try NagramiXTranslationCloudCodec.request(provider: configuration.provider, credential: credentials,
                    model: configuration.model, texts: texts, source: source, target: target)
                let scope = "\(context.account.peerId.toInt64()):\(configuration.revision)"
                let cancel = NagramiXTranslationCloudClient.shared.translate(request: request, provider: configuration.provider, count: texts.count, scope: scope, allowed: {
                    let current = NagramiXTranslationSettings.current
                    guard current.enabled, current.revision == configuration.revision else { return false }
                    if let chatKey { return NagramiXTranslationSettings.chat(chatKey).enabled ?? current.automatic }
                    return true
                }) { result in
                    switch result {
                    case let .success(value): subscriber.putNext(value); subscriber.putCompletion()
                    case let .failure(error): subscriber.putError(error)
                    }
                }
                return ActionDisposable { cancel() }
            } catch { subscriber.putError(error as? NagramiXTranslationFailure ?? .invalidText); return EmptyDisposable }
        }
    }
    return combineLatest(signals) |> map { $0.flatMap { $0 } }
}

public func nagramiXTranslateText(context: AccountContext, text: String, entities: [MessageTextEntity], source: String, target: String,
                                configuration: NagramiXTranslationConfiguration? = nil, chatKey: String? = nil) -> Signal<(String, [MessageTextEntity]), NagramiXTranslationFailure> {
    let configuration = configuration ?? NagramiXTranslationSettings.current
    if NagramiXTranslationLanguage.base(source) == NagramiXTranslationLanguage.base(target) { return .single((text, entities)) }
    let plan: NagramiXTranslationTextPlan
    do { plan = try NagramiXTranslationTextPlan(text: text, spans: nagramiXTranslationSpans(entities)) }
    catch { return .fail(error as? NagramiXTranslationFailure ?? .invalidText) }
    return nagramiXTranslateFragments(context: context, configuration: configuration, texts: plan.texts, source: source, target: target, chatKey: chatKey)
    |> timeout(180, queue: .mainQueue(), alternate: .fail(.network))
    |> mapToSignal { values -> Signal<(String, [MessageTextEntity]), NagramiXTranslationFailure> in
        do {
            let (result, ranges) = try plan.restore(values)
            return .single((result, zip(entities, ranges).map { MessageTextEntity(range: $0.1, type: $0.0.type) }))
        } catch { return .fail(error as? NagramiXTranslationFailure ?? .invalidResponse) }
    }
}

public enum NagramiXTranslationRuntime {
    public static let failed = Notification.Name("NagramiXTranslationFailed")
    private static let lock = NSLock()
    private static let stamps = NSCache<NSString, NSString>()
    private static var failures: [String: TimeInterval] = [:]

    private static func cacheKey(context: AccountContext, message: Message, target: String) -> NSString {
        return "\(context.account.peerId.toInt64()):\(message.id):\(NagramiXTranslationSettings.current.revision):\(target)" as NSString
    }
    private static func fingerprint(_ message: Message) -> String {
        let entities = (message.attributes.first { $0 is TextEntitiesMessageAttribute } as? TextEntitiesMessageAttribute)?.entities ?? []
        return message.text + String(reflecting: entities)
    }
    public static func hasTranslation(context: AccountContext, message: Message, target: String) -> Bool {
        guard NagramiXTranslationSettings.current.enabled else { return true }
        return self.stamps.object(forKey: self.cacheKey(context: context, message: message, target: target)) as String? == self.fingerprint(message)
    }
    private static func blocked(_ key: String) -> Bool {
        self.lock.lock(); defer { self.lock.unlock() }
        return Date().timeIntervalSince1970 - (self.failures[NagramiXTranslationSettings.current.revision + ":" + key] ?? 0) < 30
    }
    public static func clearFailure(chat key: String) {
        self.lock.lock(); defer { self.lock.unlock() }
        self.failures.removeValue(forKey: NagramiXTranslationSettings.current.revision + ":" + key)
    }
    private static func report(context: AccountContext, message: Message, error: NagramiXTranslationFailure) {
        let key = nagramiXTranslationChatKey(context: context, peerId: message.id.peerId, threadId: message.threadId)
        let revision = NagramiXTranslationSettings.current.revision
        let failureKey = revision + ":" + key
        self.lock.lock()
        let now = Date().timeIntervalSince1970
        let show = now - (self.failures[failureKey] ?? 0) >= 30
        self.failures = self.failures.filter { now - $0.value < 60 }
        self.failures[failureKey] = now
        self.lock.unlock()
        if show {
            DispatchQueue.main.async {
                let current = NagramiXTranslationSettings.current
                guard current.enabled, current.revision == revision, NagramiXTranslationSettings.chat(key).enabled ?? current.automatic else { return }
                NotificationCenter.default.post(name: self.failed, object: nil, userInfo: ["chat": key, "error": error])
            }
        }
    }
    public static func translate(context: AccountContext, messageIds: [EngineMessage.Id], target: String) -> Signal<Never, NoError> {
        let configuration = NagramiXTranslationSettings.current
        let interface = context.sharedContext.currentPresentationData.with { $0 }.strings.baseLanguageCode
        return context.account.postbox.transaction { transaction -> [Message] in
            return Array(Set(messageIds)).compactMap { transaction.getMessage($0) }.filter {
                $0.id.namespace == Namespaces.Message.Cloud && $0.id.peerId.namespace != Namespaces.Peer.SecretChat && $0.adAttribute == nil && !$0.text.isEmpty
                    && $0.effectivelyIncoming(context.account.peerId) && $0.richText == nil
            }
        }
        |> mapToSignal { messages -> Signal<Never, NoError> in
            let signals = messages.map { message -> Signal<Never, NoError> in
                let key = nagramiXTranslationChatKey(context: context, peerId: message.id.peerId, threadId: message.threadId)
                let choice = NagramiXTranslationSettings.chat(key)
                guard configuration.enabled, choice.enabled ?? configuration.automatic, !self.blocked(key) else { return .complete() }
                if self.hasTranslation(context: context, message: message, target: target), message.attributes.contains(where: { ($0 as? TranslationMessageAttribute)?.toLang == target }) { return .complete() }
                let entities = (message.attributes.first { $0 is TextEntitiesMessageAttribute } as? TextEntitiesMessageAttribute)?.entities ?? []
                let work: Signal<(String, [MessageTextEntity]), NagramiXTranslationFailure>
                if let source = nagramiXTranslationSource(message.text, interface: interface, ignored: configuration.ignored),
                   NagramiXTranslationLanguage.base(source) != NagramiXTranslationLanguage.base(target) {
                    work = nagramiXTranslateText(context: context, text: message.text, entities: entities, source: source, target: target, configuration: configuration, chatKey: key)
                } else {
                    // Native history expects an attribute for every visible item.
                    // Same-language/ignored/undetermined text stays local and exact.
                    work = .single((message.text, entities))
                }
                return work
                |> mapToSignal { text, translatedEntities -> Signal<Never, NagramiXTranslationFailure> in
                    return context.account.postbox.transaction { transaction in
                        let currentConfig = NagramiXTranslationSettings.current
                        let currentChoice = NagramiXTranslationSettings.chat(key)
                        guard currentConfig.enabled, currentConfig.revision == configuration.revision,
                              currentChoice.enabled ?? currentConfig.automatic,
                              let current = transaction.getMessage(message.id), self.fingerprint(current) == self.fingerprint(message),
                              NagramiXTranslationLanguage.base(currentChoice.target ?? (currentConfig.target.isEmpty ? interface : currentConfig.target)) == NagramiXTranslationLanguage.base(target) else { return }
                        self.stamps.countLimit = 2000; self.stamps.totalCostLimit = 2_000_000
                        self.stamps.setObject(self.fingerprint(current) as NSString, forKey: self.cacheKey(context: context, message: current, target: target), cost: current.text.utf8.count)
                        transaction.updateMessage(current.id, update: { value in
                            var attributes = value.attributes.filter { !($0 is TranslationMessageAttribute) }
                            attributes.append(TranslationMessageAttribute(text: text, entities: translatedEntities, toLang: target))
                            return .update(StoreMessage(id: value.id, customStableId: nil, globallyUniqueId: value.globallyUniqueId, groupingKey: value.groupingKey,
                                threadId: value.threadId, timestamp: value.timestamp, flags: StoreMessageFlags(value.flags), tags: value.tags, globalTags: value.globalTags,
                                localTags: value.localTags, forwardInfo: value.forwardInfo.flatMap(StoreMessageForwardInfo.init), authorId: value.author?.id,
                                text: value.text, attributes: attributes, media: value.media))
                        })
                    } |> castError(NagramiXTranslationFailure.self) |> ignoreValues
                }
                |> `catch` { error -> Signal<Never, NoError> in
                    if error != .cancelled, NagramiXTranslationSettings.current.revision == configuration.revision { self.report(context: context, message: message, error: error) }
                    return .complete()
                }
            }
            return combineLatest(signals) |> ignoreValues
        }
    }
}
