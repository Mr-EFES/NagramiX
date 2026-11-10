import Foundation
import UIKit
import SwiftSignalKit
import TelegramCore
import AccountContext

public func nagramiXTranscriptionSettingsSignal() -> Signal<NagramiXTranscriptionConfiguration, NoError> {
    Signal { subscriber in
        let observer = NotificationCenter.default.addObserver(forName: NagramiXTranscriptionSettings.changed, object: nil, queue: nil) { _ in subscriber.putNext(NagramiXTranscriptionSettings.current) }
        subscriber.putNext(NagramiXTranscriptionSettings.current)
        return ActionDisposable { NotificationCenter.default.removeObserver(observer) }
    }
}

private final class NagramiXTranscriptionOnce {
    private let lock = NSLock(); private var taken = false
    func take() -> Bool { self.lock.lock(); defer { self.lock.unlock() }; if self.taken { return false }; self.taken = true; return true }
}
private struct NagramiXTranscriptionStamp: Codable { let tag: String; let resource: String }

public enum NagramiXTranscriptionRuntime {
    private static let stampKey = "nagramix.asr.v1"
    // Manual work can outlive a chat controller; lifecycle cancellation must
    // therefore have process lifetime, independent of the visible-chat helper.
    private static let lifecycleObservers: [NSObjectProtocol] = [UIApplication.didEnterBackgroundNotification, UIApplication.didReceiveMemoryWarningNotification].map { name in
        NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { _ in NagramiXTranscriptionCoordinator.shared.cancelAll() }
    }

    private static var contextJobs: [String: MetaDisposable] = [:] // Main queue only.
    private static func contextKey(_ context: AccountContext, _ id: EngineMessage.Id) -> String {
        "\(context.account.peerId.toInt64()):\(id.peerId.toInt64()):\(id.namespace):\(id.id)"
    }
    public static func contextRunning(context: AccountContext, messageId: EngineMessage.Id) -> Bool {
        assert(Thread.isMainThread); return self.contextJobs[self.contextKey(context, messageId)] != nil
    }
    public static func toggleContext(context: AccountContext, messageId: EngineMessage.Id, completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        assert(Thread.isMainThread)
        let key = self.contextKey(context, messageId)
        if let current = self.contextJobs.removeValue(forKey: key) { current.dispose(); return }
        let job = MetaDisposable(); self.contextJobs[key] = job
        job.set((self.contextTranscribe(context: context, messageId: messageId) |> deliverOnMainQueue).start(next: { result in
            guard self.contextJobs[key] === job else { return }
            self.contextJobs.removeValue(forKey: key)?.dispose(); completion(result)
        }))
    }

    private static func contextTranscribe(context: AccountContext, messageId: EngineMessage.Id) -> Signal<Result<String, NagramiXTranscriptionFailure>, NoError> {
        // Resolve first: a native Telegram request must never be used for a
        // protected temporary voice or round video, even with Premium.
        return context.engine.messages.nagramiXTranscriptionMessages([messageId])
        |> mapToSignal { messages -> Signal<Result<String, NagramiXTranscriptionFailure>, NoError> in
            guard let message = messages.first, Self.file(message) != nil else { return .single(.failure(.unavailableMedia)) }
            let configuration = Self.configuration(for: message)
            guard configuration.enabled else { return .single(.failure(.disabled)) }
            if configuration.provider != .telegram {
                return Self.transcribe(context: context, messageId: messageId, forceRefresh: true)
            }
            return Self.contextTelegramTranscribe(context: context, messageId: messageId)
        }
    }

