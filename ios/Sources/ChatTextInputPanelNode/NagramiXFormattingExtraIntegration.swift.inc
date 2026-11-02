    private func nagramiXExtraFormattingAvailable(_ action: NagramiXFormattingKeyboard.ExtraAction) -> Bool {
        guard self.nagramiXFormattingActive, let state = self.presentationInterfaceState,
              self.nagramiXFormattingWidth(state) > 0, let node = self.richTextInputNode else { return false }
        switch action {
        case .selectAll: return !node.inputContentIsEmpty
        case .pullQuote:
            return node.usesNativeRichTextEngine && self.nagramiXFormattingSelection().valid
                && state.chatLocation.peerId?.namespace != Namespaces.Peer.SecretChat
        }
    }

    private func nagramiXApplyExtraFormatting(_ action: NagramiXFormattingKeyboard.ExtraAction) {
        guard self.nagramiXExtraFormattingAvailable(action), let node = self.richTextInputNode else { return }
        switch action {
        case .pullQuote: node.performFormatAction(.pullQuote)
        case .selectAll: node.nagramiXSelectAll()
        }
        self.nagramiXUpdateFormatting()
    }
