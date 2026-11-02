import Foundation
import Postbox
import TelegramApi
import SwiftSignalKit
import NagramiXMediaSettings

private struct NagramiXGhostReadMarker: Codable { let maxId: Int32 }

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
    guard index.id.namespace == Namespaces.Message.Cloud else { return true }
    let key = nagramiXGhostReadKey(index.id.peerId, threadId: threadId)
    let old = transaction.getPreferencesEntry(key: key)?.get(NagramiXGhostReadMarker.self)?.maxId ?? 0
    if index.id.id > old {
        transaction.setPreferencesEntry(key: key, value: PreferencesEntry(NagramiXGhostReadMarker(maxId: index.id.id)))
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
