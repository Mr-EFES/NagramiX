import Foundation

// Platform adapters only. Model, selection, replacement, draft mutations, route and enqueue builder
// below are extracted from the pinned production files. This does not link UIKit or real Postbox.
public protocol Media: AnyObject { func isEqual(to: Media) -> Bool }
public struct MediaId: Hashable, Codable { public var id: Int64; public init(_ id: Int64) { self.id = id } }
public enum EnginePeer { public struct Id: Equatable, Codable { let value: Int64; public init(_ value: Int64) { self.value = value }; public func toInt64() -> Int64 { value } } }
public struct PixelDimensions { public let width: Int32; public let height: Int32 }
public class TelegramMediaFile: Media, Equatable {
    public let fileId: MediaId
    public var isVideo = false
    public var isInstantVideo = false
    public var isMusic = false
    public var isVoice = false
    public var dimensions: PixelDimensions?
    public var mimeType = "application/octet-stream"
    public var payload = Data([1, 2, 3])
    public var partialReference: Int64?
    public func withUpdatedPartialReference(_ reference: Int64?) -> TelegramMediaFile {
        let result = TelegramMediaFile(fileId.id)
        result.partialReference = reference
        result.isVideo = isVideo; result.isInstantVideo = isInstantVideo; result.isMusic = isMusic; result.isVoice = isVoice
        result.dimensions = dimensions; result.mimeType = mimeType; result.payload = payload
        return result
    }
    public init(_ id: Int64) { self.fileId = MediaId(id) }
    public required init(decoder: PostboxDecoder) { self.fileId = MediaId(0) }
    public func isEqual(to other: Media) -> Bool { (other as? TelegramMediaFile)?.fileId == fileId }
    public static func == (lhs: TelegramMediaFile, rhs: TelegramMediaFile) -> Bool { lhs.fileId == rhs.fileId }
}
public class TelegramMediaImage: Media {
    public init() {}
    public required init(decoder: PostboxDecoder) {}
    public func isEqual(to other: Media) -> Bool { other is TelegramMediaImage }
}
public class TelegramMediaMap: Media {
    public required init(decoder: PostboxDecoder) {}
    public func isEqual(to other: Media) -> Bool { other is TelegramMediaMap }
}
public enum EngineMedia {
    case file(TelegramMediaFile), image(TelegramMediaImage), map(TelegramMediaMap)
    public init(_ media: Media) {
        if let value = media as? TelegramMediaFile { self = .file(value) }
        else if let value = media as? TelegramMediaImage { self = .image(value) }
        else { self = .map(media as! TelegramMediaMap) }
    }
}
public enum AdaptedPostboxDecoder { public struct RawObjectData: Codable { public let data: Data } }
public struct MemoryBuffer { public init(data: Data) {} }
public struct PostboxDecoder { public init(buffer: MemoryBuffer) {} }
public struct PostboxEncoder {
    public init() {}
    public func encodeObjectToRawData<T>(_ value: T) -> AdaptedPostboxDecoder.RawObjectData { .init(data: Data()) }
}
public enum ReplyMarkupButtonAction: Equatable { case disabled; public init(decoder: PostboxDecoder) { self = .disabled } }
public enum ReplyMarkupButton { public enum Style { public enum Color: Int32, Codable { case primary, danger } } }
public enum InstantPageButtonRowAlignment: Int32 { case justify, left, center, right }
public struct ItemCollectionId: Equatable {}
public struct EngineMessageReplySubject: Equatable { public var id: Int64 }
public struct StoryId {}
public protocol MessageAttribute {}
public struct MessageTextEntity: Equatable { public var marker: String }
public struct TextEntitiesMessageAttribute: MessageAttribute { public var entities: [MessageTextEntity] }
public enum AnyMediaReference {
    case standalone(media: Media), message(origin: Int64, media: Media)
    public var media: Media { switch self { case let .standalone(media), let .message(_, media): return media } }
    public var partial: Int64? { if case let .message(origin, _) = self { return origin }; return nil }
}
public enum EnqueueMessage {
    case message(text: String, attributes: [MessageAttribute], inlineStickers: [MediaId: Media], mediaReference: AnyMediaReference?, threadId: Int64?, replyToMessageId: EngineMessageReplySubject?, replyToStoryId: StoryId?, localGroupingKey: Int64?, correlationId: Int64?, bubbleUpEmojiOrStickersets: [ItemCollectionId])
}
public struct InterfaceState {
    public var editMessage: Bool?
    public var composeInputState: ChatTextInputState
    public var reply = 47
    public func withUpdatedComposeInputState(_ draft: ChatTextInputState) -> InterfaceState { var copy = self; copy.composeInputState = draft; return copy }
}
public enum InputMode { case text }
public struct PresentationState {
    public var interfaceState: InterfaceState
    public func updatedInterfaceState(_ update: (InterfaceState) -> InterfaceState) -> PresentationState { var copy = self; copy.interfaceState = update(interfaceState); return copy }
    public func updatedInputMode(_ update: (InputMode) -> InputMode) -> PresentationState { _ = update(.text); return self }
}
public final class SendSpy {
    public var sends: [(Bool?, Int32?)] = []
    public func sendCurrentMessage(silentPosting: Bool?, scheduleTime: Int32?) { sends.append((silentPosting, scheduleTime)) }
}
public final class ChatControllerImpl {
    public var presentationInterfaceState: PresentationState
    public let chatDisplayNode = SendSpy()
    public var errors = 0
    public init(_ draft: ChatTextInputState) { presentationInterfaceState = PresentationState(interfaceState: InterfaceState(composeInputState: draft)) }
    public func updateChatPresentationInterfaceState(animated: Bool, interactive: Bool, _ update: (PresentationState) -> PresentationState, completion: ((Bool) -> Void)?) {
        presentationInterfaceState = update(presentationInterfaceState)
        completion?(true)
    }
}

// The attributed-text and Markdown boundary is an identity for this test; native TextFormat is
// guarded byte-for-byte. The real structural model, UTF-16 caret and replacement code execute.
public func attributedString(from content: ChatInputContent) -> NSAttributedString {
    NSAttributedString(string: content.plainText)
}
public func chatInputContent(from text: NSAttributedString) -> ChatInputContent {
    ChatInputContent(blocks: text.string.components(separatedBy: "\n").map { .paragraph(ChatInputParagraph(runs: [ChatInputRun(text: $0)])) })
}
public func chatInputRuns(fromAttributedString text: NSAttributedString) -> [ChatInputRun] { [ChatInputRun(text: text.string)] }
public func convertMarkdownToAttributes(_ text: NSAttributedString) -> NSAttributedString { text }
public func trimChatInputText(_ text: NSAttributedString) -> NSAttributedString { text }
public func breakChatInputText(_ text: NSAttributedString) -> [NSAttributedString] { [text] }
public func generateChatInputTextEntities(_ text: NSAttributedString, generateLinks: Bool = true, maxAnimatedEmojisInText: Int = 0) -> [MessageTextEntity] { text.length == 0 ? [] : [.init(marker: "preserved")] }
public struct EnabledEntityTypes { public static let all = EnabledEntityTypes() }
public func generateTextEntities(_ text: String, enabledTypes: EnabledEntityTypes, currentEntities: [MessageTextEntity]) -> [MessageTextEntity] { currentEntities }
