extension MessageId { typealias Namespace = Int32 }
private enum PeerReadStateValidationError { case retry }
private func inputPeer(postbox: TestPostbox, peerId: PeerId) -> Signal<Api.InputPeer, PeerReadStateValidationError> {
    .single(apiInputPeer(postbox.storage.getPeer(peerId)!)!)
}
private func nagramiXShouldSuppressTemporarySecretHistory(peerId: PeerId) -> Bool { false }
private func manualPush(postbox: TestPostbox, network: TestNetwork, peerId: PeerId, namespace: Int32, original: PeerReadState, allowed: PeerReadState?) -> Signal<(MessageId.Namespace, PeerReadState), PeerReadStateValidationError> {
    // PRODUCTION_GUARD
    return .single((namespace, readState))
}
func testManualMarkPush() {
    let account = BulkReadReconciliationTests.chat()
    let id = BulkReadReconciliationTests.id
    let db = account.postbox.storage
    BulkReadReconciliationTests.state(account, 0, 7, count: 7)
    nagramiXBulkReadMessages(account: account, onServer: false).start()
    BulkReadReconciliationTests.state(account, 7, 7, marked: true)
    let original = db.bulkStates[id]![Namespaces.Message.Cloud]!
    let allowed = nagramiXNativePushState(transaction: db, peerId: id, state: original)
    precondition(allowed == nil)
    manualPush(postbox: account.postbox, network: account.network, peerId: id, namespace: Namespaces.Message.Cloud, original: original, allowed: allowed).start()
    precondition(account.network.requests.count == 1 && account.network.requests[0] == (-1, 1))
}
