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
        guard !self.isDismissed,
              UIApplication.shared.applicationState == .active,
              let item = self.pager.centralItemNode(),
              item.nagramiXCanBeginDirectionalPiPSwipe || item.nagramiXBlocksPiPSourcePan,
              touch.view?.isDescendant(of: self.scrollView) == true,
              item.view.bounds.contains(touch.location(in: item.view)) else { return false }
        // Footer/navigation controls live outside this scroll view. Preserve any
        // controls embedded in the video too, including ASButtonNode-backed views.
        var view = touch.view
        while let current = view, current !== self.view {
            if current is UIControl || current.asyncdisplaykit_node is ASButtonNode {
                return false
            }
            view = current.superview
        }
        self.nagramiXDirectionalPiPTouchTimestamp = touch.timestamp
        return true
    }

    public override func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard gestureRecognizer === self.nagramiXDirectionalPiPGesture else {
            return super.gestureRecognizerShouldBegin(gestureRecognizer)
        }
        guard !self.isDismissed,
              let gesture = gestureRecognizer as? UIPanGestureRecognizer,
              UIApplication.shared.applicationState == .active,
              let item = self.pager.centralItemNode(),
              item.nagramiXCanBeginDirectionalPiPSwipe || item.nagramiXBlocksPiPSourcePan else { return false }
        // Число пальцев уже ограничено minimum/maximumNumberOfTouches.
        // Не используем текущее число касаний как второй gate до .began.
        let velocity = gesture.velocity(in: self.scrollView)
        return velocity.x.isFinite && velocity.y.isFinite
    }

    private func nagramiXResetDirectionalPiPSwipe(animated: Bool, cancelPreparation: Bool = true) {
        let item = self.nagramiXDirectionalPiPItem
        let transform = self.nagramiXDirectionalPiPInitialTransform
        // Clear identity before cancellation: the native failure callback can be synchronous.
        self.nagramiXDirectionalPiPRequest = nil
        self.nagramiXDirectionalPiPItem = nil
        self.nagramiXDirectionalPiPTranslation = .zero
        self.nagramiXDirectionalPiPTransferring = false
        self.nagramiXDirectionalPiPIsFlick = false
        if let item {
            let layer = item.nagramiXPiPSwipeView.layer
            let previous = layer.presentation()?.transform ?? layer.transform
            layer.removeAnimation(forKey: "nagramiX.pip.swipe.return")
            layer.removeAnimation(forKey: "nagramiX.pip.swipe.exit")
            item.nagramiXPiPSwipeView.transform = transform
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
            if started {
                self.nagramiXAnimateDirectionalPiPTransfer(item, request: request)
            } else {
                self.nagramiXResetDirectionalPiPSwipe(animated: true)
            }
        })
        if !accepted, self.nagramiXDirectionalPiPRequest == request {
            self.nagramiXResetDirectionalPiPSwipe(animated: true)
        }
    }

    private func nagramiXAnimateDirectionalPiPTransfer(_ item: GalleryItemNode, request: UUID) {
        // AVKit подтвердил запуск. Теперь источник может уйти за границу экрана.
        // Обе координаты сохраняются: горизонтальный свайп не добавляет вертикаль.
        self.nagramiXDirectionalPiPTransferring = true
        let delta = self.nagramiXDirectionalPiPTranslation
        let distance = hypot(delta.x, delta.y)
        guard distance > 0.0 else {
            self.nagramiXResetDirectionalPiPSwipe(animated: false, cancelPreparation: false)
            return
        }
        let travel = max(self.view.bounds.width, self.view.bounds.height)
        let layer = item.nagramiXPiPSwipeView.layer
        let previous = layer.presentation()?.transform ?? layer.transform
        let destination = NagramiXPiPReleaseDecision(
            kind: self.nagramiXDirectionalPiPIsFlick ? .swipe : .drag,
            x: Double(delta.x), y: Double(delta.y)
        ).destination(travel: Double(travel))
        let target = CGPoint(x: CGFloat(destination.x), y: CGFloat(destination.y))
        item.nagramiXPiPSwipeView.transform = self.nagramiXDirectionalPiPInitialTransform
            .translatedBy(x: target.x, y: target.y)
            .scaledBy(x: 0.25, y: 0.25)
        let animation = CABasicAnimation(keyPath: "transform")
        animation.fromValue = NSValue(caTransform3D: previous)
        animation.toValue = NSValue(caTransform3D: layer.transform)
        animation.duration = 0.2
        animation.timingFunction = CAMediaTimingFunction(name: .easeIn)
        layer.add(animation, forKey: "nagramiX.pip.swipe.exit")
        // Штатная галерея исчезает за 0.2с. Возвращаем геометрию для Expand
        // после исчезновения, без видимого скачка к исходному положению.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.22) { [weak self, weak item] in
            guard let self, let item, self.nagramiXDirectionalPiPRequest == request,
                  self.nagramiXDirectionalPiPItem === item else { return }
            self.nagramiXResetDirectionalPiPSwipe(animated: false, cancelPreparation: false)
        }
    }

    @objc private func nagramiXDirectionalPiPPan(_ gesture: UIPanGestureRecognizer) {
        // Новые касания не перезапускают уже отпущенный запрос и не двигают
        // заглушку во время подтверждённой передачи.
        guard !self.nagramiXDirectionalPiPTransferring, self.nagramiXDirectionalPiPRequest == nil else { return }
        switch gesture.state {
        case .began:
            self.nagramiXCancelSwipePreparation()
            guard let item = self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe else { return }
            // .began только захватывает поверхность текущего видео.
            // Подготовка AVKit начнётся после отпускания пальца.
            item.nagramiXPiPSwipeView.layer.removeAnimation(forKey: "nagramiX.pip.swipe.return")
            self.nagramiXDirectionalPiPInitialTransform = item.nagramiXPiPSwipeView.transform
            self.nagramiXDirectionalPiPItem = item
        case .changed, .ended:
            guard let item = self.nagramiXDirectionalPiPItem else { return }
            guard item === self.pager.centralItemNode(), item.nagramiXCanBeginDirectionalPiPSwipe,
                  UIApplication.shared.applicationState == .active else {
                self.nagramiXResetDirectionalPiPSwipe(animated: false)
                return
            }
            let translation = gesture.translation(in: self.scrollView)
            let velocity = gesture.velocity(in: self.scrollView)
            guard translation.x.isFinite, translation.y.isFinite,
                  velocity.x.isFinite, velocity.y.isFinite else {
                self.nagramiXResetDirectionalPiPSwipe(animated: false)
                return
            }
            self.nagramiXDirectionalPiPTranslation = translation
            item.nagramiXPiPSwipeView.transform = self.nagramiXDirectionalPiPInitialTransform.translatedBy(
                x: translation.x, y: translation.y
            )
            // Пока палец на экране, AVKit не запускается. Одна точка принятия
            // решения исключает переход посреди удерживания и повторный start.
            guard gesture.state == .ended else { return }
            let decision = NagramiXPiPReleaseDecision.resolve(
                x: Double(translation.x), y: Double(translation.y),
                velocityX: Double(velocity.x), velocityY: Double(velocity.y),
                elapsed: CACurrentMediaTime() - self.nagramiXDirectionalPiPTouchTimestamp
            )
            guard decision.kind != .cancel else {
                self.nagramiXResetDirectionalPiPSwipe(animated: true)
                return
            }
            NSLog("NagramiX PiP: release=%@", decision.kind == .swipe ? "swipe" : "drag")
            self.nagramiXDirectionalPiPIsFlick = decision.kind == .swipe
            self.nagramiXCommitDirectionalPiPSwipe(item)
        case .cancelled, .failed:
            self.nagramiXResetDirectionalPiPSwipe(animated: true)
        default:
            break
        }
    }