    private static func contextTelegramTranscribe(context: AccountContext, messageId: EngineMessage.Id) -> Signal<Result<String, NagramiXTranscriptionFailure>, NoError> {
        let configuration = NagramiXTranscriptionSettings.current
        guard configuration.enabled else { return .single(.failure(.disabled)) }
        guard configuration.provider == .telegram else {
            return self.transcribe(context: context, messageId: messageId, forceRefresh: true)
        }
        return context.engine.data.get(TelegramEngine.EngineData.Item.Peer.Peer(id: context.account.peerId))
        |> mapToSignal { peer -> Signal<Result<String, NagramiXTranscriptionFailure>, NoError> in
            guard peer?.isPremium == true else { return .single(.failure(.authorization)) }
            let current = NagramiXTranscriptionSettings.current
            guard current.enabled, current.provider == .telegram, current.revision == configuration.revision else { return .single(.failure(.cancelled)) }
            // Always make a new server request. Telegram controls whether its
            // backend recomputes the text or returns its own cached result.
            return context.engine.messages.nagramiXTranscriptionMessages([messageId])
            |> mapToSignal { messages -> Signal<Result<String, NagramiXTranscriptionFailure>, NoError> in
                let current = NagramiXTranscriptionSettings.current
                guard current.enabled, current.provider == .telegram, current.revision == configuration.revision else { return .single(.failure(.cancelled)) }
                guard let message = messages.first, Self.canUseTelegram(message) else { return .single(.failure(.unavailableMedia)) }
                // Only ordinary live messages reach the native server RPC.
                return context.engine.messages.transcribeAudio(messageId: messageId)
                |> map { result in
                    switch result {
                    case .success: return .success("")
                    case .error: return .failure(.network)
                    }
                }
            }
        }
    }

    public static func handlesContext(_ message: EngineRawMessage) -> Bool {
        let configuration = self.configuration(for: message)
        return configuration.enabled && self.file(message) != nil
            && (configuration.provider != .telegram || self.canUseTelegram(message))
    }

    private static func configuration(for message: EngineRawMessage) -> NagramiXTranscriptionConfiguration {
        var configuration = NagramiXTranscriptionSettings.current
        if nagramiXCanTranscribeTemporaryMedia(message), !configuration.enabled || configuration.provider == .telegram {
            // Preserve the native button when custom ASR is disabled, without
            // sending the original ID to Telegram or enabling a cloud service.
            configuration.automatic = configuration.enabled && configuration.automatic
            configuration.enabled = true
            configuration.provider = .apple
            if configuration.language == "auto" { configuration.language = Locale.current.identifier.replacingOccurrences(of: "_", with: "-") }
        }
        return configuration
    }

