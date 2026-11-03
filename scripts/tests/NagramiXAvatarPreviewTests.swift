@main enum Tests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { fatalError("avatar regression: " + message) }
    }
    static func main() {
        for option in [true, false] {
            NagramiXTabSettings.current.chatActionsOnHold = option
            let row = RowHost()
            let item = row.item!
            var preview = 0, story = 0, normal = 0, nativePreview = 0, community = 0
            var selectedThread: Int64?
            var selectedMessage: Int?
            item.interaction.nagramiXOpenChatWithoutReadReceipts = { _ in preview += 1 }
            item.interaction.openStories = { _, _ in story += 1 }
            item.interaction.openCommunity = { _ in community += 1 }
            item.interaction.peerSelected = { _, _, _, _, _ in normal += 1 }
            item.interaction.messageSelected = { _, thread, message, _ in normal += 1; selectedThread = thread; selectedMessage = message.id }
            item.interaction.activateChatPreview = { _, _, _, _, _ in nativePreview += 1 }
            for stats in [StoryStats(totalCount: 1), StoryStats(totalCount: 4), StoryStats(totalCount: 0, hasLiveItems: true)] {
                var data = PeerData(); data.storyState = StoryState(stats: stats); item.content = .peer(data)
                let oldStory = story
                row.avatarStoryTapGesture(TapRecognizer())
                check(story == oldStory + 1 && preview == 0 && normal == 0, "short avatar tap with stories opens native stories, not preview")
            }
            for stats in [StoryStats?.none, StoryStats(totalCount: 0)] {
                var data = PeerData(); data.storyState = stats.map { StoryState(stats: $0) }; item.content = .peer(data)
                let oldNormal = normal
                row.avatarStoryTapGesture(TapRecognizer())
                check(normal == oldNormal + 1 && preview == 0, "avatar without stories opens ordinary row route")
            }
            var data = PeerData(); data.messages = [Message(id: 90, threadId: 55)]; item.content = .peer(data)
            item.index = .forum(0, 0, 44, 0, 0)
            row.avatarStoryTapGesture(TapRecognizer())
            check(selectedThread == 44 && selectedMessage == 90, "normal avatar route preserves native message and forum thread")
            data.peer.peer = .user(UserPeer(id: 7, botInfo: BotInfo(flags: .hasForum))); data.forumTopicData = Topic(id: 77); item.content = .peer(data)
            row.avatarStoryTapGesture(TapRecognizer())
            check(selectedThread == 77, "native bot forum topic handling is shared")
            data = PeerData(); data.peer.peer = .plain(Peer(id: 8, containerPeerId: 9)); item.content = .peer(data)
            row.avatarStoryTapGesture(TapRecognizer())
            check(community == 1, "native linked-community avatar route remains intact")
            data = PeerData(); data.storyState = StoryState(stats: StoryStats(totalCount: 3)); item.content = .peer(data)
            for state in [TapRecognizer.State.began, .cancelled, .failed] {
                let tap = TapRecognizer(); tap.state = state; let oldStory = story
                row.avatarStoryTapGesture(tap)
                check(story == oldStory, "tap opens only on ended")
            }
            for _ in 0..<12 {
                let oldStory = story, oldNormal = normal, oldPreview = preview
                row.nagramiXHoldBeganOnAvatar = true
                row.activate(ContextGesture(), CGPoint(x: 20, y: 20))
                check(preview == oldPreview + 1 && story == oldStory && normal == oldNormal, "long avatar hold exclusively opens read-only preview")
                check(row.contextContainer.cancelled && row.avatarTapRecognizer!.cancellations == preview, "long hold cancels context extraction and pending short tap")
            }
            let oldPreview = preview
            row.nagramiXHoldBeganOnAvatar = false
            row.activate(ContextGesture(), CGPoint(x: 100, y: 20))
            check(preview == oldPreview && nativePreview == 1, "hold outside avatar preserves preference/native menu route")
            item.editing = true
            check(!row.nagramiXCanOpenAvatarWithoutReadReceipts, "editing excludes custom avatar route")
            item.editing = false; item.hasActiveRevealControls = true
            check(!row.nagramiXCanOpenAvatarWithoutReadReceipts, "reveal controls exclude custom avatar route")
            item.hasActiveRevealControls = false; item.interaction.isInlineMode = true
            check(!row.nagramiXCanOpenAvatarWithoutReadReceipts, "inline picker excludes preview route")
            item.interaction.isInlineMode = false; item.useCommunityViewLayout = true
            check(!row.nagramiXCanOpenAvatarWithoutReadReceipts, "community layout retains native handling")
        }
        let root = ViewController(), folder = ViewController(), preview = PreviewController(), active = ViewController()
        let navigation = NavigationController([root, folder, preview])
        var completions = 0
        preview.makeCommit(navigation)(active, true, { completions += 1 })
        check(navigation.viewControllers.count == 3 && navigation.viewControllers[0] === root && navigation.viewControllers[1] === folder && navigation.viewControllers.last === active, "reply atomically replaces only preview and preserves parent stack")
        check(completions == 1 && navigation.commits == 1, "native completion invoked once after commit")
        navigation.viewControllers.removeLast()
        check(navigation.viewControllers.last === folder, "one Back returns to previous menu, never preview")
        let stale = PreviewController(), destination = ViewController()
        navigation.viewControllers = [root, stale]
        let deferred = stale.makeCommit(navigation)
        navigation.viewControllers = [root]
        deferred(destination, true, { completions += 1 })
        check(navigation.viewControllers.count == 1 && navigation.viewControllers.last === root && completions == 1, "reply deferred past Back cannot resurrect closed preview/chat")
        navigation.viewControllers = [root, stale, folder]
        deferred(destination, true, { completions += 1 })
        check(navigation.viewControllers.last === folder && completions == 1, "another top screen prevents stale replacement")
        navigation.viewControllers = [root, stale]
        let first = stale.makeCommit(navigation), second = stale.makeCommit(navigation)
        first(active, true, { completions += 1 }); second(destination, true, { completions += 1 })
        check(navigation.viewControllers.count == 2 && navigation.viewControllers.last === active && completions == 2, "duplicate Reply callback cannot stack two active chats")
        var disposable: PreviewController? = PreviewController()
        let released = disposable!.makeCommit(navigation)
        weak var weakPreview = disposable
        disposable = nil
        released(destination, true, { completions += 1 })
        check(weakPreview == nil && navigation.viewControllers.last === active, "pending commit does not retain or resurrect removed preview")
        print("PASS: \(count) actual avatar tap/hold, native row selection and preview replacement checks; UIKit/metadata/navigation boundaries")
    }
}
