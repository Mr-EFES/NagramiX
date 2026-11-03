func pictureInPictureButtonPressed() {
        if self.nativePictureInPictureContent == nil {
            self.setupNativePictureInPicture()
        }
        
        DispatchQueue.main.async { [weak self] in
            guard let self else {
                return
            }
            
            if let currentPictureInPictureNode = self.context.sharedContext.mediaManager.currentPictureInPictureNode as? UniversalVideoGalleryItemNode, let currentItem = currentPictureInPictureNode.item, case let .message(currentMessage, _) = currentItem.contentInfo, case let .message(message, _) = self.item?.contentInfo, currentMessage.id == message.id {
                if let controller = self.galleryController() as? GalleryController {
                    controller.dismiss(forceAway: true)
                }
                return
            }
            
            if #available(iOS 15.0, *) {
                if let nativePictureInPictureContent = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl {
                    self.context.engine.accountData.addAppLogEvent(type: "pip_btn")
                    nativePictureInPictureContent.beginPictureInPicture()
                    return
                }
            }
        }
    }
