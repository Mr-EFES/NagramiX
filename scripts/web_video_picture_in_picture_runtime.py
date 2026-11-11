"""Production web-PiP decisions and handoff; UIKit/WebKit IO are adapters."""
from validate_quick_format import block
from validate_pip_swipe_handoff import clean, G, U


def fixture(source):
    gallery = (source / G).read_text()
    item = (source / U).read_text()
    config = clean(block(gallery, 'public struct GalleryConfiguration'))
    content_kind = clean(block(item, 'private func nagramiXUsesEmbeddedPictureInPicture('))
    policy = clean(block(item, 'private func nagramiXCanOfferWebPictureInPicture('))
    start = clean(block(item, '    private func nagramiXBeginWebPictureInPicture()'))
    custom_close = block(item, 'overlayNode.customClose = { [weak overlayNode, weak mediaManager] in')
    activate = block(item, '    override func activateAsInitial()')
    activate = activate[:activate.index('        if let videoNode = self.videoNode')] + '        nativeActivations += 1\n    }'
    activate = clean(activate).replace('override ', '')
    button = block(item, '    @objc func pictureInPictureButtonPressed()')
    button = button[:button.index('        if self.nativePictureInPictureContent == nil')] + '        nativeButtons += 1\n    }'
    button = clean(button)
    swipe = block(item, '    override func maybePerformActionForSwipeDismiss()')
    swipe = swipe[:swipe.index('        guard #available')] + '        nativeSwipes += 1\n        return false\n    }'
    swipe = clean(swipe).replace('override ', '')
    restore = block(item, 'if nagramiXUsesEmbeddedPictureInPicture(self.item) {\n                self.skipInitialPause = true')
    return ADAPTERS + '\n' + config + '\n' + content_kind + '\n' + policy + '\n' + '''
final class GalleryHarness {
    var item: UniversalVideoGalleryItem?
    var context: Context { item!.context }
    var videoNode: VideoNode? = VideoNode()
    var isCentral: Bool? = true
    var validLayout: Int? = 1
    var hasPictureInPicture = true
    var nagramiXWebPiPTransitionStarted = false
    var customUnembedWhenPortrait: ((OverlayMediaItemNode) -> Bool)?
    var scrollNode = ScrollNode()
    var initiallyActivated = false
    var skipInitialPause = false
    var playOnContentOwnership = true
    var placeholderSuppressed = false
    var nativeActivations = 0, nativeButtons = 0, nativeSwipes = 0
    var constructionCount = 0
    var refuseConstruction = false
    var navigation: Navigation? = Navigation()
    init(_ item: UniversalVideoGalleryItem) { self.item = item }
    func baseNavigationController() -> Navigation? { navigation }
    func nagramiXSetNativePictureInPicturePlaceholderSuppressed(_ value: Bool) { placeholderSuppressed = value }
    func expandIntoCustomPiP() {
        guard !refuseConstruction else { return }
        constructionCount += 1
        let node = OverlayMediaItemNode()
        _ = customUnembedWhenPortrait?(node)
        customUnembedWhenPortrait = nil
    }
    func restore() {
        ''' + restore + '''
    }
''' + start + '\n' + activate + '\n' + button + '\n' + swipe + '\n}\n' + '''
func installClose(_ overlayNode: OverlayMediaItemNode, _ mediaManager: MediaManager, _ item: UniversalVideoGalleryItem) {
    ''' + custom_close + '''
}
''' + TESTS


ADAPTERS = r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

