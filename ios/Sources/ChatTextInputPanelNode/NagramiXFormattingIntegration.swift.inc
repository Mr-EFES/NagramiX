    private func nagramiXFormattingWidth(_ state: ChatPresentationInterfaceState) -> CGFloat {
        guard NagramiXFormattingSettings.enabled, !self.sendingTextDisabled, !self.extendedSearchLayout,
              state.inputTextPanelState.mediaRecordingState == nil,
              state.interfaceState.mediaDraftState == nil else { return 0 }
        return 36
    }

    // ChatControllerNode owns keyboard replacement. Consult this at its normal
    // input-view assignment so later layouts cannot replace our panel with nil.
    public func nagramiXFormattingInputView(for state: ChatPresentationInterfaceState) -> UIView? {
        guard self.nagramiXFormattingActive else { return nil }
        guard self.nagramiXFormattingWidth(state) > 0, case .text = state.inputMode else {
            self.nagramiXFormattingActive = false
            self.nagramiXUpdateFormatting()
            return nil
        }
        return self.nagramiXFormattingKeyboard
    }

    private func nagramiXInstallFormatting() {
        self.nagramiXFormattingButton.addTarget(self, action: #selector(self.nagramiXToggleFormatting), for: .touchUpInside)
        self.nagramiXFormattingButton.isHidden = true
        self.textInputContainerBackgroundView.contentView.addSubview(self.nagramiXFormattingButton)
        self.nagramiXFormattingObserver = NotificationCenter.default.addObserver(
            forName: NagramiXFormattingSettings.changedNotification, object: nil, queue: .main
        ) { [weak self] _ in
            guard let self else { return }
            if !NagramiXFormattingSettings.enabled { self.nagramiXCloseFormatting(reload: true) }
            self.requestLayout(transition: .immediate)
        }
    }

    private func nagramiXCloseFormatting(reload: Bool) {
        self.nagramiXFormattingActive = false
        if let keyboard = self.nagramiXFormattingKeyboard, let node = self.richTextInputNode,
           node.keyboardInputView === keyboard {
            node.keyboardInputView = nil
            if reload && node.isInputFirstResponder { node.reloadInputViews() }
        }
        self.nagramiXUpdateFormatting()
    }

    @objc private func nagramiXToggleFormatting() {
        guard let state = self.presentationInterfaceState, self.nagramiXFormattingWidth(state) > 0 else { return }
        self.loadTextInputNodeIfNeeded()
        guard let node = self.richTextInputNode else { return }
        if self.nagramiXFormattingActive {
            self.nagramiXCloseFormatting(reload: true)
            self.ensureFocused()
            return
        }
        if self.nagramiXFormattingKeyboard == nil {
            let keyboard = NagramiXFormattingKeyboard(title: state.strings.TextFormat_Format)
            keyboard.action = { [weak self] action in self?.nagramiXApplyFormatting(action) }
            self.nagramiXFormattingKeyboard = keyboard
        }
        // Publish text mode first: switching away from stickers/bot keyboards
        // runs the same host transition as the native keyboard accessory.
        self.interfaceInteraction?.updateInputModeAndDismissedButtonKeyboardMessageId { state in
            return (.text, state.keyboardButtonsMessage?.id)
        }
        self.nagramiXFormattingActive = true
        node.keyboardInputView = self.nagramiXFormattingKeyboard
        self.nagramiXUpdateFormatting()
        if node.isInputFirstResponder { node.reloadInputViews() }
        else { node.makeInputFirstResponder() }
        self.requestLayout(transition: .immediate)
    }

    private func nagramiXFormattingSelection() -> NagramiXFormattingSelection {
        return NagramiXFormattingSelection(text: self.richTextInputNode?.attributedText ?? NSAttributedString(string: ""),
                                          range: self.richTextInputNode?.selectedRange ?? NSRange(location: 0, length: 0))
    }

    private func nagramiXFormattingAvailable(_ action: NagramiXFormattingAction, selection: NagramiXFormattingSelection) -> Bool {
        return action.isAvailable(selection: selection.range, textLength: selection.text.length,
            secret: self.presentationInterfaceState?.chatLocation.peerId?.namespace == Namespaces.Peer.SecretChat,
            native: self.richTextInputNode?.usesNativeRichTextEngine == true,
            containsSpoiler: selection.contains(ChatTextInputAttributes.spoiler),
            containsMonospace: selection.contains(ChatTextInputAttributes.monospace))
    }

    private func nagramiXFormattingSelected(_ action: NagramiXFormattingAction, selection: NagramiXFormattingSelection) -> Bool {
        switch action {
        case .bold: return selection.covers(ChatTextInputAttributes.bold)
        case .italic: return selection.covers(ChatTextInputAttributes.italic)
        case .monospace: return selection.covers(ChatTextInputAttributes.monospace)
        case .strikethrough: return selection.covers(ChatTextInputAttributes.strikethrough)
        case .underline: return selection.covers(ChatTextInputAttributes.underline)
        case .spoiler: return selection.covers(ChatTextInputAttributes.spoiler)
        case .link: return selection.covers(ChatTextInputAttributes.textUrl)
        case .quote, .code:
            return selection.covers(ChatTextInputAttributes.block) { value in
                guard let value = value as? ChatTextInputTextQuoteAttribute else { return false }
                switch value.kind {
                case .quote: return action == .quote
                case .code: return action == .code
                }
            }
        case .date: return selection.covers(ChatTextInputAttributes.date)
        }
    }

    private func nagramiXUpdateFormatting() {
        guard let state = self.presentationInterfaceState else { return }
        self.nagramiXFormattingButton.tintColor = state.theme.chat.inputPanel.panelControlColor
        self.nagramiXFormattingButton.setImage(UIImage(systemName: self.nagramiXFormattingActive ? "keyboard" : "textformat",
            withConfiguration: UIImage.SymbolConfiguration(pointSize: 21, weight: .regular)), for: .normal)
        self.nagramiXFormattingButton.accessibilityLabel = self.nagramiXFormattingActive ? state.strings.nagramiXFormattingKeyboard : state.strings.nagramiXQuickFormatting
        self.nagramiXFormattingButton.accessibilityTraits = .button
        guard self.nagramiXFormattingActive, let keyboard = self.nagramiXFormattingKeyboard else { return }
        let selection = self.nagramiXFormattingSelection()
        let strings = state.strings
        let labels: [(NagramiXFormattingAction, String, String)] = [
            (.quote, strings.TextFormat_Quote, "text.quote"), (.spoiler, strings.TextFormat_Spoiler, "eye.slash"),
            (.bold, strings.TextFormat_Bold, "bold"), (.italic, strings.TextFormat_Italic, "italic"),
            (.monospace, strings.TextFormat_Monospace, "textformat.abc"), (.link, strings.TextFormat_Link, "link"),
            (.date, strings.TextFormat_Date, "calendar"), (.strikethrough, strings.TextFormat_Strikethrough, "strikethrough"),
            (.underline, strings.TextFormat_Underline, "underline"), (.code, strings.TextFormat_Code, "chevron.left.forwardslash.chevron.right")
        ]
        keyboard.update(title: strings.TextFormat_Format, items: labels.map { action, title, symbol in
            return NagramiXFormattingKeyboard.Item(action: action, title: title, symbol: symbol,
                enabled: self.nagramiXFormattingAvailable(action, selection: selection),
                selected: self.nagramiXFormattingSelected(action, selection: selection))
        }, background: state.theme.list.blocksBackgroundColor, foreground: state.theme.list.itemPrimaryTextColor,
           accent: state.theme.list.itemAccentColor)
    }

    private func nagramiXApplyFormatting(_ action: NagramiXFormattingAction) {
        guard self.nagramiXFormattingActive, let state = self.presentationInterfaceState,
              self.nagramiXFormattingWidth(state) > 0, let node = self.richTextInputNode,
              self.nagramiXFormattingAvailable(action, selection: self.nagramiXFormattingSelection()) else { return }
        if action == .link || action == .date {
            // Native dialogs own focus restoration and, for rich content, the
            // structural selection. Never serialize it through the flat editor.
            self.nagramiXCloseFormatting(reload: true)
            if action == .link { self.formatAttributesLink(self) }
            else { self.formatAttributesDate(self) }
        } else if node.usesNativeRichTextEngine {
            switch action {
            case .quote: node.performFormatAction(.quote)
            case .spoiler: node.performFormatAction(.spoiler)
            case .bold: node.performFormatAction(.bold)
            case .italic: node.performFormatAction(.italic)
            case .monospace: node.performFormatAction(.monospace)
            case .strikethrough: node.performFormatAction(.strikethrough)
            case .underline: node.performFormatAction(.underline)
            case .code: node.performFormatAction(.code)
            case .link, .date: break
            }
        } else {
            switch action {
            case .quote: self.formatAttributesQuote(self)
            case .spoiler: self.formatAttributesSpoiler(self)
            case .bold: self.formatAttributesBold(self)
            case .italic: self.formatAttributesItalic(self)
            case .monospace: self.formatAttributesMonospace(self)
            case .strikethrough: self.formatAttributesStrikethrough(self)
            case .underline: self.formatAttributesUnderline(self)
            case .code: self.formatAttributesCodeBlock(self)
            case .link, .date: break
            }
        }
        self.nagramiXUpdateFormatting()
    }
