import Foundation
import Postbox
import MtProtoKit
internal import TelegramApi
import SwiftSignalKit
import NagramiXMediaSettings

private struct NagramiXGhostReadMarker: Codable {
    let maxId: Int32
    // Upper bound available to a native push already queued before the bulk action.
    var previousRead: Int32?
}

private func nagramiXGhostReadKey(_ peerId: PeerId, threadId: Int64?) -> ValueBoxKey {
    // Keep the original peer key intact. Legacy peer-wide watermarks cannot
    // safely be assigned to an arbitrary topic or retired by a topic receipt.
    let key = ValueBoxKey(length: threadId == nil ? 16 : 24)
    key.setInt64(0, value: threadId == nil ? 0x4e61677247686f73 : 0x4e61677254687264)
    key.setInt64(8, value: peerId.toInt64())
    if let threadId { key.setInt64(16, value: threadId) }
    return key
}

func nagramiXHasPrivateRead(transaction: Transaction, peerId: PeerId, threadId: Int64? = nil) -> Bool {
    return transaction.getPreferencesEntry(key: nagramiXGhostReadKey(peerId, threadId: threadId))?.get(NagramiXGhostReadMarker.self) != nil
}

func nagramiXAcknowledgePrivateRead(transaction: Transaction, peerId: PeerId, maxId: Int32, threadId: Int64? = nil) {
    let key = nagramiXGhostReadKey(peerId, threadId: threadId)
    if let marker = transaction.getPreferencesEntry(key: key)?.get(NagramiXGhostReadMarker.self), marker.maxId <= maxId {
        transaction.updatePreferencesEntry(key: key, { _ in nil })
    }
}

// Preferences belong to this Postbox account. The private watermark and local
// read commit together; no user-default/account-id or schema migration is needed.
func nagramiXRecordPrivateRead(transaction: Transaction, index: MessageIndex, threadId: Int64? = nil) -> Bool {
    guard NagramiXGhostSettings.current.hidesMessageReads else { return false }
    if index.id.peerId.namespace == Namespaces.Peer.SecretChat {
        if index.id.namespace == Namespaces.Message.SecretIncoming, index.timestamp > 0 {
            let key = nagramiXGhostReadKey(index.id.peerId, threadId: nil)
            let previousDate = transaction.getPreferencesEntry(key: key)?.get(NagramiXGhostReadMarker.self)?.maxId ?? 0
            if index.timestamp > previousDate {
                transaction.setPreferencesEntry(key: key, value: PreferencesEntry(NagramiXGhostReadMarker(maxId: index.timestamp, previousRead: 0)))
            }
        }
        return true
    }
    guard index.id.namespace == Namespaces.Message.Cloud else { return true }
    let key = nagramiXGhostReadKey(index.id.peerId, threadId: threadId)
    let old = transaction.getPreferencesEntry(key: key)?.get(NagramiXGhostReadMarker.self)?.maxId ?? 0
    if index.id.id > old {
        let prior = transaction.getPreferencesEntry(key: key)?.get(NagramiXGhostReadMarker.self)
        transaction.setPreferencesEntry(key: key, value: PreferencesEntry(NagramiXGhostReadMarker(maxId: index.id.id, previousRead: prior?.previousRead)))
    }
    return true
}

func nagramiXPreservePrivateRead(transaction: Transaction, peerId: PeerId, localMaxId: Int32, serverMaxId: Int32, threadId: Int64? = nil) -> Bool {
    let key = nagramiXGhostReadKey(peerId, threadId: threadId)
    guard let marker = transaction.getPreferencesEntry(key: key)?.get(NagramiXGhostReadMarker.self) else { return false }
    if serverMaxId >= marker.maxId {
        transaction.updatePreferencesEntry(key: key, { _ in nil })
        return false
    }
    return NagramiXGhostSettings.preservesPrivateRead(privateMaxId: marker.maxId, localMaxId: localMaxId, serverMaxId: serverMaxId)
}

