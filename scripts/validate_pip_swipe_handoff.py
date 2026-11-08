#!/usr/bin/env python3
"""Exercise native PiP swipe and handoff bodies without UIKit or a live decoder.

The actual content/delegate, source freeze, scroll delegate, setup and button
bodies run unchanged. AVKit event delivery, UIKit rendering and animation clocks
are bounded adapters. An optional integrated mode verifies all seven preceding
stages and the full source checkpoint; neither mode claims device animation.
"""
import argparse
import hashlib
import json
import importlib.util
import shutil
from pathlib import Path
import re
import resource
import subprocess
import tempfile

from validate_quick_format import block, manifest
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks

ROOT = Path(__file__).resolve().parents[1]
G = 'submodules/GalleryUI/Sources/GalleryController.swift'
N = 'submodules/GalleryUI/Sources/GalleryControllerNode.swift'
I = 'submodules/GalleryUI/Sources/GalleryItemNode.swift'
U = 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'
PATHS = (G, N, I, U)


def clean(text):
    return text.replace('fileprivate ', '').replace('private(set) ', '').replace('private ', '').replace('public ', '').replace('open ', '').replace('@objc ', '')


def custom_members(text):
    lines = text.splitlines()
    result = []
    for line in lines:
        if not re.match(r'^    (?:(?:private(?:\(set\))?|public|open) )?(?:weak )?(?:var|func) nagramiX\w+', line):
            continue
        if 'func ' in line:
            result.append(clean(block(text, line.strip())))
        else:
            result.append(clean(line))
    return '\n'.join(result)


def boundary():
    text = (ROOT / 'scripts/tests/NagramiXNativePiPBaselineBoundary.swift').read_text()
    text = text.replace('final class ImmediateQueue { func async(_ f: @escaping () -> Void) { f() } }', '''final class ImmediateQueue {
    var pending: [() -> Void] = []
    func async(_ f: @escaping () -> Void) { pending.append(f) }
    func flush() { while !pending.isEmpty { let work = pending.removeFirst(); work() } }
}''')
    text = text.replace('    func pictureInPictureControllerDidStopPictureInPicture(_ controller: AVPictureInPictureController)\n', '    func pictureInPictureControllerDidStopPictureInPicture(_ controller: AVPictureInPictureController)\n    func pictureInPictureController(_ controller: AVPictureInPictureController, failedToStartPictureInPictureWithError error: Error)\n')
    old = block(text, '    func startPictureInPicture()')
    text = text.replace(old, '''    static var completeStartsAutomatically = false
    func startPictureInPicture() {
        starts += 1
        guard isPictureInPicturePossible else { return }
        delegate?.pictureInPictureControllerWillStartPictureInPicture(self)
        if Self.completeStartsAutomatically { finishStart() }
    }
    func finishStart() {
        isPictureInPictureActive = true
        delegate?.pictureInPictureControllerDidStartPictureInPicture(self)
    }
    func failStart() {
        isPictureInPictureActive = false
        delegate?.pictureInPictureController(self, failedToStartPictureInPictureWithError: NSError(domain: "fixture", code: 1))
    }''')
    text = text.replace('    func setCanPlaybackWithoutHierarchy(_ value: Bool) { withoutHierarchy = value }', '    var hierarchyCalls: [Bool] = []\n    func setCanPlaybackWithoutHierarchy(_ value: Bool) { hierarchyCalls.append(value); withoutHierarchy = value }')
    text = text.replace('var toggles = 0, pauses = 0', 'var toggles = 0, pauses = 0, plays = 0')
    text = text.replace('    func togglePlayPause() { toggles += 1 }', '    func play() { plays += 1 }\n    func togglePlayPause() { toggles += 1 }')
    text = text.replace('struct UIColor { init(white: Double, alpha: Double) {}; var cgColor: Int { 0 } }', 'struct UIColor { init(white: Double, alpha: Double) {}; var cgColor: Int { 0 }; func withAlphaComponent(_ value: CGFloat) -> Self { self } }')
    text = text.replace('alphaAnimations.append((from,to,duration)); completion(true)', 'alphaAnimations.append((from,to,duration)); AnimationClock.pending.append { completion(true) }')
    text = text.replace('    var alphaAnimations:', '    func removeAnimation(forKey: String) {}\n    var alphaAnimations:')
    text = text.replace('final class UIView { var alpha = 1.0; let layer = Layer() }', 'final class UIView { var alpha = 1.0; let layer = Layer(); func layoutIfNeeded() {} }')
    text = text.replace('class BaseController { let view = UIView(); var presentationArguments: Int? = 7 }', 'class BaseController { let view = UIView(); var presentationArguments: Int? = 7; func viewWillAppear(_ animated: Bool) {} }')
    text = text.replace('final class GalleryController: BaseController { var dismissals = 0; func dismiss(forceAway: Bool) { dismissals += 1 } }', '''final class GalleryController: BaseController {
    var dismissals = 0
    var galleryNode: GalleryScrollHarness!
    var isViewLoaded: Bool { galleryNode != nil }
    func dismiss(forceAway: Bool) { dismissals += 1 }
    // CONTROLLER_MEMBERS
}''')
    text = text.replace('final class NativeVideoContent {', 'protocol TestContent: AnyObject { var id: AnyHashable { get } }\nfinal class NativeVideoContent: TestContent { var id: AnyHashable = 1;')
    text = text.replace('var content: AnyObject = NativeVideoContent()', 'var content: TestContent = NativeVideoContent()')
    text = text.replace('class GalleryBase {', 'class GalleryBase {\n    func prepareForNativePictureInPictureSwipe() {}')
    text = text.replace('struct BackgroundNode {', 'final class BackgroundNode {')
    text = text.replace('enum Transition { case animated', 'enum Transition { case immediate; case animated')
    text = text.replace('    var toasts=0', '    var toasts=0')
    old_pan = block(text, 'final class Pan {')
    text = text.replace(old_pan, '''final class Pan {
    var value = CGPoint.zero
    var speed = CGPoint.zero
    enum State { case began, changed, ended, cancelled }
    var state: State = .changed
    var numberOfTouches = 1
    func translation(in scroll: UIScrollView) -> CGPoint { value }
    func velocity(in scroll: UIScrollView) -> CGPoint { speed }
}''')
    text = text.replace('    var isScrollEnabled=true', '    var isScrollEnabled=true\n    var isDragging=true\n    var zoomScale: CGFloat = 1.0\n    var minimumZoomScale: CGFloat = 1.0')
    text = text.replace('    var item:GalleryHarness?', '    weak var item:GalleryHarness?')
    text = text.replace('    // PRODUCTION_SCROLL', '''    var isDismissed = false
    var areControlsHidden = false
    let footerNode = UIView()
    let headerEdgeEffectView = UIView()
    var currentThumbnailContainerNode: UIView? = UIView()
    var overlayNode: UIView? = UIView()
    var titleView: UIView? = UIView()
    var navigationBar: UIView? = UIView()
    var statusBar: StatusBar? = StatusBar()
    var containerLayout: (Int, ContainerLayout)? = (0, ContainerLayout())
    func updateThumbnailContainerNodeAlpha(_ transition: Transition) {}
    func updateDismissTransition(_ value: CGFloat) {}
    func updateDistanceFromEquilibrium(_ value: CGFloat) {}
    // NODE_MEMBERS
    // PRODUCTION_SCROLL''')
    text = text.replace('// PRODUCTION_HELPER', '''enum StatusBarStyle { case Ignore, White }
final class StatusBar { var statusBarStyle: StatusBarStyle = .White }
struct ContainerLayout { let size = CGSize(width: 390, height: 844) }
final class ScrollNode { let view = UIScrollView() }
typealias GalleryItemNode = GalleryBase
// PRODUCTION_HELPER''')
    return text


