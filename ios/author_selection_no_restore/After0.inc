import Foundation
import Postbox
import SwiftSignalKit

public enum NagramiXAuthorSelectionError {
    case unavailable
    case network
    case stalled
}

/// Select existing local history without importing remote search results.
/// Selection is read-only: it cannot restore a message removed from this client.
public func nagramiXMessagesByAuthor(account: Account, peerId: PeerId, authorId: PeerId, threadId: Int64?) -> Signal<[MessageId], NagramiXAuthorSelectionError> {
    return account.postbox.transaction { transaction -> (Peer, Peer?)? in
        guard let peer = transaction.getPeer(peerId) else {
            return nil
        }
        var previousPeer: Peer?
        if peer is TelegramChannel, let cachedData = transaction.getPeerCachedData(peerId: peerId) as? CachedChannelData, let migration = cachedData.migrationReference {
            previousPeer = transaction.getPeer(migration.maxMessageId.peerId)
        }
        return (peer, previousPeer)
    }
    |> castError(NagramiXAuthorSelectionError.self)
    |> mapToSignal { values -> Signal<[MessageId], NagramiXAuthorSelectionError> in
        guard let (peer, previousPeer) = values else {
            return .fail(.unavailable)
        }
        // Each subscription owns its accumulator; Postbox pages are strictly serial.
        var selectedIds = Set<MessageId>()
        let localNamespaces = [Namespaces.Message.Cloud, Namespaces.Message.Local, Namespaces.Message.SecretIncoming, Namespaces.Message.EphemeralLocal]
        func collectLocal(peer: Peer, namespaceIndex: Int = 0, from: MessageIndex? = nil) -> Signal<Void, NagramiXAuthorSelectionError> {
            guard namespaceIndex < localNamespaces.count else {
                return .single(Void())
            }
            let namespace = localNamespaces[namespaceIndex]
            let upper = from ?? MessageIndex.upperBound(peerId: peer.id, namespace: namespace)
            return account.postbox.transaction { transaction -> MessageIndex? in
                let lower = MessageIndex.lowerBound(peerId: peer.id, namespace: namespace)
                let messages: [Message]
                if let threadId {
                    messages = transaction.getMessagesWithThreadId(peerId: peer.id, namespace: namespace, threadId: threadId, from: upper, includeFrom: false, to: lower, limit: 200)
                } else {
                    messages = transaction.getMessages(peerId: peer.id, namespace: namespace, from: upper, includeFrom: false, to: lower, limit: 200)
                }
                for message in messages where message.id.peerId == peer.id && message.author?.id == authorId {
                    selectedIds.insert(message.id)
                }
                return messages.map { $0.index }.min()
            }
            |> castError(NagramiXAuthorSelectionError.self)
            |> mapToSignal { next -> Signal<Void, NagramiXAuthorSelectionError> in
                guard let next else {
                    return collectLocal(peer: peer, namespaceIndex: namespaceIndex + 1)
                }
                guard next < upper else {
                    return .fail(.stalled)
                }
                return collectLocal(peer: peer, namespaceIndex: namespaceIndex, from: next)
            }
        }
        return collectLocal(peer: peer)
        |> mapToSignal { _ -> Signal<Void, NagramiXAuthorSelectionError> in
            if let previousPeer {
                return collectLocal(peer: previousPeer)
            }
            return .single(Void())
        }
        |> mapToSignal { _ -> Signal<[MessageId], NagramiXAuthorSelectionError> in
            return account.postbox.transaction { transaction -> [MessageId] in
                // Selection never recreates IDs deleted while pages were being read.
                return selectedIds.filter { transaction.getMessage($0)?.author?.id == authorId }.sorted()
            }
            |> castError(NagramiXAuthorSelectionError.self)
        }
    }
}
