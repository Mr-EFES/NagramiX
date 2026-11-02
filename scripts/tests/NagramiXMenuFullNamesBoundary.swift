import Foundation

// UIKit/CoreText rendering are controlled boundaries. Production geometry,
// name-cache integration and pin action declarations are extracted unchanged.
struct FakeFont { let size: CGFloat; var lineHeight: CGFloat { size * 1.2 } }
enum Font {
    static func regular(_ size: CGFloat) -> FakeFont { FakeFont(size:size) }
    static func bold(_ size: CGFloat) -> FakeFont { FakeFont(size:size) }
}
enum TextAlignment { case center }
struct DrawingOptions: OptionSet { let rawValue: Int; static let usesLineFragmentOrigin = DrawingOptions(rawValue:1) }
extension NSAttributedString {
    convenience init(string: String, font: FakeFont, textColor: Int, paragraphAlignment: TextAlignment = .center) {
        self.init(string:string,attributes:[NSAttributedString.Key("fontSize"):font.size])
    }
    func boundingRect(with size: CGSize, options: DrawingOptions, context: Int?) -> CGRect {
        CGRect(x:0,y:0,width:min(size.width,CGFloat(string.count)*6),height:16)
    }
}
extension CGSize {
    func aspectFilled(_ size: CGSize) -> CGSize {
        let scale=max(size.width/width,size.height/height)
        return CGSize(width:width*scale,height:height*scale)
    }
}
struct UIImage {
    let size: CGSize
    init?(bundleImageName: String) { size=CGSize(width:20,height:20) }
}
final class ImmediateTextNode {
    var maximumNumberOfLines=1
    var attributedText: NSAttributedString?
    var measurements=0
    var measuredWidths: [CGFloat]=[]
    func updateLayout(_ size: CGSize) -> CGSize {
        measurements += 1;measuredWidths.append(size.width)
        let text=attributedText!.string
        let font=attributedText!.attribute(NSAttributedString.Key("fontSize"),at:0,effectiveRange:nil) as! CGFloat
        let lines=max(1,ceil(CGFloat(text.count)*font*0.55/size.width))
        let visibleLines=maximumNumberOfLines == 0 ? lines : min(lines,CGFloat(maximumNumberOfLines))
        return CGSize(width:size.width,height:min(size.height,visibleLines*font*1.2))
    }
}
struct EnginePeer {
    var firstName: String
    var lastName: String
    var isScam=false,isFake=false,isVerified=false,isPremium=false
    var emojiStatus: Int?
    var compactDisplayTitle: String { firstName }
    func displayTitle(strings: Strings, displayOrder: Bool) -> String {
        (displayOrder ? [lastName,firstName] : [firstName,lastName]).filter { !$0.isEmpty }.joined(separator:" ")
    }
}
extension EnginePeer { init(_ peer: EnginePeer) { self=peer } }
struct Strings {
    var Message_ScamAccount="SCAM",Message_FakeAccount="FAKE"
    func Conversation_PinMessagesFor(_ name: String) -> Formatted { Formatted(string:"Закрепить у меня и "+name) }
}
struct Formatted { let string: String }
struct Theme {
    struct Menu { let primaryColor=1 }
    struct Chat { struct Message { struct Incoming { let scamColor=1 };let incoming=Incoming() };let message=Message() }
    let contextMenu=Menu();let chat=Chat()
}
struct PresentationData {
    struct FontSize { var baseDisplaySize: CGFloat=17 }
    var listsFontSize=FontSize(),strings=Strings(),nameDisplayOrder=false
    let theme=Theme()
}
struct Configuration { var isPremiumDisabled=false;static func with(appConfiguration: Bool) -> Self { Self(isPremiumDisabled:appConfiguration) } }
typealias PremiumConfiguration=Configuration
final class CurrentConfig { var value=false;func with(_ f: (Bool)->Bool) -> Bool { f(value) } }
final class Context { let currentAppConfiguration=CurrentConfig() }
struct Item { var peer: EnginePeer;var reaction: Int?;var timestamp: Int? }
struct ItemsState { var mergedItems: [Item]=[];var totalCount=0 }
enum TextLayout { case singleLine,multiline }
enum TextColor { case primary }
final class ActionController {
    var dismissed=false
    func dismiss(completion: (()->Void)?) { dismissed=true;completion?() }
}
struct ContextMenuActionItem {
    let text: String
    let textLayout: TextLayout
    let action: (ActionController?,Int)->Void
    init(text: String,textColor: TextColor,textLayout: TextLayout = .singleLine,icon: (Int)->Int?,action: @escaping (ActionController?,Int)->Void) {
        self.text=text;self.textLayout=textLayout;self.action=action
    }
}
enum ContextMenuItem { case action(ContextMenuActionItem),separator }