// A user action authorizes exactly this account/peer/boundary. The global
// privacy gate stays closed while this one acknowledgement is in flight.
func nagramiXReadAfterUserAction(account: Account, peerId: PeerId, upTo messageId: MessageId, threadId expectedThreadId: Int64? = nil) -> Signal<Never, NoError> {
    guard NagramiXPrivacySettings.current.readsOnAction,
          peerId != account.peerId, peerId.namespace != Namespaces.Peer.SecretChat,
          messageId.peerId == peerId, messageId.namespace == Namespaces.Message.Cloud else { return .complete() }
    return account.postbox.transaction { transaction -> (MessageIndex, Int64?)? in
        guard NagramiXPrivacySettings.current.readsOnAction,
              let message = transaction.getMessage(messageId) else { return nil }
        if let expectedThreadId, message.threadId != expectedThreadId && Int64(messageId.id) != expectedThreadId { return nil }
        let threadId = expectedThreadId ?? message.threadId
        // Unknown context in a forum must not fall back to a peer-wide read.
        if threadId == nil, transaction.getPeer(peerId)?.isForumOrMonoForum == true { return nil }
        if let threadId {
            _ = nagramiXApplyThreadReadIndex(transaction: transaction, peerId: peerId, threadId: threadId, messageIndex: message.index)
            _ = nagramiXRecordPrivateRead(transaction: transaction, index: message.index, threadId: threadId)
        } else {
            _internal_applyMaxReadIndexInteractively(transaction: transaction, stateManager: account.stateManager, index: message.index)
        }
        return (message.index, threadId)
    }
    |> mapToSignal { boundary -> Signal<Never, NoError> in
        guard let (index, threadId) = boundary else { return .complete() }
        return nagramiXSendReadAcknowledgement(account: account, index: index, threadId: threadId, source: .action) |> ignoreValues
    }
}

func nagramiXGhostSettingsSignal() -> Signal<NagramiXGhostSettings, NoError> {
    return nagramiXPrivacySettingsSignal()
}

public func nagramiXPrivacySettingsSignal() -> Signal<NagramiXPrivacySettings, NoError> {
    return Signal { subscriber in
        let observer = NotificationCenter.default.addObserver(forName: NagramiXPrivacySettings.changedNotification, object: nil, queue: nil) { _ in subscriber.putNext(.current) }
        subscriber.putNext(.current)
        return ActionDisposable { NotificationCenter.default.removeObserver(observer) }
    }
}

// Shared native topic-local accounting. The caller decides whether a normal
// visible read may also reconcile the peer; private actions never do so.
func nagramiXApplyThreadReadIndex(transaction: Transaction, peerId: PeerId, threadId: Int64, messageIndex: MessageIndex) -> Bool {
    var markMainAsRead = false

    if var data = transaction.getMessageHistoryThreadInfo(peerId: peerId, threadId: threadId)?.data.get(MessageHistoryThreadData.self) {
        if messageIndex.id.id >= data.maxIncomingReadId {
            if let count = transaction.getThreadMessageCount(peerId: peerId, threadId: threadId, namespace: Namespaces.Message.Cloud, fromIdExclusive: data.maxIncomingReadId, toIndex: messageIndex) {
                data.incomingUnreadCount = max(0, data.incomingUnreadCount - Int32(count))
                data.maxIncomingReadId = messageIndex.id.id
            }

            var newCountIsZero = false
            if let topMessageIndex = transaction.getMessageHistoryThreadTopMessage(peerId: peerId, threadId: threadId, namespaces: Set([Namespaces.Message.Cloud])) {
                if messageIndex.id.id >= topMessageIndex.id.id {
                    let containingHole = transaction.getThreadIndexHole(peerId: peerId, threadId: threadId, namespace: topMessageIndex.id.namespace, containing: topMessageIndex.id.id)
                    if let _ = containingHole[.everywhere] {
                    } else {
                        data.incomingUnreadCount = 0
                    }
                }
            }
            newCountIsZero = data.incomingUnreadCount == 0

            if newCountIsZero, let peer = transaction.getPeer(peerId), peer.isForumOrMonoForum {
                var allTopicsAreRead = true
                for item in transaction.getMessageHistoryThreadIndex(peerId: peer.id, limit: 100) {
                    guard let data = transaction.getMessageHistoryThreadInfo(peerId: messageIndex.id.peerId, threadId: item.threadId)?.data.get(MessageHistoryThreadData.self) else {
                        continue
                    }
                    if data.incomingUnreadCount != 0 {
                        allTopicsAreRead = false
                        break
                    }
                }

                if allTopicsAreRead {
                    markMainAsRead = true
                }
            }

            data.maxKnownMessageId = max(data.maxKnownMessageId, messageIndex.id.id)

            if let entry = StoredMessageHistoryThreadInfo(data) {
                transaction.setMessageHistoryThreadInfo(peerId: peerId, threadId: threadId, info: entry)
            }
        }
    }
    return markMainAsRead
}

