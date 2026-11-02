    func nagramiXPreparePiPRestoration() {
        self.nagramiXPiPGestureController?.reset(animated: false, cancelPreparation: false)
    }

    private func nagramiXInstallDirectionalPiPGesture() {
        let controller = NagramiXPiPGestureController(host: self.view, content: self.scrollView, background: self.backgroundNode.view,
            currentItem: { [weak self] in self?.pager.centralItemNode() },
            available: { [weak self] in self?.isDismissed == false })
        self.nagramiXPiPGestureController = controller
        self.scrollView.panGestureRecognizer.require(toFail: controller.recognizer)
        self.pager.nagramiXInstallDirectionalPiPGesture(controller.recognizer)
    }

    private func nagramiXResetDirectionalPiPSwipe(animated: Bool, cancelPreparation: Bool = true) {
        self.nagramiXPiPGestureController?.reset(animated: animated, cancelPreparation: cancelPreparation)
    }

    var nagramiXAllowsSystemPiPTransition: Bool { return !self.isDismissed }
