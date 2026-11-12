"""Выполнить production gallery handoff/restore без имитации пикселей UIKit."""
from validate_quick_format import block
from system_web_picture_in_picture_runtime import GALLERY


def fixture(source):
 code=(source/GALLERY).read_text()
 state=block(code,'private struct NagramiXNativePiPVisualState {')
 ack=block(code,'private final class NagramiXNativePiPPresentationAcknowledgement {')
 methods='\n'.join(block(code,marker) for marker in [
  '    private func nagramiXBeginWebPictureInPicture()',
  '    private func nagramiXRestoreSystemWebPiP(',
  '    private func nagramiXFinishSystemWebPiP(',
  '    private func nagramiXAwaitNativePiPPresentation(',
  '    private func nagramiXFinishNativePiPVisualTransition(',
 ])
 methods=methods.replace('private func','func')
 return BOUNDARY+state+'\n'+ack+FIELDS+methods+'\n}\n'+TESTS

def negatives(text):
 for name,old,new,why in [
  ('lost-source-lease','self.nagramiXSystemWebPiPKeeper = self','self.nagramiXSystemWebPiPKeeper = nil','system PiP retains its original content owner'),
  ('premature-gallery-dismiss','if active {','if active || !self.nagramiXWebPiPHasStarted {','gallery stays visible until actual system PiP callback'),
  ('pause-transferred-owner','wasStarted && !restored && self.videoNode?.ownsContentNode == true','wasStarted && !restored','stale owner cannot pause transferred content'),
  ('stale-gallery-restore','guard let self, self.nagramiXSystemWebPiPGeneration == generation else { completion(false); return }','guard let self, self.nagramiXSystemWebPiPGeneration != nil else { completion(false); return }','retired restore cannot change new owner'),
 ]:
  assert text.count(old)==1,(name,text.count(old))
  yield name,text.replace(old,new,1),why