// Capture each outgoing item's own context before enqueue. A later incoming
// message, scheduled item or unsuccessful enqueue cannot widen this boundary.
struct NagramiXReadActionBoundary: Hashable {
    let messageId: MessageId
    let threadId: Int64?
}

func nagramiXReadBoundaryBeforeEnqueue(transaction: Transaction, peerId: PeerId, message: EnqueueMessage) -> NagramiXReadActionBoundary? {
    guard NagramiXPrivacySettings.current.readsOnAction,
          !message.attributes.contains(where: { $0 is OutgoingScheduleInfoMessageAttribute }) else { return nil }
    var threadId: Int64?
    switch message {
    case let .message(_, _, _, _, value, reply, _, _, _, _):
        threadId = value
        if threadId == nil, transaction.getPeer(peerId)?.isForum == true {
            // Match native forum destination resolution, including General.
            if let reply, reply.messageId.peerId == peerId {
                threadId = transaction.getMessage(reply.messageId)?.threadId
            }
        }
    case let .forward(_, value, _, _, _): threadId = value
    }
    if threadId == nil, transaction.getPeer(peerId)?.isForum == true { threadId = 1 }
    if threadId == nil, transaction.getPeer(peerId)?.isForumOrMonoForum == true { return nil }
    if let threadId {
        return transaction.getMessageHistoryThreadTopMessage(peerId: peerId, threadId: threadId, namespaces: Set([Namespaces.Message.Cloud])).map { NagramiXReadActionBoundary(messageId: $0.id, threadId: threadId) }
    }
    return transaction.getTopPeerMessageIndex(peerId: peerId, namespace: Namespaces.Message.Cloud).map { NagramiXReadActionBoundary(messageId: $0.id, threadId: nil) }
}

// The secret-chat boundary is a date, never a cloud message id. Network requests
// always use the immutable boundary captured in the confirmation transaction.
private struct BulkReadTarget: Hashable {
    let peerId: PeerId
    let threadId: Int64?
    let maximum: Int32
    var unreadMark: String? = nil
}

private struct BulkUnreadMark: Codable {
    let token: String
}

private func bulkMarkKey(peerId: PeerId, threadId: Int64?) -> ValueBoxKey {
    let key = nagramiXGhostReadKey(peerId, threadId: threadId)
    key.setInt64(0, value: threadId == nil ? 0x4e61524d61726b50 : 0x4e61524d61726b54)
    return key
}

// A scheduled native push may use only the boundary available before the
// local command. Later ordinary reads that pass the watermark work normally.
func nagramiXNativePushState(transaction: Transaction, peerId: PeerId, state: PeerReadState) -> PeerReadState? {
    let key = nagramiXGhostReadKey(peerId, threadId: nil)
    guard let marker = transaction.getPreferencesEntry(key: key)?.get(NagramiXGhostReadMarker.self),
          let previous = marker.previousRead else { return state }
    switch state {
    case let .idBased(incoming, outgoing, known, count, marked):
        guard incoming <= marker.maxId else { return state }
        guard previous > 0 else { return nil }
        return .idBased(maxIncomingReadId: previous, maxOutgoingReadId: outgoing, maxKnownId: known, count: count, markedUnread: marked)
    case let .indexBased(incoming, outgoing, count, marked):
        guard incoming.timestamp <= marker.maxId else { return state }
        guard previous > 0 else { return nil }
        let allowed = MessageIndex(id: incoming.id, timestamp: previous)
        return .indexBased(maxIncomingReadIndex: allowed, maxOutgoingReadIndex: outgoing, count: count, markedUnread: marked)
    }
}

