override func controlsVisibilityUpdated(isVisible: Bool, animated: Bool) {
        self.areControlsVisible = isVisible
        self.controlsVisiblePromise.set(isVisible)
        
        self.videoNode?.isUserInteractionEnabled = isVisible ? self.videoNodeUserInteractionEnabled : false
        self.videoNode?.notifyPlaybackControlsHidden(!isVisible)
        
        if let validLayout = self.validLayout {
            self.containerLayoutUpdated(validLayout.layout, navigationBarHeight: validLayout.navigationBarHeight, transition: animated ? .animated(duration: 0.2, curve: .easeInOut) : .immediate)
        }
    }
