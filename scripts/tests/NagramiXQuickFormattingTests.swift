import Foundation

final class NotificationProbe: @unchecked Sendable { var events: [Notification.Name] = [] }

@main struct QuickFormattingTests {
    static func main() {
        let defaults = UserDefaults.standard, key = "nagramix.messages.quickFormatting"
        if CommandLine.arguments.count > 1 {
            let command = CommandLine.arguments[1], value = CommandLine.arguments[2] == "true"
            if command == "fresh" { defaults.removeObject(forKey: key) }
            if command == "set" { NagramiXFormattingSettings.setEnabled(value); defaults.synchronize() }
            precondition(NagramiXFormattingSettings.enabled == value)
            if command == "fresh" { precondition(defaults.object(forKey: key) == nil) }
            print("PASS cold " + command + " " + String(value)); return
        }
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) {
            precondition(value(), label); checks += 1
        }
        defaults.removeObject(forKey: key)
        check(!NagramiXFormattingSettings.enabled, "absent is OFF")
        check(defaults.object(forKey: key) == nil, "getter is read only")
        let probe = NotificationProbe()
        let observer = NotificationCenter.default.addObserver(forName: nil, object: nil, queue: nil) { note in
            if note.name == NagramiXFormattingSettings.changedNotification || note.name == NagramiXTabSettings.changedNotification { probe.events.append(note.name) }
        }
        _ = NagramiXFormattingSettings.enabled
        check(probe.events.isEmpty, "reading does not broadcast")
        for value in [false, true, false, true] {
            NagramiXFormattingSettings.setEnabled(value)
            check(NagramiXFormattingSettings.enabled == value, "explicit preference")
        }
        check(probe.events.count == 8, "one keyboard and one settings notification per setter")
        NotificationCenter.default.removeObserver(observer)

        let text = NSMutableAttributedString(string: "А😀Б текст")
        let full = NSRange(location: 0, length: text.length), bold = ChatTextInputAttributes.bold
        let invalid = [NSRange(location: 0, length: 0), NSRange(location: NSNotFound, length: 1), NSRange(location: -1, length: 1), NSRange(location: 0, length: -1), NSRange(location: text.length, length: 1), NSRange(location: 1, length: Int.max)]
        for range in invalid {
            let selection = NagramiXFormattingSelection(text: text, range: range)
            check(!selection.valid && !selection.contains(bold) && !selection.covers(bold), "invalid selection is safe")
            for action in NagramiXFormattingAction.allCases {
                check(!action.isAvailable(selection: range, textLength: text.length, secret: false, native: false, containsSpoiler: false, containsMonospace: false), "invalid action disabled")
            }
        }
        let emoji = NagramiXFormattingSelection(text: text, range: NSRange(location: 1, length: 2))
        check(emoji.valid, "UTF16 emoji selection")
        text.addAttribute(bold, value: true, range: NSRange(location: 0, length: 3))
        let mixed = NagramiXFormattingSelection(text: text, range: full)
        check(mixed.contains(bold) && !mixed.covers(bold), "mixed range is not active")
        check(emoji.covers(bold), "UTF16 coverage")
        text.addAttribute(bold, value: true, range: full)
        text.addAttribute(ChatTextInputAttributes.italic, value: true, range: full)
        check(mixed.covers(bold) && mixed.covers(ChatTextInputAttributes.italic), "combined formats remain active")
        for native in [false, true] {
            for secret in [false, true] {
                for spoiler in [false, true] {
                    for mono in [false, true] {
                        for action in NagramiXFormattingAction.allCases {
                            let denied = (secret && [.quote, .spoiler, .date].contains(action)) || (native && action == .date) || (spoiler && action == .monospace) || (mono && action == .spoiler)
                            check(action.isAvailable(selection: full, textLength: text.length, secret: secret, native: native, containsSpoiler: spoiler, containsMonospace: mono) == !denied, "stock capability matrix")
                        }
                    }
                }
            }
        }