func nagramiXLocalUnreadMark(transaction: Transaction, peerId: PeerId, threadId: Int64?, serverValue: Bool) -> Bool {
    let key = bulkMarkKey(peerId: peerId, threadId: threadId)
    guard transaction.getPreferencesEntry(key: key) != nil else { return serverValue }
    if !serverValue { transaction.setPreferencesEntry(key: key, value: nil) }
    return false
}

private func captureBulkRead(transaction: Transaction, server: Bool) -> [BulkReadTarget] {
    var targets = Set<BulkReadTarget>()

    func record(_ peerId: PeerId, _ threadId: Int64?, _ maximum: Int32, previous: Int32) {
        guard maximum > 0 else { return }
        let key = nagramiXGhostReadKey(peerId, threadId: threadId)
        let old = transaction.getPreferencesEntry(key: key)?.get(NagramiXGhostReadMarker.self)
        let bound = max(old?.maxId ?? 0, maximum)
        let marker = NagramiXGhostReadMarker(maxId: bound, previousRead: old?.previousRead ?? (old == nil ? previous : 0))
        transaction.setPreferencesEntry(key: key, value: PreferencesEntry(marker))
        if server {
            targets.insert(BulkReadTarget(peerId: peerId, threadId: threadId, maximum: bound))
        }
    }

    func unmark(_ peerId: PeerId, _ threadId: Int64?) {
        let key = bulkMarkKey(peerId: peerId, threadId: threadId)
        let token = UUID().uuidString
        transaction.setPreferencesEntry(key: key, value: PreferencesEntry(BulkUnreadMark(token: token)))
        if server { targets.insert(BulkReadTarget(peerId: peerId, threadId: threadId, maximum: 0, unreadMark: token)) }
    }

    // Read the two original private-read keyspaces as well. Old installations
    // can have pending reads for chats or topics that no longer appear in a list.
    if server {
        for id: Int64 in [0x4e61677247686f73, 0x4e61677254687264, 0x4e61524d61726b50, 0x4e61524d61726b54] {
            let prefix = ValueBoxKey(length: 8)
            prefix.setInt64(0, value: id)
            for key in transaction.preferenceKeys(withPrefix: prefix) {
                guard key.length == 16 || key.length == 24 else { continue }
                let peerId = PeerId(key.getInt64(8))
                let threadId = key.length == 24 ? key.getInt64(16) : nil
                let entry = transaction.getPreferencesEntry(key: key)
                if id == 0x4e61677247686f73 || id == 0x4e61677254687264 {
                    if let marker = entry?.get(NagramiXGhostReadMarker.self), marker.maxId > 0 {
                        targets.insert(BulkReadTarget(peerId: peerId, threadId: threadId, maximum: marker.maxId))
                    }
                } else if let mark = entry?.get(BulkUnreadMark.self) {
                    targets.insert(BulkReadTarget(peerId: peerId, threadId: threadId, maximum: 0, unreadMark: mark.token))
                }
            }
        }
    }

    let groups: [PeerGroupId] = [.root, Namespaces.PeerGroup.archive]
    for group in groups {
        // Forum unread totals may be maintained by topic rather than peer state.
        for peer in transaction.getChatListPeers(groupId: group, filterPredicate: nil, additionalFilter: nil) {
            let peerId = peer.id
            if peer.isForumOrMonoForum {
                for item in transaction.getMessageHistoryThreadIndex(peerId: peerId, limit: Int(Int32.max)) {
                    guard var data = item.info.data.get(MessageHistoryThreadData.self), data.isMarkedUnread || data.incomingUnreadCount > 0 else { continue }
                    let highest = max(data.maxKnownMessageId, item.index.id.id)
                    if highest > 0 {
                        record(peerId, item.threadId, highest, previous: data.maxIncomingReadId)
                        if data.isMarkedUnread && peer.isMonoForum { unmark(peerId, item.threadId) }
                        data.maxIncomingReadId = max(highest, data.maxIncomingReadId)
                        data.incomingUnreadCount = 0
                        data.isMarkedUnread = false
                        if let info = StoredMessageHistoryThreadInfo(data) {
                            transaction.setMessageHistoryThreadInfo(peerId: peerId, threadId: item.threadId, info: info)
                        }
                    }
                }
            }
            for (namespace, state) in transaction.getPeerReadStates(peerId) ?? [] where state.isUnread {
                switch state {
                case let .idBased(incoming, outgoing, known, _, marked) where namespace == Namespaces.Message.Cloud:
                    let highest = max(known, transaction.getTopPeerMessageIndex(peerId: peerId, namespace: namespace)?.id.id ?? 0)
                    let bound = max(incoming, highest)
                    if marked { unmark(peerId, nil) }
                    if bound > incoming {
                        record(peerId, nil, bound, previous: incoming)
                    }
                    transaction.setLocalReadState(peerId: peerId, namespace: namespace, state: .idBased(maxIncomingReadId: bound, maxOutgoingReadId: outgoing, maxKnownId: highest, count: 0, markedUnread: false))
                case let .indexBased(incoming, outgoing, _, _) where namespace == Namespaces.Message.SecretIncoming:
                    let bound = max(incoming, transaction.getTopPeerMessageIndex(peerId: peerId, namespace: namespace) ?? incoming)
                    if bound > incoming { record(peerId, nil, bound.timestamp, previous: incoming.timestamp) }
                    transaction.setLocalReadState(peerId: peerId, namespace: namespace, state: .indexBased(maxIncomingReadIndex: bound, maxOutgoingReadIndex: outgoing, count: 0, markedUnread: false))
                default: break
                }
            }
        }
    }
    // Existing and freshly extended watermarks can refer to the same scope.
    // Only the highest captured boundary for each peer/topic needs a receipt.
    var highest: [ValueBoxKey: BulkReadTarget] = [:]
    for target in targets {
        let key = target.unreadMark == nil ? nagramiXGhostReadKey(target.peerId, threadId: target.threadId) : bulkMarkKey(peerId: target.peerId, threadId: target.threadId)
        if let token = target.unreadMark, transaction.getPreferencesEntry(key: key)?.get(BulkUnreadMark.self)?.token != token { continue }
        if let previous = highest[key], previous.maximum >= target.maximum { continue }
        highest[key] = target
    }
    return Array(highest.values)
}

