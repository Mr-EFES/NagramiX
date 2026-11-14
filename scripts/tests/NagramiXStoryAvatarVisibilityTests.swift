@main struct StoryAvatarVisibilityTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ reason: String) {
            if !value() { print("FAIL: " + reason); exit(96) }
            checks += 1
        }
        func content(_ anonymous: Bool, ready: Bool = true, own: Bool = false) -> StoryContentContext {
            let result = StoryContentContext()
            result.nagramiXAnonymousViewing = anonymous
            if ready { result.stateValue = .init(slice: .init(effectivePeer: EnginePeer(id: own ? 1 : 2), item: .init(id: 9, storyItem: .init(id: 9, media: .image(TelegramMediaImage()))))) }
            return result
        }
        func transition(_ kind: Int, _ avatar: AvatarNode, _ indicator: UIView) -> StoryContainerScreen.TransitionIn? {
            switch kind {
            case 0: return peerTransition(avatar)()
            case 1: return archiveTransition(avatar)
            default: return PeerInfoScreenNode(avatar: avatar, indicator: indicator).transition(fromAvatar: kind == 2)
            }
        }
        for kind in 0..<4 {
            for anonymous in [false, true] {
                for confirmation in [false, true] {
                    for accept in [false, true] {
                        NagramiXTabSettings.current.confirmStoryViewing = confirmation
                        let avatar = AvatarNode(), indicator = UIView(), host = ViewController()
                        let source = kind == 3 ? indicator : avatar.view
                        var prepared = transition(kind, avatar, indicator)
                        var viewer: StoryContainerScreen? = StoryContainerScreen(content(anonymous), transitionIn: prepared)
                        weak var lifetime = viewer
                        check(!source.isHidden, "source remains visible before confirmation")
                        viewer!.nagramiXPush(from: host)
                        viewer = nil
                        let needsConfirmation = anonymous || confirmation
                        check(!source.isHidden, "pending source remains visible in both modes")
                        if needsConfirmation {
                            check(host.pushed == nil && host.confirmation != nil, "confirmation preserves native approval gate")
                            if accept { host.confirmation!.confirmed() } else { host.confirmation!.cancelled() }
                            host.confirmation = nil
                        }
                        if needsConfirmation && !accept {
                            check(lifetime == nil && host.pushed == nil, "cancel releases unpresented story")
                            check(!source.isHidden && source.visibilityWrites.isEmpty, "cancel never hides the source")
                        } else {
                            check(host.pushed === lifetime && !source.isHidden, "push alone does not hide source before appearance")
                            host.pushed!.viewDidAppear(false)
                            check(source.isHidden, "real viewer appearance hides transition source")
                            check(source.visibilityWrites == [true], "appearance changes visibility once")
                            host.pushed!.viewDidAppear(false)
                            check(source.visibilityWrites == [true], "reappearance does not start a second hide")
                            check((host.pushed!.node.hostView.componentView as? StoryContainerScreenComponent.View)?.animationCount == 1, "native entry animation executes once")
                            host.pushed = nil
                            check(lifetime == nil && !source.isHidden, "viewer disposal restores original avatar without requiring destination transition")
                            check(source.visibilityWrites == [true, false], "restore occurs even while transition object is still retained")
                        }
                        prepared = nil
                        check(!source.isHidden, "transition release leaves avatar visible")
                    }
                }
            }
        }
        // Slow content, cancelling before acceptance, disappearance of the
        // navigation host and timeout must never hide a source in advance.
        for anonymous in [false, true] {
            for ready in [false, true] {
                NagramiXTabSettings.current.confirmStoryViewing = true
                let avatar = AvatarNode(), host = ViewController(), data = content(anonymous, ready: ready)
                var viewer: StoryContainerScreen? = StoryContainerScreen(data, transitionIn: peerTransition(avatar)())
                weak var lifetime = viewer
                viewer!.nagramiXPush(from: host); viewer = nil
                check(!avatar.isHidden, "waiting for content preserves avatar")
                if !ready { data.subscriber!.putNext(content(anonymous).stateValue!) }
                check(host.confirmation != nil && !avatar.isHidden, "late state still waits for acceptance")
                host.confirmation!.cancelled(); host.confirmation = nil
                check(lifetime == nil && !avatar.isHidden, "late cancellation preserves avatar")
            }
            do {
                let avatar = AvatarNode(), host = ViewController(), data = content(anonymous, ready: false)
                var viewer: StoryContainerScreen? = StoryContainerScreen(data, transitionIn: peerTransition(avatar)())
                weak var lifetime = viewer
                viewer!.nagramiXPush(from: host); viewer = nil
                Timer.fire(30)
                check(lifetime == nil && host.pushed == nil && !avatar.isHidden, "content timeout leaves original avatar visible")
            }
            do {
                let avatar = AvatarNode()
                var host: ViewController? = ViewController()
                var viewer: StoryContainerScreen? = StoryContainerScreen(content(anonymous), transitionIn: peerTransition(avatar)())
                weak var lifetime = viewer
                viewer!.nagramiXPush(from: host!); viewer = nil; host = nil
                check(lifetime == nil && !avatar.isHidden, "lost host does not hide or retain avatar")
            }
        }
        // Repeated cancel/open cycles on the very same list cell.
        let avatar = AvatarNode(), host = ViewController()
        for _ in 0..<5 {
            var viewer: StoryContainerScreen? = StoryContainerScreen(content(true), transitionIn: peerTransition(avatar)())
            viewer!.nagramiXPush(from: host); viewer = nil
            host.confirmation!.cancelled(); host.confirmation = nil
            check(!avatar.isHidden, "repeat cancellation leaves same cell intact")
        }
        // Weak transition callbacks must not retain a removed/recycled source.
        var removed: AvatarNode? = AvatarNode()
        weak var weakSource = removed
        let prepared = peerTransition(removed)()
        removed = nil
        check(weakSource == nil, "transition callback weakly captures original avatar")
        _ = prepared
        check(peerTransition(nil)() == nil && archiveTransition(nil) == nil, "missing source keeps native optional transition")
        print("PASS \(checks) production story avatar/confirmation/lifecycle checks; UIKit and OS are explicit boundaries")
    }
}
