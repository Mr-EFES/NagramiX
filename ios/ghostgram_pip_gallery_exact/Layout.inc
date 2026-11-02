        if let pictureInPictureNode = self.pictureInPictureNode {
            if let item = self.item {
                var placeholderSize = item.content.dimensions.fitted(layout.size)
                placeholderSize.height += 2.0
                transition.updateFrame(node: pictureInPictureNode, frame: CGRect(origin: CGPoint(x: floor((layout.size.width - placeholderSize.width) / 2.0), y: floor((layout.size.height - placeholderSize.height) / 2.0)), size: placeholderSize))
                pictureInPictureNode.updateLayout(placeholderSize, transition: transition)
            }
        }
        