private func sendBulkRead(account: Account, target: BulkReadTarget) -> Signal<Bool, NoError> {
    let peerId = target.peerId
    return account.postbox.transaction { transaction -> Signal<Bool, NoError> in
        let request: Signal<Api.Bool, MTRpcError>
        let markKey = bulkMarkKey(peerId: peerId, threadId: target.threadId)
        if let token = target.unreadMark {
            guard transaction.getPreferencesEntry(key: markKey)?.get(BulkUnreadMark.self)?.token == token else { return .single(true) }
            // An explicit newer "mark unread" takes precedence over a stale retry.
            let marked: Bool
            if let threadId = target.threadId {
                marked = transaction.getMessageHistoryThreadInfo(peerId: peerId, threadId: threadId)?.data.get(MessageHistoryThreadData.self)?.isMarkedUnread == true
            } else {
                marked = transaction.getPeerReadStates(peerId)?.contains(where: { $0.1.markedUnread }) == true
            }
            if marked {
                transaction.setPreferencesEntry(key: markKey, value: nil)
                return .single(true)
            }
            guard let input = transaction.getPeer(peerId).flatMap(apiInputPeer) else { return .single(false) }
            if let threadId = target.threadId {
                guard let subPeer = transaction.getPeer(PeerId(threadId)).flatMap(apiInputPeer) else { return .single(false) }
                request = account.network.request(Api.functions.messages.markDialogUnread(flags: 0, parentPeer: input, peer: .inputDialogPeer(.init(peer: subPeer))))
            } else {
                request = account.network.request(Api.functions.messages.markDialogUnread(flags: 0, parentPeer: nil, peer: .inputDialogPeer(.init(peer: input))))
            }
        } else {
            guard nagramiXHasPrivateRead(transaction: transaction, peerId: peerId, threadId: target.threadId) else { return .single(true) }
            if peerId.namespace == Namespaces.Peer.SecretChat {
                guard let peer = transaction.getPeer(peerId), let secret = apiInputSecretChat(peer) else { return .single(false) }
                request = account.network.request(Api.functions.messages.readEncryptedHistory(peer: secret, maxDate: target.maximum))
            } else {
                let index = MessageIndex(id: MessageId(peerId: peerId, namespace: Namespaces.Message.Cloud, id: target.maximum), timestamp: 0)
                return nagramiXRequestReadAcknowledgement(account: account, index: index, threadId: target.threadId, source: .confirmedBulk)
            }
        }
        return request
        |> map { result -> Bool in if case .boolTrue = result { return true }; return false }
        |> `catch` { _ in .single(false) }
        |> mapToSignal { success -> Signal<Bool, NoError> in
            guard success else { return .single(false) }
            return account.postbox.transaction { transaction in
                if let token = target.unreadMark {
                    if transaction.getPreferencesEntry(key: markKey)?.get(BulkUnreadMark.self)?.token == token {
                        transaction.setPreferencesEntry(key: markKey, value: nil)
                    }
                } else {
                    nagramiXAcknowledgePrivateRead(transaction: transaction, peerId: peerId, maxId: target.maximum, threadId: target.threadId)
                }
                return true
            }
        }
    }
    |> switchToLatest
    |> timeout(20.0, queue: .concurrentDefaultQueue(), alternate: .single(false))
}

