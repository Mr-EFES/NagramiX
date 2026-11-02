        private func nagramiXMeasureRows(presentationData: PresentationData, width: CGFloat) {
            let fraction = presentationData.listsFontSize.baseDisplaySize / 17.0
            let minimumHeight = (self.displayReadTimestamps ? 56.0 : 44.0) * fraction
            let fontSize = presentationData.listsFontSize.baseDisplaySize
            let premiumDisabled = PremiumConfiguration.with(appConfiguration: self.context.currentAppConfiguration.with { $0 }).isPremiumDisabled
            var heights: [CGFloat] = []
            var measures: [NagramiXReactionNameMeasureKey: CGFloat] = [:]
            self.nagramiXNameMeasureNode.maximumNumberOfLines = 0
            for item in self.state.mergedItems.prefix(self.state.totalCount) {
                let text = item.peer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder)
                let inset = nagramiXReactionCredibilityInset(peer: item.peer, presentationData: presentationData, premiumDisabled: premiumDisabled)
                let nameWidth = nagramiXReactionNameWidth(width: width, hasReaction: item.reaction != nil, credibilityInset: inset)
                let key = NagramiXReactionNameMeasureKey(text: text, width: nameWidth, fontSize: fontSize)
                let titleHeight: CGFloat
                if let cached = measures[key] ?? self.nagramiXNameMeasures[key] {
                    titleHeight = cached
                } else {
                    self.nagramiXNameMeasureNode.attributedText = NSAttributedString(string: text, font: Font.regular(fontSize), textColor: presentationData.theme.contextMenu.primaryColor)
                    titleHeight = self.nagramiXNameMeasureNode.updateLayout(CGSize(width: nameWidth, height: .greatestFiniteMagnitude)).height
                }
                measures[key] = titleHeight
                let subtitleHeight: CGFloat
                if self.displayReadTimestamps && item.timestamp != nil {
                    subtitleHeight = floor(fraction * 2.0) + ceil(Font.regular(floor(fraction * 15.0)).lineHeight)
                } else {
                    subtitleHeight = 0.0
                }
                heights.append(max(minimumHeight, ceil(titleHeight + subtitleHeight + 12.0 * fraction)))
            }
            // Retain only the current loaded page set; never accumulate old names.
            self.nagramiXNameMeasures = measures
            self.nagramiXRowLayout = NagramiXReactionRowLayout(heights: heights, count: self.state.totalCount, placeholderHeight: minimumHeight)
        }
