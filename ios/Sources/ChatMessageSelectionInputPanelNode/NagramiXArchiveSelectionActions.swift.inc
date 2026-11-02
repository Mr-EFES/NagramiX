    private func updateActions() {
        self.nagramiXSelectionGeneration &+= 1
        let generation = self.nagramiXSelectionGeneration
        self.actions = nil
        self.forwardButton.isEnabled = !self.selectedMessages.isEmpty
        self.forwardButton.isImplicitlyDisabled = true
        self.shareButton.isImplicitlyDisabled = true
        self.nagramiXCanCopySelection = false
        self.forwardWithoutSourceButton.isImplicitlyDisabled = true
        self.broadcastButton.isImplicitlyDisabled = true
        self.nagramiXTransferDisposable.set(nil)
        self.canDeleteMessagesDisposable.set(nil)
        guard let context = self.context, !self.selectedMessages.isEmpty else {
            if let (width, leftInset, rightInset, bottomInset, additionalSideInsets, maxHeight, maxOverlayHeight, metrics, isSecondary, isMediaInputExpanded, deviceMetrics) = self.validLayout, let interfaceState = self.presentationInterfaceState {
                let _ = self.updateLayout(width: width, leftInset: leftInset, rightInset: rightInset, bottomInset: bottomInset, additionalSideInsets: additionalSideInsets, maxHeight: maxHeight, maxOverlayHeight: maxOverlayHeight, isSecondary: isSecondary, transition: .immediate, interfaceState: interfaceState, metrics: metrics, deviceMetrics: deviceMetrics, isMediaInputExpanded: isMediaInputExpanded)
            }
            return
        }
        let selectedIds = self.selectedMessages
        self.canDeleteMessagesDisposable.set((combineLatest(
            context.sharedContext.chatAvailableMessageActions(engine: context.engine, accountPeerId: context.account.peerId, messageIds: selectedIds, keepUpdated: true),
            self.nagramiXSelectedMessagesSignal(context: context, ids: selectedIds, keepUpdated: true)
        )
        |> deliverOnMainQueue
        |> mapToSignal { [weak self] nativeActions, messages -> Signal<(ChatAvailableMessageActions, Bool), NoError> in
            guard let self, messages.count == selectedIds.count else { return .single((nativeActions, false)) }
            let canCopy = self.interfaceInteraction?.canCopyMessagesWithoutSource?(messages) == true
            var messageMap: [EngineMessage.Id: EngineMessage] = [:]
            var peerMap: [EnginePeer.Id: EnginePeer] = [:]
            for message in messages {
                messageMap[message.id] = EngineMessage(message)
                for (id, peer) in message.peers { peerMap[id] = EnginePeer(peer) }
            }
            return context.sharedContext.chatAvailableMessageActions(engine: context.engine, accountPeerId: context.account.peerId, messageIds: selectedIds, messages: messageMap, peers: peerMap)
            |> map { resolvedActions in
                // Только возможности переноса берём от отображаемых snapshots.
                // Права удаления/жалоб/меток остаются от настоящего Postbox.
                var options = nativeActions.options
                options.subtract([.forward, .externalShare])
                options.formUnion(resolvedActions.options.intersection([.forward, .externalShare]))
                let actions = ChatAvailableMessageActions(options: options, banAuthor: nativeActions.banAuthor, banAuthors: nativeActions.banAuthors, disableDelete: nativeActions.disableDelete, isCopyProtected: nativeActions.isCopyProtected || resolvedActions.isCopyProtected, setTag: nativeActions.setTag, editTags: nativeActions.editTags)
                return (actions, canCopy)
            }
        }
        |> deliverOnMainQueue).startStrict(next: { [weak self] result in
            guard let self, self.nagramiXSelectionGeneration == generation, self.selectedMessages == selectedIds else { return }
            let (actions, canCopy) = result
            self.actions = actions
            self.nagramiXCanCopySelection = canCopy
            if let (width, leftInset, rightInset, bottomInset, additionalSideInsets, maxHeight, maxOverlayHeight, metrics, isSecondary, isMediaInputExpanded, deviceMetrics) = self.validLayout, let interfaceState = self.presentationInterfaceState {
                let _ = self.updateLayout(width: width, leftInset: leftInset, rightInset: rightInset, bottomInset: bottomInset, additionalSideInsets: additionalSideInsets, maxHeight: maxHeight, maxOverlayHeight: maxOverlayHeight, isSecondary: isSecondary, transition: .immediate, interfaceState: interfaceState, metrics: metrics, deviceMetrics: deviceMetrics, isMediaInputExpanded: isMediaInputExpanded)
            }
        }))
    }
