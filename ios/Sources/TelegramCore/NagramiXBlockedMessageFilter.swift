import Foundation
import Postbox
import SwiftSignalKit
import TelegramApi
import MtProtoKit

private final class NagramiXWeakBlockedMessageFilter {
    weak var value: NagramiXBlockedMessageFilter?
    init(_ value: NagramiXBlockedMessageFilter) { self.value = value }
}

// Только локальный показ истории. Сообщения, read state и серверные права не меняются.
public final class NagramiXBlockedMessageFilter {
    private struct Cache: Codable {
        let accountPeerId: Int64
        let authorIds: [Int64]
    }
    private static let registry = Atomic<[ObjectIdentifier: NagramiXWeakBlockedMessageFilter]>(value: [:])
    public static let settingsChanged = Notification.Name("NagramiXBlockedMessagesSettingsChanged")
    public static var enabled: Bool {
        return UserDefaults.standard.object(forKey: "nagramix.messages.hideBlocked") as? Bool ?? true
    }

    static func forPostbox(_ postbox: Postbox) -> NagramiXBlockedMessageFilter? {
        return self.registry.with { $0[ObjectIdentifier(postbox)]?.value }
    }

    private let queue = Queue(name: "org.nagramix.blocked-message-filter")
    private let peerId: PeerId
    private let network: Network
    private let postbox: Postbox
    private let path: String
    private let ids = Atomic<Set<PeerId>>(value: [])
    private let revisions = ValuePromise<Int>(0, ignoreRepeated: false)
    private var revision = 0
    private var syncGeneration: UInt64 = 0
    private var syncing = false
    private var pendingChanges: [PeerId: Bool] = [:]
    private var lastSync: CFAbsoluteTime?
    private let syncDisposable = MetaDisposable()
    private var observers: [NSObjectProtocol] = []

    public init(postbox: Postbox, network: Network, peerId: PeerId, basePath: String) {
        self.postbox = postbox
        self.network = network
        self.peerId = peerId
        self.path = basePath + "/nagramix-blocked-authors.json"
        _ = Self.registry.modify { value in
            var value = value
            value[ObjectIdentifier(postbox)] = NagramiXWeakBlockedMessageFilter(self)
            return value
        }
        self.queue.async { [weak self] in
            guard let self else { return }
            if let data = try? Data(contentsOf: URL(fileURLWithPath: self.path)),
               let cache = try? JSONDecoder().decode(Cache.self, from: data), cache.accountPeerId == self.peerId.toInt64() {
                self.publish(Set(cache.authorIds.map { PeerId($0) }).subtracting([self.peerId]), persist: false)
            }
        }
        self.observers.append(NotificationCenter.default.addObserver(forName: Self.settingsChanged, object: nil, queue: nil, using: { [weak self] _ in
            self?.queue.async {
                guard let self else { return }
                self.revision &+= 1
                self.revisions.set(self.revision)
                if Self.enabled {
                    self.startSync(force: true)
                } else {
                    self.syncGeneration &+= 1
                    self.syncing = false
                    self.pendingChanges.removeAll()
                    self.syncDisposable.set(nil)
                }
            }
        }))
        self.observers.append(NotificationCenter.default.addObserver(forName: Notification.Name("UIApplicationWillEnterForegroundNotification"), object: nil, queue: nil, using: { [weak self] _ in
            self?.queue.async { self?.startSync(force: true) }
        }))
    }

    deinit {
        self.syncDisposable.dispose()
        for observer in self.observers { NotificationCenter.default.removeObserver(observer) }
        _ = Self.registry.modify { value in
            var value = value
            let key = ObjectIdentifier(self.postbox)
            if value[key]?.value == nil || value[key]?.value === self { value.removeValue(forKey: key) }
            return value
        }
    }

    public var updates: Signal<Int, NoError> {
        self.queue.async { [weak self] in self?.startSync(force: false) }
        return self.revisions.get()
    }

