@main enum NativePiPTests {
    static var checks=0
    static func check(_ value:@autoclosure()->Bool,_ label:String) {
        if !value(){fatalError("Native PiP regression: "+label)};checks+=1
    }
    static func gallery()->GalleryHarness {
        AVPictureInPictureController.supported=true
        AVPictureInPictureController.possibleOnCreation=true
        NagramiXTabSettings.videoPiPSwipeEnabled=true
        return GalleryHarness()
    }
    static func main() {
        let first=gallery()
        check(first.nativePictureInPictureContent == nil,"controller starts through the same native entry on first use")
        first.pictureInPictureButtonPressed()
        let button=AVPictureInPictureController.instances.last!
        check(button.starts==1 && first.dismissals==1,"first ready button uses native start exactly once")
        check(button.contentSource?.sampleBufferDisplayLayer === first.videoNode!.layer,"native source is the existing video layer")
        check(first.context.sharedContext.mediaManager.currentPictureInPictureNode === first,"native manager keeps the same gallery owner")
        check(first.videoNode!.withoutHierarchy,"native lifecycle allows continuing video")
        check(first.gallery.view.layer.alphaAnimations.first?.2==0.2,"native enter animation preserved")
        var restored=false
        let content=first.nativePictureInPictureContent as! NativePictureInPictureContentImpl
        content.pictureInPictureController(button,restoreUserInterfaceForPictureInPictureStopWithCompletionHandler:{restored=$0})
        check(restored && first.navigation.currentWindow!.presentations==1,"native restore reuses the same gallery/window")
        check(first.gallery.view.alpha==1 && first.gallery.view.layer.alphaAnimations.last?.2==0.35,"native restore animation and visibility preserved")
        first.expandPIP()
        check(!first.videoNode!.withoutHierarchy && first.context.sharedContext.mediaManager.currentPictureInPictureNode == nil,"native stop releases the owner and background allowance")
        first.pictureInPictureButtonPressed()
        check(button.starts==2,"same native controller supports another entry after restore")
        content.stop()

        let swipe=gallery(),scroll=GalleryScrollHarness(nil)
        scroll.pager.item=swipe
        scroll.gesture(distance:32,translation:CGPoint(x:0,y:-32),velocity:.zero)
        let player=AVPictureInPictureController.instances.last!
        check(player.starts==1 && swipe.dismissals==1 && scroll.closed==0,"first short swipe starts via button without native close")
        check(swipe.context.engine.accountData.logs.contains("pip_btn"),"swipe calls the exact native button entry")
        check(player.contentSource?.sampleBufferDisplayLayer === swipe.videoNode!.layer,"swipe and button use identical native source type")
        (swipe.nativePictureInPictureContent as! NativePictureInPictureContentImpl).stop()
        scroll.gesture(distance:12,translation:CGPoint(x:0,y:-12),velocity:CGPoint(x:0,y:0.4))
        check(player.starts==2 && scroll.closed==0,"quick intentional upward flick uses the same controller")
        (swipe.nativePictureInPictureContent as! NativePictureInPictureContentImpl).stop()
        check(!swipe.maybePerformActionForSwipeDownDismiss(),"down gesture remains the native close action")

        let cases:[(CGFloat,CGPoint,CGPoint,Bool)] = [
            (0,.zero,.zero,false),(7,CGPoint(x:0,y:-7),CGPoint(x:0,y:2),false),
            (31,CGPoint(x:0,y:-31),.zero,false),(32,CGPoint(x:0,y:-32),.zero,true),
            (8,CGPoint(x:0,y:-8),CGPoint(x:0,y:0.35),true),
            (-100,CGPoint(x:0,y:100),CGPoint(x:0,y:-2),false),
            (100,CGPoint(x:0,y:-100),CGPoint(x:0,y:-0.3),false),
            (60,CGPoint(x:100,y:-60),.zero,false),(60,CGPoint(x:0,y:60),.zero,false),
            (.nan,CGPoint(x:0,y:-100),.zero,false),(.infinity,CGPoint(x:0,y:-100),.zero,false)
        ]
        for (d,t,v,expected) in cases {
            check(nagramiXShouldBeginFastPictureInPictureSwipe(distance:d,translation:t,velocity:v)==expected,"gesture threshold, direction, reversal and finite inputs")
        }
        for mode in 0..<7 {
            let owner=gallery()
            if mode==0 {NagramiXTabSettings.videoPiPSwipeEnabled=false}
            if mode==1 {owner.context.currentAppConfiguration.value.data=["ios_killswitch_disable_swipe_pip":true]}
            if mode==2 {owner.context.currentAppConfiguration.value.data=["ios_killswitch_disable_native_pip_v2":true]}
            if mode==3 {owner.item!.contentInfo = .message(Message(adAttribute:1),0)}
            if mode==4 {(owner.item!.content as! NativeVideoContent).fileReference.media.isAnimated=true}
            if mode==5 {owner.videoNode!.hasLayer=false}
            if mode==6 {owner.isCentral=false}
            let before=AVPictureInPictureController.instances.count
            let didHandle=owner.maybePerformActionForSwipeDismiss()
            check(!didHandle && AVPictureInPictureController.instances.count==before,"OFF, killswitches, unsupported source and noncentral item do not dispatch")
        }
        let off=gallery(),close=GalleryScrollHarness(nil);close.pager.item=off;NagramiXTabSettings.videoPiPSwipeEnabled=false
        close.gesture(distance:-60,translation:CGPoint(x:0,y:60),velocity:CGPoint(x:0,y:-2))
        check(close.closed==1 && off.nativePictureInPictureContent == nil,"downward native close preserved")
        let rebound=GalleryScrollHarness(gallery())
        rebound.gesture(distance:10,translation:CGPoint(x:0,y:-10),velocity:.zero)
        check(rebound.scrollView.offsets.last?.0.y==844 && rebound.scrollView.offsets.last?.1==true,"small gesture retains native animated rebound")
        let unavailable=gallery();AVPictureInPictureController.possibleOnCreation=false
        unavailable.pictureInPictureButtonPressed();let denied=AVPictureInPictureController.instances.last!
        check(denied.starts==0 && unavailable.dismissals==0,"native AVKit readiness is respected without synthetic transition")
        AVPictureInPictureController.possibleOnCreation=true
        let monitored=gallery();monitored.item!.contentInfo = .message(Message(effectiveMedia:[TelegramMediaFile()]),0)
        monitored.pictureInPictureButtonPressed();let removed=AVPictureInPictureController.instances.last!
        monitored.context.engine.data.messages.emit(nil)
        check(removed.stops==1,"native original-message deletion stops PiP")
        print("Native PiP baseline checks: \(checks)")
    }
}
