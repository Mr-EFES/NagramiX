"""Actual wide-post eligibility, geometry and native-background integration.

ASDisplayNode/theme/wallpaper edges are adapters; this does not certify pixels.
"""
from validate_quick_format import block
VIEW='submodules/TelegramUI/Components/Chat/ChatMessageItemView/Sources/ChatMessageItemView.swift'
BACKGROUND='submodules/ChatMessageBackground/Sources/ChatMessageBackground.swift'


def fixture(source):
    view=(source/VIEW).read_text();background=(source/BACKGROUND).read_text()
    code='import Foundation\n'
    for marker in ['public enum ChatMessageBackgroundMergeType:', 'public enum ChatMessageBackgroundType:']:
        code+='\n'+block(background,marker).replace('public ','')
    code+='\n'+BOUNDARY
    for marker in ['public func nagramiXIsWideChannelPost(', 'public func nagramiXWideChannelPostColumn(']:
        code+='\n'+block(view,marker).replace('public ','')
    members=view[view.index('    public private(set) var nagramiXWidePostFrame:'):view.index('    public let layoutConstants',view.index('    public private(set) var nagramiXWidePostFrame:'))]
    code+='\nfinal class EnvelopeProbe: ASDisplayNode {\n'+members.replace('public ','')+'\n}\n'+CHECKS
    return code


BOUNDARY=r'''
class ASDisplayNode {
 var frame=CGRect.zero;weak var parent:ASDisplayNode?;var children:[ASDisplayNode]=[]
 func insertSubnode(_ node:ASDisplayNode,at:Int){node.removeFromSupernode();node.parent=self;children.insert(node,at:min(at,children.count))}
 func insertSubnode(_ node:ASDisplayNode,aboveSubnode:ASDisplayNode){let i=children.firstIndex{$0===aboveSubnode} ?? 0;insertSubnode(node,at:i+1)}
 func removeFromSupernode(){parent?.children.removeAll{$0===self};parent=nil}
}
enum ContainedViewLayoutTransition {case immediate}
struct PrincipalThemeEssentialGraphics {var id:Int;var radius:CGFloat}
struct Wallpaper {var hasWallpaper=false}
struct Corners {var bubbleMode=true;var hasTails=true;var radius:CGFloat=16}
struct Theme {var id=1}
struct ChatPresentationThemeData {var theme=Theme();var wallpaper=Wallpaper()}
class WallpaperBackgroundNode {}
class WallpaperBubbleBackgroundNode {var lastRect=CGRect.zero;func update(rect:CGRect,within:CGSize,transition:ContainedViewLayoutTransition){lastRect=rect}}
struct PresentationResourcesChat {
 static func principalGraphics(theme:Theme,wallpaper:Wallpaper,bubbleCorners:Corners)->PrincipalThemeEssentialGraphics{PrincipalThemeEssentialGraphics(id:theme.id,radius:bubbleCorners.radius)}
}
class ChatMessageBackground:ASDisplayNode {
 weak var backdropNode:ChatMessageBubbleBackdrop?;var type:ChatMessageBackgroundType?;var graphics:PrincipalThemeEssentialGraphics?
 func setType(type:ChatMessageBackgroundType,highlighted:Bool,graphics:PrincipalThemeEssentialGraphics,maskMode:Bool,hasWallpaper:Bool,transition:ContainedViewLayoutTransition,backgroundNode:WallpaperBackgroundNode?){self.type=type;self.graphics=graphics}
 func updateLayout(size:CGSize,transition:ContainedViewLayoutTransition){}
}
class ChatMessageBubbleBackdrop:ASDisplayNode {
 var type:ChatMessageBackgroundType?;var backgroundContent:WallpaperBubbleBackgroundNode?=WallpaperBubbleBackgroundNode()
 func setType(type:ChatMessageBackgroundType,theme:ChatPresentationThemeData,essentialGraphics:PrincipalThemeEssentialGraphics,maskMode:Bool,backgroundNode:WallpaperBackgroundNode?){self.type=type}
 func updateFrame(_ value:CGRect,transition:ContainedViewLayoutTransition){frame=value}
}
enum PeerInfo {case broadcast(Int),group}
class TelegramChannel {var info:PeerInfo;init(_ info:PeerInfo){self.info=info}}
struct MessageID {var peerId=1}
struct Message {var id=MessageID();var peers:[Int:Any]=[1:TelegramChannel(.broadcast(0))];var adAttribute:Int?;var incoming=true;func effectivelyIncoming(_ id:Int)->Bool{incoming}}
enum ChatLocation {case peer(Int),replyThread(Int),custom}
struct Presentation {var isPreview=false;var chatBubbleCorners=Corners();var theme=ChatPresentationThemeData()}
struct Account {var peerId=2}
struct Context {var account=Account()}
struct PresentationContext {var backgroundNode:WallpaperBackgroundNode?=WallpaperBackgroundNode()}
struct Interaction {var presentationContext=PresentationContext()}
struct ChatMessageItem {var message=Message();var chatLocation=ChatLocation.peer(1);var presentationData=Presentation();var context=Context();var controllerInteraction=Interaction()}
'''

