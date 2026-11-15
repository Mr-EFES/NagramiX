"""Реальные Arguments, измерение и формулы рамок; типографика — явная граница."""
from validate_quick_format import block
import re

D='submodules/TelegramUI/Components/Chat/ChatMessageDateAndStatusNode/Sources/ChatMessageDateAndStatusNode.swift'
S='submodules/TelegramUI/Components/Chat/ChatMessageStickerItemNode/Sources/ChatMessageStickerItemNode.swift'
A='submodules/TelegramUI/Components/Chat/ChatMessageAnimatedStickerItemNode/Sources/ChatMessageAnimatedStickerItemNode.swift'
M='submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift'
T='submodules/Display/Source/TextNode.swift'


def line(text, needle):
    values=[x.strip() for x in text.splitlines() if needle in x]
    assert len(values)==1,(needle,len(values))
    return values[0]


def producer(source):
    native=(source/D).read_text();text=(source/T).read_text()
    args=block(native,'    public struct Arguments {')
    nested='\n'.join(block(native,m) for m in ['    public struct TrailingReactionSettings {','    public struct StandaloneReactionSettings {','    public enum LayoutInput {'])
    enums='\n'.join(block(native,m) for m in ['public enum ChatMessageDateAndStatusOutgoingType:','public enum ChatMessageDateAndStatusType:'])
    typography=block(text,'public enum TextVerticalAlignment {')+'\n'+block(text,'public final class TextNodeLayoutArguments {')
    measurement=native[native.index('            let dateFont = '):native.index('            let checkOffset = ')]
    size=line(native,'let layoutSize = CGSize(width: leftInset + impressionWidth + date.size.width')
    sent=line(native,'checkSentFrame = CGRect(origin:')
    read=line(native,'checkReadFrame = CGRect(origin:')
    clock=line(native,'clockPosition = CGPoint(x: leftInset + date.size.width')
    offset=line(native,'let checkOffset = ')
    metric=line(native,'let checkSize: CGFloat = ').replace('let checkSize:','let glyphMetric:')
    return (BOUNDARY+'\n'+typography+'\n'+enums+'\n'+(source/M).read_text()+'\npublic enum ChatMessageDateAndStatusNode {\n'+nested+'\n'+args+'\n}\n'+r'''
public enum StatusProbe {
 public static func measure(_ arguments:ChatMessageDateAndStatusNode.Arguments)->(CGSize,CGRect,CGRect,CGPoint,String) {
  let updatedDateText=arguments.dateText
  let dateColor=UIColor.white
  let dateLayout=TextNode.asyncLayout(nil)
'''+measurement+r'''
  let leftInset:CGFloat=0,impressionWidth:CGFloat=0
  let backgroundInsets=UIEdgeInsets(top:2,left:7,bottom:2,right:7)
  let offset:CGFloat = -0.5
'''+offset+'\n'+metric+r'''
  let checkSize=CGSize(width:glyphMetric,height:ceil(glyphMetric*0.85))
  let statusWidth:CGFloat=floor(floor(arguments.presentationData.fontSize.baseDisplaySize*13.0/17.0))
  var checkSentFrame:CGRect?
  var checkReadFrame:CGRect?
  var clockPosition=CGPoint()
'''+sent+'\n'+read+'\n'+clock+'\n'+size+r'''
  let visible=dateApply()
  return (layoutSize,checkSentFrame!.offsetBy(dx:backgroundInsets.left,dy:backgroundInsets.top),checkReadFrame!.offsetBy(dx:backgroundInsets.left,dy:backgroundInsets.top),CGPoint(x:clockPosition.x+backgroundInsets.left,y:clockPosition.y+backgroundInsets.top),visible.text)
 }
}
''')


