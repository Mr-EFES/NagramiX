"""Run the production poster, clipping/layout lease and restore transaction bodies."""
from validate_quick_format import block
from validate_pip_swipe_handoff import clean, U, G, N

D = 'submodules/GalleryUI/Sources/GalleryVideoDecoration.swift'


def poster_fixture(source):
    text = (source / U).read_text()
    poster = clean(block(text, 'private final class UniversalVideoGalleryItemPictureInPictureNode:'))
    d = (source / D).read_text()
    decoration = clean(block(d, 'public final class GalleryVideoDecoration:'))
    maker = clean(block(text, '    func nagramiXMakePiPPreviewPoster()'))
    host = '''
final class PosterController {let view=UIView()}
final class PosterHost {
 var item:UniversalVideoGalleryItem?
 var videoNode:ASDisplayNode?
 let controller=PosterController()
 func galleryController()->PosterController?{controller}
''' + maker + '\n}\n'
    return POSTER_BOUNDARY + poster + '\n' + decoration + host + POSTER_TESTS


def restore_fixture(source):
    text = (source / U).read_text()
    names = [
        '    private func nagramiXCancelInterfaceRestore()',
        '    private func nagramiXRestoreInterface(',
        '    public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler',
        '    public func requestExpand()',
        '    public func pictureInPictureControllerDidStartPictureInPicture(',
    ]
    methods = '\n'.join(clean(block(text, name)) for name in names)
    return RESTORE_BOUNDARY + '\nfinal class Restorer {\n' + RESTORE_FIELDS + methods + '\n}\n' + RESTORE_TESTS


