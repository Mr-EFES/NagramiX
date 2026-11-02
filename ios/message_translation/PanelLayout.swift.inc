    private func nagramiXLayoutTranslation(width: CGFloat, transition: ContainedViewLayoutTransition) -> CGFloat {
        self.buttonIconNode.isHidden = true
        self.closeButton.isHidden = true
        self.moreButton.isHidden = false
        self.buttonTextNode.maximumNumberOfLines = 0
        let moreSize = self.moreButton.measure(CGSize(width: 100, height: 44))
        let available = max(1, width - moreSize.width - 42)
        let textSize = self.buttonTextNode.updateLayout(CGSize(width: available, height: .greatestFiniteMagnitude))
        let height = max(44, textSize.height + 12)
        let buttonWidth = min(available + 20, textSize.width + 20)
        transition.updateFrame(node: self.button, frame: CGRect(x: 8 + floorToScreenPixels((available + 20 - buttonWidth) / 2), y: 0, width: buttonWidth, height: height))
        let textFrame = CGRect(x: 10, y: floorToScreenPixels((height - textSize.height) / 2), width: textSize.width, height: textSize.height)
        transition.updatePosition(node: self.buttonTextNode, position: textFrame.center)
        self.buttonTextNode.bounds = CGRect(origin: .zero, size: textFrame.size)
        transition.updateFrame(node: self.moreButton, frame: CGRect(x: width - moreSize.width - 11, y: floorToScreenPixels((height - moreSize.height) / 2), width: moreSize.width, height: moreSize.height))
        return height
    }
