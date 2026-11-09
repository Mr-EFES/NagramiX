#!/usr/bin/env python3
"""Проверить передачу изображения native PiP без служебной подложки."""
import argparse
import json
from pathlib import Path
import resource
import re
import subprocess
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_pip_swipe_handoff import U, G, N, clean
from validate_pip_swipe_handoff import runtime as native_runtime
from validate_upstream_13_2_release import checked_plan, digest, guard_checks


ROOT = Path(__file__).resolve().parents[1]
STAGE = 'pip_visual_continuity'
GEOMETRY_BOUNDARY = '''import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
'''


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True,
                            text=True, **kwargs)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def execute(swiftc, root, name, text, diagnostic=None):
    path = root / (name + '.swift')
    path.write_text(text)
    results = []
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        binary = root / (name + '-' + mode)
        run([swiftc, '-swift-version', '5', '-parse-as-library',
             '-warnings-as-errors', '-module-cache-path', root / 'cache',
             *flags, path, '-o', binary])
        result = subprocess.run([str(binary)], capture_output=True, text=True,
                                timeout=60, preexec_fn=lambda: resource.setrlimit(
                                    resource.RLIMIT_CORE, (0, 0)))
        if diagnostic is None:
            assert result.returncode == 0, result.stdout + result.stderr
        else:
            assert result.returncode == 93 and diagnostic in result.stderr, (name, diagnostic, result.stdout + result.stderr)
        results.append({'name': name, 'mode': mode,
                        'exit_code': result.returncode,
                        'output': (result.stdout + result.stderr).strip()})
        binary.unlink()
    return results


def source_contract(source):
    plan = checked_plan(STAGE)
    assert set(plan['inputs']) == {U, G}
    assert plan['required_previous_stage'] == 'edit_history_number_badges'
    assert not plan['copies'] and not plan['deletions']
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    after = (source / U).read_text()
    before = (ROOT / 'ios' / plan['previous'][U]).read_text()
    # Скругление, controls и декодер остаются у штатного sample-buffer PiP.
    for marker in (
        '    private final class PlaybackDelegate:',
        '    override var usesNativePictureInPictureSwipe:',
        '    override func prepareForNativePictureInPictureSwipe(',
        '    override func maybePerformActionForSwipeDismiss()',
        '    override func maybePerformActionForSwipeDownDismiss()',
    ):
        assert block(after, marker) == block(before, marker), marker
    assert 'AVPictureInPictureController.ContentSource(sampleBufferDisplayLayer: videoLayer, playbackDelegate: contentDelegate)' in after
    # Никаких private AVKit масок и повторения исторического presentation crash.
    for forbidden in ('layer.presentation()', 'AVPlayerViewController',
                      'NSClassFromString', 'setValue(', 'value(forKey:'):
        assert forbidden not in after or forbidden in before, forbidden
    return plan


