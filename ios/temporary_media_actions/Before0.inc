import Foundation
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

/// Visual/playback routing only. It never changes a message's lifetime,
/// consumed attribute, archive visibility or server forwarding permissions.
public func nagramiXCanPlayTemporaryVoiceInline(_ message: Message) -> Bool {
    let defaults = UserDefaults.standard
    guard defaults.bool(forKey: "nagramix.messages.saveTemporaryMessages") || defaults.bool(forKey: "nagramix.messages.replayViewOnce"),
          message.id.namespace == Namespaces.Message.Cloud,
          message.id.peerId.namespace == Namespaces.Peer.CloudUser,
          !message.id.peerId.isVerificationCodes,
          !message.flags.isSending, !message.flags.contains(.Failed),
          message.media.count == 1, let file = message.media.first as? TelegramMediaFile,
          file.isVoice, !file.isInstantVideo else { return false }
    if message.minAutoremoveOrClearTimeout == viewOnceTimeout { return true }
    // Retained temporary voices have no expiry attribute. Keep it that way:
    // the native burn appearance must not give the local copy a real timer.
    return message.attributes.contains { ($0 as? NagramiXArchivedMessageAttribute)?.isTemporary == true }
}
