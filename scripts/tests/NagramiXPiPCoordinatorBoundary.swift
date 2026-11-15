import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#else
extension CGSize {func equalTo(_ value:CGSize)->Bool{self==value}}
#endif
var clock:Double=0
func CACurrentMediaTime()->Double{clock}
extension Double {static func now()->Double{clock}}
extension Int {static let clear=0}
final class Disposable {var action:(()->Void)?;init(_ f:@escaping()->Void){action=f};func dispose(){action?();action=nil}}
final class MetaDisposable {var current:Disposable?;func set(_ value:Disposable?){current?.dispose();current=value}}
final class Signal<T> {
 var value:T;var observers:[UUID:(T)->Void]=[:]
 init(_ value:T){self.value=value}
 func set(_ value:T){self.value=value;Array(observers.values).forEach{$0(value)}}
 func start(next:@escaping(T)->Void)->Disposable{let id=UUID();observers[id]=next;next(value);return Disposable{[weak self] in self?.observers.removeValue(forKey:id)}}
}
infix operator |> : AdditionPrecedence
func |> <A,B>(value:A,f:(A)->B)->B{f(value)}
func deliverOnMainQueue<T>(_ value:Signal<T>)->Signal<T>{value}
struct Queue {static func mainQueue()->Queue{Queue()}}
enum SwiftSignalKit {
 final class Timer {
  static var all:[Timer]=[]
  var valid=false,deadline:Double=0;let timeout:Double,repeats:Bool,body:()->Void
  init(timeout:Double,repeat repeats:Bool,completion:@escaping()->Void,queue:Queue){self.timeout=timeout;self.repeats=repeats;body=completion}
  func start(){valid=true;deadline=clock+timeout;Self.all.append(self)}
  func invalidate(){valid=false}
  static func advance(_ delta:Double){clock+=delta;for t in all where t.valid && t.deadline<=clock{t.valid=t.repeats;t.deadline=clock+t.timeout;t.body()};all.removeAll{!$0.valid}}
 }
}
final class MainQueue {
 var jobs:[(Double,()->Void)]=[]
 func async(execute:@escaping()->Void){jobs.append((clock,execute))}
 func asyncAfter(deadline:Double,execute:@escaping()->Void){jobs.append((deadline,execute))}
 func run(){let work=jobs.filter{$0.0<=clock};jobs.removeAll{$0.0<=clock};work.forEach{$0.1()}}
}
enum DispatchQueue {static let main=MainQueue()}
final class Layer {
 enum Status {case rendering,failed}
 var status=Status.rendering,requiresFlushToResumeDecoding=false,isReadyForDisplay=true
 func removeAnimation(forKey:String){}
}
typealias AVSampleBufferDisplayLayer=Layer
class View {
 let layer=Layer();var window:AnyObject?=NSObject()
 var bounds=CGRect(x:0,y:0,width:390,height:844),alpha:Double=1
 func layoutIfNeeded(){}
}
class ViewController {
 let view=View();var presentationArguments:Int?=7;var presentingViewController:ViewController?
 var dismissed=false
 func dismiss(animated:Bool,completion:(()->Void)?){dismissed=true;view.window=nil;completion?()}
}
final class ScrollView {
 var zoomScale:Double=1,minimumZoomScale:Double=1,isDragging=false
 var contentOffset=CGPoint(x:0,y:844),contentSize=CGSize(width:390,height:2532)
 func setContentOffset(_ point:CGPoint,animated:Bool){contentOffset=point}
}
final class Scroll {let view=ScrollView()}
final class Pager {weak var item:GalleryLifecycleBoundary?;func centralItemNode()->GalleryLifecycleBoundary?{item}}
final class ChatController {var transitions:[Double]=[];func updatePushedTransition(_ value:Double,transition:Transition){transitions.append(value)}}
enum Transition {case immediate}
final class ResetNode {
 let scrollView=ScrollView(),pager=Pager();var resets=0
 var nagramiXNativePictureInPictureDistance:CGFloat?
 weak var nagramiXNativePictureInPictureItem:GalleryLifecycleBoundary?
 var nagramiXNativePictureInPictureRejected=false,nagramiXSuppressNativePictureInPictureChatTransition=false
 var navigation=Navigation()
 func baseNavigationController()->Navigation?{navigation}
 func scrollViewDidScroll(_ view:ScrollView){resets+=1}
 // PRODUCTION_RESET
}
typealias GalleryItemNode=GalleryLifecycleBoundary
final class GalleryController:ViewController {
 let galleryNode=ResetNode();var backdrop=false,canPrepare=true,restores=0
 func nagramiXPrepareNativePiPBackdrop()->Bool{canPrepare}
 func nagramiXShowNativePiPBackdrop(){backdrop=true}
 func nagramiXFinishNativePiPBackdrop(animated:Bool){backdrop=false}
 func nagramiXResetNativePictureInPictureSwipe(owner:GalleryItemNode?=nil,restoreChatTransition:Bool=true){galleryNode.nagramiXResetNativePictureInPictureSwipe(owner:owner,restoreChatTransition:restoreChatTransition)}
 func nagramiXLockNativePictureInPictureSwipe(){galleryNode.nagramiXLockNativePictureInPictureSwipe()}
 func nagramiXPrepareNativePiPRestore(){restores+=1;galleryNode.nagramiXResetNativePictureInPictureSwipe(restoreChatTransition:false)}
 func dismiss(forceAway:Bool){dismiss(animated:false,completion:nil)}
}
final class Window {
 enum Level {case root};var attaches=true,presents=0
 func present(_ controller:ViewController,on:Level,blockInteraction:Bool,completion:@escaping()->Void){presents+=1;controller.view.window=attaches ? NSObject():nil;controller.presentingViewController=ViewController()}
}
final class Navigation {var currentWindow:Window?=Window();let topViewController:AnyObject?=ChatController()}
final class Manager {weak var currentPictureInPictureNode:AnyObject?}
final class Shared {let mediaManager=Manager()}
final class Engine {
 final class Account {var logs:[String]=[];func addAppLogEvent(type:String){logs.append(type)}}
 let accountData=Account()
}
final class Context {let sharedContext=Shared(),engine=Engine()}
final class WebEmbedVideoContent {}
final class Item {var allowed=true,embedded=false;var content:AnyObject=NSObject()}
func nagramiXUsesEmbeddedPictureInPicture(_ item:Item?)->Bool{item?.embedded==true}
func nagramiXCanOfferWebPictureInPicture(_ item:Item)->Bool{item.allowed}
final class GalleryVideoDecoration {var active=false;func setNagramiXPiPTransitionActive(_ value:Bool){active=value}}
final class UniversalVideoNode {
 let view=View(),layer=Layer();let decoration:AnyObject=GalleryVideoDecoration()
 var sourceLayer:Layer?=Layer(),ownsContentNode=true,backgroundColor:Int?=1
 var bounds:CGRect{view.bounds}
 var restore:((@escaping(Bool)->Void)->Void)?
 let isNativePictureInPictureActive=Signal(false)
 var accepts=true,enters=0,stops=0,pauses=0,layouts:[(CGSize,CGSize)]=[],activeFlags:[Bool]=[]
 func getVideoLayer()->Layer?{sourceLayer}
 func updateLayout(size:CGSize,actualSize:CGSize,transition:Transition){layouts.append((size,actualSize))}
 func setNagramiXNativePiPRestore(_ value:((@escaping(Bool)->Void)->Void)?){restore=value}
 func enterNativePictureInPicture()->Bool{enters+=1;return accepts}
 func exitNativePictureInPicture(){stops+=1;isNativePictureInPictureActive.set(false)}
 func setNativePictureInPictureIsActive(_ value:Bool){activeFlags.append(value)}
 func pause(){pauses+=1}
}
final class NagramiXNativePiPSourceClipping {init?(source:Layer,root:Layer){};func restore(){}}
// AVKit event delivery and renderer readiness are explicit controllable hosts.
final class NativePictureInPictureContentImpl {
 var canBeginPictureInPicture=true,matchesSourceLayer=true,isStarting=false,isActive=false,cancelled=false,starts=0,cancels=0
 var isStartingOrActive:Bool{isStarting || isActive}
 let will:(NativePictureInPictureContentImpl)->Void,did:(NativePictureInPictureContentImpl)->Void,end:(NativePictureInPictureContentImpl)->Void,failed:(NativePictureInPictureContentImpl)->Void,expand:(@escaping(Bool)->Void)->Void
 init(will:@escaping(NativePictureInPictureContentImpl)->Void,did:@escaping(NativePictureInPictureContentImpl)->Void,end:@escaping(NativePictureInPictureContentImpl)->Void,failed:@escaping(NativePictureInPictureContentImpl)->Void,expand:@escaping(@escaping(Bool)->Void)->Void){self.will=will;self.did=did;self.end=end;self.failed=failed;self.expand=expand}
 func beginPictureInPicture()->Bool{guard canBeginPictureInPicture else{return false};starts+=1;isStarting=true;will(self);return true}
 func finish(){isStarting=false;isActive=true;if !cancelled{did(self)}}
 func fail(){isStarting=false;failed(self)}
 func stop(){isActive=false;isStarting=false;end(self)}
 func cancelPendingStart(){cancelled=true;isStarting=false;isActive=false;cancels+=1}
 func requestExpand(){expand{ok in if ok{self.stop()}}}
}
// PRODUCTION_STATE
private typealias UniversalVideoGalleryItemNode=GalleryLifecycleBoundary
private final class GalleryLifecycleBoundary {
 let context=Context(),scrollNode=Scroll()
 var item:Item?=Item(),videoNode:UniversalVideoNode?=UniversalVideoNode()
 var isCentral:Bool?=true,hasPictureInPicture=true,validLayout:Int?=1
 var controller:GalleryController?=GalleryController(),navigation:Navigation?=Navigation()
 var activePictureInPictureController:ViewController?,activePictureInPictureNavigationController:Navigation?
 var nativePictureInPictureContent:AnyObject?
 var nagramiXPiPVisualState=NagramiXNativePiPVisualState()
 var nagramiXPiPHandoffGeneration:Int{nagramiXPiPVisualState.generation}
 weak var nagramiXPiPSourceVideoNode:UniversalVideoNode?
 weak var nagramiXPiPSourceLayer:Layer?
 var nagramiXPiPOriginalVideoBackground:Int?,nagramiXPiPSourceClipping:NagramiXNativePiPSourceClipping?
 var nagramiXPiPPresentationTimer:SwiftSignalKit.Timer?,nagramiXPiPRestoreTimer:SwiftSignalKit.Timer?,nagramiXPiPEntryTimer:SwiftSignalKit.Timer?
 var nagramiXPiPPresentationAcknowledgement:NagramiXNativePiPPresentationAcknowledgement?
 var nagramiXPiPRevealScheduled=false,nagramiXPiPRestoreDeadline:Double=0,nagramiXPiPEntryDeadline:Double=0
 var nagramiXPiPEntryGeneration=0
 weak var nagramiXPiPEntryVideoNode:UniversalVideoNode?
 var nagramiXPiPDeferredDimensions:CGSize?
 var zoomableContent:(CGSize,UniversalVideoNode)?
 var nagramiXWebPiPTransitionStarted=false,nagramiXWebPiPHasStarted=false,nagramiXSystemWebPiPWasRestored=false,nagramiXSystemWebPiPRestoring=false,nagramiXWebExpandWhenStarted=false
 var nagramiXWebRestoreCompletions:[(Bool)->Void]=[]
 var nagramiXSystemWebPiPGeneration:UUID?,nagramiXSystemWebPiPKeeper:GalleryLifecycleBoundary?
 let nagramiXSystemWebPiPDisposable=MetaDisposable()
 var nagramiXSystemWebPiPWatchdog:SwiftSignalKit.Timer?
 var placeholders=false,dismissals=0,backgroundUpdates=0,setups=0,nativePossible=true
 enum DismissKind {case pip}
 init(){controller!.galleryNode.pager.item=self;zoomableContent=(CGSize(width:1280,height:720),videoNode!)}
 func galleryController()->ViewController?{controller}
 func baseNavigationController()->Navigation?{navigation}
 func nagramiXSetNativePictureInPicturePlaceholderSuppressed(_ value:Bool){placeholders=value}
 func nagramiXRestoreNativePictureInPicturePlaceholderIfOwned(){placeholders=false}
 func beginCustomDismiss(_ type:DismissKind){dismissals+=1}
 func completeCustomDismiss(_ pip:Bool){controller?.view.window=nil}
 func updateControlsVisibility(_ value:Bool){}
 func nagramiXUpdateBackgroundVideoPlayback(){backgroundUpdates+=1}
 func setupNativePictureInPicture(){
  setups+=1
  guard videoNode?.getVideoLayer() != nil else{return}
  var didExpand=false
  let will:(NativePictureInPictureContentImpl)->Void = // PRODUCTION_willBegin
  let did:(NativePictureInPictureContentImpl)->Void = // PRODUCTION_didBegin
  let end:(NativePictureInPictureContentImpl)->Void = // PRODUCTION_didEnd
  let expand:(@escaping(Bool)->Void)->Void = // PRODUCTION_expand
  let fail:(NativePictureInPictureContentImpl)->Void = // PRODUCTION_failedToBegin
  let content=NativePictureInPictureContentImpl(will:will,did:did,end:end,failed:fail,expand:expand)
  content.canBeginPictureInPicture=nativePossible
  nativePictureInPictureContent=content
  _=didExpand
 }
 // PRODUCTION_COORDINATOR
}
