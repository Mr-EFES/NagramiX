    private func nagramiXInstallDirectionalPiPGesture() {
        let gesture = UIPanGestureRecognizer(target: self, action: #selector(self.nagramiXDirectionalPiPPan(_:)))
        gesture.minimumNumberOfTouches = 1
        gesture.maximumNumberOfTouches = 1
        gesture.delegate = self.wrappedGestureRecognizerDelegate
        self.nagramiXDirectionalPiPGesture = gesture
        self.scrollView.addGestureRecognizer(gesture)
        self.scrollView.panGestureRecognizer.require(toFail: gesture)
        self.pager.nagramiXInstallDirectionalPiPGesture(gesture)
    }

    public func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        guard gestureRecognizer === self.nagramiXDirectionalPiPGesture else { return true }
        guard !self.isDismissed, self.nagramiXDirectionalPiPRequest == nil,
              UIApplication.shared.applicationState == .active,
              let item = self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe,
              item.view.bounds.contains(touch.location(in: item.view)) else { return false }
        // Footer/navigation controls live outside this scroll view. Preserve any
        // controls embedded in the video too, including ASButtonNode-backed views.
        var view = touch.view
        while let current = view, current !== self.scrollView {
            if current is UIControl || current.asyncdisplaykit_node is ASButtonNode {
                return false
            }
            view = current.superview
        }
        return true
    }

    public override func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard gestureRecognizer === self.nagramiXDirectionalPiPGesture else {
            return super.gestureRecognizerShouldBegin(gestureRecognizer)
        }
        guard !self.isDismissed, self.nagramiXDirectionalPiPRequest == nil,
              let gesture = gestureRecognizer as? UIPanGestureRecognizer,
              gesture.numberOfTouches == 1, UIApplication.shared.applicationState == .active,
              let item = self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe else { return false }
        let velocity = gesture.velocity(in: self.scrollView)
        return velocity.x.isFinite && velocity.y.isFinite
    }

    private func nagramiXResetDirectionalPiPSwipe(animated: Bool, cancelPreparation: Bool = true) {
        let item = self.nagramiXDirectionalPiPItem
        let transform = self.nagramiXDirectionalPiPInitialTransform
        // Clear identity before cancellation: the native failure callback can be synchronous.
        self.nagramiXDirectionalPiPRequest = nil
        self.nagramiXDirectionalPiPItem = nil
        if let item {
            let layer = item.view.layer
            let previous = layer.presentation()?.transform ?? layer.transform
            layer.removeAnimation(forKey: "nagramiX.pip.swipe.return")
            item.view.transform = transform
            if animated {
                let animation = CABasicAnimation(keyPath: "transform")
                animation.fromValue = NSValue(caTransform3D: previous)
                animation.toValue = NSValue(caTransform3D: layer.transform)
                animation.duration = 0.2
                animation.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
                layer.add(animation, forKey: "nagramiX.pip.swipe.return")
            }
            if cancelPreparation {
                item.cancelPictureInPictureSwipePreparation()
            }
        }
    }

    private func nagramiXCommitDirectionalPiPSwipe(_ item: GalleryItemNode) {
        guard self.nagramiXDirectionalPiPRequest == nil,
              item === self.nagramiXDirectionalPiPItem,
              item === self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe else {
            return
        }
        let request = UUID()
        self.nagramiXDirectionalPiPRequest = request
        let accepted = item.nagramiXStartDirectionalPiP(completion: { [weak self, weak item] started in
            guard let self, let item, self.nagramiXDirectionalPiPRequest == request,
                  self.nagramiXDirectionalPiPItem === item else { return }
            // Successful AVKit transfer has already hidden the gallery. Restore
            // its geometry for Expand; on failure keep the current gallery open.
            self.nagramiXResetDirectionalPiPSwipe(animated: !started, cancelPreparation: !started)
        })
        if !accepted, self.nagramiXDirectionalPiPRequest == request {
            self.nagramiXResetDirectionalPiPSwipe(animated: true)
        }
    }

    @objc private func nagramiXDirectionalPiPPan(_ gesture: UIPanGestureRecognizer) {
        switch gesture.state {
        case .began:
            self.nagramiXCancelSwipePreparation()
            guard let item = self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe,
                  item.prepareForPictureInPictureSwipe() else { return }
            item.view.layer.removeAnimation(forKey: "nagramiX.pip.swipe.return")
            self.nagramiXDirectionalPiPInitialTransform = item.view.transform
            self.nagramiXDirectionalPiPItem = item
        case .changed, .ended:
            guard let item = self.nagramiXDirectionalPiPItem else { return }
            guard item === self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe,
                  UIApplication.shared.applicationState == .active else {
                self.nagramiXResetDirectionalPiPSwipe(animated: false)
                return
            }
            // Once requested, leave the source visible and stationary until AVKit
            // confirms the transfer (or its bounded failure callback restores it).
            guard self.nagramiXDirectionalPiPRequest == nil else { return }
            let translation = gesture.translation(in: self.scrollView)
            let velocity = gesture.velocity(in: self.scrollView)
            guard translation.x.isFinite, translation.y.isFinite,
                  velocity.x.isFinite, velocity.y.isFinite else {
                self.nagramiXResetDirectionalPiPSwipe(animated: false)
                return
            }
            let distance = hypot(translation.x, translation.y)
            let factor = distance > 72.0 ? 72.0 / distance : 1.0
            item.view.transform = self.nagramiXDirectionalPiPInitialTransform.translatedBy(
                x: translation.x * factor, y: translation.y * factor
            )
            let flick = gesture.state == .ended && distance >= 12.0
                && hypot(velocity.x, velocity.y) >= 600.0
                && translation.x * velocity.x + translation.y * velocity.y > 0.0
            if distance >= 48.0 || flick {
                self.nagramiXCommitDirectionalPiPSwipe(item)
            } else if gesture.state == .ended {
                self.nagramiXResetDirectionalPiPSwipe(animated: true)
            }
        case .cancelled, .failed:
            self.nagramiXResetDirectionalPiPSwipe(animated: true)
        default:
            break
        }
    }