def runtime(source):
    read = lambda p: (source / p).read_text()
    u, n, g = read(U), read(N), read(G)
    value = boundary()
    controller_members = custom_members(g) + '\n' + clean(block(g, '    override public func viewWillAppear('))
    value = value.replace('// CONTROLLER_MEMBERS', controller_members)
    value = value.replace('// NODE_MEMBERS', custom_members(n))
    scroll_methods = '\n'.join(clean(block(n, marker)) for marker in (
        '    open func scrollViewWillBeginDragging(',
        '    open func scrollViewDidScroll(',
        '    open func scrollViewWillEndDragging(',
    ))
    value = value.replace('// PRODUCTION_SCROLL', scroll_methods)
    value = value.replace('// PRODUCTION_HELPER', block(n, 'func nagramiXShouldBeginFastPictureInPictureSwipe('))
    content = clean(block(u, 'private final class NativePictureInPictureContentImpl:')).replace('UniversalVideoGalleryItemNode', 'GalleryHarness')
    markers = ('    private func setupNativePictureInPicture()', '    @objc func pictureInPictureButtonPressed()',
               '    func expandPIP()', '    override var usesNativePictureInPictureSwipe:',
               '    override func prepareForNativePictureInPictureSwipe(',
               '    override func maybePerformActionForSwipeDismiss()',
               '    override func maybePerformActionForSwipeDownDismiss()')
    methods = '\n'.join(clean(block(u, marker)) for marker in markers)
    for line in u.splitlines():
        if re.match(r'^    fileprivate func nagramiX\w*PictureInPicture\w*\(', line):
            methods += '\n' + clean(block(u, line.strip()))
    methods = methods.replace('UniversalVideoGalleryItemNode', 'GalleryHarness')
    custom = custom_members(u).replace('UniversalVideoGalleryItemNode', 'GalleryHarness')
    # UniversalVideo has unrelated existing helpers. Keep only newly introduced
    # state/methods; the native setup/button above owns the production handoff.
    custom = '\n'.join(line for line in custom.splitlines() if 'nagramiXPiPHandoffGeneration' in line)
    gallery = '''
final class GalleryHarness: GalleryBase {
    let context: AccountContext
    let footerContentNode = Footer()
    var gallery = GalleryController()
    let navigation = NavigationController()
    let scrollNode = ScrollNode()
    var item: Item? = Item()
    var videoNode: UniversalVideoNode? = UniversalVideoNode()
    var nativePictureInPictureContent: AnyObject?
    var activePictureInPictureController: BaseController?
    var activePictureInPictureNavigationController: NavigationController?
    var isCentral: Bool? = true
    var hasPictureInPicture = true
    var settingsButtonState = 0
    var displayStickersButton = false
    var dismissals = 0
    var customDismissBegins = 0
    init(context: AccountContext = AccountContext()) { self.context = context; super.init(); gallery.galleryNode = GalleryScrollHarness(self) }
    func galleryController() -> BaseController? { gallery }
    func baseNavigationController() -> NavigationController? { navigation }
    func beginCustomDismiss(_ type: Dismiss) { customDismissBegins += 1 }
    func completeCustomDismiss(_ active: Bool) { dismissals += 1 }
    func updateControlsVisibility(_ visible: Bool) {}
''' + custom + '\n' + methods + '\n}\n'
    return value + '\n' + content + '\n' + gallery + '\n' + TESTS


