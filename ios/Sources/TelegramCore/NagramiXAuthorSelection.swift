import Foundation
import Postbox
import SwiftSignalKit
import TelegramApi
import MtProtoKit

public enum NagramiXAuthorSelectionError {
    case unavailable
    case network
    case stalled
}

/// Returns only messages of the real sender, after storing them for the native
/// selection toolbar and permission checks. Does not alter deletion rights.
public func nagramiXMessagesByAuthor(account: Account, peerId: PeerId, authorId: PeerId, threadId: Int64?) -> Signal<[MessageId], NagramiXAuthorSelectionError> {
    return account.postbox.transaction { transaction -> (Peer, Peer?, Peer?, Peer?)? in
        guard let peer = transaction.getPeer(peerId) else {
            return nil
        }
        var previousPeer: Peer?
        if peer is TelegramChannel, let cachedData = transaction.getPeerCachedData(peerId: peerId) as? CachedChannelData, let migration = cachedData.migrationReference {
            previousPeer = transaction.getPeer(migration.maxMessageId.peerId)
        }
        let savedPeer = (peerId == account.peerId || peer.isMonoForum) ? threadId.flatMap { transaction.getPeer(PeerId($0)) } : nil
        return (peer, transaction.getPeer(authorId), previousPeer, savedPeer)
    }
    |> castError(NagramiXAuthorSelectionError.self)
    |> mapToSignal { values -> Signal<[MessageId], NagramiXAuthorSelectionError> in
        guard let (peer, author, previousPeer, savedPeer) = values else {
            return .fail(.unavailable)
        }
        // Each subscription owns its accumulator; requests are strictly serial.
        var selectedIds = Set<MessageId>()
        // Server history/search is not the only source of selectable messages. Cached
        // history, pending outgoing messages and Secret Chats are real local history.
        // Page it on the Postbox queue, without importing any cleared remote history.
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
        func collect(peer: Peer, offset: Int32) -> Signal<Void, NagramiXAuthorSelectionError> {
            if peer.id.namespace == Namespaces.Peer.SecretChat {
                return .single(Void())
            }
            guard let inputPeer = apiInputPeer(peer) else {
                return .fail(.unavailable)
            }
            let request: Signal<Api.messages.Messages, MTRpcError>
            if peer.id.namespace == Namespaces.Peer.CloudUser, peer.id != account.peerId, threadId == nil {
                // Empty sender searches are unreliable in private dialogs.
                // Traverse the whole accessible history, including non-text media.
                request = account.network.request(Api.functions.messages.getHistory(peer: inputPeer, offsetId: offset, offsetDate: 0, addOffset: 0, limit: 100, maxId: 0, minId: 0, hash: 0), automaticFloodWait: false)
            } else {
                guard let author, let fromPeer = apiInputPeer(author) else {
                    return .fail(.unavailable)
                }
                var flags: Int32 = 1 << 0
                var topMsgId: Int32?
                let inputSavedPeer = savedPeer.flatMap(apiInputPeer)
                if inputSavedPeer != nil {
                    flags |= 1 << 2
                } else if peer.id != account.peerId, let threadId {
                    flags |= 1 << 1
                    topMsgId = Int32(clamping: threadId)
                }
                request = account.network.request(Api.functions.messages.search(flags: flags, peer: inputPeer, q: "", fromId: fromPeer, savedPeerId: inputSavedPeer, savedReaction: nil, topMsgId: topMsgId, filter: .inputMessagesFilterEmpty, minDate: 0, maxDate: Int32.max - 1, offsetId: offset, addOffset: 0, limit: 100, maxId: Int32.max - 1, minId: 0, hash: 0), automaticFloodWait: false)
            }
            return request
            |> mapError { _ in NagramiXAuthorSelectionError.network }
            |> timeout(30.0, queue: Queue.concurrentDefaultQueue(), alternate: .fail(.network))
            |> mapToSignal { response -> Signal<(Bool, Int32?), NagramiXAuthorSelectionError> in
                let messages: [Api.Message]
                let chats: [Api.Chat]
                let users: [Api.User]
                switch response {
                case let .messages(data):
                    messages = data.messages
                    chats = data.chats
                    users = data.users
                case let .messagesSlice(data):
                    messages = data.messages
                    chats = data.chats
                    users = data.users
                case let .channelMessages(data):
                    messages = data.messages
                    chats = data.chats
                    users = data.users
                case .messagesNotModified:
                    return .fail(.stalled)
                }
                return account.postbox.transaction { transaction -> (Bool, Int32?) in
                    let parsedPeers = AccumulatedPeers(transaction: transaction, chats: chats, users: users)
                    updatePeers(transaction: transaction, accountPeerId: account.peerId, peers: parsedPeers)
                    var storeMessages: [StoreMessage] = []
                    var nextOffset: Int32?
                    for apiMessage in messages {
                        guard let message = StoreMessage(apiMessage: apiMessage, accountPeerId: account.peerId, peerIsForum: peer.isForumOrMonoForum), case let .Id(id) = message.id, id.peerId == peer.id, id.namespace == Namespaces.Message.Cloud else {
                            continue
                        }
                        nextOffset = min(nextOffset ?? id.id, id.id)
                        guard message.authorId == authorId else {
                            continue
                        }
                        // The server already applies the thread/saved-dialog filter.
                        if let threadId, savedPeer == nil, peer.id != account.peerId, message.threadId != threadId, Int64(id.id) != threadId {
                            continue
                        }
                        storeMessages.append(message)
                    }
                    _ = transaction.addMessages(storeMessages, location: .Random)
                    // Never hand unloaded IDs to the native permission intersection.
                    for message in storeMessages {
                        if case let .Id(id) = message.id, let stored = transaction.getMessage(id), stored.author?.id == authorId {
                            selectedIds.insert(id)
                        }
                    }
                    return (messages.isEmpty, nextOffset)
                }
                |> castError(NagramiXAuthorSelectionError.self)
            }
            |> mapToSignal { empty, nextOffset -> Signal<Void, NagramiXAuthorSelectionError> in
                if empty {
                    return .single(Void())
                }
                guard let nextOffset, nextOffset > 0, offset == 0 || nextOffset < offset else {
                    return .fail(.stalled)
                }
                return collect(peer: peer, offset: nextOffset)
            }
        }
        return collectLocal(peer: peer)
        |> mapToSignal { _ -> Signal<Void, NagramiXAuthorSelectionError> in
            return collect(peer: peer, offset: 0)
        }
        |> mapToSignal { _ -> Signal<Void, NagramiXAuthorSelectionError> in
            if let previousPeer {
                return collectLocal(peer: previousPeer)
                |> mapToSignal { _ -> Signal<Void, NagramiXAuthorSelectionError> in
                    return collect(peer: previousPeer, offset: 0)
                }
            }
            return .single(Void())
        }
        |> mapToSignal { _ -> Signal<[MessageId], NagramiXAuthorSelectionError> in
            return account.postbox.transaction { transaction -> [MessageId] in
                // Messages may have been removed while older pages were loading.
                return selectedIds.filter { transaction.getMessage($0)?.author?.id == authorId }.sorted()
            }
            |> castError(NagramiXAuthorSelectionError.self)
        }
    }
}
