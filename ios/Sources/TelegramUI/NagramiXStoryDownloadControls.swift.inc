        private var nagramiXCanDownloadStory: Bool {
            guard NagramiXStoryDownloadSettings.enabled, let component = self.component else { return false }
            let item = component.slice.item.storyItem
            guard !item.isForwardingDisabled || component.slice.effectivePeer.id == component.context.account.peerId else { return false }
            switch item.media {
            case let .image(image): return !image.representations.isEmpty
            case let .file(file): return file.isVideo || file.mimeType.hasPrefix("video/")
            default: return false
            }
        }

        @objc private func nagramiXDownloadStoryPressed() {
            guard self.nagramiXCanDownloadStory, !self.nagramiXStorySaveActive,
                  let component = self.component, let peer = PeerReference(component.slice.effectivePeer),
                  let controller = component.controller() else { return }
            // Snapshot the selected story before any permission or fetch callback.
            let reference: AnyMediaReference = .story(peer: peer, id: component.slice.item.storyItem.id, media: component.slice.item.storyItem.media._asMedia())
            self.nagramiXStorySaveActive = true
            self.state?.updated(transition: .immediate)
            let progress = SaveProgressScreen(context: component.context, content: .progress(component.strings.Story_TooltipSaving, 0.0))
            self.nagramiXStorySaveProgress = progress
            controller.present(progress, in: .current)
            let savingText = component.strings.Story_TooltipSaving
            let savedText = component.strings.Story_TooltipSaved
            self.nagramiXStorySaveDisposable.set((nagramiXSaveStoryToCameraRoll(context: component.context, userLocation: .peer(peer.id), mediaReference: reference)
            |> deliverOnMainQueue).start(next: { [weak progress] value in
                progress?.content = .progress(savingText, value)
            }, error: { [weak self, weak progress] error in
                progress?.dismiss()
                guard let self else { return }
                self.nagramiXStorySaveActive = false
                self.state?.updated(transition: .immediate)
                // DeviceAccess already explains a denied Photos permission.
                guard error != .permissionDenied, let current = self.component else { return }
                let data = current.context.sharedContext.currentPresentationData.with { $0 }
                let notice = UndoOverlayController(presentationData: data,
                    content: .info(title: nil, text: current.strings.nagramiXStorySaveFailed, timeout: nil, customUndoText: nil),
                    elevatedLayout: false, animateInAsReplacement: false, appearance: UndoOverlayController.Appearance(isBlurred: true), action: { _ in false })
                current.presentController(notice, nil)
            }, completed: { [weak self, weak progress] in
                self?.nagramiXStorySaveActive = false
                self?.state?.updated(transition: .immediate)
                progress?.content = .completion(savedText)
                Queue.mainQueue().after(3.0, { [weak progress] in progress?.dismiss() })
            }))
            progress.cancelled = { [weak self] in
                self?.nagramiXStorySaveDisposable.set(nil)
                self?.nagramiXStorySaveActive = false
                self?.state?.updated(transition: .immediate)
            }
        }