CHECKS=r'''
@main struct Main {
 static func main() {
  var checks=0
  func check(_ ok:Bool,_ why:String){guard ok else{print("FAIL "+why);exit(91)};checks+=1}
  var item=ChatMessageItem()
  for enabled in [false,true] {for preview in [false,true] {for ad in [false,true] {for broadcast in [false,true] {for peerHistory in [false,true] {
   item.presentationData.isPreview=preview;item.message.adAttribute=ad ? 1:nil
   item.message.peers=[1:TelegramChannel(broadcast ? .broadcast(0):.group)]
   item.chatLocation=peerHistory ? .peer(1):.replyThread(1)
   check(nagramiXIsWideChannelPost(item:item,enabled:enabled)==(enabled && !preview && !ad && broadcast && peerHistory),"only eligible broadcast history receives envelope")
  }}}}}
  item=ChatMessageItem();item.message.peers=[1:"private user"]
  check(!nagramiXIsWideChannelPost(item:item,enabled:true),"ordinary private chat keeps native layout")
  for width:CGFloat in [240,320,393,430,768,1024] {for safe:CGFloat in [0,20,44] {for avatar:CGFloat in [0,38] {for selection:CGFloat in [0,42] {for delivery:CGFloat in [0,24] {
   let column=nagramiXWideChannelPostColumn(width:width,leftInset:safe,rightInset:safe,edgeInset:3,contentLeft:2,contentRight:2,avatarInset:avatar,deliveryFailedInset:delivery,selectionInset:selection)
   check(column.width>=0 && column.minX>=safe,"column is finite and inside safe edge")
   check(column.maxX+selection<=width-safe+0.001,"selection translation stays within right safe edge")
   let normal=nagramiXWideChannelPostColumn(width:width,leftInset:safe,rightInset:safe,edgeInset:3,contentLeft:2,contentRight:2,avatarInset:avatar,deliveryFailedInset:delivery,selectionInset:0)
   check(abs(normal.maxX-(column.maxX+selection))<0.001,"right gap is identical before and during selection")
  }}}}}
  item=ChatMessageItem();let view=EnvelopeProbe();let parent=ASDisplayNode();let artwork=ASDisplayNode();artwork.frame=CGRect(x:6,y:0,width:184,height:184);parent.insertSubnode(artwork,at:0)
  let original=artwork.frame;let frame=CGRect(x:3,y:0,width:381,height:220)
  view.updateNagramiXWidePostContainer(item:item,parent:parent,frame:frame)
  check(parent.children.count==3 && parent.children.last===artwork,"native background sits behind original artwork")
  check(artwork.frame==original,"artwork size and proportion unchanged")
  let background=parent.children.compactMap{$0 as? ChatMessageBackground}.first!
  let backdrop=parent.children.compactMap{$0 as? ChatMessageBubbleBackdrop}.first!
  check(background.frame==frame && backdrop.frame==frame,"both native background layers share envelope")
  check(background.type == .incoming(.None),"native bubble style and direction selected")
  view.updateNagramiXWidePostAbsoluteRect(CGRect(x:10,y:50,width:393,height:220),within:CGSize(width:393,height:852))
  check(backdrop.backgroundContent!.lastRect==frame.offsetBy(dx:10,dy:50),"wallpaper tracks actual row coordinates")
  item.presentationData.theme.theme.id=2;item.presentationData.chatBubbleCorners.radius=24
  item.presentationData.chatBubbleCorners.hasTails=false
  view.updateNagramiXWidePostContainer(item:item,parent:parent,frame:frame)
  check(parent.children.count==3 && background.graphics!.id==2 && background.graphics!.radius==24,"theme change reuses correct native graphics")
  check(background.type == .incoming(.Extracted),"tail setting respected")
  view.updateNagramiXWidePostContainer(item:item,parent:parent,frame:nil)
  check(parent.children.count==1 && parent.children[0]===artwork && view.nagramiXWidePostFrame==nil,"OFF fully restores native artwork-only row")
  item.presentationData.chatBubbleCorners.bubbleMode=false
  view.updateNagramiXWidePostContainer(item:item,parent:parent,frame:frame)
  check(parent.children.count==1 && view.nagramiXWidePostFrame==frame,"bubbleless mode keeps wide envelope without introducing bubble")
  item.presentationData.chatBubbleCorners.bubbleMode=true;item.message.incoming=false
  view.updateNagramiXWidePostContainer(item:item,parent:parent,frame:frame)
  check(parent.children.compactMap{$0 as? ChatMessageBackground}.first!.type == .outgoing(.Extracted),"outgoing channel post uses proper native direction")
  print("Wide post envelope production checks: \(checks)")
 }
}
'''