    public static func file(_ message: EngineRawMessage) -> TelegramMediaFile? {
        // Temporary-media eligibility is the explicit local/secret exception.
        // Ordinary secret and non-cloud messages keep their native exclusions.
        if nagramiXCanTranscribeTemporaryMedia(message) {
            return message.media.first as? TelegramMediaFile
        }
        guard message.id.namespace == Namespaces.Message.Cloud, message.id.peerId.namespace != Namespaces.Peer.SecretChat else { return nil }
        // A retained temporary row has no TTL attribute. Do not let that make it
        // eligible after the Temporary Messages switch has been turned off.
        guard !message.attributes.contains(where: { ($0 as? NagramiXArchivedMessageAttribute)?.isTemporary == true }),
              !message.containsSecretMedia, !message.isSelfExpiring, !message.isCopyProtected() else { return nil }
        return message.media.compactMap { $0 as? TelegramMediaFile }.first { $0.isVoice || $0.isInstantVideo }
    }
    public static func hasTemporaryTranscript(_ message: EngineRawMessage) -> Bool {
        guard nagramiXCanTranscribeTemporaryMedia(message) else { return false }
        return message.attributes.contains { attribute in
            guard let text = attribute as? AudioTranscriptionMessageAttribute else { return false }
            return !text.isPending && text.error == nil && !text.text.isEmpty
        }
    }
    public static func canUseTelegram(_ message: EngineRawMessage) -> Bool {
        // The RPC needs a live server message. Never send an archived local copy
        // to Telegram under an expired/deleted message ID or create a hidden copy.
        return message.id.namespace == Namespaces.Message.Cloud
            && message.id.peerId.namespace != Namespaces.Peer.SecretChat
            && !nagramiXCanTranscribeTemporaryMedia(message)
            && self.file(message) != nil && !message.attributes.contains { $0 is NagramiXArchivedMessageAttribute }
    }
    public static func handles(_ message: EngineRawMessage) -> Bool {
        let config = self.configuration(for: message)
        return config.enabled && config.provider != .telegram && self.file(message) != nil
    }
    private static func identity(_ file: TelegramMediaFile, message: EngineRawMessage) -> String {
        // A retained file has a different local resource ID but the same immutable
        // Telegram file ID. Preserve a temporary voice's cache across that move.
        let resource = nagramiXCanTranscribeTemporaryMedia(message)
            ? "temporary:\(file.fileId.namespace):\(file.fileId.id)"
            : file.resource.id.stringRepresentation
        return resource + ":" + String(file.size ?? 0) + ":" + String(file.duration ?? 0)
    }
    public static func cached(_ message: EngineRawMessage) -> String? {
        guard let file = self.file(message),
              let data = message.attributes.compactMap({ $0 as? DerivedDataMessageAttribute }).first?.data[self.stampKey],
              let stamp = data.get(NagramiXTranscriptionStamp.self), stamp.tag == self.configuration(for: message).cacheTag,
              stamp.resource == self.identity(file, message: message),
              let text = message.attributes.compactMap({ $0 as? AudioTranscriptionMessageAttribute }).first,
              text.id == 0, !text.isPending, text.error == nil, !text.text.isEmpty else { return nil }
        return text.text
    }
    public static func transcribe(context: AccountContext, messageId: EngineMessage.Id, automatic: Bool = false, forceRefresh: Bool = false) -> Signal<Result<String, NagramiXTranscriptionFailure>, NoError> {
        _ = self.lifecycleObservers
        return Signal { subscriber in
            let bag = DisposableSet(); let consumer = MetaDisposable(); bag.add(consumer)
            bag.add(context.engine.messages.nagramiXTranscriptionMessages([messageId]).start(next: { messages in
                guard let message = messages.first, let file = Self.file(message) else { subscriber.putNext(.failure(.unavailableMedia)); subscriber.putCompletion(); return }
                let config = Self.configuration(for: message)
                guard config.enabled, config.provider != .telegram, !automatic || (config.automatic && message.flags.contains(.Incoming)) else {
                    subscriber.putNext(.failure(.disabled)); subscriber.putCompletion(); return
                }
                if !forceRefresh, let cached = Self.cached(message) { subscriber.putNext(.success(cached)); subscriber.putCompletion(); return }
                if automatic, message.attributes.contains(where: { ($0 as? AudioTranscriptionMessageAttribute)?.text.isEmpty == false }) {
                    subscriber.putNext(.success("")); subscriber.putCompletion(); return
                }
                guard (file.duration ?? 0) > 0, (file.duration ?? 0) <= 900 else { subscriber.putNext(.failure(.tooLarge)); subscriber.putCompletion(); return }
                let resource = Self.identity(file, message: message)
                let originalTranscription = message.attributes.compactMap { $0 as? AudioTranscriptionMessageAttribute }.first
                let key = "\(context.account.peerId.toInt64()):\(message.id.peerId.toInt64()):\(message.id.namespace):\(message.id.id):\(resource):\(config.cacheTag)"
                // A menu request must run again even if an automatic or button
                // request for the same message is already running or queued.
                let requestKey = forceRefresh ? key + ":manual:" + UUID().uuidString : key
                let cancellation = NagramiXTranscriptionCoordinator.shared.request(key: requestKey, configuration: config, automatic: automatic, work: { token, finish in
                    guard Self.valid(config, token, message: message), Self.file(message) != nil else { finish(.failure(.cancelled)); return }
                    Self.load(context: context, message: message, file: file, automatic: automatic, token: token) { loaded in
                        switch loaded {
                        case let .failure(error): finish(.failure(error))
                        case let .success(path):
                            NagramiXTranscriptionMedia.prepare(path: path, cancellation: token) { prepared in
                                switch prepared {
                                case let .failure(error): finish(.failure(error))
                                case let .success(media):
                                    guard Self.valid(config, token, message: message), Self.file(message) != nil else { finish(.failure(.cancelled)); return }
                                    let recognized: (Result<String, NagramiXTranscriptionFailure>) -> Void = { result in
                                        // Keep temporary audio alive until the recognizer has closed it.
                                        _ = media
                                        guard !token.cancelled else { finish(.failure(.cancelled)); return }
                                        switch result {
                                        case let .failure(error): finish(.failure(error))
                                        case let .success(text):
                                            let storage = MetaDisposable()
                                            storage.set(Self.store(context: context, messageId: messageId, resource: resource, config: config, text: text, token: token, automatic: automatic, forceRefresh: forceRefresh, expectedText: originalTranscription?.text, expectedId: originalTranscription?.id).start(next: { saved in
                                                storage.dispose(); finish(saved ? .success(text) : .failure(.cancelled))
                                            }))
                                        }
                                    }
                                    // Retries use only already available local recognizers, never a paid cloud service.
                                    var candidates: [NagramiXTranscriptionProvider] = [config.provider]
                                    if config.localFallback == true {
                                        for provider in [NagramiXTranscriptionProvider.apple, .whisper, .vosk] where !candidates.contains(provider) { candidates.append(provider) }
                                    }
                                    func attempt(_ index: Int, firstError: NagramiXTranscriptionFailure?) {
                                        guard Self.valid(config, token, message: message), Self.file(message) != nil else { recognized(.failure(.cancelled)); return }
                                        guard index < candidates.count else { recognized(.failure(firstError ?? .unavailable)); return }
                                        let provider = candidates[index]
                                        let completed: (Result<String, NagramiXTranscriptionFailure>) -> Void = { result in
                                            switch result {
                                            case .success: recognized(result)
                                            case let .failure(error):
                                                if error == .cancelled || error == .noSpeech || error == .tooLarge { recognized(.failure(error)); return }
                                                attempt(index + 1, firstError: firstError ?? error)
                                            }
                                        }
                                        if provider == .apple {
                                            // A fallback must not trigger a new permission prompt.
                                            guard (index == 0 && !automatic) || NagramiXTranscriptionApple.authorized else { completed(.failure(.permission)); return }
                                            guard NagramiXTranscriptionApple.available(config.language) else { completed(.failure(.unavailable)); return }
                                            NagramiXTranscriptionApple.transcribe(url: media.audio, language: config.language, automatic: automatic || index > 0, cancellation: token, completion: completed)
                                        } else if provider == .whisper {
                                            guard NagramiXWhisperModels.shared.installed(config.whisper) else { completed(.failure(.missingModel)); return }
                                            NagramiXTranscriptionWhisper.transcribe(media: media, configuration: config, cancellation: token, completion: completed)
                                        } else if provider == .vosk {
                                            guard NagramiXTranscriptionVosk.available(config) else { completed(.failure(.missingModel)); return }
                                            NagramiXTranscriptionVosk.transcribe(media: media, configuration: config, cancellation: token, completion: completed)
                                        } else if index == 0 && provider.cloud {
                                            guard let key = NagramiXTranscriptionKeys.read(provider), !key.isEmpty else { completed(.failure(.missingKey)); return }
                                            DispatchQueue.global(qos: .utility).async {
                                                do {
                                                    guard Self.valid(config, token, message: message), Self.file(message) != nil else { throw NagramiXTranscriptionFailure.cancelled }
                                                    let data = try Data(contentsOf: media.audio)
                                                    NagramiXTranscriptionCloud.shared.transcribe(configuration: config, key: key, audio: data, cancellation: token, completion: completed)
                                                } catch { completed(.failure(error as? NagramiXTranscriptionFailure ?? .storage)) }
                                            }
                                        } else { completed(.failure(.unavailable)) }
                                    }
                                    attempt(0, firstError: nil)
                                }
                            }
                        }
                    }
                }, completion: { result in subscriber.putNext(result); subscriber.putCompletion() })
                consumer.set(ActionDisposable { cancellation.cancel() })
            }))
            return bag
        }
    }
    private static func valid(_ config: NagramiXTranscriptionConfiguration, _ token: NagramiXTranscriptionCancellation, message: EngineRawMessage) -> Bool {
        let current = Self.configuration(for: message)
        return !token.cancelled && current.enabled && current.revision == config.revision && current.cacheTag == config.cacheTag
    }
    private static func load(context: AccountContext, message: EngineRawMessage, file: TelegramMediaFile, automatic: Bool, token: NagramiXTranscriptionCancellation,
                             completion: @escaping (Result<String, NagramiXTranscriptionFailure>) -> Void) {
        let once = NagramiXTranscriptionOnce(); let bag = DisposableSet()
        func finish(_ result: Result<String, NagramiXTranscriptionFailure>) {
            guard once.take() else { return }; bag.dispose(); completion(result)
        }
        let timeout = DispatchWorkItem { finish(.failure(.network)) }
        DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 120, execute: timeout)
        bag.add(ActionDisposable { timeout.cancel() })
        token.add { finish(.failure(.cancelled)) }
        let retained = message.attributes.contains { $0 is NagramiXArchivedMessageAttribute }
        if !automatic && !retained {
            bag.add(context.engine.resources.fetch(reference: .media(media: .message(message: MessageReference(message), media: file), resource: file.resource), userLocation: .peer(message.id.peerId), userContentType: .audioVideoMessage).start(error: { _ in finish(.failure(.network)) }))
        }
        let data = context.engine.resources.data(id: EngineMediaResource.Id(file.resource.id))
        let ready = automatic || retained ? (data |> take(1)) : (data |> filter { $0.isComplete } |> take(1))
        bag.add(ready.start(next: { value in finish(value.isComplete ? .success(value.path) : .failure(.unavailableMedia)) }))
    }
    private static func store(context: AccountContext, messageId: EngineMessage.Id, resource: String, config: NagramiXTranscriptionConfiguration, text: String, token: NagramiXTranscriptionCancellation, automatic: Bool, forceRefresh: Bool, expectedText: String?, expectedId: Int64?) -> Signal<Bool, NoError> {
        context.engine.messages.nagramiXUpdateTranscriptionAttributes(messageId: messageId) { current in
            guard !token.cancelled, !text.isEmpty, text.utf16.count <= 100_000,
                  Self.configuration(for: current).enabled, Self.configuration(for: current).revision == config.revision,
                  Self.configuration(for: current).cacheTag == config.cacheTag,
                  let file = Self.file(current), Self.identity(file, message: current) == resource,
                  let entry = EngineCodableEntry(NagramiXTranscriptionStamp(tag: config.cacheTag, resource: resource)) else { return nil }
            // Queued background/button work must not overwrite a newer result.
            let existing = current.attributes.compactMap { $0 as? AudioTranscriptionMessageAttribute }.first
            if !forceRefresh && (existing?.text != expectedText || existing?.id != expectedId) { return nil }
            if automatic, existing?.text.isEmpty == false { return nil }
            var derived = current.attributes.compactMap { $0 as? DerivedDataMessageAttribute }.first?.data ?? [:]
            derived[Self.stampKey] = entry
            var attributes = current.attributes.filter { !($0 is AudioTranscriptionMessageAttribute) && !($0 is DerivedDataMessageAttribute) }
            attributes.append(DerivedDataMessageAttribute(data: derived))
            attributes.append(AudioTranscriptionMessageAttribute(id: 0, text: text, isPending: false, didRate: true, error: nil))
            return attributes
        }
    }
}

