"""Execute actual width preparation, native selection policy and frame placement.

Only text measurement and unrelated nominal message/UIKit values are adapters.
"""
from validate_quick_format import block
from validate_download_sheet_edge import clean

BASE = 'submodules/TelegramUI/'
BUBBLE = BASE + 'Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift'
ITEM = BASE + 'Components/Chat/ChatMessageItem/Sources/ChatMessageItem.swift'
COMMON = BASE + 'Components/Chat/ChatMessageItemCommon/Sources/'


def fixture(source, previous):
    code = (source / BUBBLE).read_text()
    common = (source / (COMMON + 'ChatMessageItemCommon.swift')).read_text()
    selection = (source / (COMMON + 'ChatMessageBubblelessSelection.swift')).read_text()
    metrics = (source / (COMMON + 'ChatMessageBubblelessMetrics.swift')).read_text()
    policy_start = previous.index('        var canHaveSelection = true', previous.index('    override public func updateSelectionState'))
    policy_end = previous.index('        if let selectionState = item.controllerInteraction.selectionState, canHaveSelection {', policy_start)
    legacy_policy = 'func originalEligibility(_ item: ChatMessageItem) -> Bool {\n' + previous[policy_start:policy_end] + '\n return canHaveSelection\n}\n'
    enum = 'enum ChatMessageItemContent {\n case message(message:Message,read:Bool,selection:Selection,attributes:Int,location:Int?)\n case group(messages:[(Message,Bool,Selection,Int,Int?)])\n'
    enum += clean(block((source / ITEM).read_text(), '    public var isInSelection: Bool {')) + '\n'
    enum += clean(block((source / ITEM).read_text(), '    public var firstMessage: EngineRawMessage {')) + '\n}\n'
    width_start = code.index('        var tmpWidth: CGFloat')
    width_end = code.index('        let bubblelessColumn:', width_start)
    budget = code[width_start:width_end]
    layout_start = code.index('        let calculatedBubbleHeight =')
    layout_end = code.index('        let bubbleContentWidth =', layout_start)
    placement = code[layout_start:layout_end]
    fixed = next(x for x in common.splitlines() if 'let bubble = ChatMessageItemBubbleLayoutConstants' in x)
    text = BOUNDARY + enum + clean(block(common, 'public struct ChatMessageItemWidthFill {'))
    text += '\n' + clean(block(common, 'public struct ChatMessageItemBubbleLayoutConstants {'))
    text += '\nfunc constants(fill: CGFloat) -> Constants {\n' + fixed + '\n var value=bubble;value.maximumWidthFill.freeMaximumFillFactor=fill;return Constants(bubble:value)\n}\n'
    text += next(x for x in metrics.splitlines() if x.startswith('public let chatMessageBubblelessSelectionRoom:')).replace('public ', '') + '\n'
    text += clean(block(selection, 'public func chatMessageSelectionContentOffset(')) + '\n' + legacy_policy
    text += block(code, 'private func nagramiXBubbleCanHaveSelection(') + '\n' + block(code, 'private func nagramiXBubbleSelectionWidthInset(')
    shell = '''
func FUNCTION(item:ChatMessageItem,params:Params,layoutConstants:Constants,avatarInset:CGFloat,allowFullWidth:Bool,isFailed:Bool,needsShareButton:Bool,isSidePanelOpen:Bool,isAd:Bool,incoming:Bool,bubbleStyle:Style) -> CGFloat {
 let baseWidth=params.width-params.leftInset-params.rightInset
 BUDGET
 return max(0,maximumContentWidth)
}
'''
    text += shell.replace('FUNCTION', 'productionBudget').replace('BUDGET', budget)
    call = '        tmpWidth -= nagramiXBubbleSelectionWidthInset(item: item, incoming: incoming, hasBubble: !bubbleStyle.isBubbleless)\n'
    assert budget.count(call) == 1
    text += shell.replace('FUNCTION', 'originalBudget').replace('BUDGET', budget.replace(call, ''))
    text += '''
func place(params:Params,layoutConstants:Constants,avatarInset:CGFloat,incoming:Bool,width:CGFloat,height:CGFloat,alignment:Alignment = .none,hideBackground:Bool = false) -> CGRect {
 let contentSize=CGSize(width:width,height:height),headerSize=CGSize.zero
 let minimalContentSize=layoutConstants.bubble.minimumSize
 let detachedContentNodesHeight:CGFloat=0,additionalTopHeight:CGFloat=0,deliveryFailedInset:CGFloat=0
 let bubblelessColumn:(originX:CGFloat,width:CGFloat)?=nil,avatarOffset:CGFloat?=nil
 let bubbleStyle=Style.bubble
''' + placement + '\n _=contentOrigin;_=contentUpperRightCorner;return backgroundFrame\n}\n' + TESTS
    return text


