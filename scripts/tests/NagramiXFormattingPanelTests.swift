import Foundation

@main struct FormattingPanelTests {
    static func main() {
        QuickFormattingTests.main()
        if CommandLine.arguments.count > 1 { return }
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ message: String) {
            precondition(value(), message); checks += 1
        }

        // The approved default layout is 4x3 on every ordinary phone width.
        for width in [320.0, 375, 390, 393, 402, 414, 430, 440, 667, 844, 1024] {
            for height in [130.0, 216, 240, 280, 330] {
                let grid = NagramiXFormattingGrid.layout(size: CGSize(width: width, height: height), count: 10,
                    minimumLabelWidth: 60, minimumKeyHeight: 65, accessibility: false, footerMinimumLabelWidth: 90)
                check(grid.columns == 4 && grid.frames.count == 12, "one 4x3 grid, no footer")
                check(grid.frames[10].minX == grid.frames[6].minX, "pull quote directly below date")
                check(grid.frames[11].minX == grid.frames[7].minX, "select all directly below strike")
                check(grid.frames[10].minY == grid.frames[8].minY && grid.frames[11].minY == grid.frames[9].minY,
                      "all four third-row actions share one baseline")
                for (i, frame) in grid.frames.enumerated() {
                    check(frame.size == grid.frames[0].size && frame.width > 0 && frame.height >= 60, "identical accessible touch sizes")
                    check(frame.minX >= 0 && frame.maxX <= grid.contentSize.width + 0.001, "no horizontal overflow")
                    check(frame.maxY <= grid.contentSize.height + 0.001, "scroll reaches every action")
                    for other in grid.frames.dropFirst(i + 1) { check(!frame.intersects(other), "keys never overlap") }
                }
                if height >= 216 { check(grid.contentSize.height <= height + 0.001, "three ordinary rows fit without hiding the first") }
            }
        }
        for width in [280.0, 320, 440, 844] {
            for labelWidth in [100.0, 150, 240] {
                let grid = NagramiXFormattingGrid.layout(size: CGSize(width: width, height: 230), count: 10,
                    minimumLabelWidth: labelWidth, minimumKeyHeight: 90, accessibility: true, footerMinimumLabelWidth: labelWidth)
                check(grid.frames.count == 12 && grid.columns <= 4, "large accessibility text retains every action")
                check(grid.frames.allSatisfy { $0.width >= labelWidth + 4 || grid.columns == 1 }, "large labels get fewer columns rather than clipping")
            }
        }
        for bad in [CGFloat.nan, .infinity, -1] {
            check(NagramiXFormattingGrid.layout(size: CGSize(width: 393, height: 230), count: 10,
                minimumLabelWidth: 60, minimumKeyHeight: 65, accessibility: false, footerMinimumLabelWidth: bad).frames.isEmpty,
                  "bad extra geometry cannot create unsafe frames")
        }

        NagramiXFormattingSettings.setEnabled(true)
        let p = FormattingPanel(), editor = p.richTextInputNode!, state = p.presentationInterfaceState!
        let empty = EmptyInputView()
        var hostRequests = 0
        p.nagramiXConfigureFormattingHost(inputView: empty) { hostRequests += 1 }
        editor.content = NSAttributedString(string: "А😀Б")
        editor.selectedRange = NSRange(location: 0, length: 4)
        p.nagramiXToggleFormatting()
        check(p.nagramiXFormattingActive && editor.keyboardInputView === empty, "native empty view suppresses system keyboard")
        check(p.nagramiXFormattingPanelView(for: state) === p.nagramiXFormattingKeyboard, "real content belongs to app input node")
        check(hostRequests == 1 && editor.reloads == 1, "one host transition and one keyboard reload")
        check(editor.selectedRange == NSRange(location: 0, length: 4), "activation preserves actual selection")
        func input(_ current: ChatInputNode? = nil, makeMedia: () -> ChatInputNode? = { nil }) -> ChatInputNode? {
            inputNodeForChatPresentationIntefaceState(state, context: AccountContext(), currentNode: current,
                interfaceInteraction: p.interfaceInteraction, controllerInteraction: ChatControllerInteraction(),
                inputPanelNode: p, makeMediaInputNode: makeMedia)
        }
        let hosted = input()!
        check(hosted.view.subviews.first === p.nagramiXFormattingKeyboard, "single real keyboard instance hosted")
        check(input(hosted) === hosted, "layout reuses the node rather than restarting its entry animation")
        for height in [346.0, 216, 320] {
            let result = hosted.updateLayout(width: 393, leftInset: 0, rightInset: 0, bottomInset: 34,
                standardInputHeight: height, inputHeight: 0, maximumHeight: 700, inputPanelHeight: 52,
                transition: .immediate, interfaceState: state, layoutMetrics: LayoutMetrics(), deviceMetrics: DeviceMetrics(),
                isVisible: true, isExpanded: false)
            check(result.0 == height && result.1 == 0, "same standard height as native emoji, no second safe inset")
            check(hosted.view.subviews.first?.frame == CGRect(x: 0, y: 0, width: 393, height: height), "actual content has exact native node bounds")
        }
        let oldFrame = p.nagramiXFormattingKeyboard!.frame
        p.nagramiXFormattingKeyboard!.updateHeight(216)
        check(p.nagramiXFormattingKeyboard!.frame == oldFrame, "height preparation does not jump ahead of host animation")
        check(p.nagramiXFormattingKeyboard!.intrinsicContentSize.height == 216, "UIKit fallback still receives new intrinsic height")

