import Postbox

public extension Message {
    var nagramiXAllowsScreenshotBypass: Bool {
        return !self.containsSecretMedia
            && self.minAutoremoveOrClearTimeout != viewOnceTimeout
            && self.paidContent == nil
            && !self.id.peerId.isVerificationCodes
    }
}
