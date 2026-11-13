"""Actual gallery dismissal and restored controls, with bounded UI scheduling."""
from validate_quick_format import block
from validate_pip_swipe_handoff import clean, G, U, N


def fixture(source):
    g = (source / G).read_text()
    u = (source / U).read_text()
    n = (source / N).read_text()
    policy = clean(block(u, '    var nagramiXCanAnimateVideoDismissal: Bool'))
    dismiss = clean(block(g, '    func dismiss(forceAway: Bool)'))
    reset = clean(block(n, '    func nagramiXPrepareNativePiPRestore()'))
    backdrop = '\n'.join(clean(block(g, marker)) for marker in [
        '    func nagramiXPrepareNativePiPBackdrop()',
        '    private func nagramiXRestoreHiddenMediaAfterPiP()',
        '    private func nagramiXPreparePiPPreviewFallback()',
        '    private func nagramiXCancelNativePiPBackdropPreparation(',
        '    func nagramiXShowNativePiPBackdrop()',
        '    func nagramiXFinishNativePiPBackdrop(',
    ])
    early = block(u, '    override func animateOut(to node: (ASDisplayNode, CGRect, () -> (UIView?, UIView?)),').split('        if let status =', 1)[0]
    early = early[early.index('        guard '):] + 'completion()\n'
    native = u[u.index('let content = NativePictureInPictureContentImpl(context: self.context,'):]
    will = clean(block(native, 'willBegin: {'))[len('willBegin: '):]
    did = clean(block(native, 'didBegin: {'))[len('didBegin: '):]
    return BOUNDARY + '\nclass UniversalVideoGalleryItemNode: GalleryItemNode {\n' + '''
 var videoNode:VideoNode?
 var nagramiXPiPVisualState=VisualState()
 var nagramiXWebPiPTransitionStarted=false
 var nativePictureInPictureContent:AnyObject?
 var canMakePoster=true
 func nagramiXMakePiPPreviewPoster()->ASDisplayNode?{canMakePoster ? ASDisplayNode():nil}
''' + policy + '''
 override func animateOut(completion:()->Void){
''' + early + '''
 }
}
final class GalleryController:Controller {
 let galleryNode=GalleryNode()
 var entries=[Entry()]
 var presentationArguments:Any?=GalleryControllerPresentationArguments()
 let _hiddenMedia=Hidden()
 let actionInteraction:Interaction?=Interaction()
 let presentingViewController:Presenter?=Presenter()
 let baseNavigationController:Navigation?=Navigation()
 var isViewLoaded=true
 var nagramiXNativePiPBackdrop:View?
 var nagramiXNativePiPBackdropPoster:ASDisplayNode?
 weak var nagramiXNativePiPBackdropSource:View?
 var nagramiXNativePiPBackdropBounds:CGRect?
 var nagramiXNativePiPBackdropActive=false,nagramiXNativePiPBackdropPreparing=false
 var nagramiXNativePiPBackdropGeneration=0
''' + dismiss + '\n' + backdrop + '''\n}
final class RestoredControls {
 var isDismissed=true
 let pager=Pager(),scrollView=ScrollView()
 var areControlsHidden=false
 let navigationBar:View?=View(),statusBar:View?=View(),titleView:View?=View()
 let headerEdgeEffectView=View(),footerNode=Footer(),backgroundNode=ColorNode()
 var resets=0,thumbnailUpdates=0
 func nagramiXResetNativePictureInPictureSwipe(restoreChatTransition:Bool){precondition(!restoreChatTransition);resets+=1}
 func updateThumbnailContainerNodeAlpha(_ t:Transition){thumbnailUpdates+=1}
''' + reset + '''\n}
final class NativeHarness {
 let gallery=GalleryController(),navigation=Navigation(),context=Context()
 var nativePictureInPictureContent:AnyObject?
 var activePictureInPictureController:Controller?
 var activePictureInPictureNavigationController:Navigation?
 var nagramiXPiPVisualState=VisualState()
 var videoNode:VideoNode?=VideoNode()
 var begins=0,dismissals=0
 func galleryController()->Controller?{gallery}
 func baseNavigationController()->Navigation?{navigation}
 func nagramiXBeginNativePiPVisualTransition()->Bool{guard gallery.nagramiXPrepareNativePiPBackdrop() else{return false};nagramiXPiPVisualState.phase = .starting;return true}
 func beginCustomDismiss(_ mode:DismissMode){begins+=1}
 func completeCustomDismiss(_ pip:Bool){precondition(pip);dismissals+=1}
 func callbacks()->(will:(NativePictureInPictureContentImpl)->Void,did:(NativePictureInPictureContentImpl)->Void,expanded:()->Bool){
  var didExpand=true
  let will:(NativePictureInPictureContentImpl)->Void = ''' + will + '''
  let did:(NativePictureInPictureContentImpl)->Void = ''' + did + '''
  return (will,did,{didExpand})
 }
}
''' + TESTS


