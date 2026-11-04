// Window/keyboard notifications remain a boundary; the actual native adapter
// and the actual final policy are executed with the notification's duration.
@main enum TimingTests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { fatalError("keyboard timing regression: " + message) }
    }
    static func same(_ a: ComponentTransition, _ b: ComponentTransition) -> Bool {
        switch (a.animation, b.animation) {
        case (.none, .none): return true
        case let (.curve(x, c), .curve(y, d)): return (x == y || (x.isNaN && y.isNaN)) && c == d
        default: return false
        }
    }
    static func main() {
        Tests.main()
        let size = CGSize(width: 393, height: 852)
        let modes: [NagramiXExpandedPanelAnimation.Mode] = [.emoji, .formatting, .keyboard, .formatting, .emoji, .keyboard]
        for duration in [0.0, -0.0, Double.ulpOfOne, Double.leastNonzeroMagnitude, -1.0, Double.nan, Double.infinity] {
            let input = ComponentTransition(ContainedViewLayoutTransition.animated(duration: duration, curve: .spring))
            check(!input.animation.isImmediate, "native adapter retains the animated enum even without usable duration")
            var policy = NagramiXExpandedPanelAnimation()
            check(same(policy.resolve(mode: .keyboard, size: size, transition: input, reduceMotion: false), input), "initial layout does not invent mode motion")
            for mode in modes {
                check(policy.resolve(mode: mode, size: size, transition: input, reduceMotion: false) == .spring(duration: 0.4), "mode switch needs positive finite duration")
                check(same(policy.resolve(mode: mode, size: size, transition: input, reduceMotion: false), input), "steady notification does not restart motion")
            }
            check(policy.resolve(mode: .formatting, size: size, transition: input, reduceMotion: true) == .immediate, "Reduce Motion overrides fallback")
            check(same(policy.resolve(mode: .emoji, size: CGSize(width: 852, height: 393), transition: input, reduceMotion: false), input), "resizing preserves native layout policy")
        }
        let curves: [ContainedViewLayoutTransitionCurve] = [.spring, .easeInOut, .custom(0.2, 0.1, 0.7, 1)]
        for curve in curves {
            for duration in [0.16, 0.25, 0.4, 0.5] {
                var policy = NagramiXExpandedPanelAnimation()
                _ = policy.resolve(mode: .keyboard, size: size, transition: .immediate, reduceMotion: false)
                let input = ComponentTransition(ContainedViewLayoutTransition.animated(duration: duration, curve: curve))
                for mode in modes {
                    check(policy.resolve(mode: mode, size: size, transition: input, reduceMotion: false) == input, "valid keyboard duration and curve survive all mode pairs")
                }
            }
        }
        let zero = ComponentTransition(ContainedViewLayoutTransition.animated(duration: 0, curve: .spring))
        let host = ExpandedHost()
        _ = host.layout(336, .immediate)
        host.editor.changedInputView = { [weak host] in _ = host?.layout(0, zero) }
        host.nagramiXToggleEmoji()
        check(host.panelTransition == .spring(duration: 0.4), "zero-duration reload notification uses fallback before explicit state update")
        check(host.emojiKeyboard!.inputNode!.view.layer.motion?.duration == 0.4, "emoji receives actual positive animation")
        for _ in 0..<5 { check(host.layout(0, zero) == 336, "repeated zero-duration frames preserve height") }
        Timeline.now += 0.1
        host.nagramiXToggleFormatting(); _ = host.layout(0, zero)
        check(host.panelTransition == .spring(duration: 0.4), "custom mode exchange survives zero-duration parent layout")
        check(!host.emojiKeyboard!.inputNode!.view.isHidden, "outgoing emoji remains until motion completes")
        check(host.nagramiXFormattingPanel!.layer.motion?.duration == 0.4, "formatting receives same positive animation")
        for _ in 0..<3 { _ = host.layout(0, zero) }
        check(!host.emojiKeyboard!.inputNode!.view.isHidden, "repeat zero-duration layouts cannot hide outgoing content")
        host.nagramiXToggleFormatting()
        check(host.editor.customInputView == nil && host.editor.focused, "return preserves first responder and restores native input view")
        check(host.layout(0, zero) == 336, "keyboard return retains zero-frame height hold")
        check(host.layout(290, zero) == 290, "real keyboard frame still supplies final height")
        print("\(count) native-adapter/timing checks passed in addition to the existing panel suite; UIKit/CA delivery not exercised")
    }
}
