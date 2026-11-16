
var checks=0
func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("PiP refinement: "+message+"\n").utf8));exit(96)};checks+=1}
func advance(_ delta:Double){SwiftSignalKit.Timer.advance(delta);DispatchQueue.main.run()}
func finish(_ h:GalleryLifecycleBoundary){
 if h.item!.embedded {h.videoNode!.isNativePictureInPictureActive.set(true)}
 else {(h.nativePictureInPictureContent as! NativePictureInPictureContentImpl).finish()}
}
func stop(_ h:GalleryLifecycleBoundary){
 if h.item!.embedded {h.nagramiXFinishSystemWebPiP(stop:true)}
 else {(h.nativePictureInPictureContent as! NativePictureInPictureContentImpl).stop()}
}
@main struct Tests {static func main(){
 for embedded in [false,true] {for earlyAnimation in [false,true] {
  for dimensions in [CGSize(width:1920,height:1080),CGSize(width:1080,height:1920),CGSize(width:640,height:640),CGSize(width:2560,height:720),CGSize(width:720,height:2560),CGSize(width:1333,height:777)] {
   let h=GalleryLifecycleBoundary();h.item!.embedded=embedded
   if embedded {h.item!.content=WebEmbedVideoContent()}
   h.nagramiXApplyVideoDimensions(dimensions)
   let factor:CGFloat=embedded ? 1:2
   check(h.zoomableContent!.0==CGSize(width:dimensions.width*factor,height:dimensions.height*factor),"decoded aspect ratio retained before entry")
   h.videoNode!.sourceLayer?.isReadyForDisplay=false
   check(h.nagramiXRequestPictureInPicture(),"all aspect ratios admitted by shared request")
   h.pictureInPictureButtonPressed()
   if embedded {
    check(h.dismissals==0 && h.controller!.view.alpha==1 && h.detached==0,"WebKit source stays visible during asynchronous probe")
   } else {
    check(h.dismissals==1 && h.controller!.view.alpha==0 && h.detached==0,"native fade starts before DidStart; no early detachment")
   }
   check(!h.controller!.backdrop,"no entry poster overlays the live source")
   if earlyAnimation {advance(0.21);check(h.detached==0,"fade alone cannot dismiss before confirmed PiP")}
   finish(h)
   if !earlyAnimation || embedded {check(h.detached==0,"DidStart alone does not cut off native fade");advance(0.21)}
   check(h.detached==1 && h.nagramiXPiPVisualState.phase == .active && h.controller!.view.window==nil,"confirmed native fade removes gallery exactly once")
   check(h.nagramiXPiPEntryTimer==nil,"entry timeout cancelled after actual start")
   let locked=h.controller!.galleryNode.nagramiXNativePictureInPictureDistance
   check(!h.nagramiXRequestPictureInPicture() && h.controller!.galleryNode.nagramiXNativePictureInPictureDistance==locked,"ongoing swipe after DidStart cannot reset source geometry")
   stop(h);advance(0.3)
   check(h.nagramiXPiPVisualState.phase == .idle && h.detached==1,"close and late callbacks do not repeat dismissal")
  }
 }}
 for embedded in [false,true] {
  let h=GalleryLifecycleBoundary();h.item!.embedded=embedded
  check(h.nagramiXRequestPictureInPicture(),"entry begins")
  if embedded {h.nagramiXFinishSystemWebPiP(stop:true)}else{(h.nativePictureInPictureContent as! NativePictureInPictureContentImpl).fail()}
  advance(0.3)
  check(h.detached==0 && h.controller!.view.window != nil && h.controller!.view.alpha==1 && !h.nagramiXPiPHandoffFadeFinished,"failed native/web start restores original gallery and stale fade cannot dismiss it")
  check(h.nagramiXPiPVisualState.phase == .idle,"failure returns to idle")
  let quick=GalleryLifecycleBoundary();quick.item!.embedded=embedded;_ = quick.nagramiXRequestPictureInPicture();finish(quick);stop(quick);advance(0.3)
  check(quick.detached==1 && quick.nagramiXPiPVisualState.phase == .idle,"close during fade still removes gallery once")
  let restore=GalleryLifecycleBoundary();restore.item!.embedded=embedded;_ = restore.nagramiXRequestPictureInPicture();finish(restore)
  restore.expandPIP();DispatchQueue.main.run()
  check(restore.detached==1 && restore.navigation!.currentWindow!.presents==1,"immediate expand detaches old presentation before single restore")
  if embedded {restore.videoNode!.isNativePictureInPictureActive.set(false)}
  advance(0.03);advance(0.06);advance(0.03)
  check(restore.nagramiXPiPVisualState.phase == .idle && restore.controller!.view.alpha==1,"existing source returns without stale fade")
 }
 for reason in [0,1,2,3] {
  let h=GalleryLifecycleBoundary();h.videoNode!.sourceLayer=nil;_ = h.nagramiXRequestPictureInPicture()
  switch reason {
  case 0:advance(5.1)
  case 1:h.isCentral=false;advance(0.04)
  case 2:h.videoNode=UniversalVideoNode();advance(0.04)
  default:let owner=NSObject();h.context.sharedContext.mediaManager.currentPictureInPictureNode=owner;advance(0.04);withExtendedLifetime(owner){}
  }
  check(h.nagramiXPiPVisualState.phase == .idle && h.detached==0 && h.controller!.view.alpha==1,"timeout/recycle/owner change rolls back without hidden gallery")
 }
 let h=GalleryLifecycleBoundary();h.item!.embedded=true;_ = h.nagramiXRequestPictureInPicture();advance(5.1)
 check(h.detached==0 && h.controller!.view.alpha==1 && h.nagramiXPiPVisualState.phase == .idle,"WebKit timeout restores gallery after its fade")
 print("\(checks) actual PiP transition checks passed")
}}