def fixture(source):
    u = (source / U).read_text()
    text = native_runtime(source)
    assert text.startswith(GEOMETRY_BOUNDARY), 'Early geometry gate must use actual runtime imports'
    text = text[:text.index('var checks = 0')]
    state = clean(block(u, 'private struct NagramiXNativePiPVisualState'))
    acknowledgement = clean(block(u, 'private final class NagramiXNativePiPPresentationAcknowledgement'))
    props = '\n'.join(clean(line) for line in u.splitlines()
                      if re.match(r'^    private (?:weak )?var nagramiXPiP', line))
    generation = '    var nagramiXPiPHandoffGeneration: Int { self.nagramiXPiPVisualState.generation }'
    assert generation in text
    # Старый builder выбирает строки generation даже из новых method bodies.
    # Заменяем весь его custom-сегмент настоящими полями production, не обрывками.
    begin = text.index(generation)
    end = text.index('    func setupNativePictureInPicture()', begin)
    text = text[:begin] + props + '\n' + text[end:]
    methods = '\n'.join(clean(block(u, marker)) for marker in (
        '    private func nagramiXBeginNativePiPVisualTransition()',
        '    private func nagramiXFinishNativePiPVisualTransition(',
        '    private func nagramiXAwaitNativePiPPresentation(',
        '    private func nagramiXNativePiPRendererReady()',
        '    private func nagramiXTryFinishNativePiPRestore()',
        '    private func updateDisplayPlaceholder() {',
        '    private func updateDisplayPlaceholder(_ displayPlaceholder: Bool) {',
    ))
    text = text.replace('    func updateControlsVisibility(_ visible: Bool) {}', '''
    func updateControlsVisibility(_ visible: Bool) {}
    var disablePictureInPicturePlaceholder = false
    var pictureInPictureNode: UniversalVideoGalleryItemPictureInPictureNode?
    let pictureInPictureButton: PictureButton? = PictureButton()
    let presentationData = PresentationData()
    let validLayout: (ContainerLayout, CGFloat)? = nil
    func insertSubnode(_ node: UniversalVideoGalleryItemPictureInPictureNode, aboveSubnode: ScrollNode) {}
'''+methods)
    text = text.replace('final class UniversalVideoNode {', '''final class UniversalVideoNode {
    var backgroundColor: UIColor?
    let view = UIView()
    var bounds = CGRect(x: 0,y: 0,width: 390,height: 220)
''')
    text = text.replace('final class VideoLayer {}', '''final class VideoLayer {
    enum Status {case unknown, rendering, failed}
    var status: Status = .rendering
    var requiresFlushToResumeDecoding = false
    var isReadyForDisplay = true
}
typealias AVSampleBufferDisplayLayer = VideoLayer''')
    text = text.replace('final class UIView { var alpha = 1.0; let layer = Layer(); func layoutIfNeeded() {} }', VIEW_BOUNDARY)
    text = text.replace('struct UIColor { init(white: Double, alpha: Double) {}; var cgColor: Int { 0 }; func withAlphaComponent(_ value: CGFloat) -> Self { self } }', '''struct UIColor: Equatable {
    var shade: Double
    init(white: Double,alpha: Double) {self.shade=white+alpha}
    var cgColor:Int {0}
    func withAlphaComponent(_ value:CGFloat)->Self {self}
    static let black=Self(white:0,alpha:1)
    static let clear=Self(white:0,alpha:0)
}''')
    text = text.replace('enum SwiftSignalKit { final class Timer { func invalidate() {} } }', TIMER_BOUNDARY)
    text = text.replace('    func flush() { while !pending.isEmpty { let work = pending.removeFirst(); work() } }', '''
    var delayed:[() -> Void]=[]
    func asyncAfter(deadline:Double,execute f:@escaping ()->Void){delayed.append(f)}
    func flush() { while !pending.isEmpty { let work = pending.removeFirst(); work() } }
    func displayTurn(){let current=delayed;delayed=[];for f in current{f()}}
''')
    text = text.replace('func async(_ f: @escaping () -> Void)', 'func async(execute f: @escaping () -> Void)')
    text = text.replace('    // CONTROLLER_MEMBERS', '    // CONTROLLER_MEMBERS')
    text = text.replace('class BaseController {', '''class BaseController {
    var presentingViewController:BaseController?
    var dismissed=false
    var onDismiss:(()->Void)?
    func dismiss(animated:Bool,completion:(()->Void)?){dismissed=true;view.window=nil;onDismiss?();completion?()}
''')
    text = text.replace('    var dismissals = 0\n    var galleryNode:', '    var baseNavigationController: NavigationController?\n    var dismissals = 0\n    var galleryNode:')
    text = text.replace('gallery.galleryNode = GalleryScrollHarness(self)', 'gallery.galleryNode = GalleryScrollHarness(self); gallery.baseNavigationController=navigation')
    text = text.replace('final class NavigationController { let currentWindow: Window? = Window();', 'final class NavigationController { let view=UIView(); var currentWindow: Window? = Window();')
    text = text.replace('var topViewController: AnyObject? = ChatController()', 'var topViewController: BaseController? = ChatController()')
    text = text.replace('final class ChatController {', 'final class ChatController: BaseController {')
    text = text.replace('    var presentations = 0', '    var dropsCompletion=false\n    var presentations = 0')
    text = text.replace('presentations += 1; completion()', '''presentations += 1
        let container=BaseController()
        controller.presentingViewController=container
        container.onDismiss = { [weak controller] in controller?.view.window=nil }
        PresentationClock.pending.append { [weak self] in
            guard !container.dismissed else{return}
            controller.view.window=1
            if self?.dropsCompletion == false {completion()}
        }''')
    text = text.replace('func completeCustomDismiss(_ active: Bool) { dismissals += 1 }', 'func completeCustomDismiss(_ active: Bool) { dismissals += 1; gallery.view.window=nil }')
    text = text.replace('func galleryController() -> BaseController? { gallery }', 'var hasGallery=true\n    func galleryController() -> BaseController? { hasGallery ? gallery : nil }')
    text += '\n'+state+'\n'+acknowledgement+'\n'+SUPPORT_BOUNDARY+'\n'+TESTS
    text = text.replace('if #available(iOS 17.4, *) {', 'if FixtureFlags.hasReadyForDisplay {')
    return text


