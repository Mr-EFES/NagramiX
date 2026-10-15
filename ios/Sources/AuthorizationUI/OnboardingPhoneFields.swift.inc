    func nagramiXPreferredHeight(width: CGFloat) -> CGFloat {
        let title = self.countryButton.titleNode.measure(CGSize(width: max(1.0, width - 64.0), height: .greatestFiniteMagnitude))
        return max(52.0, title.height + 20.0) + 12.0 + 52.0
    }

    private func nagramiXLayoutFields(_ size: CGSize) {
        let countryHeight = self.nagramiXPreferredHeight(width: size.width) - 64.0
        self.countryButton.frame = CGRect(x: 0.0, y: 0.0, width: size.width, height: countryHeight)
        let phoneY = countryHeight + 12.0
        self.phoneBackground.frame = CGRect(x: 0.0, y: phoneY, width: size.width, height: 52.0)
        if let image = self.countryButtonArrow.image {
            self.countryButtonArrow.frame = CGRect(x: size.width - image.size.width - 16.0, y: (countryHeight - image.size.height) / 2.0, width: image.size.width, height: image.size.height)
        }
        let code = CGRect(x: 16.0, y: phoneY, width: 64.0, height: 52.0)
        let number = CGRect(x: 88.0, y: phoneY, width: max(1.0, size.width - 104.0), height: 52.0)
        let input = code.union(number)
        self.phoneInputNode.frame = input
        self.phoneInputNode.countryCodeField.frame = code.offsetBy(dx: -input.minX, dy: -input.minY)
        self.phoneInputNode.numberField.frame = number.offsetBy(dx: -input.minX, dy: -input.minY)
        self.phoneInputNode.placeholderNode.frame = number.offsetBy(dx: -input.minX, dy: -input.minY + 17.0 - UIScreenPixel)
    }