def calls(source):
    result=''
    for kind,path in [('Static',S),('Animated',A)]:
        text=(source/path).read_text()
        date=line(text,'dateText: ')
        reference=line(text,'dateTextForHeight: ')
        result+=r'''
func arguments__KIND__(_ enabled:Bool,_ dice:Bool,_ font:CGFloat,_ dateText:String)->ChatMessageDateAndStatusNode.Arguments {
 let mediaSettings=NagramiXMediaSettings(photoQuality:100,sendLargePhotos:true,stickerSize:100,showStickerTime:enabled)
 let telegramDice:Int?=dice ? 1:nil
 _ = telegramDice
 return ChatMessageDateAndStatusNode.Arguments(
  context:AccountContext(),presentationData:ChatPresentationData(font),edited:false,impressionCount:nil,
  __DATE__
  __REFERENCE__
  type:.FreeOutgoing(.Sent(read:true)),layoutInput:.standalone(reactionSettings:nil),constrainedSize:CGSize(width:800,height:1000),availableReactions:nil,savedMessageTags:nil,reactions:[],reactionPeers:[],displayAllReactionPeers:false,areReactionsTags:false,areStarReactionsEnabled:false,messageEffect:nil,replyCount:0,starsCount:nil,isPinned:false,hasAutoremove:false,canViewReactionList:false,animationCache:AnimationCache(),animationRenderer:MultiAnimationRenderer())
}
'''.replace('__KIND__',kind).replace('__DATE__',date).replace('__REFERENCE__',reference)
    # Native caller positioning must consume the corrected node height.
    static=(source/S).read_text();animated=(source/A).read_text()
    static_frame=line(static,'var dateAndStatusFrame = CGRect(').replace('var dateAndStatusFrame','let dateAndStatusFrame',1)
    animated_frame=line(animated,'let dateAndStatusFrame = CGRect(')
    common='let wideColumn:CGRect?=nil;let displayLeftInset:CGFloat=0;let layoutSize=CGSize(width:390,height:300);let updatedImageFrame=CGRect(x:20,y:0,width:300,height:240);\n'
    result+='\nfunc nativeStaticFrame(_ dateAndStatusSize:CGSize)->CGRect {\n'+common+'let dateOffset=CGPoint(x:dateAndStatusSize.width+4,y:dateAndStatusSize.height+16)\n'+static_frame+'\n_ = wideColumn;return dateAndStatusFrame\n}\n'
    result+='\nfunc nativeAnimatedFrame(_ dateAndStatusSize:CGSize)->CGRect {\n'+common+'let imageBottomPadding:CGFloat=20\n'+animated_frame+'\n_ = layoutSize;return dateAndStatusFrame\n}\n'
    return result


def consumer(source):
    return 'import Foundation\n#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n'+calls(source)+TESTS


def fixture(source):
    return producer(source)+'\n'+consumer(source)


