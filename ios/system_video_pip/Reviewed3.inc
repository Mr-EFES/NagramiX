override func maybePerformActionForSwipeDismiss() -> Bool {
        if !NagramiXTabSettings.videoPiPSwipeEnabled {
            return false
        }
        if let data = self.context.currentAppConfiguration.with({ $0 }).data {
            if let _ = data["ios_killswitch_disable_swipe_pip"] {
                return false
            }
            var swipeUpToClose = false
            if let value = data["video_swipe_up_to_close"] as? Double, value == 1.0 {
                swipeUpToClose = true
            } else if let value = data["video_swipe_up_to_close"] as? Bool, value {
                swipeUpToClose = true
            }
            
            if swipeUpToClose {
                self.context.engine.accountData.addAppLogEvent(type: "swipe_up_close")
                
                return false
            }
        }
        
        if #available(iOS 15.0, *) {
            if let nativePictureInPictureContent = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl {
                self.context.engine.accountData.addAppLogEvent(type: "swipe_up_pip")
                nativePictureInPictureContent.beginPictureInPicture()
                return true
            }
        }
        return false
    }
