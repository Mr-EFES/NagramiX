import Foundation
import Postbox
internal import TelegramApi
import SwiftSignalKit
import NagramiXMediaSettings

public func nagramiXReadModeSignal() -> Signal<NagramiXReadMode, NoError> {
    return nagramiXPrivacySettingsSignal() |> map { $0.readMode } |> distinctUntilChanged
}

enum NagramiXReadAcknowledgementSource {
    case visible, action, confirmedBulk

    var isAllowed: Bool {
        let settings = NagramiXPrivacySettings.current
        switch self {
        case .confirmedBulk: return true
        case .visible: return !settings.hidesMessageReads
        case .action: return settings.readsOnAction
        }
    }
}

// Normal reading resumes for the currently visible boundary only. Turning a
// switch OFF never flushes privately read chats in the background.
func nagramiXReadPreviouslyLocalMessage(account: Account, index: MessageIndex) -> Signal<Void, NoError> {
    return nagramiXSendReadAcknowledgement(account: account, index: index, threadId: nil, source: .visible)
}

func nagramiXSendReadAcknowledgement(account: Account, index: MessageIndex, threadId: Int64?, source: NagramiXReadAcknowledgementSource) -> Signal<Void, NoError> {
    return nagramiXRequestReadAcknowledgement(account: account, index: index, threadId: threadId, source: source)
    |> filter { $0 }
    |> map { _ in () }
}

func nagramiXRequestReadAcknowledgement(account: Account, index: MessageIndex, threadId: Int64?, source: NagramiXReadAcknowledgementSource, bulkGeneration: UUID? = nil) -> Signal<Bool, NoError> {
    guard source.isAllowed, index.id.namespace == Namespaces.Message.Cloud,
          (source == .confirmedBulk || index.id.peerId != account.peerId),
          index.id.peerId.namespace != Namespaces.Peer.SecretChat else { return .single(false) }
    return account.postbox.transaction { transaction -> (Api.InputPeer, Api.InputPeer?)? in
        guard source.isAllowed,
              nagramiXHasPrivateRead(transaction: transaction, peerId: index.id.peerId, threadId: threadId),
              let peer = transaction.getPeer(index.id.peerId),
              let inputPeer = apiInputPeer(peer) else { return nil }
        if source == .confirmedBulk {
            guard peerKeepsReadState(peer),
                  nagramiXBulkHistoryIsPending(transaction: transaction, peerId: peer.id, threadId: threadId, maximum: index.id.id, generation: bulkGeneration) else { return nil }
        }
        if let threadId, let channel = peer as? TelegramChannel, channel.flags.contains(.isMonoforum) {
            guard let subPeer = transaction.getPeer(PeerId(threadId)).flatMap(apiInputPeer) else { return nil }
            return (inputPeer, subPeer)
        }
        return (inputPeer, nil)
    }
    |> mapToSignal { target -> Signal<Bool, NoError> in
        guard let (inputPeer, subPeer) = target, source.isAllowed else { return .single(false) }
        let acknowledged: Signal<Bool, NoError>
        let accepted: (Api.Bool) -> Bool = { if case .boolTrue = $0 { return true }; return false }
        if let threadId {
            if let subPeer {
                acknowledged = account.network.request(Api.functions.messages.readSavedHistory(parentPeer: inputPeer, peer: subPeer, maxId: index.id.id))
                |> map(accepted) |> `catch` { _ in .single(false) }
            } else {
                // Never widen a topic receipt to channels.readHistory, or
                // clamp an invalid root id into a different discussion.
                guard let discussionId = Int32(exactly: threadId) else { return .single(false) }
                acknowledged = account.network.request(Api.functions.messages.readDiscussion(peer: inputPeer, msgId: discussionId, readMaxId: index.id.id))
                |> map(accepted) |> `catch` { _ in .single(false) }
            }
        } else {
            switch inputPeer {
            case let .inputPeerChannel(data):
                acknowledged = account.network.request(Api.functions.channels.readHistory(channel: .inputChannel(.init(channelId: data.channelId, accessHash: data.accessHash)), maxId: index.id.id))
                |> map { result -> Bool in
                    if case .boolTrue = result { return true }
                    return false
                }
                |> `catch` { _ in .single(false) }
            default:
                acknowledged = account.network.request(Api.functions.messages.readHistory(peer: inputPeer, maxId: index.id.id))
                |> map { result -> Bool in
                    if case let .affectedMessages(data) = result {
                        account.stateManager.addUpdateGroups([.updatePts(pts: data.pts, ptsCount: data.ptsCount)])
                    }
                    return true
                }
                |> `catch` { _ in .single(false) }
            }
        }
        return acknowledged |> mapToSignal { success -> Signal<Bool, NoError> in
            guard success else { return .single(false) }
            // Retire only this scope/boundary accepted by the server.
            return account.postbox.transaction { transaction -> Bool in
                nagramiXAcknowledgePrivateRead(transaction: transaction, peerId: index.id.peerId, maxId: index.id.id, threadId: threadId)
                return true
            }
        }
    }
}