BOUNDARY=r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
#if canImport(UIKit)
import UIKit
import CoreText
enum Font {static func regular(_ value:CGFloat)->UIFont{UIFont.systemFont(ofSize:value)}}
extension NSAttributedString {
 convenience init(string:String,font:UIFont,textColor:UIColor){self.init(string:string,attributes:[.font:font,.foregroundColor:textColor])}
}
#else
public struct UIColor {public static let white=UIColor()}
public struct UIEdgeInsets {public var top:CGFloat,left:CGFloat,bottom:CGFloat,right:CGFloat;public init(top:CGFloat=0,left:CGFloat=0,bottom:CGFloat=0,right:CGFloat=0){self.top=top;self.left=left;self.bottom=bottom;self.right=right}}
public enum CTLineTruncationType {case middle}
public enum NSTextAlignment {case natural}
enum Font {static func regular(_ value:CGFloat)->CGFloat{value}}
extension NSAttributedString {
 convenience init(string:String,font:CGFloat,textColor:UIColor){self.init(string:string,attributes:[NSAttributedString.Key("probeFontSize"):font])}
}
#endif
public struct TextNodeCutout {}
public struct TextNodeLayout {public let size:CGSize}
public final class TextNode {
 public let text:String
 init(_ text:String){self.text=text}
 public static func asyncLayout(_ maybeNode:TextNode?)->(TextNodeLayoutArguments)->(TextNodeLayout,()->TextNode){
  return {a in
   let text=a.attributedString?.string ?? ""
   let size:CGSize
   if text.isEmpty {size = .zero} else {
    #if canImport(UIKit)
    let rect=a.attributedString!.boundingRect(with:a.constrainedSize,options:[.usesLineFragmentOrigin,.usesFontLeading],context:nil)
    size=CGSize(width:ceil(rect.width),height:ceil(rect.height))
    #else
    let font=a.attributedString!.attribute(NSAttributedString.Key("probeFontSize"),at:0,effectiveRange:nil) as? CGFloat ?? 11
    size=CGSize(width:CGFloat(text.count)*font*0.6,height:ceil(font*1.2))
    #endif
   }
   return (TextNodeLayout(size:size),{TextNode(text)})
  }
 }
}
public struct AccountContext {public init(){}}
public struct ChatPresentationData {
 public struct Size {public var baseDisplaySize:CGFloat}
 public var fontSize:Size
 public init(_ value:CGFloat){fontSize=Size(baseDisplaySize:value)}
}
public struct AvailableReactions {public init(){}}
public struct SavedMessageTags {public init(){}}
public struct MessageReaction {public struct Reaction {public init(){}};public init(){}}
public struct EnginePeer {public init(){}}
public enum AvailableMessageEffects {public struct MessageEffect {public init(){}}}
public struct AnimationCache {public init(){}}
public struct MultiAnimationRenderer {public init(){}}
'''

TESTS=r'''
@main enum StickerSpacingChecks {
 static func main(){
  var checks=0
  func check(_ condition:Bool,_ message:String){if !condition{print("FAIL: "+message);exit(96)};checks+=1}
  for font:CGFloat in [14,17,20,26,34] {for text in ["15:58","٢٣:٥٩","8:03 PM"] {
   for kind in [0,1] {
    let make=kind==0 ? argumentsStatic:argumentsAnimated
    let visible=StatusProbe.measure(make(true,false,font,text))
    let hidden=StatusProbe.measure(make(false,false,font,text))
    check(hidden.4.isEmpty && visible.4==text,"only timestamp glyphs disappear")
    check(hidden.0.height==visible.0.height && hidden.0.height>4,"hidden time retains native status row height")
    check(hidden.0.width<visible.0.width,"hidden time keeps compact width")
    for value in [visible,hidden] {
     check(value.1.minY>=0 && value.1.maxY<=value.0.height,"sent mark stays inside reserved row")
     check(value.2.minY>=0 && value.2.maxY<=value.0.height,"read mark stays inside reserved row")
     check(value.3.y>=0 && value.3.y<=value.0.height,"sending clock remains within row")
    }
    let frame=kind==0 ? nativeStaticFrame(hidden.0):nativeAnimatedFrame(hidden.0)
    let baseline=kind==0 ? nativeStaticFrame(visible.0):nativeAnimatedFrame(visible.0)
    check(frame.minY==baseline.minY && frame.maxY==baseline.maxY,"native caller preserves time-ON vertical spacing")
    check(frame.minY+hidden.1.maxY<=frame.maxY,"sent mark never overflows into next message")
    check(frame.minY+hidden.2.maxY<=frame.maxY,"read mark never overflows into next message")
   }
   let diceOn=StatusProbe.measure(argumentsAnimated(true,true,font,text))
   let diceOff=StatusProbe.measure(argumentsAnimated(false,true,font,text))
   check(diceOn.0==diceOff.0 && diceOff.4==text,"dice retain native time regardless of sticker toggle")
   let ordinary=ChatMessageDateAndStatusNode.Arguments(context:AccountContext(),presentationData:ChatPresentationData(font),edited:false,impressionCount:nil,dateText:"",type:.FreeIncoming,layoutInput:.standalone(reactionSettings:nil),constrainedSize:CGSize(width:800,height:1000),availableReactions:nil,savedMessageTags:nil,reactions:[],reactionPeers:[],displayAllReactionPeers:false,areReactionsTags:false,areStarReactionsEnabled:false,messageEffect:nil,replyCount:0,starsCount:nil,isPinned:false,hasAutoremove:false,canViewReactionList:false,animationCache:AnimationCache(),animationRenderer:MultiAnimationRenderer())
   check(StatusProbe.measure(ordinary).0.height==4,"other empty-date callers keep their original geometry")
  }}
  print("PASS sticker spacing production checks: \(checks)")
 }
}
'''