    public func shouldHide(_ message: Message, enabled: Bool) -> Bool {
        return enabled && Self.shouldHide(authorId: message.author?.id, isIncoming: message.flags.contains(.Incoming), accountPeerId: self.peerId, blockedAuthorIds: self.ids.with { $0 })
    }

    public static func shouldHide(authorId: PeerId?, isIncoming: Bool, accountPeerId: PeerId, blockedAuthorIds: Set<PeerId>) -> Bool {
        guard isIncoming, let authorId, authorId != accountPeerId else { return false }
        return blockedAuthorIds.contains(authorId)
    }

    static func resolvedAuthors(_ snapshot: Set<PeerId>, changes: [PeerId: Bool], accountPeerId: PeerId) -> Set<PeerId> {
        var result = snapshot
        for (peerId, blocked) in changes {
            if blocked { result.insert(peerId) } else { result.remove(peerId) }
        }
        result.remove(accountPeerId)
        return result
    }

    // Вызывается после успешной штатной операции или при replay updatePeerBlocked.
    func setBlocked(_ peerId: PeerId, _ blocked: Bool) {
        guard peerId != self.peerId else { return }
        self.queue.async { [weak self] in
            guard let self else { return }
            if self.syncing { self.pendingChanges[peerId] = blocked }
            var ids = self.ids.with { $0 }
            if blocked { ids.insert(peerId) } else { ids.remove(peerId) }
            self.publish(ids, persist: true)
        }
    }

    private func publish(_ ids: Set<PeerId>, persist: Bool) {
        let previous = self.ids.swap(ids)
        guard previous != ids else { return }
        if persist, let data = try? JSONEncoder().encode(Cache(accountPeerId: self.peerId.toInt64(), authorIds: ids.map { $0.toInt64() }.sorted())) {
            try? data.write(to: URL(fileURLWithPath: self.path), options: .atomic)
        }
        self.revision &+= 1
        self.revisions.set(self.revision)
    }

    private func startSync(force: Bool) {
        guard Self.enabled, !self.syncing else { return }
        if !force, let lastSync = self.lastSync, CFAbsoluteTimeGetCurrent() - lastSync < 60.0 { return }
        self.syncing = true
        self.pendingChanges.removeAll()
        self.syncGeneration &+= 1
        self.loadPage(offset: 0, collected: [], generation: self.syncGeneration)
    }

    private func loadPage(offset: Int32, collected: Set<PeerId>, generation: UInt64) {
        self.syncDisposable.set((self.network.request(Api.functions.contacts.getBlocked(flags: 0, offset: offset, limit: 200))
        |> retryRequestIfNotFrozen
        |> deliverOn(self.queue)).start(next: { [weak self] result in
            guard let self, self.syncing, self.syncGeneration == generation else { return }
            guard let result else {
                self.syncing = false
                self.pendingChanges.removeAll()
                return // Отказ/заморозка не означает пустой чёрный список.
            }
            let blocked: [Api.PeerBlocked]
            let totalCount: Int32?
            switch result {
            case let .blocked(data): blocked = data.blocked; totalCount = nil
            case let .blockedSlice(data): blocked = data.blocked; totalCount = data.count
            }
            var ids = collected
            for item in blocked {
                if case let .peerBlocked(data) = item { ids.insert(data.peerId.peerId) }
            }
            let nextOffset = Int64(offset) + Int64(blocked.count)
            if let totalCount, nextOffset < Int64(totalCount) {
                // Неполный/непродвигающийся ответ не стирает прошлое состояние.
                guard !blocked.isEmpty, nextOffset <= Int64(Int32.max) else {
                    self.syncing = false
                    self.pendingChanges.removeAll()
                    return
                }
                self.loadPage(offset: Int32(nextOffset), collected: ids, generation: generation)
                return
            }
            ids = Self.resolvedAuthors(ids, changes: self.pendingChanges, accountPeerId: self.peerId)
            self.syncing = false
            self.pendingChanges.removeAll()
            self.lastSync = CFAbsoluteTimeGetCurrent()
            self.publish(ids, persist: true)
        }))
    }
}