        for _ in 0..<20 {
            let reloads = editor.reloads, nilWrites = editor.nilInputWrites
            p.nagramiXCloseFormatting(reload: false, preserveInputView: true)
            state.inputMode = .media
            let media = ChatEntityKeyboardInputNode()
            check(input(hosted, makeMedia: { media }) === media, "native emoji factory resumes without formatting")
            check(editor.keyboardInputView === empty && editor.reloads == reloads, "formatting-to-emoji keeps same empty view")
            p.nagramiXToggleFormatting()
            check(editor.keyboardInputView === empty && editor.reloads == reloads, "emoji-to-formatting avoids another zero-height reload")
            check(editor.nilInputWrites == nilWrites, "no intermediate system keyboard during rapid handoff")
        }
        let requests = hostRequests
        p.nagramiXCloseFormatting(reload: true)
        check(editor.keyboardInputView == nil && !p.nagramiXFormattingActive, "system keyboard restored")
        check(hostRequests == requests, "keyboard notification owns return; no premature zero-height layout")
        check(input() == nil, "text mode returns to the original native path")
        p.nagramiXToggleFormatting()
        let foreign = UIView(); editor.keyboardInputView = foreign
        p.nagramiXCloseFormatting(reload: true)
        check(editor.keyboardInputView === foreign, "foreign input-view ownership preserved")

        // Component-based composers retain their native UIKit path and must
        // not clear formatting on every text/selection update.
        let componentPanel = FormattingPanel(), componentEditor = componentPanel.richTextInputNode!
        componentPanel.nagramiXToggleFormatting()
        let content = componentEditor.keyboardInputView, reloads = componentEditor.reloads
        updateComponentInput(panelNode: componentPanel, component: Component(hideKeyboard: false), presentationInterfaceState: state)
        check(componentEditor.keyboardInputView === content && componentEditor.reloads == reloads, "component refresh preserves active formatting")
        let nilWrites = componentEditor.nilInputWrites
        updateComponentInput(panelNode: componentPanel, component: Component(hideKeyboard: true), presentationInterfaceState: state)
        check(componentEditor.keyboardInputView is EmptyInputView && !componentPanel.nagramiXFormattingActive, "component switches to native emoji placeholder")
        check(componentEditor.nilInputWrites == nilWrites, "component handoff is atomic")
        let componentEmpty = componentEditor.keyboardInputView, count = componentEditor.reloads
        updateComponentInput(panelNode: componentPanel, component: Component(hideKeyboard: true), presentationInterfaceState: state)
        check(componentEditor.keyboardInputView === componentEmpty && componentEditor.reloads == count, "native emoji placeholder reused")
        updateComponentInput(panelNode: componentPanel, component: Component(hideKeyboard: false), presentationInterfaceState: state)
        check(componentEditor.keyboardInputView == nil, "component returns to system keyboard")
        print("PASS \(checks) approved grid/native host/ownership checks; UIKit animation requires iPhone")
    }
}
