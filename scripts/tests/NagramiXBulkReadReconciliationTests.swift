// Each case runs the production capture, dispatch and server reconciliation with an isolated account.
@main struct BulkReadReconciliationTests {
    static let cloud = Namespaces.Message.Cloud
    static let id = PeerId(namespace: Namespaces.Peer.CloudChannel, value: 11)

    static func chat(_ status: TelegramChannel.ParticipationStatus = .member, flags: TelegramChannel.Flags = []) -> Account {
        let account = Account()
        let channel = TelegramChannel(id: id, flags: flags)
        channel.participationStatus = status
        account.postbox.storage.peers[id] = channel
        return account
    }

    static func state(_ account: Account, _ incoming: Int32, _ known: Int32, count: Int32 = 0, marked: Bool = false) {
        account.postbox.storage.bulkStates[id] = [cloud: .idBased(maxIncomingReadId: incoming, maxOutgoingReadId: 1, maxKnownId: known, count: count, markedUnread: marked)]
    }

    static func result(_ signal: Signal<NagramiXBulkReadBatch?, NoError>) -> NagramiXBulkReadBatch? {
        var values: [NagramiXBulkReadBatch?] = []
        signal.start(next: { values.append($0) })
        precondition(values.count == 1)
        return values[0]
    }

    static func offlineBatch(_ account: Account) -> NagramiXBulkReadBatch {
        account.network.offline = true
        let batch = result(nagramiXBulkReadMessages(account: account, onServer: true))!
        account.network.offline = false
        return batch
    }

    static func manualMark() -> Bool {
        let account = chat()
        let db = account.postbox.storage
        state(account, 5, 5, marked: true)
        let batch = offlineBatch(account)
        precondition(!nagramiXLocalUnreadMark(transaction: db, peerId: id, threadId: nil, serverValue: true))
        state(account, 5, 5, marked: true)
        let value = nagramiXLocalUnreadMark(transaction: db, peerId: id, threadId: nil, serverValue: true)
        precondition(result(batch.send()) == nil && account.network.requests.isEmpty)
        return value
    }

    static func acknowledgedDuringLookup() -> Bool {
        let account = chat()
        state(account, 3, 9, count: 6)
        let batch = offlineBatch(account)
        account.postbox.beforeEmission = {
            _ = nagramiXPreservePrivateRead(transaction: account.postbox.storage, peerId: id, localMaxId: 9, serverMaxId: 9)
        }
        let remaining = result(batch.send())
        precondition(account.network.requests.isEmpty)
        return remaining == nil
    }

    static func nonMember(_ status: TelegramChannel.ParticipationStatus, server: Bool) -> Bool {
        let account = chat(status)
        state(account, 0, Int32.max - 1, marked: true)
        _ = result(nagramiXBulkReadMessages(account: account, onServer: server))
        guard case let .idBased(incoming, _, known, count, marked)? = account.postbox.storage.bulkStates[id]?[cloud] else { fatalError() }
        return incoming == 0 && known == Int32.max - 1 && count == 0 && !marked && account.network.requests.isEmpty
            && !nagramiXHasPrivateRead(transaction: account.postbox.storage, peerId: id)
    }

    static func pendingAndAcknowledged() {
        let account = chat()
        let db = account.postbox.storage
        state(account, 3, 9, count: 6)
        let batch = offlineBatch(account)
        let peer = db.peers.removeValue(forKey: id)!
        precondition(result(batch.send()) != nil && account.network.requests.isEmpty)
        db.peers[id] = peer
        account.network.reject = true
        precondition(result(batch.send()) != nil)
        state(account, 9, 15, count: 6)
        _ = result(nagramiXBulkReadMessages(account: account, onServer: false))
        account.network.duringRequest = {
            _ = nagramiXPreservePrivateRead(transaction: db, peerId: id, localMaxId: 15, serverMaxId: 9)
        }
        precondition(result(batch.send()) == nil)
        account.network.offline = true
        precondition(result(batch.send()) == nil)
        precondition(nagramiXHasPrivateRead(transaction: db, peerId: id))
        precondition(account.network.requests.map { $0.1 } == [9, 9])
        account.network.offline = false
        account.network.reject = false
        precondition(result(nagramiXBulkReadMessages(account: account, onServer: true)) == nil)
        precondition(account.network.requests.last?.1 == 15)

        // Catch-up can also retire the entire ledger before a later local read creates another one.
        state(account, 15, 22, count: 7)
        let older = offlineBatch(account)
        _ = nagramiXPreservePrivateRead(transaction: db, peerId: id, localMaxId: 22, serverMaxId: 22)
        state(account, 22, 31, count: 9)
        _ = result(nagramiXBulkReadMessages(account: account, onServer: false))
        let newer = offlineBatch(account)
        account.network.offline = true
        precondition(result(older.send()) == nil && result(newer.send()) != nil)
        account.network.offline = false
        let sent = account.network.requests.count
        precondition(result(older.send()) == nil && account.network.requests.count == sent)
        precondition(result(newer.send()) == nil && account.network.requests.last?.1 == 31)
    }

