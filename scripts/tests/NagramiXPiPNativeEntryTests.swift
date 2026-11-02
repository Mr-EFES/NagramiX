import Foundation

@main struct NativeEntryTests {
    static func main() {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ message: String) {
            checks += 1
            if !condition() { FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1) }
        }
        let host = Host(), item = UniversalVideoGalleryItemNode(host: Host())
        item.gallery.view.window = host; item.videoNode!.view.window = host
        check(item.eligible, "visible current gallery with a window host must be eligible without navigation")
        item.isCentral = false
        check(item.eligible, "actual pager owner outranks stale centrality cache")
        item.footerContentNode.press()
        check(item.buttonCount == 1, "bound footer button must work before controller interaction is supplied")
        let other = UniversalVideoGalleryItemNode(host: host), interaction = ControllerInteraction()
        interaction.current = other; item.footerContentNode.controllerInteraction = interaction
        item.footerContentNode.press()
        check(item.buttonCount == 2 && other.buttonCount == 0, "bound button never redirects to a different current item")
        let fallback = Footer(); fallback.controllerInteraction = interaction; fallback.press()
        check(other.buttonCount == 1, "stock footer fallback remains available for unbound callers")
        item.gallery.node.pager.current = other
        check(!item.eligible && item.reason == "not_current_gallery", "stale item cannot start PiP")
        item.gallery.node.pager.current = item
        item.gallery.node.nagramiXAllowsSystemPiPTransition = false
        check(!item.eligible, "dismissed gallery cannot start PiP")
        item.gallery.node.nagramiXAllowsSystemPiPTransition = true
        item.item!.isSecret = true
        check(!item.eligible && item.reason == "secret_content", "secret gate preserved")
        item.item!.isSecret = false
        item.item!.contentInfo = .message(Message(adAttribute: 1), 0)
        check(!item.eligible && item.reason == "advertisement", "ad gate preserved")
        item.item!.contentInfo = .other
        let animated = NativeVideoContent(); animated.fileReference.media.isAnimated = true; item.item!.content = animated
        check(!item.eligible && item.reason == "animated_content", "GIF gate preserved")
        item.item!.content = HLSVideoContent()
        check(item.eligible, "ordinary HLS remains eligible")
        item.context.currentAppConfiguration.value.data = ["ios_killswitch_disable_native_pip_v2": false]
        check(!item.eligible && item.reason == "server_disabled", "existing server presence gate unchanged")
        item.context.currentAppConfiguration.value.data = nil
        AVPictureInPictureController.supported = false
        check(!item.eligible && item.reason == "unsupported_device", "unsupported hardware gate preserved")
        AVPictureInPictureController.supported = true
        for landscape in [false, true] {
            _ = landscape // UIView geometry is owned by the unchanged native layout.
            let owner = UniversalVideoGalleryItemNode(host: host), content = NagramiXSystemPiPController()
            owner.nativePictureInPictureContent = content
            owner.visual.willStart()
            check(owner.gallery.view.alpha == 1 && owner.videoNode!.view.effectiveAlpha == 1, "willStart keeps live source visible")
            check(owner.gallery.node.backgroundNode.alpha == 0 && owner.dismissCount == 0, "only backdrop fades before native success")
            owner.visual.cancel()
            check(owner.gallery.node.backgroundNode.alpha == 1 && owner.gallery.view.alpha == 1, "failed attempt restores backdrop with source visible")
            owner.visual.willStart()
            check(owner.transfer(content), "successful system transfer does not require a navigation controller")
            check(owner.beginCount == 1 && owner.dismissCount == 1 && owner.context.sharedContext.mediaManager.currentPictureInPictureNode === owner,
                  "native success commits exactly one gallery dismissal and owner")
            check(owner.activePictureInPictureNavigationController == nil && owner.nagramiXActivePiPWindowHost != nil,
                  "actual source window host is retained for restoration")
            var completions = 0
            owner.restore { restored in check(restored, "Expand restores through original window host"); completions += 1 }
            check(completions == 1 && owner.gallery.view.window === host && owner.gallery.view.alpha == 1,
                  "restoration returns the same gallery once without replacing player")
            check(owner.gallery.node.backgroundNode.alpha == 1 && owner.gallery.node.restorations == 1,
                  "restoration resets only the backdrop and existing gestures")
        }
        let reduced = UniversalVideoGalleryItemNode(host: host)
        UIAccessibility.isReduceMotionEnabled = true
        reduced.visual.willStart()
        check(reduced.gallery.view.alpha == 1 && reduced.gallery.node.backgroundNode.alpha == 0, "Reduce Motion preserves source visibility")
        reduced.visual.cancel()
        check(reduced.gallery.node.backgroundNode.alpha == 1, "Reduce Motion rollback restores backdrop")
        UIAccessibility.isReduceMotionEnabled = false
        NagramiXPiPDiagnostics.begin("button")
        NagramiXPiPDiagnostics.record("readiness=avkit_unavailable")
        check(NagramiXPiPDiagnostics.report.contains("request=button") && NagramiXPiPDiagnostics.report.contains("avkit_unavailable"), "explicit failure trace survives in defaults for copying")
        for i in 0..<100 { NagramiXPiPDiagnostics.record("stage=\(i)") }
        check(NagramiXPiPDiagnostics.report.split(separator: "\n").count == 33, "diagnostics bounded to 32 events plus version")
        NagramiXPiPDiagnostics.begin("swipe")
        check(!NagramiXPiPDiagnostics.report.contains("stage=") && NagramiXPiPDiagnostics.report.contains("request=swipe"), "new attempt replaces previous diagnostic events")
        print("PASS: \(checks) actual footer/admission/window-host/fade/transfer/restore/diagnostic checks; UIKit/AVKit boundary")
    }
}