TESTS = r'''
var checks = 0
func check(_ value: @autoclosure () -> Bool, _ label: String) {
    if !value() { FileHandle.standardError.write(Data(("REGRESSION: " + label + "\n").utf8)); exit(91) }
    checks += 1
}
func makeOwner() -> GalleryHarness {
    NagramiXTabSettings.videoPiPSwipeEnabled = true
    AVPictureInPictureController.supported = true
    AVPictureInPictureController.possibleOnCreation = true
    AVPictureInPictureController.completeStartsAutomatically = false
    return GalleryHarness()
}
func drag(_ owner: GalleryHarness, distance: CGFloat, x: CGFloat = 0, speed: CGFloat = -100, touches: Int = 1) {
    let scroll = owner.gallery.galleryNode.scrollView
    scroll.isDragging = true
    scroll.panGestureRecognizer.state = .changed
    scroll.panGestureRecognizer.value = CGPoint(x: x, y: -distance)
    scroll.panGestureRecognizer.speed = CGPoint(x: 0, y: speed)
    scroll.panGestureRecognizer.numberOfTouches = touches
    scroll.contentOffset.y = scroll.contentSize.height / 3.0 + distance
    owner.gallery.galleryNode.scrollViewDidScroll(scroll)
}
func release(_ owner: GalleryHarness, velocity: CGFloat = 0) -> CGPoint {
    let scroll = owner.gallery.galleryNode.scrollView
    scroll.isDragging = false
    scroll.panGestureRecognizer.state = .ended
    var target = CGPoint.zero
    owner.gallery.galleryNode.scrollViewWillEndDragging(scroll, withVelocity: CGPoint(x: 0, y: velocity), targetContentOffset: &target)
    return target
}
func content(_ context: AccountContext, _ video: UniversalVideoNode, _ id: AnyHashable) -> NativePictureInPictureContentImpl {
    NativePictureInPictureContentImpl(context: context, mediaManager: context.sharedContext.mediaManager, accountId: 1, hiddenMedia: nil, videoNode: video, canSkip: true, willBegin: { _ in }, didBegin: { _ in }, didEnd: { _ in }, expand: { $0() }, contentId: id)
}
@main enum PiPSwipeTests {
    static func main() {
        check(nagramiXShouldBeginFastPictureInPictureSwipe(distance: 12, translation: CGPoint(x:0,y:-12), velocity:.zero), "short slow upward swipe admitted")
        check(nagramiXShouldBeginFastPictureInPictureSwipe(distance: 8, translation: CGPoint(x:0,y:-8), velocity:CGPoint(x:0,y:0.4)), "short fast upward swipe admitted")
        for (distance, translation, velocity) in [(7.0,CGPoint(x:0,y:-7),CGPoint.zero), (12.0,CGPoint(x:30,y:-12),CGPoint.zero),(-30.0,CGPoint(x:0,y:30),CGPoint.zero),(12.0,CGPoint(x:0,y:-12),CGPoint(x:0,y:-0.1)),(Double.nan,CGPoint(x:0,y:-12),CGPoint.zero),(12.0,CGPoint(x:Double.infinity,y:-12),CGPoint.zero)] {
            check(!nagramiXShouldBeginFastPictureInPictureSwipe(distance:CGFloat(distance),translation:translation,velocity:velocity), "invalid direction or values cannot start PiP")
        }
        let owner = makeOwner(), root = owner.gallery.galleryNode!
        root.scrollViewWillBeginDragging(root.scrollView)
        check(AVPictureInPictureController.instances.last?.starts == 0, "prewarming does not start PiP")
        drag(owner, distance: 12)
        check(owner.nativePictureInPictureContent != nil && DispatchQueue.main.pending.count == 1, "changed gesture dispatches before release")
        let locked = root.scrollView.contentOffset.y
        drag(owner, distance: 200)
        check(root.scrollView.contentOffset.y == locked && DispatchQueue.main.pending.count == 1, "accepted source no longer follows finger")
        let target = release(owner, velocity: 2)
        check(target.y == locked && DispatchQueue.main.pending.count == 1 && root.closed == 0, "release neither rebounds nor starts a second PiP")
        DispatchQueue.main.flush()
        let controller = AVPictureInPictureController.instances.last!
        check(controller.starts == 1 && owner.videoNode!.withoutHierarchy, "single accepted native start keeps live source")
        check(owner.gallery.view.alpha == 1 && owner.dismissals == 0 && owner.customDismissBegins == 0, "gallery remains until native DidStart")
        controller.finishStart()
        check(owner.customDismissBegins == 1 && owner.gallery.view.alpha == 0, "native DidStart performs gallery handoff")
        check(owner.dismissals == 0, "gallery fade completion remains asynchronous")
        AnimationClock.flush()
        check(owner.dismissals == 1, "confirmed native handoff completes once")
        controller.stopPictureInPicture()
        owner.gallery.viewWillAppear(false)
        check(root.scrollView.contentOffset.y == root.scrollView.contentSize.height/3, "restore resets frozen input")
        drag(owner, distance: 12)
        DispatchQueue.main.flush()
        check(controller.starts == 2, "restored gallery supports the next first swipe")
        controller.failStart()
        check(owner.gallery.view.alpha == 1 && owner.context.sharedContext.mediaManager.currentPictureInPictureNode == nil && !owner.videoNode!.withoutHierarchy, "failed start restores gallery and ownership")
        check(root.scrollView.contentOffset.y == root.scrollView.contentSize.height/3, "failed start releases frozen source")
        let race = makeOwner(), raceRoot = race.gallery.galleryNode!
        raceRoot.scrollViewWillBeginDragging(raceRoot.scrollView)
        drag(race, distance:12)
        let raceController = AVPictureInPictureController.instances.last!
        raceController.isPictureInPicturePossible = false
        DispatchQueue.main.flush()
        check(raceController.starts == 0 && raceRoot.scrollView.contentOffset.y == raceRoot.scrollView.contentSize.height/3, "readiness lost before dispatch restores input")
        let unavailable = makeOwner(), unavailableRoot = unavailable.gallery.galleryNode!
        AVPictureInPictureController.possibleOnCreation = false
        unavailableRoot.scrollViewWillBeginDragging(unavailableRoot.scrollView)
        drag(unavailable, distance:32)
        _ = release(unavailable, velocity:2)
        check(unavailableRoot.closed == 0 && unavailableRoot.scrollView.contentOffset.y == unavailableRoot.scrollView.contentSize.height/3, "unready PiP intent does not close or freeze gallery")
        AVPictureInPictureController.possibleOnCreation = true
        for mode in 0..<5 {
            let disabled = makeOwner(), disabledRoot = disabled.gallery.galleryNode!
            if mode == 0 { NagramiXTabSettings.videoPiPSwipeEnabled = false }
            if mode == 1 { disabled.hasPictureInPicture = false }
            if mode == 2 { disabled.isCentral = false }
            if mode == 3 { disabled.videoNode!.hasLayer = false }
            if mode == 4 { disabled.context.currentAppConfiguration.value.data = ["ios_killswitch_disable_swipe_pip":true] }
            let old = AVPictureInPictureController.instances.count
            disabledRoot.scrollViewWillBeginDragging(disabledRoot.scrollView)
            drag(disabled, distance:32)
            check(AVPictureInPictureController.instances.count == old && DispatchQueue.main.pending.isEmpty, "disabled or unsupported shortcut does not dispatch")
        }
        let warming = makeOwner(), warmingRoot = warming.gallery.galleryNode!
        AVPictureInPictureController.possibleOnCreation = false
        warmingRoot.scrollViewWillBeginDragging(warmingRoot.scrollView)
        drag(warming, distance: 12)
        let warmingController = AVPictureInPictureController.instances.last!
        check(DispatchQueue.main.pending.isEmpty, "unready source is not launched prematurely")
        warmingController.isPictureInPicturePossible = true
        drag(warming, distance: 18)
        check(DispatchQueue.main.pending.count == 1, "readiness during the first gesture can still start PiP")
        DispatchQueue.main.flush(); warmingController.failStart()
        AVPictureInPictureController.possibleOnCreation = true
        let multiple = makeOwner(), multiRoot = multiple.gallery.galleryNode!
        multiRoot.scrollViewWillBeginDragging(multiRoot.scrollView)
        drag(multiple, distance: 20, touches: 2)
        _ = release(multiple, velocity: 0)
        check(DispatchQueue.main.pending.isEmpty, "multi-touch cannot trigger the early shortcut")
        let zoomed = makeOwner(), zoomRoot = zoomed.gallery.galleryNode!
        zoomed.scrollNode.view.zoomScale = 2
        zoomRoot.scrollViewWillBeginDragging(zoomRoot.scrollView)
        drag(zoomed, distance: 20)
        check(DispatchQueue.main.pending.isEmpty, "zoomed content keeps native pan interaction")
        let existing = makeOwner()
        existing.pictureInPictureButtonPressed(); DispatchQueue.main.flush()
        let existingController = AVPictureInPictureController.instances.last!
        existingController.finishStart(); AnimationClock.flush()
        let reopened = makeOwner()
        reopened.context.sharedContext.mediaManager.currentPictureInPictureNode = existing
        let beforeReuse = AVPictureInPictureController.instances.reduce(0) { $0 + $1.starts }
        reopened.gallery.galleryNode.scrollViewWillBeginDragging(reopened.gallery.galleryNode.scrollView)
        drag(reopened, distance: 12); DispatchQueue.main.flush()
        check(reopened.gallery.dismissals == 1 && AVPictureInPictureController.instances.reduce(0) { $0 + $1.starts } == beforeReuse, "matching active PiP reuses native dismiss branch")
        let different = makeOwner()
        different.item!.contentInfo = .message(Message(id: 2), 0)
        different.context.sharedContext.mediaManager.currentPictureInPictureNode = existing
        different.gallery.galleryNode.scrollViewWillBeginDragging(different.gallery.galleryNode.scrollView)
        drag(different, distance: 12); DispatchQueue.main.flush()
        check(different.gallery.dismissals == 0 && AVPictureInPictureController.instances.last!.starts == 1, "different message does not reuse another PiP source")
        AVPictureInPictureController.instances.last!.failStart()
        let expand = makeOwner()
        expand.pictureInPictureButtonPressed(); DispatchQueue.main.flush()
        let expandController = AVPictureInPictureController.instances.last!
        expandController.finishStart()
        let expandContent = expand.nativePictureInPictureContent as! NativePictureInPictureContentImpl
        var restored = false
        expandContent.pictureInPictureController(expandController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler: { restored = $0 })
        AnimationClock.flush()
        check(restored && expand.gallery.view.alpha == 1 && expand.dismissals == 0, "quick expand ignores stale gallery fade completion")
        expandController.stopPictureInPicture()
        let stale = makeOwner(), staleRoot = stale.gallery.galleryNode!
        staleRoot.scrollViewWillBeginDragging(staleRoot.scrollView)
        drag(stale, distance: 12)
        stale.isCentral = false
        staleRoot.pager.item = different
        staleRoot.scrollViewDidScroll(staleRoot.scrollView)
        let staleNative = AVPictureInPictureController.instances.last!
        DispatchQueue.main.flush()
        check(staleNative.starts == 0, "changed central item cancels a queued old source")
        let oldOwner = makeOwner(), sharedRoot = oldOwner.gallery.galleryNode!
        sharedRoot.scrollView.isDragging = false
        oldOwner.pictureInPictureButtonPressed(); DispatchQueue.main.flush()
        let oldController = AVPictureInPictureController.instances.last!
        sharedRoot.nagramiXResetNativePictureInPictureSwipe(owner: oldOwner)
        oldOwner.isCentral = false
        let replacement = GalleryHarness(context: oldOwner.context)
        replacement.gallery = oldOwner.gallery
        replacement.item!.contentInfo = .message(Message(id: 2), 0)
        sharedRoot.pager.item = replacement
        replacement.pictureInPictureButtonPressed(); DispatchQueue.main.flush()
        let replacementController = AVPictureInPictureController.instances.last!
        replacementController.finishStart()
        let newChat = replacement.navigation.topViewController as! ChatController
        let chatPushes = newChat.pushes.count
        oldController.failStart()
        check(sharedRoot.nagramiXNativePictureInPictureDistance != nil && replacement.gallery.view.alpha == 0 && oldOwner.context.sharedContext.mediaManager.currentPictureInPictureNode === replacement, "stale failure cannot reset another item source or visibility")
        AnimationClock.flush()
        replacementController.stopPictureInPicture()
        check(newChat.pushes.count == chatPushes, "closing PiP over the chat does not restore a pushed gallery transition")
        let rotating = makeOwner(), rotationRoot = rotating.gallery.galleryNode!
        rotationRoot.scrollViewWillBeginDragging(rotationRoot.scrollView)
        drag(rotating, distance: 12)
        rotationRoot.scrollView.contentSize.height = 3000
        rotationRoot.scrollViewDidScroll(rotationRoot.scrollView)
        check(rotationRoot.scrollView.contentOffset.y == 1012 && release(rotating).y == 1012, "frozen source rebases relative to the new layout height")
        DispatchQueue.main.flush(); AVPictureInPictureController.instances.last!.failStart()
        let prewarmContext = AccountContext(), independentVideo = UniversalVideoNode()
        independentVideo.withoutHierarchy = true
        var inactive: NativePictureInPictureContentImpl? = NativePictureInPictureContentImpl(context: prewarmContext, mediaManager: prewarmContext.sharedContext.mediaManager, accountId: 1, hiddenMedia: nil, videoNode: independentVideo, canSkip: true, willBegin: { _ in }, didBegin: { _ in }, didEnd: { _ in }, expand: { $0() })
        check(inactive!.canBeginPictureInPicture, "prewarmed native controller is available without taking playback ownership")
        inactive = nil
        check(independentVideo.withoutHierarchy && independentVideo.hierarchyCalls.isEmpty, "unused prewarm does not clear another source playback ownership")
        for ending in [0, 1] {
            let lifeContext = AccountContext(), lifeVideo = UniversalVideoNode()
            var life: NativePictureInPictureContentImpl? = NativePictureInPictureContentImpl(context: lifeContext, mediaManager: lifeContext.sharedContext.mediaManager, accountId: 1, hiddenMedia: nil, videoNode: lifeVideo, canSkip: true, willBegin: { _ in }, didBegin: { _ in }, didEnd: { _ in }, expand: { $0() })
            check(life!.beginPictureInPicture(), "native start acquires hierarchy permission")
            let lifeController = AVPictureInPictureController.instances.last!
            if ending == 0 { lifeController.failStart() } else { lifeController.finishStart(); lifeController.stopPictureInPicture() }
            life = nil
            check(lifeVideo.hierarchyCalls == [true, false] && !lifeVideo.withoutHierarchy, "owned hierarchy playback releases once on stop or failure and not again in deinit")
        }
        let automaticContext = AccountContext(), automaticVideo = UniversalVideoNode()
        let automatic = content(automaticContext, automaticVideo, 99)
        let automaticController = AVPictureInPictureController.instances.last!
        automatic.updateIsCentral(isCentral: true)
        check(!automaticController.canStartPictureInPictureAutomaticallyFromInline, "prewarming alone does not enable automatic background PiP")
        check(automatic.beginPictureInPicture(), "explicit PiP request is accepted")
        automatic.updateIsCentral(isCentral: true)
        check(automaticController.canStartPictureInPictureAutomaticallyFromInline, "previous automatic behavior follows an explicit accepted start")
        automatic.updateIsCentral(isCentral: false)
        check(!automaticController.canStartPictureInPictureAutomaticallyFromInline, "noncentral source disables automatic PiP")
        automaticController.failStart()
        let handoffContext = AccountContext(), sharedVideo = UniversalVideoNode()
        var previous: NativePictureInPictureContentImpl? = content(handoffContext, sharedVideo, 10)
        let previousController = AVPictureInPictureController.instances.last!
        check(previous!.beginPictureInPicture(), "old source begins before handoff")
        previousController.finishStart()
        let successorOwner = GalleryHarness(context: handoffContext)
        (successorOwner.item!.content as! NativeVideoContent).id = 10
        let successor = content(handoffContext, sharedVideo, 10)
        successorOwner.nativePictureInPictureContent = successor
        handoffContext.sharedContext.mediaManager.currentPictureInPictureNode = successorOwner
        let successorController = AVPictureInPictureController.instances.last!
        check(successor.beginPictureInPicture(), "replacement same-content source begins")
        previousController.stopPictureInPicture(); previous = nil
        check(sharedVideo.hierarchyCalls == [true, true] && sharedVideo.withoutHierarchy, "old release cannot clear an active successor sharing content ID")
        successorController.finishStart(); successorController.stopPictureInPicture()
        check(sharedVideo.hierarchyCalls == [true, true, false], "successor releases the shared playback permission once")
        let idleContext = AccountContext(), idleVideo = UniversalVideoNode()
        var idlePrevious: NativePictureInPictureContentImpl? = content(idleContext, idleVideo, 20)
        let idlePreviousController = AVPictureInPictureController.instances.last!
        check(idlePrevious!.beginPictureInPicture(), "old source begins before inactive replacement")
        idlePreviousController.finishStart()
        let idleOwner = GalleryHarness(context: idleContext)
        (idleOwner.item!.content as! NativeVideoContent).id = 20
        let idleReplacement = content(idleContext, idleVideo, 20)
        idleOwner.nativePictureInPictureContent = idleReplacement
        idleContext.sharedContext.mediaManager.currentPictureInPictureNode = idleOwner
        idlePreviousController.stopPictureInPicture(); idlePrevious = nil
        check(idleVideo.hierarchyCalls == [true, false] && !idleVideo.withoutHierarchy, "an inactive prewarm cannot retain abandoned playback permission")
        let distinctContext = AccountContext(), distinctOldVideo = UniversalVideoNode(), distinctNewVideo = UniversalVideoNode()
        var distinctPrevious: NativePictureInPictureContentImpl? = content(distinctContext, distinctOldVideo, 30)
        let distinctPreviousController = AVPictureInPictureController.instances.last!
        check(distinctPrevious!.beginPictureInPicture(), "old source begins before different content handoff")
        distinctPreviousController.finishStart()
        let distinctOwner = GalleryHarness(context: distinctContext)
        (distinctOwner.item!.content as! NativeVideoContent).id = 31
        let distinctSuccessor = content(distinctContext, distinctNewVideo, 31)
        distinctOwner.nativePictureInPictureContent = distinctSuccessor
        distinctContext.sharedContext.mediaManager.currentPictureInPictureNode = distinctOwner
        let distinctController = AVPictureInPictureController.instances.last!
        check(distinctSuccessor.beginPictureInPicture(), "different content successor begins")
        distinctPreviousController.stopPictureInPicture(); distinctPrevious = nil
        check(distinctOldVideo.hierarchyCalls == [true, false] && distinctNewVideo.hierarchyCalls == [true], "different content IDs release only the old playback permission")
        distinctController.failStart()
        let multiDown = makeOwner(), downRoot = multiDown.gallery.galleryNode!
        downRoot.scrollViewWillBeginDragging(downRoot.scrollView)
        drag(multiDown, distance: -60, speed: 2000, touches: 2)
        _ = release(multiDown, velocity: -2)
        AnimationClock.flush()
        check(downRoot.closed == 1, "multi-touch rejection does not block native downward close")
        for ending in [0, 1] {
            let reused = makeOwner(), reusedRoot = reused.gallery.galleryNode!
            reusedRoot.scrollView.isDragging = false
            reused.pictureInPictureButtonPressed(); DispatchQueue.main.flush()
            let retired = reused.nativePictureInPictureContent as! NativePictureInPictureContentImpl
            let retiredController = AVPictureInPictureController.instances.last!
            if ending == 1 { retiredController.finishStart() }
            reused.setupNativePictureInPicture()
            let current = reused.nativePictureInPictureContent as! NativePictureInPictureContentImpl
            let currentController = AVPictureInPictureController.instances.last!
            check(current !== retired && current.beginPictureInPicture(), "same gallery can establish a replacement native content")
            currentController.finishStart()
            let begins = reused.customDismissBegins
            let dismissals = reused.dismissals
            if ending == 0 { retiredController.failStart() } else { retiredController.stopPictureInPicture() }
            check(reused.context.sharedContext.mediaManager.currentPictureInPictureNode === reused && reusedRoot.nagramiXNativePictureInPictureDistance != nil && reused.gallery.view.alpha == 0 && reused.videoNode!.withoutHierarchy, "retired native callbacks cannot clear the same item replacement")
            retired.pictureInPictureControllerWillStartPictureInPicture(retiredController)
            retired.pictureInPictureControllerDidStartPictureInPicture(retiredController)
            check(reused.customDismissBegins == begins && reused.dismissals == dismissals, "retired native start callbacks cannot retire the new source")
            currentController.stopPictureInPicture()
            AnimationClock.flush()
        }
        let doubleButton = makeOwner()
        doubleButton.pictureInPictureButtonPressed(); doubleButton.pictureInPictureButtonPressed()
        DispatchQueue.main.flush()
        let doubleController = AVPictureInPictureController.instances.last!
        check(doubleController.starts == 1 && doubleButton.gallery.dismissals == 0 && doubleButton.gallery.galleryNode.nagramiXNativePictureInPictureDistance != nil, "in-flight duplicate button does not restart or unfreeze")
        let commands = doubleButton.nativePictureInPictureContent as! NativePictureInPictureContentImpl
        commands.contentDelegate!.pictureInPictureController(doubleController, setPlaying: true)
        commands.contentDelegate!.pictureInPictureController(doubleController, setPlaying: true)
        commands.contentDelegate!.pictureInPictureController(doubleController, setPlaying: false)
        commands.contentDelegate!.pictureInPictureController(doubleController, setPlaying: false)
        check(doubleButton.videoNode!.plays == 2 && doubleButton.videoNode!.pauses == 2 && doubleButton.videoNode!.toggles == 0, "R3 explicit play and pause remain intact")
        doubleController.failStart()
        let button = makeOwner()
        NagramiXTabSettings.videoPiPSwipeEnabled = false
        button.pictureInPictureButtonPressed(); DispatchQueue.main.flush()
        let buttonController = AVPictureInPictureController.instances.last!
        check(buttonController.starts == 1, "OFF shortcut leaves the native button working")
        buttonController.finishStart(); buttonController.stopPictureInPicture()
        print("PASS PiP swipe/handoff production checks: \(checks)")
    }
}
'''