POSTER_BOUNDARY = r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
extension CGRect {var center:CGPoint{CGPoint(x:midX,y:midY)}}
enum NoError:Error {}
struct Signal<T,E> {let name:String}
struct MediaPlayerStatus {}
typealias ImageDraw = (TransformImageArguments)->DrawingContext?
struct UIEdgeInsets {var top:CGFloat=0,left:CGFloat=0,bottom:CGFloat=0,right:CGFloat=0}
struct Corner {var radius:CGFloat=0}
struct ImageCorners {var topLeft=Corner(),topRight=Corner(),bottomLeft=Corner(),bottomRight=Corner();var extendedEdges=UIEdgeInsets()}
func isRoundEqualCorners(_ c:ImageCorners)->Bool {c.topLeft.radius==c.topRight.radius && c.topLeft.radius==c.bottomLeft.radius && c.topLeft.radius==c.bottomRight.radius}
enum Resize {case aspectFill}
struct TransformImageArguments {let corners:ImageCorners;let imageSize:CGSize;let boundingSize:CGSize;let intrinsicInsets:UIEdgeInsets;var resizeMode:Resize = .aspectFill;var drawingRect:CGRect{CGRect(origin:.zero,size:boundingSize)}}
final class UIColor {static let black=UIColor();let cgColor=0}
struct Image {let cgImage=0;let scale:CGFloat=1;let size=CGSize(width:10,height:10)}
struct Graphics {func setFillColor(_ x:Int){};func fill(_ r:CGRect){}}
final class DrawingContext {init?(size:CGSize,clear:Bool){};func withContext(_ f:(Graphics)->Void){f(Graphics())};func generateImage()->Image?{Image()}}
func addCorners(_ context:DrawingContext,arguments:TransformImageArguments){}
struct NSValue {init(cgPoint:CGPoint){};init(cgRect:CGRect){}}
let kCAMediaTimingFunctionSpring="spring"
enum AnimationClock {static var pending:[()->Void]=[];static func flush(){let work=pending;pending=[];work.forEach{$0()}}}
final class CALayer {
 var mask:CALayer?,contents:Int?,contentsScale:CGFloat=1,contentsCenter=CGRect.zero
 var frame=CGRect.zero
 var position:CGPoint{frame.center}
 var capture=false,bypass=false
 func animate(from:Any,to:Any,keyPath:String,timingFunction:String,duration:Double,removeOnCompletion:Bool=false,completion:((Bool)->Void)?=nil){if let completion{AnimationClock.pending.append({completion(true)})}}
}
final class UIView {
 var frame=CGRect.zero;let layer=CALayer();weak var superview:UIView?;var subviews:[UIView]=[]
 func addSubview(_ view:UIView){view.removeFromSuperview();subviews.append(view);view.superview=self}
 func removeFromSuperview(){superview?.subviews.removeAll{$0===self};superview=nil}
 func convert(_ rect:CGRect,to view:UIView)->CGRect{rect.offsetBy(dx:frame.minX-view.frame.minX,dy:frame.minY-view.frame.minY)}
}
class ASDisplayNode {
 let view=UIView();var layer:CALayer{view.layer};var children:[ASDisplayNode]=[];weak var supernode:ASDisplayNode?
 var isUserInteractionEnabled=true,clipsToBounds=false;var cornerRadius:CGFloat=0
 var backgroundColor:UIColor?
 var frame:CGRect{get{view.frame}set{view.frame=newValue;layer.frame=newValue}}
 var bounds:CGRect{CGRect(origin:.zero,size:frame.size)}
 init(){}
 func addSubnode(_ node:ASDisplayNode){node.removeFromSupernode();children.append(node);node.supernode=self;view.addSubview(node.view)}
 func removeFromSupernode(){supernode?.children.removeAll{$0===self};supernode=nil;view.removeFromSuperview()}
}
final class TransformImageNode:ASDisplayNode {
 var source:String?,arguments:TransformImageArguments?,synchronous=false
 func setSignal(_ signal:Signal<ImageDraw,NoError>,attemptSynchronously:Bool=false,dispatchOnDisplayLink:Bool=true){source=signal.name;synchronous=attemptSynchronously}
 func asyncLayout()->(TransformImageArguments)->()->Void {{args in {self.arguments=args}}}
}
enum ContainedViewLayoutTransition {
 case immediate,animated
 func updateFrame(node:ASDisplayNode,frame:CGRect){node.frame=frame}
 func updateFrame(layer:CALayer,frame:CGRect){layer.frame=frame}
}
protocol UniversalVideoDecoration:AnyObject {}
protocol UniversalVideoContentNode:AnyObject {func updateLayout(size:CGSize,actualSize:CGSize,transition:ContainedViewLayoutTransition)}
final class Player:ASDisplayNode,UniversalVideoContentNode {var layouts=0;func updateLayout(size:CGSize,actualSize:CGSize,transition:ContainedViewLayoutTransition){layouts+=1}}
protocol Media:AnyObject {var id:Int{get}}
final class TelegramMediaFile:Media {let id:Int;init(_ id:Int){self.id=id}}
final class TelegramMediaImage:Media {let id:Int;init(_ id:Int){self.id=id}}
struct Page {var image:TelegramMediaImage?}
final class TelegramMediaWebpage:Media {enum Content{case Loaded(Page)};let id=100;let content:Content;init(_ image:TelegramMediaImage){content = .Loaded(Page(image:image))}}
struct FileMediaReference {let media:TelegramMediaFile;static func standalone(media:TelegramMediaFile)->Self{Self(media:media)}}
struct ImageMediaReference {let media:TelegramMediaImage;static func standalone(media:TelegramMediaImage)->Self{Self(media:media)}}
enum MediaResourceUserLocation {case other}
struct Postbox {}
struct Account {let postbox=Postbox()}
struct AccountContext {let account=Account()}
protocol UniversalVideoContent {var dimensions:CGSize{get}}
final class NativeVideoContent:UniversalVideoContent {let dimensions=CGSize(width:640,height:360);let fileReference=FileMediaReference(media:TelegramMediaFile(11));let userLocation=MediaResourceUserLocation.other}
final class HLSVideoContent:UniversalVideoContent {let dimensions=CGSize(width:640,height:360);let fileReference=FileMediaReference(media:TelegramMediaFile(12));let userLocation=MediaResourceUserLocation.other}
final class WebEmbedVideoContent:UniversalVideoContent {let dimensions=CGSize(width:640,height:360);let webpageContent=Page(image:TelegramMediaImage(13))}
final class OtherContent:UniversalVideoContent {let dimensions=CGSize(width:640,height:360)}
struct Message {let media:Media?}
struct GalleryMediaSubject {}
enum ContentInfo {case message(Message,GalleryMediaSubject?);case webPage(TelegramMediaWebpage,Media,Int)}
final class UniversalVideoGalleryItem {
 let context=AccountContext();let content:UniversalVideoContent
 var contentInfo:ContentInfo?,isSecret=false,peerIsCopyProtected=false
 init(_ content:UniversalVideoContent){self.content=content}
}
func selectedMediaForMessage(message:Message,mediaSubject:GalleryMediaSubject?)->Media?{message.media}
func mediaGridMessageVideo(postbox:Postbox,userLocation:MediaResourceUserLocation,videoReference:FileMediaReference,useLargeThumbnail:Bool,synchronousLoad:Bool,useMiniThumbnailIfAvailable:Bool)->Signal<ImageDraw,NoError>{precondition(useLargeThumbnail && synchronousLoad && useMiniThumbnailIfAvailable);return Signal(name:"video:\(videoReference.media.id)")}
func chatMessagePhoto(postbox:Postbox,userLocation:MediaResourceUserLocation,photoReference:ImageMediaReference,synchronousLoad:Bool,highQuality:Bool)->Signal<ImageDraw,NoError>{precondition(synchronousLoad && highQuality);return Signal(name:"image:\(photoReference.media.id)")}
func nagramiXSetLayerDisableScreenshots(_ layer:CALayer,_ required:Bool,allowsBypass:Bool){layer.capture=required;layer.bypass=allowsBypass}
'''

POSTER_TESTS = r'''
@main struct Tests {
 static func main(){
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data((message+"\n").utf8));exit(96)};checks+=1}
  for (content,id) in [(NativeVideoContent() as UniversalVideoContent,"video:11"),(HLSVideoContent(),"video:12"),(WebEmbedVideoContent(),"image:13")] {
   let item=UniversalVideoGalleryItem(content),poster=UniversalVideoGalleryItemPictureInPictureNode(item:UniversalVideoGalleryItem(content))
   check(poster.children.count==1 && (poster.children[0] as? TransformImageNode)?.source==id,"poster uses the original media thumbnail, without technical card")
   check(!poster.isUserInteractionEnabled,"poster cannot create another player")
   let image=poster.children[0] as! TransformImageNode
   check(image.synchronous,"cached poster requested synchronously before native animation")
   for size in [CGSize(width:390,height:219),CGSize(width:844,height:475)] {
    poster.updateLayout(size,transition:.immediate)
    check(image.frame==CGRect(origin:.zero,size:size) && image.arguments?.boundingSize==size,"poster layout follows native video rectangle")
    check(image.arguments?.imageSize==item.content.dimensions,"poster preserves source dimensions")
   }
  }
  for secret in [false,true] {for protected in [false,true] {
   let item=UniversalVideoGalleryItem(OtherContent());item.isSecret=secret;item.peerIsCopyProtected=protected;item.contentInfo = .message(Message(media:TelegramMediaFile(41)),nil)
   let poster=UniversalVideoGalleryItemPictureInPictureNode(item:item),image=poster.children[0] as! TransformImageNode
   check(image.source=="video:41","fallback selects message file thumbnail")
   check(image.layer.capture == (secret || protected) && image.layer.bypass == !secret,"poster keeps content capture policy")
  }}
  do {
   let item=UniversalVideoGalleryItem(OtherContent());let image=TelegramMediaImage(42);item.contentInfo = .webPage(TelegramMediaWebpage(image),image,0)
   check((UniversalVideoGalleryItemPictureInPictureNode(item:item).children[0] as! TransformImageNode).source=="image:42","embedded platform fallback uses its webpage image")
   item.contentInfo = .message(Message(media:TelegramMediaWebpage(image)),nil)
   check((UniversalVideoGalleryItemPictureInPictureNode(item:item).children[0] as! TransformImageNode).source=="image:42","message webpage fallback uses its cached image")
  }
  do {
   let host=PosterHost();host.item=UniversalVideoGalleryItem(NativeVideoContent());host.videoNode=ASDisplayNode();host.videoNode!.frame=CGRect(x:12,y:180,width:640,height:360)
   let poster=host.nagramiXMakePiPPreviewPoster()
   check(poster != nil && poster!.frame==CGRect(x:12,y:180,width:640,height:360),"fallback poster uses source rectangle in gallery coordinates")
   host.videoNode!.frame = .zero;check(host.nagramiXMakePiPPreviewPoster()==nil,"invalid source rectangle cannot fabricate a preview")
  }
  let decoration=GalleryVideoDecoration(),player=Player()
  let original=CGSize(width:640,height:360),rotated=CGSize(width:360,height:640)
  decoration.updateLayout(size:original,actualSize:original,transition:.immediate);decoration.updateContentNode(player)
  var completions=0
  decoration.setNagramiXPiPTransitionActive(true)
  for _ in 0..<60 {
   decoration.updateLayout(size:rotated,actualSize:rotated,transition:.animated)
   var corners=ImageCorners();corners.topLeft.radius=24;corners.topRight.radius=24;corners.bottomLeft.radius=24;corners.bottomRight.radius=24
   decoration.updateCorners(corners)
   decoration.updateClippingFrame(CGRect(origin:.zero,size:rotated),completion:{completions+=1})
   check(player.frame.size==original && player.layouts==1,"PiP lease prevents client source rectangle animation")
   check(!decoration.contentContainerNode.clipsToBounds && decoration.contentContainerNode.layer.mask==nil,"PiP lease cannot reintroduce a client corner mask")
  }
  check(completions==60,"frozen clipping requests complete instead of blocking dismissal")
  decoration.setNagramiXPiPTransitionActive(false)
  check(player.frame.size==rotated && player.layouts==2,"returned layer receives latest deferred layout once")
  check(decoration.contentContainerNode.clipsToBounds && decoration.contentContainerNode.cornerRadius==24,"returned source receives latest deferred corners")
  decoration.setNagramiXPiPTransitionActive(false);check(player.layouts==2,"releasing geometry lease is idempotent")
  decoration.updateContentNode(nil);decoration.updateClippingFrame(CGRect(origin:.zero,size:original),completion:{completions+=1})
  check(completions==61,"missing content must complete gallery dismissal")
  decoration.updateContentNode(player);decoration.updateClippingFrame(CGRect(origin:.zero,size:original),completion:{completions+=1})
  check(completions==61,"normal live clipping still waits for its actual animation")
  AnimationClock.flush();check(completions==62,"normal live clipping completes once")
  print("PiP poster and geometry production checks: \(checks)")
 }
}
'''

RESTORE_FIELDS = r'''
 var didExpand=false,isStarting=false
 var nagramiXRestoreCompletions:[(Bool)->Void]=[]
 var nagramiXRestoreGeneration=0
 var nagramiXRestoreInFlight=false,nagramiXExpandWhenStarted=false
 var pictureInPictureController:AVPictureInPictureController?=AVPictureInPictureController()
 var expand: (@escaping(Bool)->Void)->Void = {_ in}
 var didBegin: (Restorer)->Void = {_ in}
