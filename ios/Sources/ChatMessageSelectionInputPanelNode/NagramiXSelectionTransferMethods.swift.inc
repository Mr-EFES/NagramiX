    private func nagramiXSelectedMessagesSignal(context: AccountContext, ids: Set<EngineMessage.Id>) -> Signal<[EngineRawMessage], NoError> {
        let messageIds = ids.sorted()
        return context.engine.data.get(EngineDataMap(
            messageIds.map(TelegramEngine.EngineData.Item.Messages.Message.init)
        ))
        |> deliverOnMainQueue
        |> map { messages in
            return messageIds.compactMap { id -> EngineRawMessage? in
                return (messages[id] ?? nil)?._asMessage() ?? context.account.nagramiXMessageArchive.deletedMessage(id: id)
            }
        }
    }

    @objc private func forwardWithoutSourceButtonPressed() {
        guard NagramiXTabSettings.current.showForwardWithoutAuthor else {
            return
        }
        self.nagramiXPerformSelectionTransfer(button: self.forwardWithoutSourceButton, action: self.interfaceInteraction?.forwardMessagesWithoutSource)
    }

    @objc private func broadcastButtonPressed() {
        guard NagramiXTabSettings.current.showBroadcastMessages else {
            return
        }
        self.nagramiXPerformSelectionTransfer(button: self.broadcastButton, action: self.interfaceInteraction?.copyMessagesWithoutSource)
    }

    private func nagramiXPerformSelectionTransfer(button: GlassButtonView, action: (([EngineRawMessage]) -> Void)?) {
        guard let context = self.context, let action, !self.selectedMessages.isEmpty else {
            return
        }
        if self.presentationInterfaceState?.renderedPeer?.peer is TelegramSecretChat {
            return
        }
        if let actions = self.actions, actions.isCopyProtected {
            self.interfaceInteraction?.displayCopyProtectionTip(button, false)
            return
        }
        guard !button.isImplicitlyDisabled else {
            return
        }

        // Resolve fresh messages at the tap; never send a cached/deleted subset.
        let selectedIds = self.selectedMessages
        self.nagramiXTransferDisposable.set((self.nagramiXSelectedMessagesSignal(context: context, ids: selectedIds)
        |> deliverOnMainQueue).startStrict(next: { [weak self, weak button] messages in
            guard let self, let button, self.selectedMessages == selectedIds,
                messages.count == selectedIds.count,
                self.interfaceInteraction?.canCopyMessagesWithoutSource?(messages) == true else {
                return
            }
            if button === self.forwardWithoutSourceButton {
                guard NagramiXTabSettings.current.showForwardWithoutAuthor else { return }
            } else {
                guard NagramiXTabSettings.current.showBroadcastMessages else { return }
            }
            action(messages)
        }))
    }
