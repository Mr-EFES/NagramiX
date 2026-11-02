// Только явное согласие на один story ID; не меняет maxReadId и общую приватность.
func _internal_nagramiXRecordStoryView(account: Account, peerId: PeerId, id: Int32) -> Signal<Bool, NoError> {
    guard id > 0, peerId != account.peerId else { return .single(false) }
    return account.postbox.transaction { transaction -> Api.InputPeer? in
        return transaction.getPeer(peerId).flatMap(apiInputPeer)
    }
    |> mapToSignal { inputPeer -> Signal<Bool, NoError> in
        guard let inputPeer else { return .single(false) }
        return account.network.request(Api.functions.stories.incrementStoryViews(peer: inputPeer, id: [id]))
        |> map { result -> Bool in
            if case .boolTrue = result { return true }
            return false
        }
        |> `catch` { _ -> Signal<Bool, NoError> in return .single(false) }
    }
}