'''
RESTORE_BOUNDARY = r'''
import Foundation
enum DispatchQueue {static let main=Scheduler()}
final class Scheduler {var jobs:[()->Void]=[];func async(_ job:@escaping()->Void){jobs.append(job)};func flush(){let pending=jobs;jobs=[];pending.forEach{$0()}}}
final class AVPictureInPictureController {var isPictureInPictureActive=true;var stops=0;func stopPictureInPicture(){stops+=1}}
'''
RESTORE_TESTS = r'''
@main struct Tests {
 static func main(){
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data((message+"\n").utf8));exit(96)};checks+=1}
  do {
   let owner=Restorer();var presentations=0;var pending:[(Bool)->Void]=[];var answers:[Bool]=[]
   owner.expand={presentations+=1;pending.append($0)}
   owner.requestExpand()
   check(presentations==1 && owner.pictureInPictureController!.stops==0,"first tap presents original gallery before stopping PiP")
   owner.requestExpand();owner.pictureInPictureController(owner.pictureInPictureController!,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler:{answers.append($0)})
   check(presentations==1,"app and system restore requests share one presentation")
   pending[0](true)
   check(owner.didExpand && answers==[true],"native restore receives successful attachment acknowledgement")
   check(owner.pictureInPictureController!.stops==1,"queued app restore requests stop PiP only once after success")
   pending[0](false);check(owner.didExpand && answers==[true],"duplicate presentation completion is ignored")
   owner.pictureInPictureController(owner.pictureInPictureController!,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler:{answers.append($0)})
   check(presentations==1 && answers==[true,true],"already restored UI is not presented twice")
  }
  do {
   let owner=Restorer();var pending:[(Bool)->Void]=[];owner.expand={pending.append($0)}
   owner.requestExpand();pending[0](false)
   check(!owner.didExpand && owner.pictureInPictureController!.stops==0,"failed restore leaves native PiP running")
   owner.requestExpand();check(pending.count==2,"failed restore can retry without reopening a player")
   pending[1](true);check(owner.pictureInPictureController!.stops==1,"successful retry stops native PiP once")
  }
  do {
   let owner=Restorer();var pending:[(Bool)->Void]=[];var answers:[Bool]=[];owner.expand={pending.append($0)}
   owner.pictureInPictureController(owner.pictureInPictureController!,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler:{answers.append($0)})
   owner.nagramiXCancelInterfaceRestore();owner.requestExpand();pending[0](true)
   check(answers==[false] && !owner.didExpand && owner.pictureInPictureController!.stops==0,"old acknowledgement cannot finish a new restore")
   pending[1](true);check(owner.didExpand && owner.pictureInPictureController!.stops==1,"current restore alone finishes")
  }
  do {
   let owner=Restorer();var sequence:[String]=[]
   owner.isStarting=true;owner.expand={completion in sequence.append("present");completion(true)};owner.didBegin={_ in sequence.append("start")}
   owner.requestExpand();check(owner.nagramiXExpandWhenStarted && sequence.isEmpty,"tap during start waits for native DidStart")
   owner.pictureInPictureControllerDidStartPictureInPicture(owner.pictureInPictureController!)
   check(sequence==["start"],"native start finishes before restoration is requested")
   DispatchQueue.main.flush();check(sequence==["start","present"] && owner.pictureInPictureController!.stops==1,"queued tap restores on the next display turn")
  }
  print("PiP restore production checks: \(checks)")
 }
}
'''
