func expandPIP() {
        if #available(iOS 15.0, *) {
            if let nativePictureInPictureContent = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl {
                nativePictureInPictureContent.requestExpand()
            }
        }
    }
