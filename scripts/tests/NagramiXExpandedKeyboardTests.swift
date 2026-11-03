@main enum Tests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { fatalError("keyboard regression: " + message) }
    }
    static func near(_ a: CGFloat, _ b: CGFloat) -> Bool { abs(a - b) < 0.001 }
    static let phone = CGSize(width: 393, height: 852)
    static func main() {
        var geometry = NagramiXExpandedInputGeometry()
        geometry.update(size: phone, inputHeight: 336, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
        check(geometry.customInputHeight == 336, "cache measured system height")
        for raw in [CGFloat(336), 0, 42, 500, 0] {
            geometry.update(size: phone, inputHeight: raw, safeBottom: 34, standardInputHeight: 310, customInputActive: true, focused: true)
            check(geometry.customInputHeight == 336, "custom mode never caches placeholder/stale system frames")
        }
        geometry.recordCustomPanelHeight(336, safeBottom: 34)
        let generation = geometry.beginKeyboardHandoff()!
        for raw in [CGFloat(0), 42, 100, 0, 220] {
            geometry.update(size: phone, inputHeight: raw, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
            check(geometry.bottomInset == 336, "no zero/partial-height collapse on return")
        }
        geometry.update(size: phone, inputHeight: 290, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
        check(geometry.bottomInset == 290 && geometry.customInputHeight == 290, "adopt actual keyboard with predictions off")
        check(!geometry.expireHandoff(generation), "completed handoff rejects timeout")
        geometry.update(size: phone, inputHeight: 0, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
        check(geometry.bottomInset == 34, "normal keyboard dismissal is not frozen")

        geometry.update(size: phone, inputHeight: 336, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
        geometry.recordCustomPanelHeight(336, safeBottom: 34)
        let staleStart = geometry.beginKeyboardHandoff()!
        geometry.update(size: phone, inputHeight: 336, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
        geometry.update(size: phone, inputHeight: 0, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
        check(geometry.bottomInset == 336, "unchanged stale frame cannot finish handoff before zero frame")
        geometry.update(size: phone, inputHeight: 336, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
        check(!geometry.expireHandoff(staleStart), "real full frame finishes stale-start handoff")
        geometry.recordCustomPanelHeight(336, safeBottom: 34)
        let oldGeneration = geometry.beginKeyboardHandoff()!
        let newGeneration = geometry.beginKeyboardHandoff()!
        check(!geometry.expireHandoff(oldGeneration), "old delayed callback cannot cancel a newer return")
        check(geometry.expireHandoff(newGeneration), "hardware keyboard return has bounded fallback")
        geometry.update(size: phone, inputHeight: 0, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
        check(geometry.bottomInset == 34, "fallback releases retained height")
        geometry.recordCustomPanelHeight(336, safeBottom: 34)
        let cancelled = geometry.beginKeyboardHandoff()!
        geometry.update(size: phone, inputHeight: 0, safeBottom: 34, standardInputHeight: 310, customInputActive: true, focused: true)
        check(!geometry.expireHandoff(cancelled), "new custom mode cancels old fallback")
        _ = geometry.beginKeyboardHandoff()
        geometry.update(size: CGSize(width: 852, height: 393), inputHeight: 0, safeBottom: 21, standardInputHeight: 216, customInputActive: true, focused: true)
        check(geometry.customInputHeight == 216, "rotation invalidates portrait keyboard cache")
        geometry.update(size: phone, inputHeight: .nan, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true)
        check(geometry.bottomInset == 34 && geometry.customInputHeight == 310, "invalid system frame cannot poison geometry")
        geometry.recordCustomPanelHeight(310, safeBottom: 34)
        _ = geometry.beginKeyboardHandoff()
        geometry.update(size: phone, inputHeight: 0, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: false)
        check(geometry.bottomInset == 34, "focus loss cancels hold")
        geometry.update(size: phone, inputHeight: 400, safeBottom: 34, standardInputHeight: 310, customInputActive: false, focused: true, systemInputActive: false)
        check(geometry.customInputHeight == 310, "foreign input view cannot overwrite system keyboard cache")

        let host = ExpandedHost()
        check(host.layout(336) == 336, "initial system layout")
        host.nagramiXToggleFormatting()
        for raw in [CGFloat(336), 0, 42, 0, 500] {
            check(host.layout(raw) == 336, "formatting row retains measured height across UIKit notifications")
            check(host.lastPanelHeight == 336, "panel and action row share one height")
        }
        let placeholder = host.editor.customInputView
        let reloads = host.editor.reloads
        for _ in 0..<24 {
            host.nagramiXToggleEmoji()
            check(host.layout(0) == 336, "formatting to emoji retains row position")
            check(host.lastPanelTransition == .immediate, "equal-height custom panels exchange in place")
            check(host.editor.customInputView === placeholder && host.editor.reloads == reloads, "formatting to emoji does not reload input views")
            host.nagramiXToggleFormatting()
            check(host.layout(0) == 336, "emoji to formatting retains row position")
            check(host.lastPanelTransition == .immediate, "reverse custom exchange does not restart slide")
            check(host.editor.customInputView === placeholder && host.editor.reloads == reloads, "emoji to formatting shares placeholder identity")
        }
        host.nagramiXToggleFormatting()
        for raw in [CGFloat(0), 34, 100, 220] { check(host.layout(raw) == 336, "formatting to keyboard never visits bottom of screen") }
        check(host.layout(290) == 290, "system notification supplies final keyboard height")
        check(host.editor.customInputView == nil, "system keyboard restored")
        host.nagramiXToggleEmoji()
        check(host.layout(0) == 290 && host.lastPanelHeight == 290, "emoji uses current measured height")
        host.emojiKeyboard?.setEmojiMode(false)
        check(host.layout(0) == 290, "emoji internal return action uses same handoff")
        check(host.layout(290) == 290, "internal return settles")
        host.nagramiXToggleFormatting()
        host.layout(0)
        host.nagramiXToggleFormatting()
        host.layout(0)
        host.nagramiXToggleEmoji()
        check(host.layout(0) == 290, "rapid switch cancels in-flight system handoff")
        DispatchQueue.main.drain()
        check(host.layout(0) == 290, "stale timeout cannot collapse active custom panel")
        host.nagramiXToggleEmoji()
        host.layout(0)
        DispatchQueue.main.drain()
        check(host.layout(0) == 34, "no-keyboard fallback releases action row")

        let foreign = UIView()
        host.nagramiXToggleFormatting()
        host.editor.customInputView = foreign
        host.nagramiXSetFormattingMode(false)
        check(host.editor.customInputView === foreign, "formatting does not clear another input-view owner")
        host.nagramiXToggleEmoji()
        host.editor.customInputView = foreign
        host.emojiKeyboard?.setEmojiMode(false)
        check(host.editor.customInputView === foreign, "emoji does not clear another input-view owner")
        host.editor.focused = false
        host.editor.customInputView = nil
        host.nagramiXToggleEmoji()
        check(!host.editor.focusSawSystemKeyboard, "placeholder installed before focus prevents system keyboard flash")
        check(host.componentState!.transitions.last!.animated, "normal panel request keeps spring animation")
        UIAccessibility.isReduceMotionEnabled = true
        host.nagramiXRequestInputPanelLayout()
        check(host.componentState!.transitions.last == .immediate, "Reduce Motion remains immediate")
        NagramiXFormattingSettings.enabled = false
        host.nagramiXToggleFormatting()
        check(!host.nagramiXFormattingActive, "OFF prevents opening formatting")
        print("PASS: \(count) actual expanded keyboard geometry, ownership, handoff and replay checks; UIKit/component boundaries")
    }
}
