    func nagramiXUpdateMessageReactions(message: Message, reactions: [UpdateMessageReaction], isLarge: Bool, storeAsRecentlyUsed: Bool) {
        if self.nagramiXReadHistoryDisabled {
            self.context.account.nagramiXMessageArchive.deferredReactions.stage(
                message: message, threadId: self.chatLocation.threadId,
                sendAsPeerId: self.presentationInterfaceState.currentSendAsPeerId,
                reactions: reactions,
                maxCount: self.presentationInterfaceState.isPremium ? Int(self.context.userLimits.maxReactionsPerMessage) : 1,
                isLarge: isLarge, storeAsRecentlyUsed: storeAsRecentlyUsed
            )
        } else {
            self.context.account.nagramiXMessageArchive.deferredReactions.discard(messageId: message.id)
            let _ = updateMessageReactionsInteractively(account: self.context.account, messageIds: [message.id], reactions: reactions, isLarge: isLarge, storeAsRecentlyUsed: storeAsRecentlyUsed).startStandalone()
        }
    }

    func nagramiXFlushDeferredReactionsIfActive() {
        guard !self.nagramiXReadHistoryDisabled, self.nagramiXVisibleForDeferredReactions,
              !self.isUpdatingChatLocationThread,
              self.canReadHistoryValue, self.effectiveNavigationController?.topViewController === self,
              case .standard(.default) = self.presentationInterfaceState.mode,
              let peerId = self.chatLocation.peerId else { return }
        if let subject = self.subject {
            if case .message = subject { } else { return }
        }
        self.context.account.nagramiXMessageArchive.deferredReactions.flush(
            account: self.context.account, peerId: peerId, threadId: self.chatLocation.threadId
        )
    }

    func nagramiXExplainPreviewPaidReactions() {
        self.present(UndoOverlayController(presentationData: self.presentationData,
            content: .info(title: nil, text: self.presentationData.strings.nagramiXPreviewPaidReactions,
                timeout: nil, customUndoText: nil), action: { _ in return false }), in: .window(.root))
    }