BOUNDARY = r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
enum Clock {static var jobs:[()->Void]=[];static func flush(){let work=jobs;jobs=[];work.forEach{$0()}}}
enum Phase {case idle,starting,active,restoring}
struct VisualState {var phase=Phase.idle;mutating func didStart()->Bool{guard phase == .starting else{return false};phase = .active;return true}}
class VideoNode {var ownsContentNode=true,nativeActive=true;func setNativePictureInPictureIsActive(_ value:Bool){nativeActive=value}}
final class ASDisplayNode {let view=View()}
final class NativePictureInPictureContentImpl {var isStartingOrActive=true}
enum DismissMode {case pip}
final class MediaManager {weak var currentPictureInPictureNode:AnyObject?}
final class Shared {let mediaManager=MediaManager()}
final class Context {let sharedContext=Shared()}
class GalleryItemNode {let index=0;var calls=0;func animateOut(completion:()->Void){calls+=1;completion()};func animateOut(to:Int,addToTransitionSurface:(Int)->Void,completion:@escaping()->Void){calls+=1;Clock.jobs.append(completion)}}
final class Pager {var item:GalleryItemNode?;var isScrollEnabled=false;func centralItemNode()->GalleryItemNode?{item}}
final class GalleryNode {let pager=Pager(),view=View();var contentAnimations:[Bool]=[];var suppressed=false;func nagramiXSetNativePictureInPictureChatTransitionSuppressed(_ value:Bool){suppressed=value};func animateOut(animateContent:Bool,completion:@escaping()->Void){contentAnimations.append(animateContent);Clock.jobs.append(completion)}}
struct Message {let id=1}
struct ModelEntry {let message=Message()}
struct Entry {let entry=ModelEntry();let mediaSubject:Int?=nil}
struct Arguments {let transitionNode=0;let addToTransitionSurface:(Int)->Void={_ in}}
final class GalleryControllerPresentationArguments {func transitionArguments(_ id:Int,_ media:Int)->Arguments?{Arguments()}}
func selectedMediaForMessage(message:Message,mediaSubject:Int?)->Int?{1}
struct Value {let media:(Int,Int)?;static func single(_ value:(Int,Int)?)->Value{Value(media:value)}}
final class Hidden {var clears=0,media:(Int,Int)?=(1,1);func set(_ value:Value){clears+=1;media=value.media}}
final class Interaction {var allowed=false;func updateCanReadHistory(_ value:Bool){allowed=value}}
final class Presenter {var dismissals=0;func dismiss(animated:Bool,completion:(()->Void)?){dismissals+=1;completion?()}}
class Controller {let view=View()}
class ChatController:Controller {func updatePushedTransition(_ value:Double,transition:Transition){}}
final class Navigation {var topViewController:Controller?=ChatController()}
enum Curve {case customSpring(damping:Double,initialVelocity:Double)}
enum Transition {case immediate,animated(duration:Double,curve:Curve)}
final class Layer {var removals:[String]=[];func removeAnimation(forKey:String){removals.append(forKey)}}
class View {
 var alpha=1.0;let layer=Layer();var window:Int?=1
 var frame=CGRect(x:0,y:0,width:390,height:844)
 init(frame:CGRect=CGRect(x:0,y:0,width:390,height:844)){self.frame=frame}
 var bounds:CGRect{CGRect(origin:.zero,size:frame.size)}
 var canSnapshot=true,snapshotFlags:[Bool]=[],snapshotAction:(()->Void)?
 var autoresizingMask:[Int]=[],isUserInteractionEnabled=true,accessibilityElementsHidden=false
 weak var superview:View?;var subviews:[View]=[]
 func convert(_ frame:CGRect,to view:View)->CGRect{frame}
 func snapshotView(afterScreenUpdates:Bool)->View?{snapshotFlags.append(afterScreenUpdates);snapshotAction?();return canSnapshot ? View():nil}
 func layoutIfNeeded(){}
 func addSubview(_ view:View){view.removeFromSuperview();subviews.append(view);view.superview=self}
 func removeFromSuperview(){superview?.subviews.removeAll{$0===self};superview=nil}
 static func animate(withDuration:Double,animations:()->Void,completion:@escaping(Bool)->Void){animations();Clock.jobs.append({completion(true)})}
}
typealias UIView=View
final class ScrollView:View {var isScrollEnabled=false;var contentSize=CGSize(width:390,height:2532);var contentOffset=CGPoint.zero;func setContentOffset(_ p:CGPoint,animated:Bool){contentOffset=p}}
final class Footer:View {var visibility=0.0;func setVisibilityAlpha(_ alpha:Double,animated:Bool){visibility=alpha}}
struct Color {static let black=Color();var alpha=0.0;func withAlphaComponent(_ alpha:Double)->Color{var result=self;result.alpha=alpha;return result}}
final class ColorNode {var backgroundColor:Color?=Color.black}
'''

TESTS = r'''
@main struct Tests {
 static func main(){
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data((message+"\n").utf8));exit(96)};checks+=1}
  for owns in [false,true] {for phase in [Phase.idle,.starting,.active,.restoring] {for web in [false,true] {for native in [false,true] {
   let item=UniversalVideoGalleryItemNode();item.videoNode=VideoNode();item.videoNode!.ownsContentNode=owns;item.nagramiXPiPVisualState.phase=phase;item.nagramiXWebPiPTransitionStarted=web
   if native{item.nativePictureInPictureContent=NativePictureInPictureContentImpl()}
   check(item.nagramiXCanAnimateVideoDismissal == (owns && phase == .idle && !web && !native),"live dismissal is allowed only for the idle owned source")
   let gallery=GalleryController();gallery.galleryNode.pager.item=item
   gallery.dismiss(forceAway:false)
   if !item.nagramiXCanAnimateVideoDismissal {
    check(item.calls==0 && gallery.galleryNode.contentAnimations==[true],"preview Back does not animate or detach the active PiP source")
   } else {
    check(item.calls==1 && gallery.galleryNode.contentAnimations==[false],"ordinary owned video preserves native return animation")
   }
   Clock.flush()
   check(gallery.presentingViewController!.dismissals==1 && gallery.actionInteraction!.allowed,"first Back completes gallery dismissal")
   var answers=0;item.animateOut(completion:{answers+=1});check(answers==1,"preview direct dismissal completion cannot hang")
  }}}}
  for hidden in [false,true] {
   let controls=RestoredControls();controls.areControlsHidden=hidden
   controls.nagramiXPrepareNativePiPRestore()
   check(!controls.isDismissed && controls.pager.isScrollEnabled && controls.scrollView.isScrollEnabled,"restored gallery clears old dismissal and scroll lock")
   check(controls.scrollView.contentOffset.y==controls.scrollView.contentSize.height/3 && controls.resets==1,"restored gallery has neutral swipe offset")
   check(controls.navigationBar!.alpha == (hidden ? 0:1) && controls.titleView!.alpha == (hidden ? 0:1),"restore preserves chosen controls visibility")
   check(controls.footerNode.visibility == (hidden ? 0:1) && controls.backgroundNode.backgroundColor!.alpha==1,"restore removes stale transparent dismissal state")
  }
  do {
   let gallery=GalleryController(),item=UniversalVideoGalleryItemNode();gallery.galleryNode.pager.item=item
   let chat=gallery.baseNavigationController!.topViewController!.view
   var visibleAtCapture=false;chat.snapshotAction={visibleAtCapture=gallery._hiddenMedia.media==nil}
   check(gallery.nagramiXPrepareNativePiPBackdrop(),"normal source preview can prepare backdrop")
   check(visibleAtCapture && chat.snapshotFlags==[true],"original post thumbnail is unhidden before screen capture")
   gallery.nagramiXShowNativePiPBackdrop();check(gallery.nagramiXNativePiPBackdrop?.superview === gallery.view,"prepared source preview is used beneath PiP")
   gallery.view.window=nil;gallery.nagramiXFinishNativePiPBackdrop(animated:false)
   check(gallery._hiddenMedia.media==nil,"detached PiP gallery leaves original post preview visible")
   gallery.view.window=1;chat.canSnapshot=false;item.canMakePoster=false
   check(!gallery.nagramiXPrepareNativePiPBackdrop(),"failed capture does not fabricate a backdrop")
   check(gallery._hiddenMedia.media?.0==1,"cancelled handoff restores normal gallery hidden media")
  }
  do {
   let gallery=GalleryController(),item=UniversalVideoGalleryItemNode();gallery.galleryNode.pager.item=item
   gallery.baseNavigationController!.topViewController!.view.canSnapshot=false
   check(gallery.nagramiXPrepareNativePiPBackdrop(),"uncapturable chat can use an actual poster-backed page")
   check(gallery.nagramiXNativePiPBackdropSource === gallery.view && gallery.nagramiXNativePiPBackdropPoster != nil,"fallback retains async thumbnail node with its page")
   check(gallery.nagramiXNativePiPBackdrop?.subviews.count==1,"fallback covers source rectangle without technical UI")
   gallery.nagramiXFinishNativePiPBackdrop(animated:false)
   check(gallery.nagramiXNativePiPBackdropPoster==nil,"finished fallback releases retained image node")
   gallery.baseNavigationController!.topViewController=nil
   check(gallery.nagramiXPrepareNativePiPBackdrop(),"missing chat controller does not reject prepared video preview")
  }
  do {
   let gallery=GalleryController(),item=UniversalVideoGalleryItemNode();gallery.galleryNode.pager.item=item
   check(gallery.nagramiXPrepareNativePiPBackdrop(),"restored gallery prepares current source preview")
   gallery.nagramiXFinishNativePiPBackdrop(animated:false)
   check(gallery._hiddenMedia.media?.0==1,"visible restored gallery reclaims source hidden media")
  }
  do {
   let owner=NativeHarness(),content=NativePictureInPictureContentImpl();owner.nativePictureInPictureContent=content
   let callbacks=owner.callbacks();callbacks.will(content)
   check(owner.gallery.nagramiXNativePiPBackdrop != nil && owner.gallery.nagramiXNativePiPBackdrop?.superview==nil,"live source stays uncovered until AVKit DidStart")
   check(owner.gallery.view.alpha==1 && owner.dismissals==0 && !callbacks.expanded(),"WillStart keeps source and gallery visible")
   callbacks.did(content)
   check(owner.gallery.nagramiXNativePiPBackdrop?.superview === owner.gallery.view && owner.dismissals==1,"prepared preview is shown only after AVKit owns window")
   check(owner.gallery.view.alpha==0 && !owner.videoNode!.nativeActive,"native DidStart performs one gallery handoff")
   callbacks.did(content);check(owner.dismissals==1,"duplicate DidStart cannot dismiss twice")
  }
  print("PiP gallery dismissal production checks: \(checks)")
 }
}
'''
