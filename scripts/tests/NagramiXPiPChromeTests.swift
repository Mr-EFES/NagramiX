import Foundation

@main struct PiPChromeTests {
    static func main() {
        let host = ChromeHost()
        host.update(isVisible: true)
        precondition(!host.playbackControls.view!.isHidden)
        host.nagramiXPiPSwipeTransitionPending = true
        host.update(isVisible: false)
        precondition(host.playbackControls.view!.isHidden)
        // Cancel возвращает видимость до завершения return-анимации.
        host.update(isVisible: true)
        precondition(!host.playbackControls.view!.isHidden)
        host.nagramiXPiPSwipeTransitionPending = false
        host.nagramiXPiPNativeTransitionInFlight = true
        host.update(isVisible: false)
        precondition(host.playbackControls.view!.isHidden)
        // После restore/stop штатный tap снова показывает контролы.
        host.nagramiXPiPNativeTransitionInFlight = false
        host.update(isVisible: true)
        precondition(!host.playbackControls.view!.isHidden)
        host.playbackControls.view = nil
        host.update(isVisible: false)
        print("PASS: actual control-host visibility through swipe/cancel/native/restore/nil-view")
    }
}