    static func membershipAndLegacyMarker() {
        let account = chat()
        let db = account.postbox.storage
        state(account, 0, 17, count: 1)
        let batch = offlineBatch(account)
        (db.peers[id] as! TelegramChannel).participationStatus = .left
        precondition(result(batch.send()) == nil && account.network.requests.isEmpty)

        // A previous installation could persist the sentinel both locally and in the pending ledger.
        let key = nagramiXGhostReadKey(id, threadId: nil)
        struct LegacyMarker: Codable { let maxId: Int32; let previousRead: Int32 }
        db.setPreferencesEntry(key: key, value: PreferencesEntry(LegacyMarker(maxId: Int32.max - 1, previousRead: 0)))
        state(account, Int32.max - 1, Int32.max - 1)
        precondition(result(nagramiXBulkReadMessages(account: account, onServer: true)) == nil)
        precondition(!nagramiXHasPrivateRead(transaction: db, peerId: id) && account.network.requests.isEmpty)
        guard case let .idBased(incoming, _, _, _, _)? = db.bulkStates[id]?[cloud] else { fatalError() }
        precondition(incoming == 0)

        (db.peers[id] as! TelegramChannel).participationStatus = .member
        state(account, 0, Int32.max - 1, count: 1)
        let message = MessageId(peerId: id, namespace: cloud, id: 24)
        db.messages[message] = Message(index: MessageIndex(id: message), threadId: nil)
        precondition(result(nagramiXBulkReadMessages(account: account, onServer: true)) == nil)
        precondition(account.network.requests.map { $0.1 } == [24])
    }

    static func monoforum() {
        let account = chat(.left, flags: .isMonoforum)
        let db = account.postbox.storage
        let subPeer = PeerId(namespace: Namespaces.Peer.CloudUser, value: 27)
        db.peers[subPeer] = Peer(id: subPeer)
        let threadId = subPeer.toInt64()
        db.threads[id] = [threadId: MessageHistoryThreadData(isMarkedUnread: true, maxIncomingReadId: 2, incomingUnreadCount: 1, maxKnownMessageId: 12)]
        let batch = offlineBatch(account)
        db.threads[id]![threadId]!.isMarkedUnread = true
        precondition(nagramiXLocalUnreadMark(transaction: db, peerId: id, threadId: threadId, serverValue: false))
        precondition(result(batch.send()) == nil)
        precondition(account.network.requests.isEmpty && account.network.savedRequests.count == 1)
        precondition(account.network.savedRequests[0] == (subPeer.value, 12))
        precondition(nagramiXLocalUnreadMark(transaction: db, peerId: id, threadId: threadId, serverValue: true))
    }

    static func main() {
        let observed = [manualMark(), acknowledgedDuringLookup(), nonMember(.left, server: true)]
        precondition(observed == Array(repeating: repaired, count: 3), "read reconciliation: \(observed)")
        if repaired {
            precondition(nonMember(.kicked, server: false))
            pendingAndAcknowledged()
            membershipAndLegacyMarker()
            monoforum()
            testManualMarkPush()
            BulkReadTests.main()
        }
        print(repaired ? "PASS all three fixes, offline and in-flight receipts, membership changes, legacy marker and monoforum" : "Reproduced all three regressions before the fix")
    }
}
