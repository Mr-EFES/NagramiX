// OS detector, UIKit state, peer/media graph and preview server are edges.
// Native text entities/attributes, SignalKit and every policy body are real.
public struct PeerId: Hashable {
    let value: Int64
    public init(_ value:Int64){self.value=value}
    public init(value:Int64){self.value=value}
    public func toInt64()->Int64{value}
}
public struct StickerPackReference: Equatable, Codable {}
public struct StringCodingKey: CodingKey, ExpressibleByStringLiteral {
    public let stringValue:String;public var intValue:Int?{Int(stringValue)}
    public init(stringValue:String){self.stringValue=stringValue}
    public init(intValue:Int){self.stringValue=String(intValue)}
    public init(stringLiteral:String){self.stringValue=stringLiteral}
}
public struct MessageId: Equatable { let value: Int32 }
protocol Media {}
final class TelegramMediaWebpage: Media {
    struct Loaded { let url: String }
    enum Content { case Loaded(Loaded), pending }
    var content = Content.Loaded(Loaded(url: "https://t.me/example"))
}
struct FileMedia: Media {}
struct AnyMediaReference { let media: Media }
enum RequestEditMessageMedia { case keep, update(AnyMediaReference) }
protocol MessageAttribute {}
struct TextEntitiesMessageAttribute: MessageAttribute { let entities: [MessageTextEntity] }
struct WebpagePreviewMessageAttribute: MessageAttribute {
    let leadingPreview: Bool; let forceLargeMedia: Bool?; let isManuallyAdded: Bool; let isSafe: Bool
    init(leadingPreview: Bool, forceLargeMedia: Bool?, isManuallyAdded: Bool = true, isSafe: Bool = false) {
        self.leadingPreview=leadingPreview;self.forceLargeMedia=forceLargeMedia;self.isManuallyAdded=isManuallyAdded;self.isSafe=isSafe
    }
}
struct OutgoingContentInfoFlags: OptionSet { let rawValue: Int; static let disableLinkPreviews=Self(rawValue:1) }
struct OutgoingContentInfoMessageAttribute: MessageAttribute { let flags: OutgoingContentInfoFlags }
struct EnginePeer { typealias Id=PeerId }
struct EngineRawMessage {
    var media:[Media]=[];var attributes:[MessageAttribute]=[]
    var textEntitiesAttribute:TextEntitiesMessageAttribute?{attributes.compactMap{$0 as? TextEntitiesMessageAttribute}.first}
}
final class AccountContext { let account=1 }
struct ServerWebpage { let webpage: TelegramMediaWebpage; let sourceUrl: String }
enum PreviewResult { case progress, result(ServerWebpage?) }
enum PreviewServer {
    static var requests=0
    static func reset(){requests=0}
}
func webpagePreview(account:Int,urls:[String],forPeerId:PeerId?)->Signal<PreviewResult,NoError>{
    PreviewServer.requests+=1
    return .single(.result(ServerWebpage(webpage:TelegramMediaWebpage(),sourceUrl:urls[0])))
}
let dataDetector:Bool?=true
func detectUrls(_ text:NSAttributedString?)->[String]{
    guard let text else{return []}
    let pattern="https?://[^\\s]+"
    let regex=try! NSRegularExpression(pattern:pattern)
    var urls=regex.matches(in:text.string,range:NSRange(location:0,length:text.length)).map{(text.string as NSString).substring(with:$0.range)}
    text.enumerateAttribute(ChatTextInputAttributes.textUrl,in:NSRange(location:0,length:text.length)){value,_,_ in
        if let link=value as? ChatTextInputTextUrlAttribute,!urls.contains(link.url){urls.append(link.url)}
    }
    return urls
}
struct Content { var allMedia:[Int]=[] }
struct InputState { var inputText=NSAttributedString(string:"");var content=Content() }
struct EditMessage { var inputState=InputState();var disableUrlPreviews=Set<String>() }
struct InterfaceState { var composeInputState=InputState();var editMessage:EditMessage?;var composeDisableUrlPreviews=Set<String>() }
enum ChatEditInterfaceMessageStateContent:Equatable { case plaintext, media(mediaOptions:Int) }
struct ChatEditInterfaceMessageState { let content:ChatEditInterfaceMessageStateContent;let mediaReference:Int? }
struct ChatPresentationInterfaceState {
    struct UrlPreview { let url:String;let webPage:TelegramMediaWebpage;var positionBelowText:Bool;var largeMedia:Bool? }
    struct Location { var peerId:PeerId?=nil }
    var interfaceState=InterfaceState();var urlPreview:UrlPreview?;var editingUrlPreview:UrlPreview?;var editMessageState:ChatEditInterfaceMessageState?;let chatLocation=Location()
    func updatedUrlPreview(_ v:UrlPreview?)->Self{var s=self;s.urlPreview=v;return s}
    func updatedEditingUrlPreview(_ v:UrlPreview?)->Self{var s=self;s.editingUrlPreview=v;return s}
    func updatedEditMessageState(_ v:ChatEditInterfaceMessageState)->Self{var s=self;s.editMessageState=v;return s}
}
final class PreviewController {
    var urlPreviewQueryState:(UrlPreviewState?,Disposable)?
    var editingUrlPreviewQueryState:(UrlPreviewState?,Disposable)?
}
func messageMediaEditingOptions(message:EngineRawMessage)->Int{1}
