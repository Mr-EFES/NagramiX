@main enum Tests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { fatalError("panel animation regression: " + message) }
    }
    static let phone = CGSize(width: 393, height: 852)
    static let frame = CGRect(x: 0, y: 516, width: 393, height: 336)
    static func main() {
        var policy = NagramiXExpandedPanelAnimation()
        check(policy.resolve(mode: .keyboard, size: phone, transition: .immediate, reduceMotion: false) == .immediate, "initial layout does not invent an animation")
        for mode: NagramiXExpandedPanelAnimation.Mode in [.emoji, .formatting, .keyboard, .formatting, .emoji, .keyboard] {
            check(policy.resolve(mode: mode, size: phone, transition: .immediate, reduceMotion: false) == .spring(duration: 0.4), "every mode change survives an immediate UIKit layout")
            check(policy.resolve(mode: mode, size: phone, transition: .immediate, reduceMotion: false) == .immediate, "steady layout does not restart the transition")
        }
        let native = ComponentTransition(animation: .curve(duration: 0.27, curve: .keyboard))
        check(policy.resolve(mode: .emoji, size: phone, transition: native, reduceMotion: false) == native, "preserve supplied keyboard duration and curve")
        check(policy.resolve(mode: .formatting, size: phone, transition: native, reduceMotion: true) == .immediate, "Reduce Motion wins")
        check(policy.resolve(mode: .emoji, size: CGSize(width: 852, height: 393), transition: .immediate, reduceMotion: false) == .immediate, "rotation does not replay an old-sized mode transition")

        let view = UIView(); view.isHidden = true
        let presenter = NagramiXExpandedPanelPresentation()
        presenter.update(view: view, frame: frame, size: phone, visible: true, transition: native, reduceMotion: false)
        check(!view.isHidden && view.layer.motion != nil, "initial panel slides from below")
        let initial = view.layer.motion!
        check(initial.duration == 0.27 && initial.from.y == phone.height + frame.height * 0.5, "entry uses caller duration and bottom origin")
        Timeline.now += 0.1
        for _ in 0..<5 { presenter.update(view: view, frame: frame, size: phone, visible: true, transition: .immediate, reduceMotion: false) }
        check(view.layer.starts.count == 1 && view.layer.motion != nil, "repeat layout preserves ongoing animation")
        presenter.update(view: view, frame: frame, size: phone, visible: false, transition: native, reduceMotion: false)
        check(!view.isHidden && view.layer.motion != nil, "outgoing content remains visible during dismissal")
        let firstCompletion = view.layer.completions.last!
        for _ in 0..<5 { presenter.update(view: view, frame: frame, size: phone, visible: false, transition: .immediate, reduceMotion: false) }
        check(!view.isHidden, "same-frame immediate completion cannot hide outgoing content early")
        Timeline.now += 0.05
        let reversingPosition = view.layer.presentation()!.position
        presenter.update(view: view, frame: frame, size: phone, visible: true, transition: native, reduceMotion: false)
        check(view.layer.motion!.from == reversingPosition, "reverse from current presentation without reseeding below")
        presenter.update(view: view, frame: frame, size: phone, visible: false, transition: native, reduceMotion: false)
        firstCompletion(true)
        check(!view.isHidden, "stale successful completion cannot hide a newer dismissal")
        view.layer.finish()
        check(view.isHidden, "current dismissal completes")
        presenter.update(view: view, frame: frame, size: phone, visible: true, transition: native, reduceMotion: false)
        presenter.update(view: view, frame: frame, size: phone, visible: true, transition: .immediate, reduceMotion: true)
        check(view.layer.motion == nil && !view.isHidden && view.frame == frame, "Reduce Motion cancels an in-flight entry")
        presenter.update(view: view, frame: frame, size: phone, visible: false, transition: native, reduceMotion: true)
        check(view.isHidden && view.layer.motion == nil, "Reduce Motion dismissal is immediate")

        let host = ExpandedHost()
        check(host.layout(336, .immediate) == 336, "seed actual system height")
        // Simulate a synchronous immediate keyboard notification inside reloadInputViews.
        host.editor.changedInputView = { [weak host] in _ = host?.layout(0, .immediate) }
        host.nagramiXToggleEmoji()
        check(host.emojiKeyboard!.inputNode!.view.layer.motion != nil, "first immediate input-view reload retains emoji entry animation")
        host.layout(0, .immediate)
        check(!host.emojiKeyboard!.inputNode!.view.isHidden, "emoji remains visible")
        let placeholder = host.editor.customInputView; let reloads = host.editor.reloads
        for _ in 0..<12 {
            Timeline.now += 0.1
            host.nagramiXToggleFormatting(); host.layout(0, .immediate)
            let emoji = host.emojiKeyboard!.inputNode!
            check(host.panelTransition == .spring(duration: 0.4), "emoji to formatting has motion")
            check(!emoji.view.isHidden && emoji.visibleRequests.last == true, "measuring formatting keeps outgoing emoji content alive")
            check(host.nagramiXFormattingPanel!.layer.motion != nil, "formatting enters with the same transition")
            for _ in 0..<3 { check(host.layout(0, .immediate) == 336, "steady height across repeated notifications") }
            check(!emoji.view.isHidden, "measuring again does not hide an ongoing emoji dismissal")
            Timeline.now += 0.08
            host.nagramiXToggleEmoji(); host.layout(0, .immediate)
            check(host.panelTransition == .spring(duration: 0.4), "formatting to emoji has motion")
            check(!host.nagramiXFormattingPanel!.isHidden, "formatting stays visible while sliding out")
            host.layout(0, .immediate)
            check(!host.nagramiXFormattingPanel!.isHidden, "repeated layout cannot finish formatting dismissal early")
            check(host.editor.customInputView === placeholder && host.editor.reloads == reloads, "animation does not reintroduce input-view reloads")
        }
        host.emojiKeyboard!.setEmojiMode(false)
        check(host.layout(0, .immediate) == 336, "internal keyboard return preserves prior height hold")
        check(!host.emojiKeyboard!.inputNode!.view.isHidden, "emoji remains visible during internal keyboard return")
        check(host.layout(290, native) == 290, "real keyboard frame settles height")
        host.emojiKeyboard!.inputNode!.view.layer.finish()
        check(host.emojiKeyboard!.inputNode!.view.isHidden, "return eventually hides emoji")
        host.nagramiXToggleFormatting(); host.layout(0, .immediate)
        UIAccessibility.isReduceMotionEnabled = true
        host.nagramiXToggleEmoji(); host.layout(0, .immediate)
        check(host.panelTransition == .immediate && host.nagramiXFormattingPanel!.isHidden, "Reduce Motion applies to both panel types")
        check(host.emojiKeyboard!.inputNode!.view.layer.motion == nil, "Reduce Motion leaves no outer emoji animation")
        UIAccessibility.isReduceMotionEnabled = false
        host.emojiKeyboard!.setEmojiMode(false); host.layout(0, .immediate)
        host.emojiKeyboard!.inputNode!.view.layer.finish()
        host.editor.changedInputView = nil
        host.layout(0, .immediate, size: CGSize(width: 852, height: 393))
        host.nagramiXToggleFormatting(); host.layout(0, .immediate, size: CGSize(width: 852, height: 393))
        check(host.panelTransition == .spring(duration: 0.4), "opening after a settled rotation still animates")
        check(host.nagramiXFormattingPanel!.layer.motion != nil, "hidden formatting measured new size before reopening")
        check(host.editor.focused, "caret remains first responder")
        print("\(count) actual panel/transition/route checks passed; UIKit, CA timing and native content bindings are boundaries")
    }
}
