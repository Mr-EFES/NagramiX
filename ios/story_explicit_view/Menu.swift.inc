        private func nagramiXRecordViewItem(_ snapshot: StoryItemSetContainerComponent) -> ContextMenuItem {
            let status = snapshot.nagramiXViewDisclosure.status(for: snapshot.nagramiXViewDisclosureKey)
            let text: String
            switch status {
            case .anonymous: text = snapshot.strings.nagramiXStoryRecordView
            case .pending: text = snapshot.strings.nagramiXStoryRecordingView
            case .recorded: text = snapshot.strings.nagramiXStoryViewRecorded
            }
            let action: ((ContextMenuActionItem.Action) -> Void)?
            if status == .anonymous {
                action = { [weak self] item in
                    item.dismissWithResult(.default)
                    self?.nagramiXRecordView(snapshot)
                }
            } else { action = nil }
            return .action(ContextMenuActionItem(text: text, textColor: status == .anonymous ? .primary : .disabled, icon: { theme in
                UIImage(systemName: status == .recorded ? "checkmark" : "eye")?.withTintColor(theme.contextMenu.primaryColor, renderingMode: .alwaysOriginal)
            }, action: action))
        }

        private func nagramiXRecordView(_ snapshot: StoryItemSetContainerComponent) {
            let target = snapshot.slice.item.id
            guard let current = self.component, current.isCentral, snapshot.isCentral,
                  !current.isDismissed, !snapshot.isDismissed,
                  current.context.account === snapshot.context.account,
                  current.nagramiXViewDisclosure === snapshot.nagramiXViewDisclosure,
                  current.slice.item.id == target, snapshot.nagramiXUsesAnonymousViewing else { return }
            // Серверный Premium Stealth Mode нельзя отключить для одной истории.
            if let timeout = current.stealthModeTimeout, timeout > 0 {
                self.nagramiXRecordViewError(snapshot, text: snapshot.strings.nagramiXStoryServerStealthActive)
                return
            }
            let disclosure = snapshot.nagramiXViewDisclosure
            let key = snapshot.nagramiXViewDisclosureKey
            guard let request = disclosure.begin(key) else { return }
            self.state?.updated(transition: .immediate)
            let _ = (snapshot.context.engine.messages.nagramiXRecordStoryView(peerId: target.peerId, id: target.id)
            |> deliverOnMainQueue).startStandalone(next: { [weak self] success in
                guard disclosure.complete(key, request: request, success: success) else { return }
                guard let self else { return }
                self.state?.updated(transition: .immediate)
                if !success, let current = self.component, current.isCentral, !current.isDismissed,
                   current.context.account === snapshot.context.account,
                   current.nagramiXViewDisclosure === disclosure, current.slice.item.id == target {
                    self.nagramiXRecordViewError(snapshot, text: snapshot.strings.nagramiXStoryRecordViewFailed)
                }
            })
        }

        private func nagramiXRecordViewError(_ snapshot: StoryItemSetContainerComponent, text: String) {
            let data = snapshot.context.sharedContext.currentPresentationData.with { $0 }.withUpdated(theme: snapshot.theme)
            snapshot.presentController(UndoOverlayController(presentationData: data,
                content: .info(title: nil, text: text, timeout: nil, customUndoText: nil),
                elevatedLayout: false, animateInAsReplacement: false, action: { _ in false }), nil)
        }