VIEW_BOUNDARY = r'''
struct AutoresizingMask:OptionSet {
    let rawValue:Int
    static let flexibleWidth=Self(rawValue:1),flexibleHeight=Self(rawValue:2)
}
final class UIView {
    var alpha=1.0
    let layer=Layer()
    var frame=CGRect(x:0,y:0,width:390,height:844)
    var bounds:CGRect {frame}
    var window:Int?=1
    var autoresizingMask:AutoresizingMask=[]
    var isUserInteractionEnabled=true
    var accessibilityElementsHidden=false
    var canSnapshot=true
    var contentMarker=UUID().uuidString
    var layouts=0
    private(set) var subviews:[UIView]=[]
    weak var superview:UIView?
    func layoutIfNeeded(){layouts+=1}
    func snapshotView(afterScreenUpdates:Bool)->UIView? {
        guard canSnapshot else{return nil}
        let result=UIView();result.contentMarker=contentMarker;return result
    }
    func addSubview(_ v:UIView){v.removeFromSuperview();subviews.append(v);v.superview=self}
    func removeFromSuperview(){superview?.subviews.removeAll{$0===self};superview=nil}
    static func animate(withDuration:Double,animations:()->Void,completion:@escaping (Bool)->Void){
        animations();AnimationClock.pending.append{completion(true)}
    }
}
'''

TIMER_BOUNDARY = r'''
enum SwiftSignalKit {
    final class Timer {
        static var instances:[Timer]=[]
        let completion:()->Void
        var active=false
        init(timeout:Double,repeat:Bool,completion:@escaping ()->Void,queue:ImmediateQueue){
            self.completion=completion;Self.instances.append(self)
        }
        func invalidate(){active=false}
        func start(){active=true}
        static func poll(){for timer in instances where timer.active{timer.completion()}}
    }
}
'''

SUPPORT_BOUNDARY = r'''
var mediaTime=0.0
enum FixtureFlags {static var hasReadyForDisplay=true}
func CACurrentMediaTime()->Double {mediaTime}
extension Double {static func now()->Double {mediaTime}}
enum PresentationClock {
    static var pending:[()->Void]=[]
    static func flush(){let current=pending;pending=[];for f in current{f()}}
}
extension TestContent {var dimensions:CGSize {CGSize(width:320,height:180)}}
extension CGSize {func fitted(_ limit:CGSize)->CGSize {self}}
func floorToScreenPixels(_ value:CGFloat)->CGFloat {floor(value)}
final class PictureButton {var isEnabled=true}
final class UniversalVideoGalleryItemPictureInPictureNode {
    enum Mode {case pictureInPicture}
    static var created=0
    var frame=CGRect.zero
    var isUserInteractionEnabled=true
    init(strings:PresentationStrings,mode:Mode){Self.created+=1}
    func updateLayout(_ size:CGSize,transition:Transition){}
    func removeFromSupernode(){}
}
var checks=0
func check(_ value:@autoclosure()->Bool,_ label:String){
    if !value(){FileHandle.standardError.write(Data(("PiP continuity regression: "+label+"\n").utf8));exit(93)}
    checks+=1
}
func makeOwner()->GalleryHarness {
    NagramiXTabSettings.videoPiPSwipeEnabled=true
    AVPictureInPictureController.supported=true
    AVPictureInPictureController.possibleOnCreation=true
    AVPictureInPictureController.completeStartsAutomatically=false
    return GalleryHarness()
}
func begin(_ owner:GalleryHarness)->NativePictureInPictureContentImpl {
    owner.pictureInPictureButtonPressed();DispatchQueue.main.flush()
    return owner.nativePictureInPictureContent as! NativePictureInPictureContentImpl
}
func controller(_ owner:GalleryHarness)->AVPictureInPictureController {
    (owner.nativePictureInPictureContent as! NativePictureInPictureContentImpl).pictureInPictureController!
}
func requestRestore(_ owner:GalleryHarness,_ callback:@escaping (Bool)->Void){
    let content=owner.nativePictureInPictureContent as! NativePictureInPictureContentImpl
    content.pictureInPictureController(controller(owner),restoreUserInterfaceForPictureInPictureStopWithCompletionHandler:callback)
}
'''

