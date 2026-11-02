import Foundation

@main struct ExpandedFormattingTests {
    static func main() {
        FormattingVisualTests.main()
        if CommandLine.arguments.count > 1 { return }
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) { precondition(value(), label); checks += 1 }
        NagramiXFormattingSettings.setEnabled(true)
        let panel = FormattingPanel(), node = panel.richTextInputNode!
        panel.nagramiXToggleFormatting()
        node.content = NSAttributedString(string: "А😀Б")
        node.selectedRange = NSRange(location: 0, length: 0)
        check(panel.nagramiXExtraFormattingAvailable(.selectAll), "select all works before selection")
        panel.nagramiXApplyExtraFormatting(.selectAll)
        check(node.selectedRange == NSRange(location: 0, length: 4), "legacy native UTF16 selection includes emoji")
        check(node.content.string == "А😀Б", "select all does not rewrite text")
        check(!panel.nagramiXExtraFormattingAvailable(.pullQuote), "legacy backend cannot represent pull quotes")
        node.usesNativeRichTextEngine = true
        node.nativeSelection.editorView.canvas.documentSizeValue = 99
        node.nativeSelection.editorView.document.blocks = [.table, .media]
        panel.nagramiXApplyExtraFormatting(.selectAll)
        check(node.nativeSelection.editorView.canvas.selected?.1 == 99, "native select all uses structural end, not flattened UTF16 length")
        check(node.nativeSelection.editorView.document.blocks.count == 2, "table/media document remains intact")
        check(panel.nagramiXExtraFormattingAvailable(.pullQuote), "native non-secret selection permits pull quote")
        panel.nagramiXApplyExtraFormatting(.pullQuote)
        check(node.calls.last == "pullQuote", "composer routes to native pull quote command")
        node.nativeSelection.editorView.state.isPullQuote = true
        check(node.nagramiXIsPullQuote, "selected-state reads native editor snapshot")
        panel.presentationInterfaceState?.chatLocation.peerId = .init(namespace: Namespaces.Peer.SecretChat)
        check(!panel.nagramiXExtraFormattingAvailable(.pullQuote), "stock secret-chat restriction preserved")
        let count = node.calls.count
        panel.nagramiXApplyExtraFormatting(.pullQuote)
        check(node.calls.count == count, "revalidate action at press")
        node.content = NSAttributedString(string: "")
        check(!panel.nagramiXExtraFormattingAvailable(.selectAll), "empty input does not select")
        panel.nagramiXCloseFormatting(reload: true)
        check(!panel.nagramiXExtraFormattingAvailable(.selectAll), "closed panel has no action")

        let host = ExpandedFormattingHost()
        host.editor.document.blocks = [.paragraph(TextBlock(text: "текст")), .table, .media]
        host.editor.canvas.documentSizeValue = 155
        host.nagramiXToggleFormatting()
        check(host.nagramiXFormattingActive && host.editor.customInputView != nil, "expanded panel owns custom keyboard placeholder")
        check(!host.nagramiXExpandedFormattingAvailable(.bold), "no selection does not format future typing")
        host.nagramiXApplyExpandedExtra(.selectAll)
        check(host.editor.canvas.selected?.0 == 0 && host.editor.canvas.selected?.1 == 155, "expanded select all uses actual structural facade")
        check(host.editor.document.blocks.count == 3, "selection preserves rich blocks")
        host.editor.state.hasSelection = true
        for action in NagramiXFormattingAction.allCases where action != .link && action != .date {
            let count = host.editor.calls.count
            host.nagramiXApplyExpandedFormatting(action)
            check(host.editor.calls.count == count + 1, "native command dispatched once")
            check(host.editor.calls.last == String(describing: action), "native format command mapping")
        }
        check(!host.nagramiXExpandedFormattingAvailable(.date), "unsupported native date remains disabled")
        host.editor.state.code = true
        check(!host.nagramiXExpandedFormattingAvailable(.spoiler), "spoiler and inline code conflict preserved")
        host.editor.state.code = false; host.editor.state.spoiler = true
        check(!host.nagramiXExpandedFormattingAvailable(.monospace), "inline code and spoiler conflict preserved")
        host.editor.state.spoiler = false
        host.nagramiXApplyExpandedExtra(.pullQuote)
        check(host.editor.calls.last == "pullQuote", "expanded pull quote is native")

