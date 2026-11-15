final class PosterLifetimeProbe {weak var node:ASDisplayNode?}
@main struct PosterTests {
 static func main(){
  var checks=0
  var diagnostics:()->String={""}
  func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("PiP poster: "+message+"\n"+diagnostics()+"\n").utf8));exit(96)};checks+=1}
  for content in [NativeVideoContent() as UniversalVideoContent,HLSVideoContent(),WebEmbedVideoContent()] {
   for dimensions in [CGSize(width:1920,height:1080),CGSize(width:1080,height:1920),CGSize(width:1000,height:1000),CGSize(width:2560,height:1080)] {
    for bounds in [CGSize(width:390,height:844),CGSize(width:844,height:390)] {
     let item=UniversalVideoGalleryItem(content)
     let poster=UniversalVideoGalleryItemPictureInPictureNode(item:item,imageSize:dimensions)
     poster.updateLayout(bounds,transition:.immediate)
     let image=poster.children[0] as! TransformImageNode
     check(image.source != nil && image.synchronous,"cached original poster is available synchronously")
     check(abs(image.frame.width/image.frame.height-dimensions.width/dimensions.height)<0.000001,"preview preserves decoded orientation and aspect")
     check(image.frame.minX>=0 && image.frame.minY>=0 && image.frame.maxX<=bounds.width+0.0001 && image.frame.maxY<=bounds.height+0.0001,"full frame visible without crop")
    }
   }
  }
  for secret in [false,true]{for protected in [false,true]{
   let item=UniversalVideoGalleryItem(NativeVideoContent());item.isSecret=secret;item.peerIsCopyProtected=protected
   let poster=UniversalVideoGalleryItemPictureInPictureNode(item:item)
   let image=poster.children[0] as! TransformImageNode
   check(image.layer.capture==(secret || protected) && image.layer.bypass == !secret,"source capture policy retained")
  }}
  let controller=GalleryController(),host=PosterHost(),video=ASDisplayNode()
  diagnostics={"covers=\(controller.view.subviews.count), completionCount=\(AnimationClock.pending.count), ownerActive=\(controller.nagramiXNativePiPBackdropActive), ownsPoster=\(controller.nagramiXNativePiPBackdropPoster != nil)"}
  controller.view.frame=CGRect(x:0,y:0,width:390,height:844);controller.galleryNode.pager.item=host
  host.controller=controller;host.item=UniversalVideoGalleryItem(NativeVideoContent());host.videoNode=video
  video.frame=CGRect(x:0,y:200,width:390,height:219)
  check(controller.nagramiXPrepareNativePiPBackdrop(),"source preview prepared")
  check(UIView.snapshots==0 && controller.nagramiXNativePiPBackdrop?.superview==nil,"no full-screen chat or gallery snapshot; source stays uncovered before start")
  controller.nagramiXShowNativePiPBackdrop()
  check(controller.view.subviews.count==1 && controller.nagramiXNativePiPBackdrop!.frame==video.frame,"only vacated source rectangle covered")
  controller.nagramiXFinishNativePiPBackdrop(animated:false)
  check(controller.view.subviews.isEmpty && !controller.galleryNode.suppressed,"exit removes preview and restores interaction")
  host.nagramiXPiPVisualState.restore();host.playerStatusValue=MediaPlayerStatus(dimensions:CGSize(width:720,height:1280))
  check(controller.nagramiXPrepareNativePiPBackdrop(),"rotated source preview prepared on restore")
  let preview=controller.nagramiXNativePiPBackdrop!
  check(abs(preview.frame.width/preview.frame.height-720.0/1280.0)<0.00001,"restore uses real decoded portrait dimensions")
  controller.nagramiXShowNativePiPBackdrop()
  controller.view.frame=CGRect(x:0,y:0,width:844,height:390)
  controller.nagramiXUpdateNativePiPBackdropLayout()
  check(controller.view.subviews.count==1 && UIView.snapshots==0,"rotation rebuilds only poster instead of stretching old screen capture")
  let lifetime=PosterLifetimeProbe();lifetime.node=controller.nagramiXNativePiPBackdropPoster
  let fadingView=controller.nagramiXNativePiPBackdrop!
  var aliveAtRemoval=false
  UIView.willRemove={view in if view===fadingView {aliveAtRemoval=lifetime.node != nil}}
  controller.nagramiXFinishNativePiPBackdrop(animated:true)
  check(controller.view.subviews.count==1 && AnimationClock.pending.count==1,"cover stays until asynchronous completion")
  check(lifetime.node != nil,"image subscription lives during fade")
  AnimationClock.flush()
  UIView.willRemove=nil
  check(aliveAtRemoval,"image subscription lives through removal")
  check(lifetime.node==nil,"image subscription released after completion")
  check(controller.view.subviews.isEmpty,"successful return releases cached image subscription and cover")
  print("\(checks) PiP source poster production checks passed")
 }
}