TESTS = r'''
@main struct ContinuityTests {
    static func main(){
        stateTests()
        backdropTests()
        lifecycleTests()
        print("PiP continuity checks: \(checks)")
    }
    static func stateTests(){
        var state=NagramiXNativePiPVisualState()
        check(state.phase == .idle,"initial visual phase is idle")
        check(!state.didStart(),"unrequested didStart cannot activate visual transition")
        for _ in 0..<8 {
            let previous=state.generation
            state.begin()
            check(state.generation>previous && state.phase == .starting,"request has a new generation")
            check(state.didStart() && state.phase == .active,"only accepted source activates")
            check(!state.didStart(),"duplicate didStart does not dismiss gallery twice")
            state.restore();let generation=state.generation
            check(!state.presented(generation:generation-1),"stale presentation rejected")
            for presented in [false,true] { for stopped in [false,true] {
                for source in [false,true] {for owns in [false,true] {for window in [false,true] {for renderer in [false,true] {
                    var sample=state
                    if presented {_ = sample.presented(generation:generation)}
                    if stopped {sample.stopped()}
                    check(sample.canReveal(sourceMatches:source,ownsContent:owns,hasWindow:window,rendererReady:renderer) == (presented && stopped && source && owns && window && renderer),"all restore readiness gates required")
                }}}}
            }}
            state.cancel()
            check(state.phase == .idle && !state.presentationComplete && !state.hasStopped,"cancel clears phase flags")
            check(!state.presented(generation:generation),"canceled presentation cannot return")
        }
        for stopped in [false,true] {
            state.begin();_ = state.didStart();state.restore()
            let failedGeneration=state.generation
            if stopped {state.stopped()}
            state.restoreFailed()
            check(state.phase == .active && !state.presentationComplete && state.hasStopped == stopped,"NACK preserves actual native stop state")
            check(!state.presented(generation:failedGeneration),"NACK rejects late presentation callback")
            state.cancel()
        }
    }
    static func backdropTests(){
        let owner=makeOwner(),gallery=owner.gallery
        owner.navigation.view.contentMarker="Navigation container including full-screen gallery"
        owner.navigation.topViewController!.view.contentMarker="Underlying chat without gallery"
        gallery.view.contentMarker="Fullscreen source video"
        gallery.nagramiXPrepareNativePiPBackdrop()
        let first=gallery.nagramiXNativePiPBackdrop!
        check(first.contentMarker == owner.navigation.topViewController!.view.contentMarker && first.contentMarker != owner.navigation.view.contentMarker,"cover captures chat instead of navigation gallery overlay")
        check(first.superview == nil,"capturing cover does not hide source before WillStart")
        check(!first.isUserInteractionEnabled && first.accessibilityElementsHidden,"cover does not intercept controls or VoiceOver")
        check(first.frame == gallery.view.bounds,"cover follows complete host bounds")
        gallery.nagramiXShowNativePiPBackdrop()
        check(first.superview === gallery.view,"cover shown above source during native move")
        gallery.nagramiXShowNativePiPBackdrop()
        check(gallery.view.subviews.count==1,"repeated show has one cover")
        owner.navigation.topViewController!.view.contentMarker="Updated chat without gallery"
        gallery.nagramiXPrepareNativePiPBackdrop()
        let replacement=gallery.nagramiXNativePiPBackdrop!
        check(replacement !== first && first.superview == nil && replacement.superview === gallery.view,"fresh chat replaces old cover atomically")
        check(replacement.contentMarker == "Updated chat without gallery","replacement captures latest chat content")
        gallery.nagramiXFinishNativePiPBackdrop(animated:true)
        check(gallery.nagramiXNativePiPBackdrop == nil && replacement.alpha==0,"cover cleanup starts after native frame ready")
        check((owner.navigation.topViewController as? ChatController)?.pushes.last == 1,"visible restored gallery restores chat navigation treatment")
        AnimationClock.flush()
        check(replacement.superview == nil,"animated cleanup detaches cover")
        owner.navigation.topViewController!.view.canSnapshot=false
        gallery.nagramiXPrepareNativePiPBackdrop()
        check(gallery.nagramiXNativePiPBackdrop != nil,"pre-start source snapshot is fallback")
        check(gallery.nagramiXNativePiPBackdrop?.contentMarker == "Fullscreen source video","fallback captures pre-start video only when chat capture unavailable")
        gallery.nagramiXShowNativePiPBackdrop()
        let retained=gallery.nagramiXNativePiPBackdrop
        gallery.view.canSnapshot=false
        gallery.nagramiXPrepareNativePiPBackdrop()
        check(gallery.nagramiXNativePiPBackdrop === retained,"no replacement snapshot retains existing cover")
        gallery.nagramiXFinishNativePiPBackdrop(animated:false)
        gallery.nagramiXPrepareNativePiPBackdrop()
        check(gallery.nagramiXNativePiPBackdrop == nil,"nil snapshot creates no opaque empty cover")
    }
    static func lifecycleTests(){
        for original in [nil,UIColor.black,UIColor(white:0.3,alpha:1)] {
            let owner=makeOwner()
            owner.videoNode!.backgroundColor=original
            let content=begin(owner),av=controller(owner)
            check(owner.nagramiXPiPVisualState.phase == .starting,"accepted request enters starting phase")
            check(owner.videoNode!.backgroundColor == .clear,"source rectangle is transparent before AVKit move")
            check(owner.nagramiXPiPOriginalVideoBackground == original,"original optional background saved")
            check(owner.gallery.nagramiXNativePiPBackdrop?.superview === owner.gallery.view,"WillStart covers service surface")
            check(owner.gallery.view.alpha==1 && owner.dismissals==0 && owner.videoNode!.withoutHierarchy,"live source retained until accepted DidStart")
            owner.updateDisplayPlaceholder(true)
            check(owner.pictureInPictureNode == nil && owner.videoNode!.backgroundColor == .clear,"placeholder cannot repaint black source during transition")
            av.failStart()
            check(owner.nagramiXPiPVisualState.phase == .idle && owner.videoNode!.backgroundColor == original,"failed start restores exact optional background")
            check(owner.gallery.nagramiXNativePiPBackdrop == nil && !owner.disablePictureInPicturePlaceholder,"failed start clears cover and suppression")
            check(owner.context.sharedContext.mediaManager.currentPictureInPictureNode == nil && !owner.videoNode!.withoutHierarchy,"failed start releases native ownership")
            check(content.isStarting == false && owner.gallery.view.alpha==1,"failed start leaves working gallery")
        }
        for stoppedFirst in [false,true] {for dropped in [false,true] {
            let owner=makeOwner();let _=begin(owner);let av=controller(owner)
            av.finishStart()
            check(owner.dismissals==1 && owner.gallery.view.alpha==0 && owner.nagramiXPiPVisualState.phase == .active,"accepted native start retires gallery without trailing fade")
            owner.navigation.currentWindow!.dropsCompletion=dropped
            var restored:[Bool]=[]
            requestRestore(owner){restored.append($0)}
            check(restored.isEmpty && !owner.nagramiXPiPVisualState.presentationComplete,"restore cannot acknowledge before actual presentation")
            DispatchQueue.main.flush();SwiftSignalKit.Timer.poll()
            check(restored.isEmpty,"unattached source cannot acknowledge restore")
            owner.videoNode!.ownsContentNode=false
            if stoppedFirst {av.stopPictureInPicture()}
            check(owner.disablePictureInPicturePlaceholder && owner.gallery.nagramiXNativePiPBackdrop != nil,"cover survives either ordering before presentation")
            PresentationClock.flush()
            if dropped {check(restored.isEmpty,"dropped root-navigation completion is modeled")}
            DispatchQueue.main.flush();SwiftSignalKit.Timer.poll()
            check(restored == [true] && owner.gallery.view.layouts>0,"attachment watchdog acknowledges one completed layout")
            check(owner.nagramiXPiPVisualState.phase == .restoring && owner.gallery.nagramiXNativePiPBackdrop != nil,"presentation completion does not reveal AVKit source")
            if !stoppedFirst {check(av.isPictureInPictureActive,"AVKit is acknowledged while still active to avoid deadlock");av.stopPictureInPicture()}
            DispatchQueue.main.displayTurn()
            check(owner.gallery.nagramiXNativePiPBackdrop != nil,"no ownership keeps continuity cover")
            owner.videoNode!.ownsContentNode=true
            owner.videoNode!.layer.isReadyForDisplay=false
            owner.nagramiXTryFinishNativePiPRestore();SwiftSignalKit.Timer.poll();DispatchQueue.main.displayTurn()
            check(owner.gallery.nagramiXNativePiPBackdrop != nil,"unready native renderer cannot reveal technical surface")
            owner.videoNode!.layer.isReadyForDisplay=true
            owner.nagramiXTryFinishNativePiPRestore();owner.nagramiXTryFinishNativePiPRestore()
            check(owner.nagramiXPiPRevealScheduled && DispatchQueue.main.delayed.count==1,"one display-turn reveal is scheduled")
            owner.videoNode!.layer.isReadyForDisplay=false
            DispatchQueue.main.displayTurn()
            check(owner.gallery.nagramiXNativePiPBackdrop != nil && !owner.nagramiXPiPRevealScheduled,"readiness is rechecked on actual display turn")
            owner.videoNode!.layer.isReadyForDisplay=true
            owner.nagramiXTryFinishNativePiPRestore()
            DispatchQueue.main.displayTurn();AnimationClock.flush()
            check(owner.nagramiXPiPVisualState.phase == .idle && owner.gallery.nagramiXNativePiPBackdrop == nil,"frame readiness returns clean fullscreen player")
            check(!owner.disablePictureInPicturePlaceholder && owner.videoNode!.backgroundColor == nil,"normal gallery policy returns only after restore")
            check(restored == [true] && owner.nagramiXPiPRestoreTimer == nil,"completion remains exactly once and polling ends")
            let _=begin(owner);check(controller(owner).starts==2,"restored gallery permits next first request");controller(owner).failStart()
        }}
        rendererTests()
        cancellationTests()
    }
    static func rendererTests(){
        for supportsReady in [false,true] {
            FixtureFlags.hasReadyForDisplay=supportsReady
            let owner=makeOwner();let _=begin(owner)
            let video=owner.videoNode!,layer=video.layer
            layer.status = .unknown
            check(!owner.nagramiXNativePiPRendererReady(),"unknown renderer is not ready")
            layer.status = .rendering;layer.requiresFlushToResumeDecoding=true
            check(!owner.nagramiXNativePiPRendererReady(),"renderer requiring flush is not ready")
            layer.requiresFlushToResumeDecoding=false;layer.isReadyForDisplay=false
            check(owner.nagramiXNativePiPRendererReady() == !supportsReady,"readiness respects public API availability")
            layer.isReadyForDisplay=true
            check(owner.nagramiXNativePiPRendererReady(),"matching rendering layer ready")
            owner.videoNode=UniversalVideoNode()
            check(!owner.nagramiXNativePiPRendererReady(),"replacement source layer does not reveal old transition")
            owner.videoNode=video;controller(owner).failStart()
        }
        FixtureFlags.hasReadyForDisplay=true
    }
    static func cancellationTests(){
        var acknowledgements:[Bool]=[]
        var ack:NagramiXNativePiPPresentationAcknowledgement?=NagramiXNativePiPPresentationAcknowledgement{acknowledgements.append($0)}
        ack?.finish(true);ack?.finish(false);ack=nil
        check(acknowledgements == [true],"acknowledgement fires once across finish and deinit")
        ack=NagramiXNativePiPPresentationAcknowledgement{acknowledgements.append($0)}
        ack=nil
        check(acknowledgements == [true,false],"abandoned presentation reports failure once")
        let owner=makeOwner();let _=begin(owner);controller(owner).finishStart()
        var restored:[Bool]=[]
        requestRestore(owner){restored.append($0)}
        owner.nagramiXFinishNativePiPVisualTransition(animated:false)
        PresentationClock.flush();DispatchQueue.main.flush();SwiftSignalKit.Timer.poll()
        check(restored == [false] && owner.nagramiXPiPVisualState.phase == .idle,"cancellation invalidates delayed presentation without stale success")
        let missing=makeOwner();let _=begin(missing);controller(missing).finishStart()
        missing.navigation.currentWindow=nil
        var missingResults:[Bool]=[];requestRestore(missing){missingResults.append($0)}
        check(missingResults == [false] && missing.nagramiXPiPVisualState.phase == .active,"missing window cannot report restored")
        controller(missing).stopPictureInPicture()
        check((missing.navigation.topViewController as? ChatController)?.pushes.last == 0,"closing detached PiP leaves actual chat navigation visible")
        for stopFirst in [false,true] {
            let delayed=makeOwner();let _=begin(delayed);controller(delayed).finishStart()
            var delayedResults:[Bool]=[];requestRestore(delayed){delayedResults.append($0)}
            let proxy=delayed.gallery.presentingViewController!
            if stopFirst {controller(delayed).stopPictureInPicture()}
            mediaTime+=2.1;SwiftSignalKit.Timer.poll()
            check(delayedResults == [false],"presentation attachment timeout is bounded")
            check(delayed.nagramiXPiPVisualState.phase == (stopFirst ? .idle : .active),"failed presentation leaves no stranded restoring phase")
            check(proxy.dismissed,"failed attachment cancels pending navigation container")
            PresentationClock.flush();DispatchQueue.main.flush()
            check(delayedResults == [false] && delayed.gallery.view.window == nil,"late attachment cannot reverse timeout")
            if !stopFirst {controller(delayed).stopPictureInPicture()}
            check(delayed.nagramiXPiPVisualState.phase == .idle && delayed.gallery.nagramiXNativePiPBackdrop == nil,"NACK cleanup finishes in either stop ordering")
        }
        let stalled=makeOwner();let _=begin(stalled);controller(stalled).finishStart()
        requestRestore(stalled){_ in};PresentationClock.flush();DispatchQueue.main.flush()
        stalled.videoNode!.layer.status = .failed
        controller(stalled).stopPictureInPicture()
        mediaTime+=5.1;SwiftSignalKit.Timer.poll()
        check(stalled.nagramiXPiPVisualState.phase == .idle && stalled.gallery.view.alpha==0 && stalled.gallery.nagramiXNativePiPBackdrop == nil,"stalled renderer returns to chat without frozen veil")
        let stale=makeOwner();let _=begin(stale);controller(stale).finishStart()
        requestRestore(stale){_ in};PresentationClock.flush();DispatchQueue.main.flush();controller(stale).stopPictureInPicture()
        check(stale.nagramiXPiPRevealScheduled,"restore reaches deferred display turn")
        stale.nagramiXFinishNativePiPVisualTransition(animated:false)
        let _=stale.nagramiXBeginNativePiPVisualTransition()
        let _=stale.nagramiXPiPVisualState.didStart()
        stale.nagramiXPiPVisualState.restore()
        let newGeneration=stale.nagramiXPiPHandoffGeneration
        let _=stale.nagramiXPiPVisualState.presented(generation:newGeneration)
        stale.nagramiXPiPVisualState.stopped()
        DispatchQueue.main.displayTurn()
        check(stale.nagramiXPiPHandoffGeneration==newGeneration && stale.nagramiXPiPVisualState.phase == .restoring,"stale display turn cannot clear next session")
        stale.nagramiXFinishNativePiPVisualTransition(animated:false)
    }
}
'''