def negatives(text):
    variants = [
        ('missing-reserve', 'tmpWidth -= nagramiXBubbleSelectionWidthInset(item: item, incoming: incoming, hasBubble: !bubbleStyle.isBubbleless)',
         'tmpWidth -= 0', 'selected filled bubble keeps the ordinary safe-edge gap'),
        ('normal-mode-shrink', 'hasBubble, item.content.isInSelection, nagramiXBubbleCanHaveSelection(item)',
         'hasBubble, nagramiXBubbleCanHaveSelection(item)', 'ordinary geometry remains native'),
        ('unchecked-row-leak', 'hasBubble, item.content.isInSelection, nagramiXBubbleCanHaveSelection(item)',
         'hasBubble, item.content.firstSelected, nagramiXBubbleCanHaveSelection(item)', 'unchecked rows reserve the same column'),
        ('lost-eligibility', 'hasBubble, item.content.isInSelection, nagramiXBubbleCanHaveSelection(item)',
         'hasBubble, item.content.isInSelection', 'non-selectable rows keep their native width'),
        ('wrong-offset', 'return max(0.0, chatMessageSelectionContentOffset(incoming: incoming, bubbleMode: item.presentationData.chatBubbleCorners.bubbleMode))',
         'return max(0.0, chatMessageSelectionContentOffset(incoming: incoming, bubbleMode: item.presentationData.chatBubbleCorners.bubbleMode) - 6)',
         'selected filled bubble keeps the ordinary safe-edge gap'),
        ('bubbleless-shrink', 'hasBubble, item.content.isInSelection, nagramiXBubbleCanHaveSelection(item)',
         'item.content.isInSelection, nagramiXBubbleCanHaveSelection(item)', 'bubbleless width remains native'),
    ]
    for name, old, new, diagnostic in variants:
        assert text.count(old) == 1, (name, text.count(old))
        yield name, text.replace(old, new), diagnostic


