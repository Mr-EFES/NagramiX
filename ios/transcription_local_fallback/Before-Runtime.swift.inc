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
        job.set((self.transcribe(context: context, messageId: messageId) |> deliverOnMainQueue).start(next: { result in
            guard self.contextJobs[key] === job else { return }
            self.contextJobs.removeValue(forKey: key)?.dispose(); completion(result)
        }))
    }

    public static func file(_ message: EngineRawMessage) -> TelegramMediaFile? {
        guard message.id.namespace == Namespaces.Message.Cloud, message.id.peerId.namespace != Namespaces.Peer.SecretChat,
              !message.containsSecretMedia, !message.isSelfExpiring, !message.isCopyProtected() else { return nil }
        return message.media.compactMap { $0 as? TelegramMediaFile }.first { $0.isVoice || $0.isInstantVideo }
    }
    public static func handles(_ message: EngineRawMessage) -> Bool {
        let config = NagramiXTranscriptionSettings.current
        return config.enabled && config.provider != .telegram && self.file(message) != nil
    }
    private static func identity(_ file: TelegramMediaFile) -> String {
        file.resource.id.stringRepresentation + ":" + String(file.size ?? 0) + ":" + String(file.duration ?? 0)
    }
    public static func cached(_ message: EngineRawMessage) -> String? {
        guard let file = self.file(message),
              let data = message.attributes.compactMap({ $0 as? DerivedDataMessageAttribute }).first?.data[self.stampKey],
              let stamp = data.get(NagramiXTranscriptionStamp.self), stamp.tag == NagramiXTranscriptionSettings.current.cacheTag,
              stamp.resource == self.identity(file),
              let text = message.attributes.compactMap({ $0 as? AudioTranscriptionMessageAttribute }).first,
              text.id == 0, !text.isPending, text.error == nil, !text.text.isEmpty else { return nil }
        return text.text
    }
    public static func transcribe(context: AccountContext, messageId: EngineMessage.Id, automatic: Bool = false) -> Signal<Result<String, NagramiXTranscriptionFailure>, NoError> {
        _ = self.lifecycleObservers
        return Signal { subscriber in
            let bag = DisposableSet(); let consumer = MetaDisposable(); bag.add(consumer)
            bag.add(context.engine.messages.nagramiXLocalMessages([messageId]).start(next: { messages in
                guard let message = messages.first, let file = Self.file(message) else { subscriber.putNext(.failure(.unavailableMedia)); subscriber.putCompletion(); return }
                let config = NagramiXTranscriptionSettings.current
                guard config.enabled, config.provider != .telegram, !automatic || (config.automatic && message.flags.contains(.Incoming)) else {
                    subscriber.putNext(.failure(.disabled)); subscriber.putCompletion(); return
                }
                if let cached = Self.cached(message) { subscriber.putNext(.success(cached)); subscriber.putCompletion(); return }
                if automatic, message.attributes.contains(where: { ($0 as? AudioTranscriptionMessageAttribute)?.text.isEmpty == false }) {
                    subscriber.putNext(.success("")); subscriber.putCompletion(); return
                }
                guard (file.duration ?? 0) > 0, (file.duration ?? 0) <= 900 else { subscriber.putNext(.failure(.tooLarge)); subscriber.putCompletion(); return }
                let resource = Self.identity(file)
                let key = "\(context.account.peerId.toInt64()):\(message.id.peerId.toInt64()):\(message.id.namespace):\(message.id.id):\(resource):\(config.cacheTag)"
                let cancellation = NagramiXTranscriptionCoordinator.shared.request(key: key, configuration: config, automatic: automatic, work: { token, finish in
                    guard Self.valid(config, token) else { finish(.failure(.cancelled)); return }
                    if config.provider.cloud {
                        guard config.cloudAllowed[config.provider.rawValue] == true else { finish(.failure(.cloudPermission)); return }
                        guard NagramiXTranscriptionKeys.read(config.provider)?.isEmpty == false else { finish(.failure(.missingKey)); return }
                    }
                    if config.provider == .apple {
                        guard !automatic || NagramiXTranscriptionApple.authorized else { finish(.failure(.permission)); return }
                        guard NagramiXTranscriptionApple.available(config.language) else { finish(.failure(.unavailable)); return }
                    }
                    if config.provider == .whisper, !NagramiXWhisperModels.shared.installed(config.whisper) { finish(.failure(.missingModel)); return }
                    Self.load(context: context, message: message, file: file, automatic: automatic, token: token) { loaded in
                        switch loaded {
                        case let .failure(error): finish(.failure(error))
                        case let .success(path):
                            NagramiXTranscriptionMedia.prepare(path: path, cancellation: token) { prepared in
                                switch prepared {
                                case let .failure(error): finish(.failure(error))
                                case let .success(media):
                                    guard Self.valid(config, token) else { finish(.failure(.cancelled)); return }
                                    let recognized: (Result<String, NagramiXTranscriptionFailure>) -> Void = { result in
                                        // Keep temporary audio alive until the recognizer has closed it.
                                        _ = media
                                        guard !token.cancelled else { finish(.failure(.cancelled)); return }
                                        switch result {
                                        case let .failure(error): finish(.failure(error))
                                        case let .success(text):
                                            let storage = MetaDisposable()
                                            storage.set(Self.store(context: context, messageId: messageId, resource: resource, config: config, text: text, token: token).start(next: { saved in
                                                storage.dispose(); finish(saved ? .success(text) : .failure(.cancelled))
                                            }))
                                        }
                                    }
                                    if config.provider == .apple {
                                        NagramiXTranscriptionApple.transcribe(url: media.audio, language: config.language, automatic: automatic, cancellation: token, completion: recognized)
                                    } else if config.provider == .whisper {
                                        NagramiXTranscriptionWhisper.transcribe(media: media, configuration: config, cancellation: token, completion: recognized)
                                    } else {
                                        DispatchQueue.global(qos: .utility).async {
                                            do {
                                                guard Self.valid(config, token) else { throw NagramiXTranscriptionFailure.cancelled }
                                                let data = try Data(contentsOf: media.audio)
                                                NagramiXTranscriptionCloud.shared.transcribe(configuration: config, key: NagramiXTranscriptionKeys.read(config.provider) ?? "", audio: data, cancellation: token, completion: recognized)
                                            } catch { recognized(.failure(error as? NagramiXTranscriptionFailure ?? .storage)) }
                                        }
                                    }
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
    private static func valid(_ config: NagramiXTranscriptionConfiguration, _ token: NagramiXTranscriptionCancellation) -> Bool {
        let current = NagramiXTranscriptionSettings.current
        return !token.cancelled && current.enabled && current.revision == config.revision
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
        if !automatic {
            bag.add(context.engine.resources.fetch(reference: .media(media: .message(message: MessageReference(message), media: file), resource: file.resource), userLocation: .peer(message.id.peerId), userContentType: .audioVideoMessage).start(error: { _ in finish(.failure(.network)) }))
        }
        let data = context.engine.resources.data(id: EngineMediaResource.Id(file.resource.id))
        let ready = automatic ? (data |> take(1)) : (data |> filter { $0.isComplete } |> take(1))
        bag.add(ready.start(next: { value in finish(value.isComplete ? .success(value.path) : .failure(.unavailableMedia)) }))
    }
    private static func store(context: AccountContext, messageId: EngineMessage.Id, resource: String, config: NagramiXTranscriptionConfiguration, text: String, token: NagramiXTranscriptionCancellation) -> Signal<Bool, NoError> {
        context.engine.messages.nagramiXUpdateLocalMessageAttributes(messageId: messageId) { current in
            guard !token.cancelled, !text.isEmpty, text.utf16.count <= 100_000,
                  NagramiXTranscriptionSettings.current.enabled, NagramiXTranscriptionSettings.current.revision == config.revision,
                  let file = Self.file(current), Self.identity(file) == resource,
                  let entry = EngineCodableEntry(NagramiXTranscriptionStamp(tag: config.cacheTag, resource: resource)) else { return nil }
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