def semantic_negatives(text):
    variants = (
        ('before-stop', 'self.presentationComplete && self.hasStopped',
         'self.presentationComplete', 'all restore readiness gates required'),
        ('stale-presentation', 'guard generation == self.generation, self.phase == .restoring else { return false }',
         'guard self.phase == .restoring else { return false }', 'stale presentation rejected'),
        ('black-source', 'source.backgroundColor = self.nagramiXPiPOriginalVideoBackground',
         'source.backgroundColor = .black', 'failed start restores exact optional background'),
        ('missing-cover', 'self.view.addSubview(backdrop)',
         '_ = backdrop', 'cover shown above source during native move'),
        ('lost-completion-watchdog', 'self.nagramiXPiPPresentationTimer = timer\n        timer.start()',
         'self.nagramiXPiPPresentationTimer = timer', 'attachment watchdog acknowledges one completed layout'),
        ('repeat-acknowledgement', 'self.completion = nil',
         '// Keep callback incorrectly.', 'attachment watchdog acknowledges one completed layout'),
        ('unready-renderer', 'return layer.isReadyForDisplay',
         'return true', 'unready native renderer cannot reveal technical surface'),
        ('unbounded-renderer', '&& CACurrentMediaTime() >= self.nagramiXPiPRestoreDeadline',
         '&& false', 'stalled renderer returns to chat without frozen veil'),
        ('late-container', 'controller.presentingViewController?.dismiss(animated: false, completion: nil)',
         '// Incorrectly leave pending navigation container.', 'failed attachment cancels pending navigation container'),
        ('stale-display-turn', 'guard let self, generation == self.nagramiXPiPHandoffGeneration else { return }',
         'guard let self else { return }; _ = generation', 'stale display turn cannot clear next session'),
        ('whole-navigation-snapshot', 'self.baseNavigationController?.topViewController?.view.snapshotView(afterScreenUpdates: false)',
         'self.baseNavigationController?.view.snapshotView(afterScreenUpdates: false)',
         'cover captures chat instead of navigation gallery overlay'),
    )
    for name, before, after, diagnostic in variants:
        assert text.count(before) == 1, (name, text.count(before))
        yield name, text.replace(before, after), diagnostic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = source_contract(args.source)
    before = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='pip-continuity-') as temporary:
        root = Path(temporary)
        rejected = guard_checks(args.source, STAGE, plan, root / 'guards')
        swift = fixture(args.source)
        runs = execute(args.swiftc, root, 'native-continuity', swift)
        for name, mutated, diagnostic in semantic_negatives(swift):
            runs += execute(args.swiftc, root, name, mutated, diagnostic)
        for name in plan['outputs']:
            run([args.swiftc, '-frontend', '-parse', args.source / name])
    assert manifest(args.source) == before
    run(['python3', args.source / 'build-system/Make/PostboxImportCheck.py', args.source])
    report = {
        'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
        'fail_closed': len(rejected), 'executions': runs,
        'swift_parse': len(plan['outputs']), 'source_files': len(before),
        'source_unchanged_by_checks': True,
        'native_postbox_imports': 'passed',
        'boundary': 'Production AVKit delegate/setup/button, visual state, '
                    'presentation/restore and cover bodies execute unchanged in '
                    'explicit UIKit/window/renderer/availability/scheduling adapters. '
                    'This does not render UIKit pixels, exercise live AVKit or prove '
                    'physical corner animation. Modern public readiness and older '
                    'rendering-status fallback are separate modeled API branches.',
        'apple_sdk': 'not_run', 'ipa': 'not_built', 'physical_iphone': 'pending',
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ('executions', 'outputs')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
