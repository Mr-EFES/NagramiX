// Expand the native, reactive folder view in bounded steps. A chronological
// first page cannot find an older chat with a larger unread count. Keep native
// predicates, holes, pins and community summaries; never mutate database indices.
func nagramiXUnreadChatListView(chatListLocation: ChatListControllerLocation, location: ChatListNodeLocation, account: Account) -> Signal<ChatListNodeViewUpdate, NoError> {
    guard case .chatList = chatListLocation else {
        return chatListViewForLocation(chatListLocation: chatListLocation, location: location, account: account, shouldLoadCanMessagePeer: false)
    }
    return Signal { subscriber in
        let requestedCount = ValuePromise<Int>(80, ignoreRepeated: true)
        var currentCount = 80
        var didEmit = false
        var pendingScroll: ChatListNodeViewScrollPosition?
        if case let .scroll(index, sourceIndex, position, animated, _) = location, case let .chatList(index) = index {
            pendingScroll = .index(index: index, position: position, directionHint: sourceIndex > .chatList(index) ? .Down : .Up, animated: animated)
        }
        let disposable = (requestedCount.get()
        |> mapToSignal { count -> Signal<(Int, ChatListNodeViewUpdate), NoError> in
            return chatListViewForLocation(chatListLocation: chatListLocation, location: .initial(count: count, filter: location.filter), account: account, shouldLoadCanMessagePeer: false)
            |> map { update in (count, update) }
            |> deliverOnMainQueue
        }).start(next: { count, update in
            var scrollPosition: ChatListNodeViewScrollPosition?
            if let scroll = pendingScroll, !update.list.hasEarlier, !update.list.isLoading {
                scrollPosition = scroll
                pendingScroll = nil
            }
            var updateType = update.type
            if didEmit {
                switch updateType {
                case .Initial, .InitialUnread:
                    updateType = .Generic
                default:
                    break
                }
            }
            didEmit = true
            subscriber.putNext(ChatListNodeViewUpdate(list: update.list, type: updateType, scrollPosition: scrollPosition, nagramiXUnreadChatsFirst: true))
            // Native hole filling must complete before widening the window.
            // The promise cancels the preceding view subscription on expansion.
            if count == currentCount && update.list.hasEarlier && !update.list.isLoading && currentCount <= Int.max / 2 {
                currentCount *= 2
                let nextCount = currentCount
                Queue.mainQueue().async {
                    requestedCount.set(nextCount)
                }
            }
        }, error: { _ in }, completed: {
            subscriber.putCompletion()
        })
        return ActionDisposable {
            disposable.dispose()
        }
    }
}
