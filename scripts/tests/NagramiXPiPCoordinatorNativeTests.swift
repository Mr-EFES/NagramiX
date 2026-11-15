@main struct NativeTests {
 static func main(){
  var checks=0
  func check(_ v:@autoclosure()->Bool,_ message:String){if !v(){FileHandle.standardError.write(Data(("PiP native: "+message+"\n").utf8));exit(96)};checks+=1}
  let n=NativeLifecycle(),controller=n.pictureInPictureController!
  check(n.matchesSourceLayer,"original layer identity matches")
  n.node.layer=AVSampleBufferDisplayLayer();check(!n.matchesSourceLayer,"replaced source detected before starting")
  n.nagramiXOriginalSourceLayer=n.node.layer
  controller.isPictureInPicturePossible=false
  check(!n.beginPictureInPicture() && controller.starts==0,"actual not-ready controller stays waiting")
  controller.isPictureInPicturePossible=true
  check(n.beginPictureInPicture() && n.isStarting && controller.starts==1,"ready native start sent once")
  check(!n.beginPictureInPicture() && controller.starts==1,"duplicate native start blocked")
  n.cancelPendingStart()
  check(n.nagramiXStartCancelled && !n.isStarting && controller.stops==1,"timeout cancels underlying AVKit request")
  check(n.leaseReleases==1 && n.restoreCancels==1,"cancel releases old hierarchy/restore ownership")
  n.pictureInPictureControllerDidStartPictureInPicture(controller)
  check(n.begins==0 && controller.stops==2,"late DidStart cannot revive cancelled playback")
  n.beginPictureInPicture();n.nagramiXExpandWhenStarted=true
  n.pictureInPictureControllerDidStartPictureInPicture(controller)
  check(n.begins==1 && !n.isStarting,"new native start can complete normally")
  n.pictureInPictureControllerDidStartPictureInPicture(controller)
  check(n.begins==1,"duplicate DidStart cannot dismiss or stop current PiP")
  check(DispatchQueue.main.jobs.count==1,"queued early Expand dispatched only once")
  DispatchQueue.main.jobs.forEach{$0()}
  check(n.expands==1,"native early Expand returns existing screen")
  print("\(checks) native cancellation production checks passed")
 }
}
