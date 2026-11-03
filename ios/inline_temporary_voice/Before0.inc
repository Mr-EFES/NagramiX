import Postbox
import NagramiXMediaSettings

// Used at the capture-event producer before any local enqueue or server RPC.
public func nagramiXShouldNotifyScreenCapture() -> Bool {
    return !NagramiXPrivacySettings.current.bypassScreenshots
}

public extension Message {
    var nagramiXAllowsScreenshotBypass: Bool {
        return self.paidContent == nil
            && !self.id.peerId.isVerificationCodes
    }
}