BOUNDARY=r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
var clock:Double=0
func CACurrentMediaTime()->Double{clock}
final class Disposable {var action:(()->Void)?;init(_ action:@escaping()->Void){self.action=action};func dispose(){action?();action=nil}}
final class MetaDisposable {var current:Disposable?;func set(_ value:Disposable?){current?.dispose();current=value};func dispose(){set(nil)}}
final class Signal<T> {
 var value:T;var next:[UUID:(T)->Void]=[:]
 init(_ value:T){self.value=value}
 func set(_ value:T){self.value=value;for f in Array(next.values){f(value)}}
 func start(next:@escaping(T)->Void)->Disposable{let id=UUID();self.next[id]=next;next(value);return Disposable{[weak self] in self?.next.removeValue(forKey:id)}}
}
infix operator |> : AdditionPrecedence
func |> <A,B>(value:A,f:(A)->B)->B{f(value)}
func deliverOnMainQueue<T>(_ signal:Signal<T>)->Signal<T>{signal}
struct Queue {static func mainQueue()->Queue{Queue()}}
enum SwiftSignalKit {
 final class Timer {
  static var all:[Timer]=[]
  let timeout:Double,repeats:Bool,body:()->Void
  var valid=false,deadline:Double=0
  init(timeout:Double,repeat repeats:Bool,completion:@escaping()->Void,queue:Queue){self.timeout=timeout;self.repeats=repeats;self.body=completion}
  func start(){valid=true;deadline=clock+timeout;Self.all.append(self)}
  func invalidate(){valid=false}
  static func advance(_ delta:Double){clock+=delta;for timer in all where timer.valid && timer.deadline<=clock{if timer.repeats{timer.deadline=clock+timer.timeout}else{timer.valid=false};timer.body()};all.removeAll{!$0.valid}}
 }
}
final class MainQueue {var jobs:[()->Void]=[];func async(execute:@escaping()->Void){jobs.append(execute)};func run(){let work=jobs;jobs=[];for job in work{job()}}}
enum DispatchQueue{static let main=MainQueue()}
final class View {
 var alpha:Double=1
 var window:AnyObject?=NSObject()
 var bounds=CGRect(x:0,y:0,width:390,height:844)
 func layoutIfNeeded(){}
}
class ViewController {
 let view=View()
 var presentationArguments:Int?=7
 var presentingViewController:ViewController?
 var dismissed=false
 func dismiss(animated:Bool,completion:(()->Void)?){dismissed=true;completion?()}
}
final class GalleryController:ViewController {
 var backdrop=false,canPrepare=true
 func nagramiXPrepareNativePiPBackdrop()->Bool{canPrepare}
 func nagramiXShowNativePiPBackdrop(){backdrop=true}
 func nagramiXFinishNativePiPBackdrop(animated:Bool){backdrop=false}
}
final class Window {
 enum Layer {case root}
 var attaches=true
 var presents=0
 func present(_ controller:ViewController,on:Layer,blockInteraction:Bool,completion:@escaping()->Void){presents+=1;controller.view.window=attaches ? NSObject():nil;controller.presentingViewController=ViewController()}
}
final class Navigation {var currentWindow:Window?=Window()}
final class Manager {weak var currentPictureInPictureNode:AnyObject?}
final class Shared {let mediaManager=Manager()}
final class Context {let sharedContext=Shared()}
final class Item {var allowed=true}
func nagramiXCanOfferWebPictureInPicture(_ item:Item)->Bool{item.allowed}
final class ScrollView {var zoomScale:Double=1,minimumZoomScale:Double=1}
final class Scroll {let view=ScrollView()}
final class UniversalVideoNode {
 let isNativePictureInPictureActive=Signal(false)
 var ownsContentNode=true,accepts=true,enters=0,stops=0,pauses=0
 var restore:((@escaping(Bool)->Void)->Void)?
 var backgroundColor:Int?=0
 func setNagramiXNativePiPRestore(_ restore:((@escaping(Bool)->Void)->Void)?){self.restore=restore}
 func enterNativePictureInPicture()->Bool{enters+=1;return accepts}
 func exitNativePictureInPicture(){stops+=1}
 func pause(){pauses+=1}
}
final class Clip {func restore(){}}
'''
FIELDS=r'''
private final class GalleryLifecycleBoundary {
 let context=Context()
 var item:Item?=Item()
 var videoNode:UniversalVideoNode?=UniversalVideoNode()
 var isCentral:Bool?=true,hasPictureInPicture=true,validLayout:Int?=1
 let scrollNode=Scroll()
 var controller:GalleryController?=GalleryController()
 var navigation:Navigation?=Navigation()
 var activePictureInPictureController:ViewController?
 var activePictureInPictureNavigationController:Navigation?
 var nagramiXWebPiPTransitionStarted=false,nagramiXWebPiPHasStarted=false
 var nagramiXSystemWebPiPWasRestored=false,nagramiXSystemWebPiPRestoring=false
 var nagramiXSystemWebPiPGeneration:UUID?
 var nagramiXSystemWebPiPKeeper:GalleryLifecycleBoundary?
 let nagramiXSystemWebPiPDisposable=MetaDisposable()
 var nagramiXSystemWebPiPWatchdog:SwiftSignalKit.Timer?
 var nagramiXPiPVisualState=NagramiXNativePiPVisualState()
 var nagramiXPiPHandoffGeneration:Int{nagramiXPiPVisualState.generation}
 var nagramiXPiPPresentationTimer:SwiftSignalKit.Timer?
 var nagramiXPiPPresentationAcknowledgement:NagramiXNativePiPPresentationAcknowledgement?
 var nagramiXPiPRestoreTimer:SwiftSignalKit.Timer?
 var nagramiXPiPRevealScheduled=false
 var nagramiXPiPSourceClipping:Clip?
 var nagramiXPiPSourceVideoNode:UniversalVideoNode?
 var nagramiXPiPSourceLayer:AnyObject?
 var nagramiXPiPOriginalVideoBackground:Int?
 var placeholderSuppressed=false,dismissals=0,backgroundUpdates=0
 enum DismissKind {case pip}
 func galleryController()->ViewController?{controller}
 func baseNavigationController()->Navigation?{navigation}
 func nagramiXSetNativePictureInPicturePlaceholderSuppressed(_ value:Bool){placeholderSuppressed=value}
 func nagramiXRestoreNativePictureInPicturePlaceholderIfOwned(){placeholderSuppressed=false}
 func beginCustomDismiss(_ kind:DismissKind){dismissals+=1}
 func completeCustomDismiss(_ value:Bool){}
 func nagramiXUpdateBackgroundVideoPlayback(){backgroundUpdates+=1}
'''
TESTS=r'''
@main struct WebGalleryLifecycleTests {
 static func main(){
  var checks=0
  func check(_ condition:@autoclosure()->Bool,_ why:String){if !condition(){FileHandle.standardError.write(Data(("System gallery PiP regression: "+why+"\n").utf8));exit(91)};checks+=1}
  for _ in 0..<4 {
   let n=GalleryLifecycleBoundary(),v=UniversalVideoNode();n.videoNode=v
   check(n.nagramiXBeginWebPictureInPicture(),"system request accepted")
   check(n.dismissals==0 && n.controller!.view.alpha==1,"gallery stays visible until actual system PiP callback")
   check(!n.nagramiXBeginWebPictureInPicture() && v.enters==1,"repeat tap starts only one request")
   v.isNativePictureInPictureActive.set(true)
   check(n.dismissals==1 && n.controller!.view.alpha==0,"actual system callback dismisses gallery")
   check(n.context.sharedContext.mediaManager.currentPictureInPictureNode === n,"source owner retained while in PiP")
   v.isNativePictureInPictureActive.set(false)
   check(n.context.sharedContext.mediaManager.currentPictureInPictureNode==nil && v.pauses==1,"actual stop releases only this source")
   check(!n.placeholderSuppressed && !n.nagramiXWebPiPTransitionStarted,"stop removes technical placeholder and pending state")
  }
  do {
   let n=GalleryLifecycleBoundary();n.videoNode!.accepts=false
   check(!n.nagramiXBeginWebPictureInPicture(),"native refusal rolls back synchronously")
   check(n.context.sharedContext.mediaManager.currentPictureInPictureNode==nil && n.dismissals==0 && n.controller!.view.alpha==1,"refusal leaves gallery intact")
  }
  do {
   let n=GalleryLifecycleBoundary(),v=UniversalVideoNode();n.videoNode=v
   check(n.nagramiXBeginWebPictureInPicture(),"pending start")
   SwiftSignalKit.Timer.advance(5.1)
   check(n.context.sharedContext.mediaManager.currentPictureInPictureNode==nil && v.stops==1,"watchdog cancels unconfirmed native request")
   v.isNativePictureInPictureActive.set(true)
   check(n.dismissals==0,"late callback after cancellation cannot dismiss gallery")
  }
  for attaches in [true,false] {
   let n=GalleryLifecycleBoundary(),v=UniversalVideoNode();n.videoNode=v
   check(n.nagramiXBeginWebPictureInPicture(),"restore start")
   v.isNativePictureInPictureActive.set(true)
   n.navigation!.currentWindow!.attaches=attaches
   var results:[Bool]=[]
   v.restore?{results.append($0)}
   DispatchQueue.main.run()
   if !attaches{SwiftSignalKit.Timer.advance(2.1)}
   check(results == [attaches],"restore completion acknowledged once after actual attachment")
   if attaches {
    check(n.controller!.view.alpha==1,"restore reveals attached original gallery")
    v.isNativePictureInPictureActive.set(false)
    check(v.pauses==0 && n.context.sharedContext.mediaManager.currentPictureInPictureNode==nil,"restored player continues without reset or pause")
   } else {
    check(n.controller!.presentingViewController!.dismissed && v.stops==1,"failed restore removes exact failed presentation")
   }
  }
  do {
   let n=GalleryLifecycleBoundary(),v=UniversalVideoNode();n.videoNode=v
   check(n.nagramiXBeginWebPictureInPicture(),"ownership test start")
   v.isNativePictureInPictureActive.set(true);v.ownsContentNode=false;v.isNativePictureInPictureActive.set(false)
   check(v.pauses==0,"stale owner cannot pause transferred content")
  }
  do {
   let n=GalleryLifecycleBoundary(),v=UniversalVideoNode();n.videoNode=v
   check(n.nagramiXBeginWebPictureInPicture(),"stale restore start")
   v.isNativePictureInPictureActive.set(true)
   let oldRestore=v.restore!
   v.isNativePictureInPictureActive.set(false)
   check(n.nagramiXBeginWebPictureInPicture(),"fresh request after stop")
   var results:[Bool]=[];oldRestore{results.append($0)};DispatchQueue.main.run()
   check(results==[false] && n.context.sharedContext.mediaManager.currentPictureInPictureNode === n,"retired restore cannot change new owner")
   n.nagramiXFinishSystemWebPiP(stop:true)
  }
  do {
   let video=UniversalVideoNode()
   var owner:GalleryLifecycleBoundary?=GalleryLifecycleBoundary();owner!.videoNode=video
   weak var lease=owner
   check(owner!.nagramiXBeginWebPictureInPicture(),"lease start")
   video.isNativePictureInPictureActive.set(true);owner=nil
   check(lease != nil,"system PiP retains its original content owner")
   video.isNativePictureInPictureActive.set(false)
   check(lease == nil,"system stop releases the retained owner")
  }
  print("system web gallery production checks: \(checks)")
 }
}
'''