// Owned by one visible chat. Downloads are never started automatically.
public final class NagramiXTranscriptionAutomatic {
    private let context: AccountContext
    private var ids: [EngineMessage.Id] = []
    private var jobs: [EngineMessage.Id: MetaDisposable] = [:]
    private var attempted: Set<EngineMessage.Id> = []
    private var revision = ""
    private var observer: NSObjectProtocol?
    private var backgroundObserver: NSObjectProtocol?
    public init(context: AccountContext) {
        self.context = context
        self.observer = NotificationCenter.default.addObserver(forName: NagramiXTranscriptionSettings.changed, object: nil, queue: .main) { [weak self] _ in guard let self else { return }; self.update(self.ids) }
        self.backgroundObserver = NotificationCenter.default.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: .main) { [weak self] _ in self?.update([]) }
    }
    public func update(_ ids: [EngineMessage.Id]) {
        assert(Thread.isMainThread)
        self.ids = Array(ids.prefix(24))
        let config = NagramiXTranscriptionSettings.current
        if self.revision != config.revision { self.jobs.values.forEach { $0.dispose() }; self.jobs.removeAll(); self.attempted.removeAll(); self.revision = config.revision }
        let visible = config.enabled && config.automatic && config.provider != .telegram ? Set(self.ids) : []
        for id in Array(self.jobs.keys) where !visible.contains(id) { self.jobs.removeValue(forKey: id)?.dispose() }
        self.attempted.formIntersection(visible)
        for id in self.ids where visible.contains(id) && !self.attempted.contains(id) {
            self.attempted.insert(id)
            let job = MetaDisposable(); self.jobs[id] = job
            job.set((NagramiXTranscriptionRuntime.transcribe(context: self.context, messageId: id, automatic: true) |> deliverOnMainQueue).start(next: { [weak self] _ in self?.jobs.removeValue(forKey: id)?.dispose() }))
        }
    }
    deinit {
        if let observer { NotificationCenter.default.removeObserver(observer) }
        if let backgroundObserver { NotificationCenter.default.removeObserver(backgroundObserver) }
        self.jobs.values.forEach { $0.dispose() }
    }
}
