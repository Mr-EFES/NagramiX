var checks=0
func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("PiP coordinator: "+message+"\n").utf8));exit(96)};checks+=1}
func advance(_ delta:Double){SwiftSignalKit.Timer.advance(delta);DispatchQueue.main.run()}
@main struct Tests {
 static func main(){
  for dimensions in [CGSize(width:1920,height:1080),CGSize(width:1080,height:1920),CGSize(width:1000,height:1000),CGSize(width:1440,height:1080),CGSize(width:2560,height:1080),CGSize(width:1080,height:2560)] {
   for bounds in [CGRect(x:0,y:0,width:390,height:844),CGRect(x:0,y:0,width:844,height:390),CGRect(x:23,y:47,width:111,height:233)] {
    let fit=NagramiXPiPVideoGeometry.fittedFrame(dimensions,in:bounds)!
    check(fit.minX >= bounds.minX-0.001 && fit.minY >= bounds.minY-0.001 && fit.maxX <= bounds.maxX+0.001 && fit.maxY <= bounds.maxY+0.001,"all aspect ratios fit without crop")
    check(abs(fit.width/fit.height-dimensions.width/dimensions.height)<0.000001,"portrait/square/ultrawide ratio preserved")
    check(abs(fit.midX-bounds.midX)<0.000001 && abs(fit.midY-bounds.midY)<0.000001,"actual target rectangle center")
   }
  }
  for size in [CGSize.zero,CGSize(width:-1,height:1),CGSize(width:1,height:0),CGSize(width:CGFloat.nan,height:1),CGSize(width:CGFloat.infinity,height:1)] {
   check(NagramiXPiPVideoGeometry.fittedFrame(size,in:CGRect(x:0,y:0,width:390,height:844))==nil,"invalid geometry cannot enter")
  }
  for embedded in [false,true] {for code in [0,1,2] {
   let h=GalleryLifecycleBoundary();h.item!.embedded=embedded
   if embedded{h.item!.content=WebEmbedVideoContent()}
   if code==1{h.videoNode!.sourceLayer=nil}
   if code==2{h.nativePossible=false}
   h.controller!.galleryNode.scrollView.isDragging=true;h.controller!.galleryNode.scrollView.contentOffset.y+=18
   check(h.nagramiXRequestPictureInPicture(),"request admitted independently of layer readiness")
   h.pictureInPictureButtonPressed()
   if embedded {
    check(h.videoNode!.enters==1 && h.dismissals==0,"one existing embedded player; no early dismissal")
    h.videoNode!.isNativePictureInPictureActive.set(true)
   } else {
    if code==1{
     check(h.nativePictureInPictureContent==nil,"missing layer waits")
     h.nagramiXApplyVideoDimensions(CGSize(width:720,height:1280))
     check(h.videoNode!.layouts.last?.0==CGSize(width:1440,height:2560),"decoded portrait geometry applied before layer readiness")
     h.videoNode!.sourceLayer=Layer();advance(0.04)
    }
    if code==2{let c=h.nativePictureInPictureContent as! NativePictureInPictureContentImpl;check(c.starts==0,"not-possible waits");c.canBeginPictureInPicture=true;advance(0.04)}
    let c=h.nativePictureInPictureContent as! NativePictureInPictureContentImpl
    check(c.starts==1 && h.dismissals==0,"one native start; no early gallery dismissal")
    c.finish()
   }
   check(h.dismissals==1 && h.nagramiXPiPVisualState.phase == .active,"actual DidStart commits exactly once")
   check(h.nagramiXPiPEntryTimer==nil && h.controller!.view.window==nil,"actual gallery removed; no screenshot screen underneath")
   if embedded{h.nagramiXFinishSystemWebPiP(stop:true)}else{(h.nativePictureInPictureContent as! NativePictureInPictureContentImpl).stop()}
   check(h.nagramiXPiPVisualState.phase == .idle && !h.controller!.backdrop,"close restores state and removes poster")
  }}
  for reason in [0,1,2,3] {
   let h=GalleryLifecycleBoundary();h.videoNode!.sourceLayer=nil
   h.controller!.galleryNode.scrollView.contentOffset.y+=24;h.controller!.galleryNode.scrollView.isDragging=true
   check(h.nagramiXRequestPictureInPicture(),"readiness wait starts")
   switch reason {
   case 0:advance(5.1)
   case 1:h.isCentral=false;advance(0.04)
   case 2:h.videoNode=UniversalVideoNode();advance(0.04)
   default:let other=NSObject();h.context.sharedContext.mediaManager.currentPictureInPictureNode=other;advance(0.04);withExtendedLifetime(other){}
   }
   check(h.nagramiXPiPVisualState.phase == .idle && h.nagramiXPiPEntryTimer==nil,"timeout/recycle/centrality cancels request")
   check(h.controller!.galleryNode.scrollView.contentOffset.y==844,"failure resets full swipe position")
   check(h.controller!.view.alpha==1 && h.dismissals==0,"failed entry keeps usable original screen")
  }
  do {
   let h=GalleryLifecycleBoundary();h.hasPictureInPicture=false
   h.controller!.galleryNode.scrollView.contentOffset.y+=31
   check(!h.nagramiXRequestPictureInPicture(),"disabled PiP refused")
   check(h.controller!.galleryNode.scrollView.contentOffset.y==844,"pre-lock failure also resets drag")
  }
  do {
   let h=GalleryLifecycleBoundary();h.nagramiXRequestPictureInPicture();let old=h.nativePictureInPictureContent as! NativePictureInPictureContentImpl
   advance(5.1);check(old.cancelled,"unconfirmed native start cancelled")
   h.nagramiXRequestPictureInPicture();let current=h.nativePictureInPictureContent as! NativePictureInPictureContentImpl
   old.did(old);old.failed(old);old.end(old)
   check(h.nativePictureInPictureContent === current && h.nagramiXPiPVisualState.phase == .starting,"retired native callbacks cannot change new request")
   current.finish();check(h.dismissals==1,"new request can succeed after timeout");current.stop()
  }
  for embedded in [false,true] {
   let h=GalleryLifecycleBoundary();h.item!.embedded=embedded
   if embedded{h.item!.content=WebEmbedVideoContent()}
   h.nagramiXRequestPictureInPicture()
   if embedded{h.videoNode!.isNativePictureInPictureActive.set(true)}else{(h.nativePictureInPictureContent as! NativePictureInPictureContentImpl).finish()}
   let source=h.videoNode!
   h.nagramiXApplyVideoDimensions(CGSize(width:720,height:1280))
   check(source.layouts.isEmpty,"decoded geometry deferred while source belongs to PiP")
   if embedded {
    var a:[Bool]=[],b:[Bool]=[]
    h.nagramiXRestoreSystemWebPiP{a.append($0)};h.nagramiXRestoreSystemWebPiP{b.append($0)}
    DispatchQueue.main.run()
    check(a==[true] && b==[true] && h.navigation!.currentWindow!.presents==1,"duplicate restore shares one presentation")
    check(h.controller!.backdrop && h.nagramiXPiPVisualState.phase == .restoring,"poster stays above WebKit placard until actual stop")
    h.videoNode!.isNativePictureInPictureActive.set(false)
   } else {
    let c=h.nativePictureInPictureContent as! NativePictureInPictureContentImpl
    c.requestExpand();DispatchQueue.main.run()
    check(h.controller!.backdrop && h.nagramiXPiPVisualState.phase == .restoring,"poster stays until returned native frame")
   }
   advance(0.02)
   check(h.nagramiXPiPVisualState.phase == .idle && !h.controller!.backdrop,"actual stop plus display turn reveals returned source")
   let expected=embedded ? CGSize(width:720,height:1280):CGSize(width:1440,height:2560)
   check(source.layouts.last?.0==expected && source.layouts.last?.1==CGSize(width:720,height:1280),"actual rotated decoded size and correct source scale")
   check(source.pauses==0,"restored source retains playback position and pause state")
  }
  do {
   let h=GalleryLifecycleBoundary();h.item!.embedded=true;h.nagramiXRequestPictureInPicture();h.expandPIP()
   check(h.navigation!.currentWindow!.presents==0,"early expand waits for system start")
   h.videoNode!.isNativePictureInPictureActive.set(true);DispatchQueue.main.run();DispatchQueue.main.run()
   check(h.navigation!.currentWindow!.presents==1,"early expand restored once after start")
   advance(0.02)
   if h.nagramiXWebPiPTransitionStarted{h.nagramiXFinishSystemWebPiP(stop:true)}
  }
  do {
   let h=GalleryLifecycleBoundary();h.item!.embedded=true;h.nagramiXRequestPictureInPicture();h.videoNode!.isNativePictureInPictureActive.set(true)
   h.navigation!.currentWindow!.attaches=false
   var result:[Bool]=[];h.nagramiXRestoreSystemWebPiP{result.append($0)};DispatchQueue.main.run();advance(2.1)
   check(result==[false] && h.nagramiXPiPVisualState.phase == .active,"failed restore preserves active PiP")
   check(h.videoNode!.stops==0,"failed restore does not prematurely stop existing PiP")
   h.nagramiXFinishSystemWebPiP(stop:true)
  }
  do {
   let h=GalleryLifecycleBoundary();h.nagramiXRequestPictureInPicture()
   let c=h.nativePictureInPictureContent as! NativePictureInPictureContentImpl;c.finish()
   h.videoNode!.sourceLayer!.isReadyForDisplay=false
   c.requestExpand();DispatchQueue.main.run();advance(0.02)
   check(h.controller!.backdrop && h.nagramiXPiPVisualState.phase == .restoring,"returned source stays covered until a real frame is ready")
   h.videoNode!.sourceLayer!.isReadyForDisplay=true;advance(0.06);advance(0.02)
   check(h.nagramiXPiPVisualState.phase == .idle && !h.controller!.backdrop,"ready returned frame reveals full player")
  }
  do {
   let h=GalleryLifecycleBoundary();h.videoNode!.view.bounds = .zero;h.nagramiXRequestPictureInPicture()
   check(h.nagramiXPiPVisualState.phase == .waiting && h.dismissals==0,"pending layout does not produce an invalid PiP source")
   h.videoNode!.view.bounds=CGRect(x:0,y:0,width:390,height:219);advance(0.04)
   (h.nativePictureInPictureContent as! NativePictureInPictureContentImpl).finish()
   check(h.dismissals==1,"late valid source layout can enter without another user tap")
   (h.nativePictureInPictureContent as! NativePictureInPictureContentImpl).stop()
  }
  do {
   let h=GalleryLifecycleBoundary();h.videoNode!.sourceLayer!.isReadyForDisplay=false
   h.nagramiXRequestPictureInPicture()
   check(h.nagramiXPiPVisualState.phase == .waiting && h.dismissals==0,"AVKit possible alone cannot bypass first-frame readiness")
   h.videoNode!.sourceLayer!.isReadyForDisplay=true;advance(0.04)
   (h.nativePictureInPictureContent as! NativePictureInPictureContentImpl).finish()
   check(h.dismissals==1,"first displayed frame lets pending PiP start normally")
   (h.nativePictureInPictureContent as! NativePictureInPictureContentImpl).stop()
  }
  print("\(checks) PiP coordinator production checks passed")
 }
}