def verify_source(source, baseline):
    before, after = {p:(baseline/p).read_text() for p in PATHS}, {p:(source/p).read_text() for p in PATHS}
    marker = '        public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, setPlaying playing: Bool)'
    assert block(before[U], marker) == block(after[U], marker), 'R3 playback command changed'
    assert block(before[U], '    private final class PlaybackDelegate:') == block(after[U], '    private final class PlaybackDelegate:'), 'Native playback/seek/paused delegate changed'
    assert block(after[I], '    open func prepareForNativePictureInPictureSwipe()').strip() == 'open func prepareForNativePictureInPictureSwipe() {\n    }', 'Adapter must match actual new base item API'
    for marker in ('    override var usesNativePictureInPictureSwipe:', '    override func maybePerformActionForSwipeDownDismiss()'):
        assert block(before[U], marker) == block(after[U], marker), marker
    for text in after.values():
        assert '.presentation()' not in text, 'unsafe layer presentation lookup reintroduced'
    return {p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in PATHS}


def execute(source, swiftc, folder):
    code = runtime(source)
    early = '        if self.nagramiXTryBeginNativePictureInPictureSwipe(scrollView) {\n            return\n        }'
    reset_guard = block(code, '                    guard nativePictureInPictureContent.canBeginPictureInPicture else {')
    reset_without_recovery = re.sub(r'controller\?\.nagramiXResetNativePictureInPictureSwipe\(owner: self\)', '_ = controller', reset_guard)
    variants = {
        'current': (code, None),
        'old-long-threshold': (code.replace('return distance >= 12.0 || velocity.y >= 0.35', 'return distance >= 32.0 || velocity.y >= 0.35', 1), 'short slow upward swipe admitted'),
        'release-only': (code.replace(early, '', 1), 'changed gesture dispatches before release'),
        'source-follows-finger': (code.replace('scrollView.setContentOffset(offset, animated: false)', '_ = offset', 1), 'accepted source no longer follows finger'),
        'premature-gallery-handoff': (code.replace('self.context.sharedContext.mediaManager.currentPictureInPictureNode = self', 'self.context.sharedContext.mediaManager.currentPictureInPictureNode = self\n                self.beginCustomDismiss(.pip)\n                controller.view.alpha = 0.0', 1), 'gallery remains until native DidStart'),
        'lost-readiness-does-not-reset': (code.replace(reset_guard, reset_without_recovery, 1), 'readiness lost before dispatch restores input'),
        'stale-completion-dismisses-restore': (code.replace('self.nagramiXPiPHandoffGeneration == generation, !didExpand', '(self.nagramiXPiPHandoffGeneration == generation || self.nagramiXPiPHandoffGeneration != generation), (didExpand || !didExpand)', 1), 'quick expand ignores stale gallery fade completion'),
        'old-item-resets-new-source': (code.replace('if let owner, self.nagramiXNativePictureInPictureItem !== owner { return }', 'if let owner { _ = owner }', 1), 'stale failure cannot reset another item source or visibility'),
    }
    assert all(content != code for name, (content, _) in variants.items() if name != 'current'), 'Mutation did not match production body'
    runs = []
    for name, (content, expected) in variants.items():
        path = folder/(name+'.swift'); path.write_text(content)
        for optimized in (False, True):
            executable=folder/(name+('-O' if optimized else '-debug'))
            result=subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(folder/'cache'),*(['-O'] if optimized else []),str(path),'-o',str(executable)],capture_output=True,text=True)
            assert result.returncode==0,result.stdout+result.stderr
            result=subprocess.run([str(executable)],capture_output=True,text=True,timeout=30,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if expected is None:
                assert result.returncode==0,result.stdout+result.stderr
                runs.append(result.stdout.strip())
            else:
                assert result.returncode==91 and ('REGRESSION: '+expected) in result.stderr, name+' failed unexpectedly or accepted regression:\n'+result.stdout+result.stderr
    return runs, (len(variants)-1)*2


def checked_stage(source, baseline, folder):
    stage = 'pip_swipe_handoff'
    plan = checked_plan(stage)
    assert set(plan['inputs']) == set(PATHS)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source/name) == expected, name
    for name, expected in plan['inputs'].items():
        assert digest(baseline/name) == expected, name
    rejected = guard_checks(source, stage, plan, folder/'shared')
    wide = 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift'
    wide_value = (source/wide).read_text()
    removals = {
        '        static let wideTabBar = "nagramix.tabs.wideBar"\n':'',
        '    public var wideTabBar: Bool\n':'',
        '        unreadChatsFirst: Bool = true,\n        wideTabBar: Bool = true\n':'        unreadChatsFirst: Bool = true\n',
        '        self.wideTabBar = wideTabBar\n':'',
        '            unreadChatsFirst: self.unreadChatsFirstEnabled,\n            wideTabBar: defaults.object(forKey: Key.wideTabBar) as? Bool ?? true\n':'            unreadChatsFirst: self.unreadChatsFirstEnabled\n',
        '        defaults.set(value.wideTabBar, forKey: Key.wideTabBar)\n':'',
    }
    for before, after in removals.items():
        assert wide_value.count(before) == 1, before
        wide_value = wide_value.replace(before, after, 1)
    assert hashlib.sha256(wide_value.encode()).hexdigest() == '6d4631a3dc92c3d8140f221553d7657de32b3c825341b5d98f96b7d0f70d24d2'
    tree = folder/'missing-wide-stage'
    for name in {**plan['inputs'], **plan['guards']}:
        path=tree/name; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((OVERLAY/plan['previous'][name] if name in plan['previous'] else source/name).read_bytes())
    (tree/wide).write_text(wide_value)
    before = manifest(tree)
    spec=importlib.util.spec_from_file_location(stage, OVERLAY/(stage+'.py'))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    try:
        module.apply_pip_swipe_handoff(tree, OVERLAY)
    except (SystemExit, OSError):
        pass
    else:
        raise AssertionError('Published 0.8.9 without prior wide settings was accepted')
    assert manifest(tree) == before, 'Partial write before required prior stage refusal'
    rejected.append('exact-published-old-wide-settings')
    return rejected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--integrated',action='store_true',help='Проверить полный pre-PiP checkpoint и все семь предыдущих стадий')
    args=parser.parse_args()
    integrated=verify_integrated_baseline(args.source,args.baseline) if args.integrated else None
    hashes=verify_source(args.source,args.baseline)
    with tempfile.TemporaryDirectory(prefix='pip-swipe-check-') as temporary:
        folder=Path(temporary)
        rejected=checked_stage(args.source,args.baseline,folder)
        runs,negatives=execute(args.source,args.swiftc,folder)
        for p in PATHS:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/p)],check=True)
    report={'production_runs':runs,'semantic_negative_runs':negatives,'fail_closed':len(rejected),'source_outputs':hashes,'swift_parse_outputs':len(PATHS),'boundaries':'UIKit/AVKit, network, decoder and frame presentation are adapters; actual gesture/content/delegate bodies execute','apple_sdk':'not_run','physical_video_smoothness':'pending','integration_with_seven_prior_local_stages':integrated if integrated is not None else 'not_checked: isolated source scope'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

def verify_integrated_baseline(source, baseline):
    from validate_upstream_13_2_release import SDK_STAGES, checked_sdk_plans
    required=('wide_bottom_bar','author_selection_no_restore','preview_reply_intent',
              'cloud_credential_entry','extended_poll_integrity','bot_delete_without_block',
              'wide_tab_bar_setting','pip_swipe_handoff')
    pip_index=SDK_STAGES.index('pip_swipe_handoff')
    assert tuple(SDK_STAGES[pip_index-len(required)+1:pip_index+1])==required, 'Incomplete or reordered eight-stage PiP prefix'
    post=checked_plan('upstream_13_2_release_post')
    plans,_=checked_sdk_plans(post)
    assert len(plans)==len(SDK_STAGES)
    expected={**post['outputs'],**post['guards']}
    for plan in plans[:pip_index]:
        for name,value in {**plan['guards'],**plan['inputs']}.items():
            if name in expected:
                assert expected[name]==value, 'Broken pre-PiP dependency: '+name
            else:
                expected[name]=value
        expected.update(plan['outputs'])
    for name,value in expected.items():
        if name in post['deletions']:
            assert not (baseline/name).exists(), name
        else:
            assert digest(baseline/name)==value, 'Wrong seven-stage checkpoint: '+name
    assert (baseline/'build-system/Make/PostboxImportCheck.py').is_file(), 'Full source checkpoint missing'
    versions=json.loads((baseline/'versions.json').read_text())
    assert versions['app']=='13.2' and versions['xcode']=='27.1'
    before,after=manifest(baseline),manifest(source)
    assert len(before)>37000, 'A source projection cannot prove full integration'
    assert before.keys()==after.keys(), 'PiP unexpectedly added or deleted application files'
    changed={name for name in before if before[name]!=after[name]}
    assert changed==set(PATHS), 'PiP changed unrelated previous work: '+repr(sorted(changed))
    return {'status':'passed','preceding_stages':list(required[:-1]),'baseline_files':len(before),
            'changed_files':sorted(changed),'other_files_preserved':len(before)-len(changed),
            'recovery':'Seven stages reimplemented from agreed requirements; original missing bytes not claimed'}


if __name__=='__main__': main()
