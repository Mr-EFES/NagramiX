    private func updateDisplayPlaceholder() {
        self.updateDisplayPlaceholder(!(self.videoNode?.ownsContentNode ?? true))
    }
    
    private func updateDisplayPlaceholder(_ displayPlaceholder: Bool) {
        if displayPlaceholder && !self.disablePictureInPicturePlaceholder {
            if self.pictureInPictureNode == nil {
                let pictureInPictureNode = UniversalVideoGalleryItemPictureInPictureNode(strings: self.presentationData.strings, mode: .pictureInPicture)
                pictureInPictureNode.isUserInteractionEnabled = false
                self.pictureInPictureNode = pictureInPictureNode
                self.insertSubnode(pictureInPictureNode, aboveSubnode: self.scrollNode)
                if let validLayout = self.validLayout {
                    if let item = self.item {
                        var placeholderSize = item.content.dimensions.fitted(validLayout.0.size)
                        placeholderSize.height += 2.0
                        pictureInPictureNode.frame = CGRect(origin: CGPoint(x: floor((validLayout.0.size.width - placeholderSize.width) / 2.0), y: floorToScreenPixels((validLayout.0.size.height - placeholderSize.height) / 2.0)), size: placeholderSize)
                        pictureInPictureNode.updateLayout(placeholderSize, transition: .immediate)
                    }
                }
            }
        } else if let pictureInPictureNode = self.pictureInPictureNode {
            self.pictureInPictureNode = nil
            pictureInPictureNode.removeFromSupernode()
            self.videoNode?.backgroundColor = .black
        }

        self.pictureInPictureButton?.isEnabled = self.pictureInPictureNode == nil
    }
    
