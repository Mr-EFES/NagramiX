import Foundation

@main struct ThreadReadScopeRegression {
    static func main() {
        NagramiXPrivacySettings.update { $0.readMode = .local; $0[.readOnAction] = true }
        let account = Account()
        let peer = PeerId(namespace: Namespaces.Peer.CloudChannel, value: 9)
        let index = MessageIndex(id: MessageId(peerId: peer, namespace: Namespaces.Message.Cloud, id: 5))
        account.postbox.storage.peers[peer] = TelegramChannel(id: peer)
        account.postbox.storage.messages[index.id] = Message(index: index, threadId: 2)
        _ = nagramiXRecordPrivateRead(transaction: account.postbox.storage, index: index)
        nagramiXReadAfterUserAction(account: account, peerId: peer, upTo: index.id).start()
        let passed = account.network.requests.isEmpty && account.network.discussionRequests.count == 1 && account.postbox.storage.localReads.isEmpty
        print("Topic regression: broad RPCs=\(account.network.requests.count), discussion RPCs=\(account.network.discussionRequests.count), broad local reads=\(account.postbox.storage.localReads.count)")
        exit(passed ? 0 : 1)
    }
}
