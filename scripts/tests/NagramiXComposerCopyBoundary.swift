// UIKit pasteboard, opaque Postbox button payload and peer storage boundaries.
// All entities' Codable, formatting converters, Document/RTF and draft/send code are real.
public typealias PeerId = EnginePeer.Id
public extension EnginePeer.Id {
 typealias Id = Int64
 var id:Int64 {value}
 var namespace:Int32 {0}
 init(namespace:Int32,id:Int64){self.init(id)}
}
public extension Int64 {
    typealias Id = Int64
    var id: Int64 { self }
    var namespace: Int32 { 0 }
    func _internalGetInt64Value() -> Int64 { self }
    static func _internalFromInt64Value(_ value:Int64)->Int64 { value }
    init(namespace:Int32,id:Int64) { self=id }
    func toInt64()->Int64 { self }
}
public enum Namespaces { public enum Peer { public static let CloudUser:Int32=0 } }
public struct StickerPackReference: Equatable, Codable {}
public struct StringCodingKey: CodingKey, ExpressibleByStringLiteral {
    public init(stringLiteral:String){self.stringValue=stringLiteral}
    public let stringValue:String; public var intValue:Int? {Int(stringValue)}
    public init(stringValue:String){self.stringValue=stringValue}
    public init(intValue:Int){self.stringValue=String(intValue)}
}
public final class ChatTextInputTextCustomEmojiAttribute:NSObject {
    public let fileId:Int64;public let file:TelegramMediaFile?;public let enableAnimation:Bool
    public init(interactivelySelectedFromPackId:ItemCollectionId?,fileId:Int64,file:TelegramMediaFile?,enableAnimation:Bool=true){self.fileId=fileId;self.file=file;self.enableAnimation=enableAnimation}
}
public func buttonRef(fromChatInputButton button:ChatInputButton)->ButtonRef {
    // Buttons do not occur in text+entities. Their unchanged opaque Postbox codec is not under test.
    preconditionFailure("No button IO in clipboard fixture")
}
public struct OutgoingContentInfoMessageAttribute:MessageAttribute {
    public struct Flags:OptionSet {public let rawValue:Int;public init(rawValue:Int){self.rawValue=rawValue};public static let disableLinkPreviews=Flags(rawValue:1)}
    public var flags:Flags
}
enum UTType {
    struct TypeID {let identifier:String}
    static let utf8PlainText=TypeID(identifier:"public.utf8-plain-text")
    static let rtf=TypeID(identifier:"public.rtf")
}
final class UIPasteboard {
    static let general=UIPasteboard()
    var writes=0
    var items:[[String:Any]]=[] {didSet {writes+=1}}
}
func rtfStringWithAppliedEntities(_ text:String,entities:[MessageTextEntity])->String {
    preconditionFailure("New copy must export canonical RTF only once")
}
func convertMarkdownToAttributes(_ text:NSAttributedString)->NSAttributedString { text }
func trimChatInputText(_ text:NSAttributedString)->NSAttributedString {text}
func breakChatInputText(_ text:NSAttributedString)->[NSAttributedString] {[text]}
struct EnabledEntityTypes {static let all=EnabledEntityTypes();static let allUrl=EnabledEntityTypes()}
func generateTextEntities(_ text:String,enabledTypes:EnabledEntityTypes,currentEntities:[MessageTextEntity]=[])->[MessageTextEntity] {currentEntities}
func expandedInputStateAttributedString(_ text:NSAttributedString)->NSAttributedString {text}

#if !canImport(UIKit)
extension NSMutableAttributedString {convenience init(){self.init(string: "")}}
#endif

enum ChatPresentationInterfaceState {
    struct UrlPreview {
        let url:String;let webPage:String;let positionBelowText:Bool;let largeMedia:Bool?
    }
}
struct PreviewState {
    let interfaceState:InterfaceState
    var urlPreview:ChatPresentationInterfaceState.UrlPreview?
    func updatedUrlPreview(_ preview:ChatPresentationInterfaceState.UrlPreview?)->PreviewState {var copy=self;copy.urlPreview=preview;return copy}
}
final class PreviewDisposable {var disposed=false;func dispose(){disposed=true}}
final class PreviewController {var urlPreviewQueryState:(Int,PreviewDisposable)?}
