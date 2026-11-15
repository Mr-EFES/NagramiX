// Только аккаунт, очередь и opaque rich serializer — явные IO-границы.
// Новый native file/caption путь, Document и форматные converters исполняются.
public enum EngineMessage {public typealias Attribute=MessageAttribute}
public struct RichTextMessageAttribute:MessageAttribute {
 public let instantPage:Int
 public init(instantPage:Int,fullInstantPage:Int?){self.instantPage=instantPage}
}
public enum RichTextAttachmentScreen {public typealias Document=FixtureDocument}
public typealias FixtureDocument=Document
enum FixtureComposed {case rich(Int),plain(String,[MessageTextEntity]),empty}
enum FixtureCaption {
 static let context=FixtureCaptionContext()
 static var richCalls=0,lastRichDocument:Document?
}
final class FixtureCaptionContext {
 var userLimits=FixtureCaptionLimits(),isPremium=true
}
struct FixtureCaptionLimits {var maxCaptionLength=4096}
struct FixturePackId {var id:Int64=7}
struct FixturePack {var id=FixturePackId()}
final class CachedChannelData {var emojiPack:FixturePack?}
struct FixturePeerView {var cachedData:AnyObject?}
struct FixturePeerState {var peerView:FixturePeerView?}
struct FixtureCaptionContentData {var state=FixturePeerState()}
struct FixtureChatLocation {var threadId:Int64?=17}
struct FixtureReply {var subjectModel=EngineMessageReplySubject(id:47)}
extension InterfaceState {var replyMessageSubject:FixtureReply?{FixtureReply()}}
extension ChatControllerImpl {
 var context:FixtureCaptionContext{FixtureCaption.context}
 var contentData:FixtureCaptionContentData?{nil}
 var chatLocation:FixtureChatLocation{FixtureChatLocation()}
}
enum FixtureFileAttribute {case CustomEmoji(Bool,Bool,String,StickerPackReference)}
extension TelegramMediaFile {
 var isPremiumEmoji:Bool{false}
 var attributes:[FixtureFileAttribute]{[]}
}
extension EngineMedia {
 func _asMedia()->Media {switch self {case let .file(v):return v;case let .image(v):return v;case let .map(v):return v}}
}
func composeRichMessage(from document:Document,media:[String:EngineMedia],forSendPreview:Bool)->FixtureComposed {
 FixtureCaption.richCalls+=1;FixtureCaption.lastRichDocument=document
 return .rich(123)
}
func chatInputContent(fromDocument document:Document,media:[String:EngineMedia],emojiFiles:[Int64:TelegramMediaFile])->ChatInputContent {
 chatInputContent(fromDocument:document,resolveEmoji:{ref in Int64(ref.id).map{($0,emojiFiles[$0])}},resolveMedia:{media[$0]})
}
public func chatInputButton(fromButtonRef button:ButtonRef)->ChatInputButton {
 preconditionFailure("Opaque Postbox button IO is outside the native file/caption fixture")
}