        func panel(native: Bool = false) -> FormattingPanel {
            let panel = FormattingPanel(); panel.richTextInputNode!.usesNativeRichTextEngine = native
            panel.richTextInputNode!.content = NSAttributedString(string: "А😀Б текст")
            panel.richTextInputNode!.selectedRange = full
            return panel
        }
        for native in [false, true] {
            for action in NagramiXFormattingAction.allCases {
                let p = panel(native: native), node = p.richTextInputNode!
                p.nagramiXToggleFormatting()
                check(p.nagramiXFormattingActive && node.keyboardInputView === p.nagramiXFormattingKeyboard, "open custom keyboard")
                check(node.selectedRange == full && node.focuses == 0, "opening retains selection and responder")
                p.nagramiXApplyFormatting(action)
                if native && action == .date {
                    check(node.calls.isEmpty && p.legacy.isEmpty && p.nagramiXFormattingActive, "native unsupported date is disabled")
                } else if action == .link || action == .date {
                    check(p.legacy == [String(describing: action)] && node.calls.isEmpty && !p.nagramiXFormattingActive, "native dialog route")
                } else if native {
                    check(node.calls == [String(describing: action)] && p.legacy.isEmpty, "rich document command")
                } else {
                    check(p.legacy == [String(describing: action)] && node.calls.isEmpty, "stock legacy command")
                }
                check(node.selectedRange == full && node.content.string == "А😀Б текст", "routing does not flatten or replace text")
            }
        }
        // User video: open without selection, style separate words, clear the
        // composer after send, keep the panel, then return to the keyboard.
        // Native formatting/Send is represented by its resulting editor state;
        // the panel never implements those transformations or sends messages.
        for native in [false, true] {
            let p = panel(native: native), node = p.richTextInputNode!
            let text = NSMutableAttributedString(string: "Пример работы быстрого форматирования")
            let first = (text.string as NSString).range(of: "Пример")
            let second = (text.string as NSString).range(of: "быстрого")
            node.content = text
            node.selectedRange = NSRange(location: text.length, length: 0)
            p.nagramiXToggleFormatting()
            let keyboard = p.nagramiXFormattingKeyboard
            check(p.nagramiXFormattingActive && node.keyboardInputView === keyboard, "video: opening keeps the custom panel")
            check(NagramiXFormattingAction.allCases.allSatisfy { !p.nagramiXFormattingAvailable($0, selection: p.nagramiXFormattingSelection()) }, "video: no selection disables every action")
            node.selectedRange = first
            p.nagramiXApplyFormatting(.bold)
            check(native ? node.calls == ["bold"] : p.legacy == ["bold"], "video: bold routes to the current backend")
            text.addAttribute(bold, value: true, range: first)
            check(p.nagramiXFormattingSelected(.bold, selection: p.nagramiXFormattingSelection()), "video: first selected word highlights bold")
            node.selectedRange = second
            check(!p.nagramiXFormattingSelected(.bold, selection: p.nagramiXFormattingSelection()), "video: moving selection removes old highlight")
            p.nagramiXApplyFormatting(.italic)
            check(native ? node.calls == ["bold", "italic"] : p.legacy == ["bold", "italic"], "video: italic routes using the new selection")
            text.addAttribute(ChatTextInputAttributes.italic, value: true, range: second)
            check(p.nagramiXFormattingSelected(.italic, selection: p.nagramiXFormattingSelection()), "video: second selected word highlights italic")
            check(NagramiXFormattingSelection(text: text, range: first).covers(bold), "video: first word retains independent formatting")
            check(p.nagramiXFormattingActive && node.keyboardInputView === keyboard, "video: formatting leaves the same panel open")
            node.content = NSAttributedString(string: "")
            node.selectedRange = NSRange(location: 0, length: 0)
            check(NagramiXFormattingAction.allCases.allSatisfy { !p.nagramiXFormattingAvailable($0, selection: p.nagramiXFormattingSelection()) }, "video: clearing after send disables all actions")
            check(NagramiXFormattingAction.allCases.allSatisfy { !p.nagramiXFormattingSelected($0, selection: p.nagramiXFormattingSelection()) }, "video: clearing removes every old format highlight")
            let calls = node.calls, legacy = p.legacy
            p.nagramiXApplyFormatting(.bold)
            check(node.calls == calls && p.legacy == legacy, "video: stale tile cannot format an empty composer")
            check(p.nagramiXFormattingInputView(for: p.presentationInterfaceState!) === keyboard, "video: panel remains open after clearing the composer")
            p.nagramiXToggleFormatting()
            check(!p.nagramiXFormattingActive && node.keyboardInputView == nil && node.isInputFirstResponder, "video: keyboard returns with editor focused")
        }
        let p = panel(), node = p.richTextInputNode!
        p.nagramiXToggleFormatting()
        node.selectedRange = NSRange(location: 0, length: 0)
        p.nagramiXApplyFormatting(.bold)
        check(p.legacy.isEmpty, "live empty selection blocks stale tile")
        node.selectedRange = full
        p.nagramiXApplyFormatting(.bold); p.nagramiXApplyFormatting(.italic)
        check(p.legacy == ["bold", "italic"] && p.nagramiXFormattingActive, "combining keeps keyboard open")
        p.nagramiXToggleFormatting()
        check(!p.nagramiXFormattingActive && node.keyboardInputView == nil && node.selectedRange == full, "keyboard toggle retains selection")
        p.nagramiXToggleFormatting()
        let foreign = UIView(); node.keyboardInputView = foreign
        p.nagramiXCloseFormatting(reload: true)
        check(node.keyboardInputView === foreign, "close cannot clobber another custom keyboard")
        p.presentationInterfaceState!.inputMode = .media
        p.nagramiXToggleFormatting()
        check(p.presentationInterfaceState!.inputMode == .text && p.nagramiXFormattingActive, "switch from stickers through native host")
        check(p.nagramiXFormattingInputView(for: p.presentationInterfaceState!) === p.nagramiXFormattingKeyboard, "host preserves keyboard on layout")
        p.presentationInterfaceState!.inputMode = .media
        let oldView = node.keyboardInputView
        check(p.nagramiXFormattingInputView(for: p.presentationInterfaceState!) == nil && !p.nagramiXFormattingActive, "host restores native media mode")
        check(node.keyboardInputView === oldView, "central host still detects old view for reload")
        for reason in 0..<5 {
            let p = panel(); p.nagramiXToggleFormatting()
            switch reason {
            case 0: p.sendingTextDisabled = true
            case 1: p.extendedSearchLayout = true
            case 2: p.presentationInterfaceState!.inputTextPanelState.mediaRecordingState = 1
            case 3: p.presentationInterfaceState!.interfaceState.mediaDraftState = 1
            default: NagramiXFormattingSettings.setEnabled(false)
            }
            p.nagramiXApplyFormatting(.bold)
            check(p.legacy.isEmpty, "unavailable composer cannot format")
            check(p.nagramiXFormattingWidth(p.presentationInterfaceState!) == 0, "unavailable button reserves no width")
            check(p.nagramiXFormattingInputView(for: p.presentationInterfaceState!) == nil, "invalidated keyboard released through host")
            NagramiXFormattingSettings.setEnabled(true)
        }
        let q = panel(), content = NSMutableAttributedString(string: node.content.string)
        content.addAttribute(ChatTextInputAttributes.block, value: ChatTextInputTextQuoteAttribute(.quote), range: full)
        content.addAttribute(bold, value: true, range: full)
        content.addAttribute(ChatTextInputAttributes.italic, value: true, range: full)
        q.richTextInputNode!.content = content
        let selection = q.nagramiXFormattingSelection()
        check(q.nagramiXFormattingSelected(.quote, selection: selection) && q.nagramiXFormattingSelected(.bold, selection: selection) && q.nagramiXFormattingSelected(.italic, selection: selection), "quote bold italic highlight together")
        check(!q.nagramiXFormattingSelected(.code, selection: selection), "quote is not code")
        content.addAttribute(ChatTextInputAttributes.block, value: ChatTextInputTextQuoteAttribute(.code(language: "swift")), range: full)
        check(q.nagramiXFormattingSelected(.code, selection: q.nagramiXFormattingSelection()), "code block highlight")
        defaults.removeObject(forKey: key)
        print("PASS \(checks) проверок быстрого форматирования")
    }
}