// A retry owns the captured account and only the unsuccessful boundaries.
public final class NagramiXBulkReadBatch {
    private let account: Account
    private let targets: [BulkReadTarget]

    fileprivate init(account: Account, targets: [BulkReadTarget]) {
        self.account = account
        self.targets = targets
    }

    public func send() -> Signal<NagramiXBulkReadBatch?, NoError> {
        guard !self.targets.isEmpty else { return .single(nil) }
        return self.account.network.connectionStatus
        |> take(1)
        |> mapToSignal { status in
            if case .waitingForNetwork = status { return .single(self) }
            return self.sendBatches()
        }
    }

    private func sendBatches() -> Signal<NagramiXBulkReadBatch?, NoError> {
        return Signal { subscriber in
            let queue = Queue()
            let disposable = MetaDisposable()
            var failed: [BulkReadTarget] = []
            func sendNext(_ start: Int) {
                let end = min(start + 8, self.targets.count)
                let chunk = self.targets[start ..< end]
                let signals = chunk.map { sendBulkRead(account: self.account, target: $0) }
                disposable.set((combineLatest(signals) |> deliverOn(queue)).start(next: { results in
                    failed.append(contentsOf: zip(chunk, results).compactMap { target, success in success ? nil : target })
                    if end == self.targets.count {
                        subscriber.putNext(failed.isEmpty ? nil : NagramiXBulkReadBatch(account: self.account, targets: failed))
                        subscriber.putCompletion()
                    } else {
                        queue.async { sendNext(end) }
                    }
                }))
            }
            queue.async { sendNext(0) }
            return disposable
        }
    }
}

public func nagramiXBulkReadMessages(account: Account, onServer: Bool) -> Signal<NagramiXBulkReadBatch?, NoError> {
    return account.postbox.transaction { transaction in
        captureBulkRead(transaction: transaction, server: onServer)
    }
    |> mapToSignal { targets in
        NagramiXBulkReadBatch(account: account, targets: targets).send()
    }
}
