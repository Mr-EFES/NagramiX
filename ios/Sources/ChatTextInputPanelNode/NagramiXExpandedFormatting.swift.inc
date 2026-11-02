        private var nagramiXFormattingActive = false
        private var nagramiXFormattingPanel: NagramiXFormattingKeyboard?
        private var nagramiXFormattingInputView: UIView?
        private var nagramiXFormattingObserver: NSObjectProtocol?
        private var nagramiXFormattingGeneration = 0

        private func nagramiXSetFormattingMode(_ active: Bool, restoringKeyboard: Bool = true, notifyLayout: Bool = true) {
            guard active != self.nagramiXFormattingActive else { return }
            guard !active || NagramiXFormattingSettings.enabled else { return }
            self.nagramiXFormattingActive = active
            self.nagramiXFormattingGeneration += 1
            if active {
                // Keep a custom input view throughout emoji → formatting.
                self.emojiKeyboard?.setEmojiMode(false, preserveInputView: true, notifyLayout: false)
                let placeholder = EmptyInputView()
                self.nagramiXFormattingInputView = placeholder
                self.editor.customInputView = placeholder
                _ = self.editor.becomeFirstResponder()
            } else {
                if restoringKeyboard, let owned = self.nagramiXFormattingInputView, self.editor.customInputView === owned {
                    self.editor.customInputView = nil
                }
                self.nagramiXFormattingInputView = nil
            }
            if notifyLayout { self.componentState?.updated(transition: .spring(duration: 0.4)) }
        }

        private func nagramiXToggleFormatting() {
            self.nagramiXSetFormattingMode(!self.nagramiXFormattingActive)
        }

        private func nagramiXToggleEmoji() {
            if self.nagramiXFormattingActive {
                self.nagramiXSetFormattingMode(false, restoringKeyboard: false, notifyLayout: false)
            }
            self.emojiKeyboard?.toggle()
        }

        private func nagramiXExpandedHasContent() -> Bool {
            let blocks = self.editor.document.blocks
            guard blocks.count <= 1 else { return true }
            guard let block = blocks.first else { return false }
            switch block {
            case let .paragraph(value): return !value.text.isEmpty
            case let .code(value): return !value.text.isEmpty
            case let .pullQuote(value): return !value.text.isEmpty
            case .media, .table, .blockQuote, .details, .buttonRow: return true
            }
        }

        private func nagramiXExpandedFormattingAvailable(_ action: NagramiXFormattingAction) -> Bool {
            guard self.nagramiXFormattingActive, NagramiXFormattingSettings.enabled else { return false }
            let state = self.editor.currentState()
            guard state.hasSelection, action != .date else { return false }
            if action == .spoiler && state.code { return false }
            if action == .monospace && state.spoiler { return false }
            return true
        }

        private func nagramiXApplyExpandedFormatting(_ action: NagramiXFormattingAction) {
            guard self.nagramiXExpandedFormattingAvailable(action) else { return }
            switch action {
            case .quote: self.editor.wrapInBlockQuote()
            case .spoiler: self.editor.toggleSpoiler()
            case .bold: self.editor.toggleBold()
            case .italic: self.editor.toggleItalic()
            case .monospace: self.editor.toggleInlineCode()
            case .link:
                self.nagramiXSetFormattingMode(false)
                self.presentLinkPrompt()
            case .date: break
            case .strikethrough: self.editor.toggleStrikethrough()
            case .underline: self.editor.toggleUnderline()
            case .code: self.editor.makeCodeBlock()
            }
        }

        private func nagramiXApplyExpandedExtra(_ action: NagramiXFormattingKeyboard.ExtraAction) {
            guard self.nagramiXFormattingActive, NagramiXFormattingSettings.enabled else { return }
            switch action {
            case .pullQuote:
                guard self.editor.currentState().hasSelection else { return }
                self.editor.makePullQuote()
            case .selectAll:
                guard self.nagramiXExpandedHasContent() else { return }
                self.editor.selectAll()
            }
        }

        private func nagramiXUpdateFormattingPanel(availableSize: CGSize, height: CGFloat, environment: ViewControllerComponentContainer.Environment, transition: ComponentTransition) {
            guard self.nagramiXFormattingActive, NagramiXFormattingSettings.enabled, height > 0 else {
                if let panel = self.nagramiXFormattingPanel, !panel.isHidden {
                    let generation = self.nagramiXFormattingGeneration
                    let frame = CGRect(origin: CGPoint(x: 0, y: availableSize.height), size: panel.bounds.size)
                    transition.setFrame(view: panel, frame: frame, completion: { [weak self, weak panel] _ in
                        if self?.nagramiXFormattingGeneration == generation, self?.nagramiXFormattingActive != true { panel?.isHidden = true }
                    })
                }
                return
            }
            let strings = environment.strings
            let panel: NagramiXFormattingKeyboard
            if let current = self.nagramiXFormattingPanel {
                panel = current
            } else {
                panel = NagramiXFormattingKeyboard(title: strings.nagramiXFormattingPanelTitle, height: height)
                panel.layer.cornerRadius = 30.0
                panel.layer.cornerCurve = .continuous
                panel.layer.maskedCorners = [.layerMinXMinYCorner, .layerMaxXMinYCorner]
                panel.clipsToBounds = true
                panel.action = { [weak self] in self?.nagramiXApplyExpandedFormatting($0) }
                panel.extraAction = { [weak self] in self?.nagramiXApplyExpandedExtra($0) }
                panel.frame = CGRect(x: 0, y: availableSize.height, width: availableSize.width, height: height)
                self.nagramiXFormattingPanel = panel
                self.addSubview(panel)
            }
            let state = self.editor.currentState()
            let labels: [(NagramiXFormattingAction, String, String, String, Bool)] = [
                (.quote, strings.TextFormat_Quote, strings.TextFormat_Quote, "text.quote", state.blockQuoteDepth > 0),
                (.spoiler, strings.nagramiXFormattingSpoilerShort, strings.TextFormat_Spoiler, "eye.slash", state.spoiler),
                (.bold, strings.TextFormat_Bold, strings.TextFormat_Bold, "bold", state.bold),
                (.italic, strings.TextFormat_Italic, strings.TextFormat_Italic, "italic", state.italic),
                (.monospace, strings.nagramiXFormattingMonospaceShort, strings.TextFormat_Monospace, "textformat.abc", state.code),
                (.link, strings.TextFormat_Link, strings.TextFormat_Link, "link", state.link != nil),
                (.date, strings.TextFormat_Date, strings.TextFormat_Date, "calendar", false),
                (.strikethrough, strings.nagramiXFormattingStrikethroughShort, strings.TextFormat_Strikethrough, "strikethrough", state.strikethrough),
                (.underline, strings.nagramiXFormattingUnderlineShort, strings.TextFormat_Underline, "underline", state.underline),
                (.code, strings.TextFormat_Code, strings.TextFormat_Code, "chevron.left.forwardslash.chevron.right", state.isCodeBlock)
            ]
            panel.updateHeight(height)
            let accent = environment.theme.chat.inputPanel.panelControlAccentColor
            panel.update(title: strings.nagramiXFormattingPanelTitle, items: labels.map { action, title, full, symbol, selected in
                NagramiXFormattingKeyboard.Item(action: action, title: title, accessibilityTitle: full, symbol: symbol,
                    enabled: self.nagramiXExpandedFormattingAvailable(action), selected: selected)
            }, appearance: environment.theme.rootController.keyboardColor.keyboardAppearance, accent: accent)
            panel.updateExtras([
                .init(action: .pullQuote, title: strings.RichText_MenuPullquote, enabled: state.hasSelection, selected: state.isPullQuote),
                .init(action: .selectAll, title: strings.nagramiXFormattingSelectAll, enabled: self.nagramiXExpandedHasContent(), selected: false)
            ], accent: accent)
            if panel.isHidden {
                ComponentTransition.immediate.setFrame(view: panel, frame: CGRect(x: 0, y: availableSize.height, width: availableSize.width, height: height))
            }
            panel.isHidden = false
            transition.setFrame(view: panel, frame: CGRect(x: 0, y: availableSize.height - height, width: availableSize.width, height: height))
        }
