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

/// Recording permissions do not change retention or content-read receipts.
/// Verification codes and paid media retain their existing capture policy.
public func nagramiXShouldBlockViewOnceScreenCapture(_ message: Message) -> Bool {
    return !NagramiXPrivacySettings.current.bypassScreenshots || !message.nagramiXAllowsScreenshotBypass
}

/// The two persisted switches are historical aliases. Explicit OFF for both
/// restores the native paths; no new preference or migration is introduced.
public func nagramiXTemporaryMessagesEnabled() -> Bool {
    let defaults = UserDefaults.standard
    return defaults.bool(forKey: "nagramix.messages.saveTemporaryMessages") || defaults.bool(forKey: "nagramix.messages.replayViewOnce")
}

/// Secret non-media TTL is tied to history reads. While Temporary Messages is
/// enabled, keep local read state but never publish the secret chat's read date.
/// This is chat-wide: older temporary messages can outlive a changed peer TTL.
public func nagramiXShouldSuppressTemporarySecretHistory(peerId: PeerId) -> Bool {
    return peerId.namespace == Namespaces.Peer.SecretChat && nagramiXTemporaryMessagesEnabled()
}

private func nagramiXIsTemporaryMessage(attributes: [MessageAttribute]) -> Bool {
    return attributes.contains { attribute in
        if let value = attribute as? AutoremoveTimeoutMessageAttribute { return value.timeout > 0 }
        if let value = attribute as? AutoclearTimeoutMessageAttribute { return value.timeout > 0 }
        return (attribute as? NagramiXArchivedMessageAttribute)?.isTemporary == true
    }
}

/// Raw provenance is independent of the current preference, so asynchronous
/// operations can reject a stale temporary send after the switch is disabled.
public func nagramiXIsTemporaryMessage(_ message: Message) -> Bool {
    return nagramiXIsTemporaryMessage(attributes: message.attributes)
}

public func nagramiXIsTemporaryMessage(_ message: StoreMessage) -> Bool {
    return nagramiXIsTemporaryMessage(attributes: message.attributes)
}

private func nagramiXIsSupportedTemporaryMessage(id: MessageId, pendingOrFailed: Bool, attributes: [MessageAttribute], media: [Media]) -> Bool {
    guard !pendingOrFailed,
          !id.peerId.isVerificationCodes,
          !media.contains(where: { $0 is TelegramMediaPaidContent || $0 is TelegramMediaExpiredContent || $0 is TelegramMediaAction }),
          !attributes.contains(where: { $0 is EphemeralMessageAttribute || $0 is EphemeralOutgoingMessageAttribute }) else { return false }
    let cloud = id.namespace == Namespaces.Message.Cloud
        && (id.peerId.namespace == Namespaces.Peer.CloudUser || id.peerId.namespace == Namespaces.Peer.CloudGroup || id.peerId.namespace == Namespaces.Peer.CloudChannel)
    let secret = id.peerId.namespace == Namespaces.Peer.SecretChat
        && (id.namespace == Namespaces.Message.SecretIncoming || id.namespace == Namespaces.Message.Local)
    guard cloud || secret else { return false }
    return nagramiXIsTemporaryMessage(attributes: attributes)
}

/// Eligibility is independent of the content kind and of the 60-second native
/// secret-media classifier. It does not consume, capture, persist or start TTL.
public func nagramiXCanRetainTemporaryMessage(_ message: Message) -> Bool {
    return nagramiXTemporaryMessagesEnabled() && nagramiXIsSupportedTemporaryMessage(id: message.id, pendingOrFailed: message.flags.isSending || message.flags.contains(.Failed), attributes: message.attributes, media: message.media)
}

public func nagramiXCanRetainTemporaryMessage(_ message: StoreMessage) -> Bool {
    guard case let .Id(id) = message.id else { return false }
    return nagramiXTemporaryMessagesEnabled() && nagramiXIsSupportedTemporaryMessage(id: id, pendingOrFailed: !message.flags.intersection([.Unsent, .Sending, .Failed]).isEmpty, attributes: message.attributes, media: message.media)
}

/// Source provenance survives retention without putting TTL attributes on the
/// synthetic copy. A regular auto-delete timeout is not a view-once badge.
public func nagramiXIsViewOnceMessage(_ message: Message) -> Bool {
    return message.attributes.contains { attribute in
        if let value = attribute as? AutoremoveTimeoutMessageAttribute { return value.timeout == viewOnceTimeout }
        if let value = attribute as? AutoclearTimeoutMessageAttribute { return value.timeout == viewOnceTimeout }
        return (attribute as? NagramiXArchivedMessageAttribute)?.isViewOnce == true
    }
}

/// Archiving available bytes after a genuine deletion is independent of
/// suppressing consumption while the original is still live.
public func nagramiXCanArchiveTemporaryMessage(_ message: StoreMessage) -> Bool {
    guard UserDefaults.standard.bool(forKey: "nagramix.messages.showDeletedMessages"),
          case let .Id(id) = message.id else { return false }
    return nagramiXIsSupportedTemporaryMessage(id: id, pendingOrFailed: !message.flags.intersection([.Unsent, .Sending, .Failed]).isEmpty, attributes: message.attributes, media: message.media)
}

/// Visual routing stays voice-specific. The retained/temporary content has no
/// local consumption or countdown side effect from this eligibility check.
public func nagramiXCanPlayTemporaryVoiceInline(_ message: Message) -> Bool {
    guard nagramiXCanUseTemporaryMediaActions(message),
          message.media.count == 1, let file = message.media.first as? TelegramMediaFile else { return false }
    return file.isVoice && !file.isInstantVideo
}

public func nagramiXCanUseTemporaryMediaActions(_ message: Message) -> Bool {
    if nagramiXCanRetainTemporaryMessage(message) { return true }
    return UserDefaults.standard.bool(forKey: "nagramix.messages.showDeletedMessages")
        && message.nagramiXShowsArchiveNotice
        && message.attributes.contains { ($0 as? NagramiXArchivedMessageAttribute)?.isTemporary == true }
}

public func nagramiXCanTranscribeTemporaryMedia(_ message: Message) -> Bool {
    guard nagramiXCanUseTemporaryMediaActions(message), let file = message.media.first as? TelegramMediaFile else { return false }
    return file.isVoice || file.isInstantVideo
}

/// Explicit consent is offered only for live incoming temporary photo/video/voice.
/// Merely showing this action never marks content read or starts a countdown.
public func nagramiXCanMarkTemporaryMediaOpened(_ message: Message) -> Bool {
    guard message.flags.contains(.Incoming), nagramiXCanRetainTemporaryMessage(message),
          !message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }),
          !message.attributes.contains(where: { ($0 as? ConsumableContentMessageAttribute)?.consumed == true }) else { return false }
    return message.media.contains { media in
        if media is TelegramMediaImage { return true }
        guard let file = media as? TelegramMediaFile else { return false }
        return file.isVoice || file.isInstantVideo || file.isVideo
    }
}