struct AppConfiguration { var data: [String: Any]? }
final class Atomic<T> {
    var value: T
    init(_ value: T) { self.value = value }
    func with<R>(_ transform: (T) -> R) -> R { transform(value) }
}
enum NagramiXTabSettings { static var videoPiPSwipeEnabled = true }
enum Namespaces {
    enum Message { static let Local = 99; static let allNonRegular: Set<Int> = [100, 101] }
}
enum WebEmbedType { case youtube, vimeo, iframe }
func webEmbedType(content: WebEmbedType) -> WebEmbedType { content }
class Content { let id: AnyHashable = "same-live-player" }
final class WebEmbedVideoContent: Content { var webpageContent: WebEmbedType = .youtube }
final class SystemVideoContent: Content {}
final class PlatformVideoContent: Content {}
struct MessageId { var namespace = 1 }
struct Message { var id = MessageId(); var paidContent: Int?; var adAttribute: Int? }
enum ContentInfo { case message(Message, Int?), webPage(Int, Int, (() -> Void)?) }
final class UniversalVideoGalleryItem {
    var context = Context()
    var content: Content = WebEmbedVideoContent()
    var isSecret = false, fromPlayingVideo = false
    var contentInfo: ContentInfo? = .message(Message(), nil)
}
final class Playback { var pauses = 0; func pause() { pauses += 1 } }
final class VideoManager {
    var player = Playback()
    var lookedUp: [AnyHashable] = []
    func withUniversalVideoContent(id: AnyHashable, _ f: (Playback?) -> Void) { lookedUp.append(id); f(player) }
}
final class OverlayMediaItemNode {
    var hasAttachedContext = true, canAttachContent = true
    var customClose: (() -> Void)?
}
final class MediaManager {
    var currentPictureInPictureNode: AnyObject?
    var current: OverlayMediaItemNode?
    var universalVideoManager = VideoManager()
    var overlayMediaManager = OverlayManager()
    var sets = 0, accept = true
    func setOverlayVideoNode(_ node: OverlayMediaItemNode?) {
        sets += 1
        if accept || node == nil { current = node }
    }
    func hasOverlayVideoNode(_ node: OverlayMediaItemNode) -> Bool { current === node }
}
class ViewController {}
final class Navigation { var topViewController: AnyObject? = ViewController() }
final class OverlayManager { var controller: ViewController? = ViewController() }
final class SharedContext {
    var mediaManager = MediaManager()
}
final class Context {
    var currentAppConfiguration = Atomic(AppConfiguration(data: nil))
    var sharedContext = SharedContext()
}
final class ScrollView { var zoomScale = 1.0, minimumZoomScale = 1.0 }
final class ScrollNode { var view = ScrollView() }
final class VideoNode { var ownsContentNode = true }
'''

TESTS = r'''
var checks = 0
func check(_ value: Bool, _ diagnostic: String) {
    checks += 1
    if !value { FileHandle.standardError.write(Data(diagnostic.utf8)); exit(96) }
}
func make(_ type: WebEmbedType = .youtube) -> UniversalVideoGalleryItem {
    let item = UniversalVideoGalleryItem()
    (item.content as! WebEmbedVideoContent).webpageContent = type
    return item
}
@main struct Main {
    static func main() {
        policyTests()
        handoffTests()
        closeTests()
        restoreTests()
        print("web-video-pip production checks: \(checks)")
    }
    static func policyTests() {
        for enabled in [false, true] {
            NagramiXTabSettings.videoPiPSwipeEnabled = enabled
            for setting: Any? in [nil, "disabled", "enabled", "", 1] {
                var data: [String: Any] = [:]
                if let setting { data["youtube_pip"] = setting }
                let rawServerEnabled = (setting as? String).map { $0 != "disabled" } ?? false
                let config = GalleryConfiguration.with(appConfiguration: AppConfiguration(data: data))
                check(config.youtubePictureInPictureEnabled == (enabled || rawServerEnabled), "shared switch overrides only YouTube server gate")
                for type in [WebEmbedType.youtube, .vimeo, .iframe] {
                    let item = make(type)
                    item.context.currentAppConfiguration.value.data = data
                    let expected = enabled || (type == .youtube && rawServerEnabled)
                    check(nagramiXCanOfferWebPictureInPicture(item) == expected, "web policy honors current switch and fresh server value")
                    item.isSecret = true
                    check(!nagramiXCanOfferWebPictureInPicture(item), "secret media cannot use web fallback")
                    item.isSecret = false
                    for namespace in [Namespaces.Message.Local, 100, 101] {
                        item.contentInfo = .message(Message(id: MessageId(namespace: namespace)), nil)
                        check(!nagramiXCanOfferWebPictureInPicture(item), "local or nonregular message excluded")
                    }
                    item.contentInfo = .message(Message(paidContent: 1), nil)
                    check(!nagramiXCanOfferWebPictureInPicture(item), "paid restriction preserved")
                    item.contentInfo = .message(Message(adAttribute: 1), nil)
                    check(!nagramiXCanOfferWebPictureInPicture(item), "ad restriction preserved")
                    item.contentInfo = .webPage(1, 1, nil)
                    check(!nagramiXCanOfferWebPictureInPicture(item), "unrestorable page cannot be minimized")
                    item.contentInfo = .webPage(1, 1, {})
                    check(nagramiXCanOfferWebPictureInPicture(item) == expected, "page with restore callback may minimize")
                    item.contentInfo = nil
                    check(!nagramiXCanOfferWebPictureInPicture(item), "missing origin excluded")
                    item.content = Content()
                    check(!nagramiXCanOfferWebPictureInPicture(item), "native video excluded from web route")
                }
            }
        }
        let item = make()
        NagramiXTabSettings.videoPiPSwipeEnabled = true
        check(nagramiXCanOfferWebPictureInPicture(item), "fresh default enables YouTube")
        NagramiXTabSettings.videoPiPSwipeEnabled = false
        check(!nagramiXCanOfferWebPictureInPicture(item), "turning off does not retain a forced cached configuration")
        for content in [SystemVideoContent(), PlatformVideoContent()] as [Content] {
            item.content = content
            item.context.currentAppConfiguration.value.data = ["youtube_pip": "enabled"]
            check(!nagramiXCanOfferWebPictureInPicture(item), "OFF restores non-YouTube standard policy")
            NagramiXTabSettings.videoPiPSwipeEnabled = true
            check(nagramiXCanOfferWebPictureInPicture(item), "stock AVPlayer wrappers gain same fallback")
            NagramiXTabSettings.videoPiPSwipeEnabled = false
        }
        check(!nagramiXUsesEmbeddedPictureInPicture(nil), "missing item cannot dispatch embedded route")
    }
    static func handoffTests() {
        NagramiXTabSettings.videoPiPSwipeEnabled = true
        let owner = GalleryHarness(make())
        check(owner.nagramiXBeginWebPictureInPicture(), "web handoff starts")
        check(owner.constructionCount == 1 && owner.placeholderSuppressed, "one overlay with no technical placeholder")
        check(!owner.nagramiXBeginWebPictureInPicture() && owner.constructionCount == 1, "repeat tap cannot duplicate player")
        owner.pictureInPictureButtonPressed()
        check(owner.constructionCount == 1 && owner.nativeButtons == 0, "web button does not invoke AVKit")
        let requirements: [(String, (GalleryHarness) -> Void)] = [
            ("central row", { $0.isCentral = false }),
            ("known centrality", { $0.isCentral = nil }),
            ("layout", { $0.validLayout = nil }),
            ("live ownership", { $0.videoNode!.ownsContentNode = false }),
            ("video", { $0.videoNode = nil }),
            ("button eligibility", { $0.hasPictureInPicture = false }),
            ("unzoomed", { $0.scrollNode.view.zoomScale = 2 }),
            ("overlay host", { $0.context.sharedContext.mediaManager.overlayMediaManager.controller = nil }),
            ("navigation", { $0.navigation = nil }),
            ("presenter", { $0.navigation!.topViewController = nil }),
            ("no second native PiP", { $0.context.sharedContext.mediaManager.currentPictureInPictureNode = NSObject() }),
            ("current policy", { $0.item!.isSecret = true })
        ]
        for (name, invalidate) in requirements {
            let candidate = GalleryHarness(make()); invalidate(candidate)
            check(!candidate.nagramiXBeginWebPictureInPicture(), "preflight requires " + name)
            check(candidate.constructionCount == 0 && !candidate.placeholderSuppressed && !candidate.nagramiXWebPiPTransitionStarted, "failed preflight leaves gallery usable")
        }
        for refuse in [true, false] {
            let retry = GalleryHarness(make())
            var previousCalls = 0
            retry.customUnembedWhenPortrait = { _ in previousCalls += 1; return true }
            retry.refuseConstruction = refuse
            retry.context.sharedContext.mediaManager.accept = false
            check(!retry.nagramiXBeginWebPictureInPicture(), "failed handoff reports failure")
            check(!retry.nagramiXWebPiPTransitionStarted && !retry.placeholderSuppressed, "failed handoff restores local state")
            _ = retry.customUnembedWhenPortrait?(OverlayMediaItemNode())
            check(previousCalls == 1, "failed handoff restores prior embed callback")
            retry.refuseConstruction = false; retry.context.sharedContext.mediaManager.accept = true
            check(retry.nagramiXBeginWebPictureInPicture(), "failed handoff can retry")
        }
        let swipe = GalleryHarness(make(.iframe))
        check(swipe.maybePerformActionForSwipeDismiss(), "web swipe shares same route")
        check(swipe.nativeSwipes == 0, "web swipe does not touch native drag state")
        let disabledSwipe = GalleryHarness(make())
        disabledSwipe.context.currentAppConfiguration.value.data = ["ios_killswitch_disable_swipe_pip": true]
        check(!disabledSwipe.maybePerformActionForSwipeDismiss() && disabledSwipe.constructionCount == 0, "swipe kill switch is preserved")
        disabledSwipe.pictureInPictureButtonPressed()
        check(disabledSwipe.constructionCount == 1, "swipe kill switch does not disable explicit web button")
        let native = GalleryHarness(make()); native.item!.content = Content()
        native.pictureInPictureButtonPressed()
        _ = native.maybePerformActionForSwipeDismiss()
        check(native.nativeButtons == 1 && native.nativeSwipes == 1 && native.constructionCount == 0, "native content keeps original button and swipe paths")
        for content in [SystemVideoContent(), PlatformVideoContent()] as [Content] {
            let wrapper = GalleryHarness(make()); wrapper.item!.content = content
            wrapper.pictureInPictureButtonPressed()
            check(wrapper.constructionCount == 1 && wrapper.nativeButtons == 0, "AVPlayer wrapper uses retained overlay")
        }
    }
    static func closeTests() {
        let item = make(), manager = MediaManager(), overlay = OverlayMediaItemNode()
        manager.current = overlay
        installClose(overlay, manager, item)
        overlay.customClose?()
        check(manager.current == nil && !overlay.canAttachContent, "explicit close releases owned overlay")
        check(manager.universalVideoManager.player.pauses == 1 && manager.universalVideoManager.lookedUp == [item.content.id], "explicit close pauses only same live player")
        overlay.customClose?()
        check(manager.universalVideoManager.player.pauses == 1, "repeat close is inert")
        let expanding = OverlayMediaItemNode(); expanding.hasAttachedContext = false
        manager.current = expanding; installClose(expanding, manager, item)
        expanding.customClose?()
        check(manager.current == nil && manager.universalVideoManager.player.pauses == 1, "ownership transfer never pauses restored player")
        let stale = OverlayMediaItemNode(), current = OverlayMediaItemNode()
        installClose(stale, manager, item); manager.current = current
        stale.customClose?()
        check(manager.current === current && manager.universalVideoManager.player.pauses == 1, "stale close cannot remove another overlay")
        weak var released: OverlayMediaItemNode?
        do { let node = OverlayMediaItemNode(); released = node; installClose(node, manager, item) }
        check(released == nil, "close callback does not retain overlay")
    }
    static func restoreTests() {
        let owner = GalleryHarness(make())
        owner.item!.fromPlayingVideo = true
        owner.activateAsInitial()
        check(owner.initiallyActivated && owner.nativeActivations == 0, "web restore preserves paused state and position")
        owner.initiallyActivated = false
        owner.restore()
        check(owner.skipInitialPause && !owner.playOnContentOwnership && owner.initiallyActivated, "web restore cannot seek or play on content transfer")
        let ordinary = GalleryHarness(make())
        ordinary.activateAsInitial()
        check(ordinary.nativeActivations == 1, "initial web open retains standard activation")
        ordinary.item!.content = Content(); ordinary.item!.fromPlayingVideo = true
        ordinary.activateAsInitial(); ordinary.restore()
        check(ordinary.nativeActivations == 2 && !ordinary.skipInitialPause && ordinary.playOnContentOwnership, "native restore is unchanged")
        for content in [SystemVideoContent(), PlatformVideoContent()] as [Content] {
            let wrapper = GalleryHarness(make()); wrapper.item!.content = content; wrapper.item!.fromPlayingVideo = true
            wrapper.activateAsInitial(); wrapper.restore()
            check(wrapper.nativeActivations == 0 && wrapper.initiallyActivated && wrapper.skipInitialPause, "AVPlayer wrapper restore preserves live player")
        }
    }
}
'''


def negatives(code):
    cases = [
        ('server-gate', 'if NagramiXTabSettings.videoPiPSwipeEnabled {', 'if false {', 'shared switch overrides only YouTube server gate'),
        ('duplicate-player', 'guard !self.nagramiXWebPiPTransitionStarted,', 'guard true,', 'repeat tap cannot duplicate player'),
        ('lost-ownership', 'let videoNode = self.videoNode, videoNode.ownsContentNode,', 'let _ = self.videoNode, true,', 'preflight requires live ownership'),
        ('failed-handoff-state', 'self.nagramiXWebPiPTransitionStarted = false\n            self.nagramiXSetNativePictureInPicturePlaceholderSuppressed(false)', 'self.nagramiXWebPiPTransitionStarted = true\n            self.nagramiXSetNativePictureInPicturePlaceholderSuppressed(false)', 'failed handoff restores local state'),
        ('expansion-pauses', 'if overlayNode.hasAttachedContext {', 'if true {', 'ownership transfer never pauses restored player'),
        ('stale-close', 'mediaManager.hasOverlayVideoNode(overlayNode) else { return }', 'true else { return }', 'repeat close is inert'),
        ('restore-restarts', 'if self.item?.fromPlayingVideo == true, nagramiXUsesEmbeddedPictureInPicture(self.item) {', 'if false {', 'web restore preserves paused state and position'),
    ]
    for name, before, after, diagnostic in cases:
        assert code.count(before) == 1, (name, code.count(before))
        yield name, code.replace(before, after, 1), diagnostic
