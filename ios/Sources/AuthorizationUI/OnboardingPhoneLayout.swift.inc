    private func nagramiXLayoutPhone(_ layout: ContainerViewLayout, navigationBarHeight: CGFloat, transition: ContainedViewLayoutTransition) {
        var insets = layout.insets(options: [])
        if let keyboard = layout.inputHeight, keyboard > 0.0 {
            insets.bottom = max(insets.bottom, keyboard)
        }
        let width = min(430.0, max(1.0, layout.size.width - 48.0))
        let titleFont = UIFontMetrics(forTextStyle: .largeTitle).scaledFont(for: UIFont.systemFont(ofSize: 34.0, weight: .bold))
        self.titleNode.attributedText = NSAttributedString(string: self.strings.Login_PhoneTitle, attributes: [.font: titleFont, .foregroundColor: self.theme.list.itemPrimaryTextColor])
        let titleSize = self.titleNode.measure(CGSize(width: width, height: .greatestFiniteMagnitude))
        if let current = self.noticeNode.attributedText {
            let text = NSMutableAttributedString(attributedString: current)
            text.addAttribute(.font, value: UIFontMetrics(forTextStyle: .body).scaledFont(for: UIFont.systemFont(ofSize: 16.0)), range: NSRange(location: 0, length: text.length))
            self.noticeNode.attributedText = text
        }
        let noticeSize = self.noticeNode.updateLayout(CGSize(width: width, height: .greatestFiniteMagnitude))
        let fieldsHeight = self.phoneAndCountryNode.nagramiXPreferredHeight(width: width)
        let contactSize = self.contactSyncNode.updateLayout(width: width)
        self.contactSyncNode.isHidden = !self.hasOtherAccounts
        let buttonHeight = self.proceedNode.updateLayout(width: width, transition: transition)
        let buttonFrame: CGRect
        if let forced = self.forcedButtonFrame, (layout.inputHeight ?? 0.0).isZero {
            buttonFrame = forced
        } else {
            buttonFrame = CGRect(x: floorToScreenPixels((layout.size.width - width) / 2.0), y: layout.size.height - insets.bottom - buttonHeight - 16.0, width: width, height: buttonHeight)
        }
        self.proceedNode.isHidden = false
        transition.updateFrame(node: self.proceedNode, frame: buttonFrame)
        // The centered illustration can use the space beside the navigation
        // controls; its visible bounds stay clear of the leading back button.
        let bodyTop = max(layout.statusBarHeight ?? 20.0, 20.0) + 8.0
        let bodyHeight = max(0.0, buttonFrame.minY - 16.0 - bodyTop)
        transition.updateFrame(node: self.nagramiXContentNode, frame: CGRect(x: 0.0, y: bodyTop, width: layout.size.width, height: bodyHeight))
        let fixedHeight = titleSize.height + 12.0 + noticeSize.height + 20.0 + fieldsHeight + (self.hasOtherAccounts ? contactSize.height + 14.0 : 0.0)
        let artworkRatio: CGFloat
        if let image = self.animationNode.image, image.size.width > 0.0 {
            artworkRatio = image.size.height / image.size.width
        } else {
            artworkRatio = 864.0 / 1024.0
        }
        let preferredArtworkWidth = min(280.0, min(width, layout.size.width * 0.60))
        let artworkHeight = min(preferredArtworkWidth * artworkRatio, max(64.0, bodyHeight - fixedHeight - 24.0))
        let artworkWidth = artworkHeight / artworkRatio
        let contentHeight = artworkHeight + 16.0 + fixedHeight + 8.0
        var y = max(0.0, (bodyHeight - contentHeight) * 0.25)
        self.animationNode.isHidden = false
        transition.updateFrame(node: self.animationNode, frame: CGRect(x: (layout.size.width - artworkWidth) / 2.0, y: y, width: artworkWidth, height: artworkHeight))
        y += artworkHeight + 16.0
        transition.updateFrame(node: self.titleNode, frame: CGRect(x: (layout.size.width - titleSize.width) / 2.0, y: y, width: titleSize.width, height: titleSize.height))
        y += titleSize.height + 12.0
        transition.updateFrame(node: self.noticeNode, frame: CGRect(x: (layout.size.width - noticeSize.width) / 2.0, y: y, width: noticeSize.width, height: noticeSize.height))
        y += noticeSize.height + 20.0
        transition.updateFrame(node: self.phoneAndCountryNode, frame: CGRect(x: (layout.size.width - width) / 2.0, y: y, width: width, height: fieldsHeight))
        y += fieldsHeight
        if self.hasOtherAccounts {
            y += 14.0
            transition.updateFrame(node: self.contactSyncNode, frame: CGRect(x: (layout.size.width - contactSize.width) / 2.0, y: y, width: contactSize.width, height: contactSize.height))
            y += contactSize.height
        }
        self.nagramiXContentNode.view.contentInsetAdjustmentBehavior = .never
        self.nagramiXContentNode.view.alwaysBounceVertical = false
        self.nagramiXContentNode.view.showsVerticalScrollIndicator = false
        self.nagramiXContentNode.view.contentSize = CGSize(width: layout.size.width, height: y + 8.0)
        self.nagramiXContentNode.view.isScrollEnabled = y + 8.0 > bodyHeight
        let keyboardVisible = (layout.inputHeight ?? 0.0) > 0.0
        if keyboardVisible && !self.nagramiXHadKeyboard {
            let offset = max(0.0, min(y + 8.0 - bodyHeight, self.phoneAndCountryNode.frame.maxY - bodyHeight))
            self.nagramiXContentNode.view.setContentOffset(CGPoint(x: 0.0, y: offset), animated: false)
        } else if !keyboardVisible && self.nagramiXHadKeyboard {
            self.nagramiXContentNode.view.setContentOffset(.zero, animated: false)
        }
        self.nagramiXHadKeyboard = keyboardVisible
        self.titleActivateAreaNode.accessibilityLabel = self.titleNode.attributedText?.string ?? ""
        self.titleActivateAreaNode.frame = self.titleNode.frame
        self.noticeActivateAreaNode.accessibilityLabel = self.noticeNode.attributedText?.string ?? ""
        self.noticeActivateAreaNode.frame = self.noticeNode.frame
    }
