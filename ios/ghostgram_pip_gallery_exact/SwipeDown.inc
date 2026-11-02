    override func maybePerformActionForSwipeDownDismiss() -> Bool {
        self.context.engine.accountData.addAppLogEvent(type: "swipe_down_close")
        return false
    }
