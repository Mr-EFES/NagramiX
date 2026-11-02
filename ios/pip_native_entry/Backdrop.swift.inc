    func nagramiXSetPiPBackdrop(visible: Bool, animated: Bool, completion: @escaping () -> Void) {
        // Keep the live source view/layer visible until AVKit finishes taking
        // ownership. Only the backdrop and controls fade during willStart.
        let alpha: CGFloat = visible ? 1.0 : 0.0
        let from = CGFloat(self.backgroundNode.layer.presentation()?.opacity ?? Float(self.backgroundNode.alpha))
        self.backgroundNode.layer.removeAnimation(forKey: "opacity")
        self.backgroundNode.alpha = alpha
        if animated && !UIAccessibility.isReduceMotionEnabled {
            self.backgroundNode.layer.animateAlpha(from: from, to: alpha, duration: 0.2, completion: { _ in completion() })
        } else { completion() }
    }
