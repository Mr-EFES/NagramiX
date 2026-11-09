import Foundation
import Postbox

public struct OutgoingContentInfoFlags: OptionSet {
    public var rawValue: Int32
    
    public init() {
        self.rawValue = 0
    }
    
    public init(rawValue: Int32) {
        self.rawValue = rawValue
    }
    
    public static let nagramiXCopy = OutgoingContentInfoFlags(rawValue: 1 << 1)
    public static let disableLinkPreviews = OutgoingContentInfoFlags(rawValue: 1 << 0)
}

public class OutgoingContentInfoMessageAttribute: MessageAttribute {
    public let nagramiXCopyFallbackText: String?
    public let flags: OutgoingContentInfoFlags
    
    public init(flags: OutgoingContentInfoFlags, nagramiXCopyFallbackText: String? = nil) {
        self.nagramiXCopyFallbackText = nagramiXCopyFallbackText
        self.flags = flags
    }
    
    required public init(decoder: PostboxDecoder) {
        self.nagramiXCopyFallbackText = decoder.decodeOptionalStringForKey("ncf")
        self.flags = OutgoingContentInfoFlags(rawValue: decoder.decodeInt32ForKey("f", orElse: 0))
    }
    
    public func encode(_ encoder: PostboxEncoder) {
        encoder.encodeInt32(self.flags.rawValue, forKey: "f")
        if let value = self.nagramiXCopyFallbackText { encoder.encodeString(value, forKey: "ncf") } else { encoder.encodeNil(forKey: "ncf") }
    }
    
    public func withUpdatedFlags(_ flags: OutgoingContentInfoFlags) -> OutgoingContentInfoMessageAttribute {
        return OutgoingContentInfoMessageAttribute(flags: flags, nagramiXCopyFallbackText: self.nagramiXCopyFallbackText)
    }
}


func nagramiXCopyShouldReupload(_ message: Message, error: String) -> Bool {
    guard message.attributes.contains(where: { ($0 as? OutgoingContentInfoMessageAttribute)?.flags.contains(.nagramiXCopy) == true }),
          !message.attributes.contains(where: { $0 is ForwardSourceInfoAttribute }),
          message.media.contains(where: { $0 is TelegramMediaImage || $0 is TelegramMediaFile || $0 is TelegramMediaPoll }) else { return false }
    return error == "CHAT_FORWARDS_RESTRICTED" || error == "MEDIA_EMPTY" || error == "MEDIA_INVALID"
}

func nagramiXCopyServerFallbackText(_ message: Message, error: String) -> String? {
    guard message.media.contains(where: { $0 is TelegramMediaGame || $0 is TelegramMediaTodo }),
          ["GAME_ID_INVALID", "GAME_SHORT_NAME_INVALID", "GAME_BOT_INVALID", "BOT_METHOD_INVALID", "BOT_INVALID", "PREMIUM_ACCOUNT_REQUIRED", "MEDIA_INVALID"].contains(error),
          let info = message.attributes.first(where: { $0 is OutgoingContentInfoMessageAttribute }) as? OutgoingContentInfoMessageAttribute,
          info.flags.contains(.nagramiXCopy) else { return nil }
    return info.nagramiXCopyFallbackText
}


public enum NagramiXCopyDeliveryState {
    case queued
    case accepted
    case failed
}

public func nagramiXCopiedMessageDeliveryState(_ message: Message?, acknowledged: Bool) -> NagramiXCopyDeliveryState {
    if acknowledged { return .accepted }
    guard let message else { return .queued }
    if message.flags.contains(.Failed) { return .failed }
    return !message.flags.contains(.Unsent) && !message.flags.isSending ? .accepted : .queued
}
