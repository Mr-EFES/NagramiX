import Foundation

@main struct StoryExplicitViewTests {
    static func main() {
        let disclosure = NagramiXStoryViewDisclosure()
        let key = NagramiXStoryViewDisclosure.Key(accountId: 1, peerId: 2, storyId: 7)
        precondition(disclosure.status(for: key) == .anonymous)
        let first = disclosure.begin(key)!
        precondition(disclosure.status(for: key) == .pending && disclosure.begin(key) == nil)
        precondition(!disclosure.complete(key, request: UUID(), success: true))
        precondition(disclosure.complete(key, request: first, success: false))
        let retry = disclosure.begin(key)!
        precondition(!disclosure.complete(key, request: first, success: true))
        precondition(disclosure.status(for: key) == .pending)
        precondition(disclosure.complete(key, request: retry, success: true))
        precondition(disclosure.status(for: key) == .recorded && disclosure.begin(key) == nil)
        for other in [
            NagramiXStoryViewDisclosure.Key(accountId: 3, peerId: 2, storyId: 7),
            .init(accountId: 1, peerId: 3, storyId: 7), .init(accountId: 1, peerId: 2, storyId: 8)
        ] { precondition(disclosure.status(for: other) == .anonymous) }
        precondition(NagramiXStoryViewDisclosure().status(for: key) == .anonymous)
        precondition(disclosure.begin(.init(accountId: 1, peerId: 1, storyId: 7)) == nil)
        precondition(disclosure.begin(.init(accountId: 1, peerId: 2, storyId: 0)) == nil)

        let context = AccountContext()
        let network = context.account.network
        let target = EngineStoryId(peerId: PeerId(value: 2), id: 50)
        let story = StoryItemSetContainerComponent(context, target)
        let view = StoryViewHarness(story)
        precondition(view.entry(story).text == "Засчитать просмотр")
        view.tap(story)
        precondition(story.nagramiXUsesAnonymousViewing)
        precondition(view.entry(story).text == "Засчитываем просмотр…" && view.entry(story).action == nil)
        view.tap(story)
        precondition(network.requests.count == 1 && network.requests[0].peer.id == target.peerId && network.requests[0].ids == [50])
        network.finish(true)
        precondition(!story.nagramiXUsesAnonymousViewing && story.nagramiXAnonymousViewing)
        precondition(view.entry(story).text == "Просмотр засчитан" && view.entry(story).action == nil)
        let next = StoryItemSetContainerComponent(context, .init(peerId: target.peerId, id: 51), story.nagramiXViewDisclosure)
        precondition(next.nagramiXUsesAnonymousViewing)
        view.component = next; view.tap(next); network.finish(false)
        precondition(next.nagramiXUsesAnonymousViewing && context.errors.last == "Failed")
        view.tap(next); network.finish(false, error: true)
        precondition(next.nagramiXUsesAnonymousViewing && view.entry(next).action != nil)
        view.tap(next)
        view.component = story
        let errorCount = context.errors.count
        network.finish(false, error: true)
        precondition(context.errors.count == errorCount && next.nagramiXUsesAnonymousViewing)
        view.component = next; view.tap(next); view.component = story; network.finish(true)
        precondition(!next.nagramiXUsesAnonymousViewing)

        let guarded = StoryItemSetContainerComponent(context, .init(peerId: target.peerId, id: 52))
        let differentSession = StoryItemSetContainerComponent(context, guarded.slice.item.id)
        view.component = differentSession
        var before = network.requests.count
        view.tap(guarded)
        precondition(network.requests.count == before)
        view.component = guarded
        guarded.stealthModeTimeout = 60
        view.tap(guarded)
        precondition(network.requests.count == before && guarded.nagramiXUsesAnonymousViewing)
        precondition(context.errors.last == "Server stealth active")
        guarded.stealthModeTimeout = nil
        for state in 0..<4 {
            guarded.isCentral = state != 0; guarded.isDismissed = state == 1
            guarded.nagramiXAnonymousViewing = state != 2
            guarded.slice.item.storyItem.media = state == 3 ? .liveStream : .video
            view.tap(guarded)
            precondition(network.requests.count == before)
        }
        guarded.isCentral = true; guarded.isDismissed = false; guarded.nagramiXAnonymousViewing = true
        guarded.slice.item.storyItem.media = .video
        view.component = guarded
        view.tap(guarded)
        let beforeClose = context.errors.count
        guarded.isDismissed = true
        network.finish(false, error: true)
        precondition(context.errors.count == beforeClose && guarded.nagramiXUsesAnonymousViewing)
        guarded.isDismissed = false
        before = network.requests.count
        view.component = StoryItemSetContainerComponent(AccountContext(), guarded.slice.item.id, guarded.nagramiXViewDisclosure)
        view.tap(guarded)
        precondition(network.requests.count == before)
        view.component = story
        view.tap(guarded)
        precondition(network.requests.count == before)

        // Core: invalid/own/missing peer fail without RPC; only one explicit ID otherwise.
        for (peer,id) in [(Int64(1),Int32(9)), (2,0), (2,-1)] {
            var answer: Bool?
            let disposable = _internal_nagramiXRecordStoryView(account: context.account, peerId: .init(value: peer), id: id).start(next: { answer = $0 })
            precondition(answer == false && network.requests.count == before); disposable.dispose()
        }
        context.account.postbox.value.missing = true
        var answer: Bool?
        var disposable = _internal_nagramiXRecordStoryView(account: context.account, peerId: target.peerId, id: 99).start(next: { answer = $0 })
        precondition(answer == false && network.requests.count == before); disposable.dispose()
        context.account.postbox.value.missing = false
        for result in 0..<3 {
            answer = nil
            disposable = _internal_nagramiXRecordStoryView(account: context.account, peerId: target.peerId, id: 99).start(next: { answer = $0 })
            before += 1
            precondition(answer == nil && network.requests.count == before && network.requests.last!.ids == [99])
            network.finish(result == 0, error: result == 2)
            precondition(answer == (result == 0)); disposable.dispose()
        }
        print("PASS: production disclosure/menu/core with native SignalKit; exact ID, ACK/failure/retry, stale callbacks/actions, account/story/session isolation, server stealth and automatic-read guards; UIKit/server pending")
    }
}