        for block in [DocumentBlock.paragraph(TextBlock(text: "")), .code(TextBlock(text: "")), .pullQuote(TextBlock(text: ""))] {
            host.editor.document.blocks = [block]
            check(!host.nagramiXExpandedHasContent(), "native empty block semantics")
        }
        for block in [DocumentBlock.media, .table, .blockQuote, .details, .buttonRow, .paragraph(TextBlock(text: " "))] {
            host.editor.document.blocks = [block]
            check(host.nagramiXExpandedHasContent(), "structural or whitespace content can be selected")
        }
        host.editor.document.blocks = []
        host.editor.canvas.selected = nil
        host.nagramiXApplyExpandedExtra(.selectAll)
        check(host.editor.canvas.selected == nil, "select-all rechecks empty document at press")

        var invalidIntermediateLayouts = 0
        host.componentState?.onUpdate = {
            if host.editor.customInputView == nil || host.nagramiXFormattingActive == (host.emojiKeyboard?.isEmojiMode ?? false) { invalidIntermediateLayouts += 1 }
        }
        let initialNilWrites = host.editor.nilInputWrites
        for _ in 0 ..< 30 {
            var count = host.componentState!.updates
            host.nagramiXToggleEmoji()
            check(host.emojiKeyboard!.isEmojiMode && !host.nagramiXFormattingActive, "only emoji mode active")
            check(host.componentState!.updates == count + 1, "atomic formatting-to-emoji layout")
            count = host.componentState!.updates
            host.nagramiXToggleFormatting()
            check(host.nagramiXFormattingActive && !host.emojiKeyboard!.isEmojiMode, "only formatting mode active")
            check(host.componentState!.updates == count + 1, "atomic emoji-to-formatting layout")
        }
        check(invalidIntermediateLayouts == 0 && host.editor.nilInputWrites == initialNilWrites, "no empty keyboard/layout frame during panel handoff")
        check(host.nagramiXFormattingGeneration == 61, "generation advances on each formatting transition")
        host.componentState?.onUpdate = nil
        host.editor.state.hasSelection = true
        host.nagramiXApplyExpandedFormatting(.link)
        check(!host.nagramiXFormattingActive && host.editor.calls.last == "link", "native link prompt receives focus")
        check(host.editor.customInputView == nil, "keyboard restored before link UI")
        host.nagramiXToggleFormatting()
        let foreign = UIView(); host.editor.customInputView = foreign
        host.nagramiXSetFormattingMode(false)
        check(host.editor.customInputView === foreign, "closing cannot clear another input-view owner")
        NagramiXFormattingSettings.setEnabled(false)
        host.nagramiXToggleFormatting()
        check(!host.nagramiXFormattingActive, "default/saved OFF blocks expanded panel")

        for width in [CGFloat(288), 304, 359, 424, 760] {
            for height in [CGFloat(90), 180, 263, 350] {
                for fontWidth in [CGFloat(75), 145, 250] {
                    let grid = NagramiXFormattingGrid.layout(size: CGSize(width: width, height: height), count: 10,
                        minimumLabelWidth: 60, minimumKeyHeight: 65, accessibility: fontWidth > 145, footerMinimumLabelWidth: fontWidth)
                    check(grid.frames.count == 12, "ten styles plus two footer keys")
                    let a = grid.frames[10], b = grid.frames[11]
                    check(a.width >= fontWidth + 4 && b.width >= fontWidth + 4, "footer labels remain on one line")
                    check(a.minY >= grid.frames[9].maxY + 5.9, "extras stay below complete style grid")
                    for i in grid.frames.indices {
                        let f = grid.frames[i]
                        check(f.minX >= 0 && f.maxX <= width + 0.001 && f.height >= 60, "bounded touch target")
                        for j in grid.frames.indices where j > i { check(!f.intersects(grid.frames[j]), "keys do not overlap") }
                    }
                    check(grid.frames.allSatisfy { $0.maxY <= grid.contentSize.height + 0.001 }, "scroll range includes all controls")
                }
            }
        }
        UserDefaults.standard.removeObject(forKey: "nagramix.messages.quickFormatting")
        print("PASS \(checks) expanded formatting/footer/structural selection/mode checks")
    }
}
