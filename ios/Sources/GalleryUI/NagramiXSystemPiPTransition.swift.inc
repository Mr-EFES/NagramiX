    func nagramiXPreparePiPRestoration() {
        // Expand can arrive before the gallery's fade has finished.
        self.nagramiXResetDirectionalPiPSwipe(animated: false, cancelPreparation: false)
    }

    private func nagramiXInstallDirectionalPiPGesture() {
        let gesture = UIPanGestureRecognizer(target: self, action: #selector(self.nagramiXDirectionalPiPPan(_:)))
        gesture.minimumNumberOfTouches = 1
        gesture.maximumNumberOfTouches = 1
        gesture.delegate = self.wrappedGestureRecognizerDelegate
        self.nagramiXDirectionalPiPGesture = gesture
        self.view.addGestureRecognizer(gesture)
        self.scrollView.panGestureRecognizer.require(toFail: gesture)
        self.pager.nagramiXInstallDirectionalPiPGesture(gesture)
    }

    public func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        guard gestureRecognizer === self.nagramiXDirectionalPiPGesture else { return true }
        guard !self.isDismissed, UIApplication.shared.applicationState == .active,
              let item = self.pager.centralItemNode(),
              item.nagramiXCanBeginDirectionalPiPSwipe || item.nagramiXBlocksPiPSourcePan,
              touch.view?.isDescendant(of: self.scrollView) == true,
              item.view.bounds.contains(touch.location(in: item.view)) else { return false }
        var view = touch.view
        while let current = view, current !== self.view {
            // A pan may start on Play/Pause; taps still reach the button when
            // this recognizer fails. Sliders/switches retain their own dragging.
            if current is UISlider || current is UISwitch { return false }
            view = current.superview
        }
        self.nagramiXDirectionalPiPTouchTimestamp = touch.timestamp
        return true
    }

    public override func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard gestureRecognizer === self.nagramiXDirectionalPiPGesture else {
            return super.gestureRecognizerShouldBegin(gestureRecognizer)
        }
        guard !self.isDismissed, let gesture = gestureRecognizer as? UIPanGestureRecognizer,
              UIApplication.shared.applicationState == .active,
              let item = self.pager.centralItemNode(),
              item.nagramiXCanBeginDirectionalPiPSwipe || item.nagramiXBlocksPiPSourcePan else { return false }
        let velocity = gesture.velocity(in: self.view)
        return velocity.x.isFinite && velocity.y.isFinite
    }

    private func nagramiXResetDirectionalPiPSwipe(animated: Bool, cancelPreparation: Bool = true) {
        let item = self.nagramiXDirectionalPiPItem
        let transform = self.nagramiXDirectionalPiPRestTransform
        self.nagramiXDirectionalPiPRequest = nil
        self.nagramiXDirectionalPiPItem = nil
        self.nagramiXDirectionalPiPSourceFrame = nil
        self.nagramiXDirectionalPiPSpace = nil
        self.nagramiXDirectionalPiPTranslation = .zero
        self.nagramiXDirectionalPiPTransferring = false
        self.nagramiXDirectionalPiPIsFlick = false
        if let item {
            item.nagramiXPiPSwipeTransitionPending = false
            let layer = item.nagramiXPiPSwipeView.layer
            let previous = layer.presentation()?.transform ?? layer.transform
            layer.removeAnimation(forKey: "nagramiX.pip.swipe.settle")
            layer.removeAnimation(forKey: "nagramiX.pip.swipe.return")
            item.nagramiXPiPSwipeView.transform = transform
            if animated && !UIAccessibility.isReduceMotionEnabled {
                let animation = CABasicAnimation(keyPath: "transform")
                animation.fromValue = NSValue(caTransform3D: previous)
                animation.toValue = NSValue(caTransform3D: layer.transform)
                animation.duration = 0.2
                animation.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
                layer.add(animation, forKey: "nagramiX.pip.swipe.return")
            }
            if cancelPreparation { item.cancelPictureInPictureSwipePreparation() }
        }
    }

    private func nagramiXPiPTransform(_ item: GalleryItemNode, release: NagramiXPiPReleaseKind? = nil) -> CGAffineTransform? {
        guard let source = self.nagramiXDirectionalPiPSourceFrame,
              let pose = NagramiXPiPSourceGeometry.resolve(source: source,
                viewport: self.nagramiXDirectionalPiPViewport, safeArea: self.nagramiXDirectionalPiPSafeArea,
                translation: self.nagramiXDirectionalPiPTranslation, release: release) else { return nil }
        let center = CGPoint(x: item.nagramiXPiPSwipeView.center.x + self.nagramiXDirectionalPiPInitialTransform.tx,
                             y: item.nagramiXPiPSwipeView.center.y + self.nagramiXDirectionalPiPInitialTransform.ty)
        let scaledCenter = CGPoint(x: center.x + (source.midX - center.x) * pose.scale,
                                   y: center.y + (source.midY - center.y) * pose.scale)
        return self.nagramiXDirectionalPiPInitialTransform.scaledBy(x: pose.scale, y: pose.scale)
            .concatenating(CGAffineTransform(translationX: pose.frame.midX - scaledCenter.x,
                                           y: pose.frame.midY - scaledCenter.y))
    }

    private func nagramiXCommitDirectionalPiPSwipe(_ item: GalleryItemNode) {
        guard self.nagramiXDirectionalPiPRequest == nil,
              item === self.nagramiXDirectionalPiPItem, item === self.pager.centralItemNode(),
              item.nagramiXCanBeginDirectionalPiPSwipe,
              let target = self.nagramiXPiPTransform(item, release: self.nagramiXDirectionalPiPIsFlick ? .swipe : .drag) else {
            self.nagramiXResetDirectionalPiPSwipe(animated: true)
            return
        }
        let request = UUID()
        self.nagramiXDirectionalPiPRequest = request
        item.nagramiXPiPSwipeTransitionPending = true
        let start: () -> Void = { [weak self, weak item] in
            guard let self, let item, self.nagramiXDirectionalPiPRequest == request else { return }
            guard item === self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe,
                  UIApplication.shared.applicationState == .active else {
                self.nagramiXResetDirectionalPiPSwipe(animated: true)
                return
            }
            let accepted = item.nagramiXStartDirectionalPiP(completion: { [weak self, weak item] started in
                guard let self, let item, self.nagramiXDirectionalPiPRequest == request,
                      self.nagramiXDirectionalPiPItem === item else { return }
                if started {
                    // AVKit has finished its own source-to-window animation.
                    // Keep this geometry until the actual gallery dismissal completes.
                    self.nagramiXDirectionalPiPTransferring = true
                } else {
                    self.nagramiXResetDirectionalPiPSwipe(animated: true)
                }
            })
            if !accepted, self.nagramiXDirectionalPiPRequest == request {
                self.nagramiXResetDirectionalPiPSwipe(animated: true)
            }
        }
        let layer = item.nagramiXPiPSwipeView.layer
        let previous = layer.presentation()?.transform ?? layer.transform
        item.nagramiXPiPSwipeView.transform = target
        // Settle the visible source BEFORE AVKit starts. No simultaneous custom
        // throw/shrink during the system transition, and no fixed-delay reset.
        if UIAccessibility.isReduceMotionEnabled || !self.nagramiXDirectionalPiPIsFlick {
            start()
        } else {
            CATransaction.begin()
            CATransaction.setCompletionBlock(start)
            let animation = CABasicAnimation(keyPath: "transform")
            animation.fromValue = NSValue(caTransform3D: previous)
            animation.toValue = NSValue(caTransform3D: layer.transform)
            animation.duration = 0.18
            animation.timingFunction = CAMediaTimingFunction(name: .easeOut)
            layer.add(animation, forKey: "nagramiX.pip.swipe.settle")
            CATransaction.commit()
        }
    }

    @objc private func nagramiXDirectionalPiPPan(_ gesture: UIPanGestureRecognizer) {
        guard !self.nagramiXDirectionalPiPTransferring, self.nagramiXDirectionalPiPRequest == nil else { return }
        switch gesture.state {
        case .began:
            self.nagramiXCancelSwipePreparation()
            guard let item = self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe,
                  let space = item.nagramiXPiPSwipeView.superview else { return }
            let surface = item.nagramiXPiPSwipeView
            self.nagramiXDirectionalPiPRestTransform = surface.transform
            let presented = surface.layer.presentation()?.affineTransform() ?? surface.transform
            surface.layer.removeAnimation(forKey: "nagramiX.pip.swipe.return")
            surface.transform = presented
            self.nagramiXDirectionalPiPInitialTransform = presented
            self.nagramiXDirectionalPiPSourceFrame = item.nagramiXPiPSourceFrame(in: space)
            self.nagramiXDirectionalPiPSpace = space
            self.nagramiXDirectionalPiPViewport = self.view.convert(self.view.bounds, to: space)
            let safe = self.view.bounds.inset(by: self.view.safeAreaInsets).insetBy(dx: 12, dy: 12)
            self.nagramiXDirectionalPiPSafeArea = self.view.convert(safe, to: space)
            self.nagramiXDirectionalPiPItem = item
            fallthrough
        case .changed, .ended:
            guard let item = self.nagramiXDirectionalPiPItem, let space = self.nagramiXDirectionalPiPSpace else { return }
            guard item === self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe,
                  UIApplication.shared.applicationState == .active else {
                self.nagramiXResetDirectionalPiPSwipe(animated: true)
                return
            }
            let translation = gesture.translation(in: space), velocity = gesture.velocity(in: space)
            guard translation.x.isFinite, translation.y.isFinite, velocity.x.isFinite, velocity.y.isFinite else {
                self.nagramiXResetDirectionalPiPSwipe(animated: true)
                return
            }
            self.nagramiXDirectionalPiPTranslation = translation
            guard let transform = self.nagramiXPiPTransform(item) else {
                self.nagramiXResetDirectionalPiPSwipe(animated: true)
                return
            }
            item.nagramiXPiPSwipeView.transform = transform
            guard gesture.state == .ended else { return }
            let decision = NagramiXPiPReleaseDecision.resolve(x: Double(translation.x), y: Double(translation.y),
                velocityX: Double(velocity.x), velocityY: Double(velocity.y),
                elapsed: CACurrentMediaTime() - self.nagramiXDirectionalPiPTouchTimestamp)
            guard decision.kind != .cancel else {
                self.nagramiXResetDirectionalPiPSwipe(animated: true)
                return
            }
            self.nagramiXDirectionalPiPIsFlick = decision.kind == .swipe
            self.nagramiXCommitDirectionalPiPSwipe(item)
        case .cancelled, .failed:
            self.nagramiXResetDirectionalPiPSwipe(animated: true)
        default: break
        }
    }