BOUNDARY = r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
struct UIEdgeInsets {var top:CGFloat=0,left:CGFloat=0,bottom:CGFloat=0,right:CGFloat=0}
let UIScreenPixel:CGFloat=0.5
let chatMessageBubblelessDeliveryFailedInset:CGFloat=32
let chatMessageBubblelessMargin:CGFloat=12
func floorToScreenPixels(_ x:CGFloat)->CGFloat{floor(x*2)/2}
struct Params {var width:CGFloat,leftInset:CGFloat=0,rightInset:CGFloat=0}
enum Style {case bubble,bubbleless,bubblelessCard;var isBubbleless:Bool{self != .bubble}}
enum Alignment {case none,center}
struct Constants {var bubble:ChatMessageItemBubbleLayoutConstants}
enum Selection {case none,selectable(selected:Bool,num:Int?)}
typealias ChatHistoryMessageSelection=Selection
enum Action {case phoneCall,conferenceCall,other}
struct TelegramMediaAction {var action:Action}
struct TelegramMediaExpiredContent {}
struct Message {var id=1;var media:[Any]=[];var adAttribute:Int?}
typealias EngineRawMessage=Message
struct Thread {var effectiveTopId=1}
enum Location {case peer,replyThread(Thread)}
struct Corners {var bubbleMode=true}
struct Presentation {var chatBubbleCorners=Corners()}
struct ChatMessageItem {var content:ChatMessageItemContent;var chatLocation=Location.peer;var presentationData=Presentation();var message:EngineRawMessage{content.firstMessage}}
extension ChatMessageItemContent {
 var firstSelected:Bool {if case let .message(_,_,.selectable(value,_),_,_)=self{return value};return false}
}
func item(_ selecting:Bool,_ selected:Bool=false,kind:Int=0,group:Bool=false)->ChatMessageItem {
 var message=Message()
 if kind==1{message.media=[TelegramMediaAction(action:.other)]}
 if kind==2{message.media=[TelegramMediaExpiredContent()]}
 if kind==3{message.adAttribute=1}
 if kind==4{message.media=[TelegramMediaAction(action:.phoneCall)]}
 if kind==5{message.media=[TelegramMediaAction(action:.conferenceCall)]}
 let selection:Selection=selecting ? .selectable(selected:selected,num:nil):.none
 var value=ChatMessageItem(content:group ? .group(messages:[(message,false,selection,0,nil)]):.message(message:message,read:false,selection:selection,attributes:0,location:nil))
 if kind==6{value.chatLocation = .replyThread(Thread())}
 return value
}
'''

TESTS = r'''
@main struct BubbleEdgeTests {
 static func main(){
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data(("Bubble edge regression: "+why+"\n").utf8));exit(91)};checks+=1}
  for kind in 0...6 {for group in [false,true] {
   let i=item(true,kind:kind,group:group)
   check(nagramiXBubbleCanHaveSelection(i)==originalEligibility(i),"native eligibility stays unchanged")
  }}
  for width:CGFloat in [320,384,393,430,500,501,600,834,1024] {for safe in [(CGFloat(0),CGFloat(0)),(44,0),(0,44),(44,44)] {for avatar:CGFloat in [0,38] {for fill:CGFloat in [0.65,0.85] {for full in [false,true] {for failed in [false,true] {for share in [false,true] {
   let p=Params(width:width,leftInset:safe.0,rightInset:safe.1),c=constants(fill:fill)
   func budget(_ i:ChatMessageItem,_ incoming:Bool=true,_ style:Style = .bubble,_ legacy:Bool=false)->CGFloat {
    let f=legacy ? originalBudget:productionBudget
    return f(i,p,c,avatar,full,failed,share,false,false,incoming,style)
   }
   let ordinary=item(false),unchecked=item(true),selected=item(true,true)
   let normal=budget(ordinary),old=budget(ordinary,true,.bubble,true)
   check(normal==old,"ordinary geometry remains native")
   let selectedWidth=budget(selected),uncheckedWidth=budget(unchecked)
   check(selectedWidth==uncheckedWidth,"unchecked rows reserve the same column")
   let offset=chatMessageSelectionContentOffset(incoming:true,bubbleMode:true)
   let f0=place(params:p,layoutConstants:c,avatarInset:avatar,incoming:true,width:normal,height:100)
   let f1=place(params:p,layoutConstants:c,avatarInset:avatar,incoming:true,width:selectedWidth,height:100).offsetBy(dx:offset,dy:0)
   check(abs(f0.maxX-f1.maxX)<0.0001,"selected filled bubble keeps the ordinary safe-edge gap")
   check(f1.maxX<=p.width-p.rightInset && f1.minX>=p.leftInset,"safe edges remain inside the viewport")
   check(budget(selected,false)==budget(ordinary,false),"outgoing bubble keeps native width")
   check(budget(selected,true,.bubbleless)==budget(ordinary,true,.bubbleless),"bubbleless width remains native")
   for kind in [1,2,3,6] {check(budget(item(true,kind:kind))==normal,"non-selectable rows keep their native width")}
   let short=min(CGFloat(36),selectedWidth)
   let shortFrame=place(params:p,layoutConstants:c,avatarInset:avatar,incoming:true,width:short,height:30).offsetBy(dx:offset,dy:0)
   check(shortFrame.maxX<=f1.maxX,"short messages retain natural width within the shared boundary")
   // Explicit fixed-advance text adapter: observe reflow under the real budget,
   // without pretending to exercise TextNode/CoreText on Linux.
   let lines0=ceil(1800/max(1,normal)),lines1=ceil(1800/max(1,selectedWidth))
   check(lines1>=lines0,"text reflows vertically instead of clipping")
   check(budget(ordinary)==normal,"leaving selection restores original width")
   for group in [false,true] {check(budget(item(true,kind:0,group:group))==selectedWidth,"single rows and albums reserve one column")}
  }}}}}}}
  var off=item(true);off.presentationData.chatBubbleCorners.bubbleMode=false
  check(nagramiXBubbleSelectionWidthInset(item:off,incoming:false,hasBubble:true)==0,"bubbleless outgoing translation never becomes a negative width reserve")
  let empty=ChatMessageItem(content:.group(messages:[]))
  check(nagramiXBubbleSelectionWidthInset(item:empty,incoming:true,hasBubble:true)==0,"empty group is not selecting")
  for incoming in [false,true] {for hidden in [false,true] {
   let p=Params(width:393),c=constants(fill:0.85)
   let frame=place(params:p,layoutConstants:c,avatarInset:0,incoming:incoming,width:180,height:100,alignment:.center,hideBackground:hidden)
   check(abs(frame.midX-196.5)<=0.5,"centered placement supports dynamic visible and hidden backgrounds")
  }}
  print("Production bubble edge checks: \(checks)")
 }
}
'''
