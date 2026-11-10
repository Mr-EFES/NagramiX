#!/usr/bin/env python3
"""Проверить геометрию фона и временную обрезку исходника системного PiP."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_pip_visual_continuity import fixture as continuity_fixture, execute
from validate_pip_swipe_handoff import G, N, U, clean
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

STAGE = 'pip_backdrop_stability'
ROOT = Path(__file__).resolve().parents[1]


def fixture(source):
    text = continuity_fixture(source)
    helper = clean(block((source / U).read_text(), 'private final class NagramiXNativePiPSourceClipping'))
    text = text.replace('final class Layer {', 'class Layer {\n    weak var superlayer: Layer?\n    var masksToBounds = false\n    var mask: Layer?')
    text = text.replace('final class VideoLayer {', 'final class VideoLayer: Layer {')
    text = text.replace('var bounds:CGRect {frame}', 'var bounds:CGRect { CGRect(origin: .zero, size: frame.size) }')
    text = text.replace('    var layouts=0', '''    var coordinateOffset=CGPoint.zero
    var pendingScale=0.94, committedScale=0.94, capturedScale=0.94
    var snapshotRequests:[Bool]=[]
    func convert(_ rect:CGRect,to view:UIView)->CGRect {
        rect.offsetBy(dx:coordinateOffset.x-view.coordinateOffset.x,dy:coordinateOffset.y-view.coordinateOffset.y)
    }
    var layouts=0''')
    text = text.replace('        guard canSnapshot else{return nil}', '''        snapshotRequests.append(afterScreenUpdates)
        guard canSnapshot else{return nil}
        if afterScreenUpdates { committedScale=pendingScale }''')
    text = text.replace('let result=UIView();result.contentMarker=contentMarker;return result', 'let result=UIView();result.contentMarker=contentMarker;result.capturedScale=committedScale;return result')
    text = text.replace('transition:Transition){pushes.append(value)}', 'transition:Transition){pushes.append(value);view.pendingScale=1.0-0.06*value}')
    text = text.replace('func nagramiXPrepareNativePiPBackdrop() -> Bool {', '@discardableResult\nfunc nagramiXPrepareNativePiPBackdrop() -> Bool {')
    text = text.replace('    return GalleryHarness()', '''    let owner=GalleryHarness()
    owner.videoNode!.view.layer.superlayer=owner.gallery.view.layer
    owner.videoNode!.view.layer.masksToBounds=true
    owner.videoNode!.getVideoLayer()!.superlayer=owner.videoNode!.view.layer
    return owner''')
    text = text.replace('        backdropTests()', '        backdropTests()\n        clippingTests()')
    old = block(text, '    static func backdropTests()')
    text = text.replace(old, BACKDROP_TESTS + '\n' + CLIPPING_TESTS)
    text += '\ntypealias CALayer = Layer\n' + TRANSACTION + '\n' + helper
    return text


TRANSACTION = '''
enum CATransaction {
    static var depth=0
    static func begin(){depth+=1}
    static func setDisableActions(_ value:Bool){if !value{fatalError("implicit actions enabled")}}
    static func commit(){depth-=1}
}
'''

BACKDROP_TESTS = r'''
    static func backdropTests(){
        let owner=makeOwner(),gallery=owner.gallery,chat=owner.navigation.topViewController as! ChatController
        chat.view.frame=CGRect(x:0,y:0,width:390,height:810)
        chat.view.coordinateOffset=CGPoint(x:0,y:34)
        chat.view.contentMarker="Current chat"
        gallery.view.contentMarker="Fullscreen video must not be duplicated"
        check(gallery.nagramiXPrepareNativePiPBackdrop(),"chat capture prepares transition")
        let first=gallery.nagramiXNativePiPBackdrop!
        check(first.capturedScale==1 && chat.view.snapshotRequests.last==true,"snapshot uses committed neutral chat")
        check(first.frame==CGRect(x:0,y:34,width:390,height:810),"snapshot preserves source coordinates and size")
        check(first.autoresizingMask.isEmpty,"old pixels cannot stretch on relayout")
        check(first.contentMarker=="Current chat" && first.superview==nil,"only underlying chat captured before native start")
        gallery.nagramiXShowNativePiPBackdrop()
        check(first.frame.height==810 && first.frame.minY==34,"show never stretches source to gallery bounds")
        check(!first.isUserInteractionEnabled && first.accessibilityElementsHidden,"backdrop does not intercept controls")
        gallery.nagramiXShowNativePiPBackdrop()
        check(gallery.view.subviews.count==1,"show remains idempotent")
        gallery.galleryNode.scrollViewDidScroll(gallery.galleryNode.scrollView)
        check(chat.pushes.last==0,"scroll callback cannot shrink frozen chat")
        gallery.galleryNode.nagramiXLockNativePictureInPictureSwipe()
        gallery.nagramiXResetNativePictureInPictureSwipe()
        check(chat.pushes.last==0,"presentation reset cannot shrink frozen chat")
        gallery.nagramiXFinishNativePiPBackdrop(animated:true)
        check(chat.pushes.last==0,"chat treatment waits for backdrop removal")
        AnimationClock.flush()
        check(chat.pushes.last==1 && first.superview==nil,"chat treatment resumes after cover removal")
        chat.view.canSnapshot=false
        check(!gallery.nagramiXPrepareNativePiPBackdrop(),"missing chat snapshot rejects pre-start handoff")
        check(gallery.nagramiXNativePiPBackdrop==nil && gallery.view.snapshotRequests.isEmpty,"gallery video is never snapshot fallback")
        chat.view.canSnapshot=true
        check(gallery.nagramiXPrepareNativePiPBackdrop(),"next attempt can capture chat")
        let retained=gallery.nagramiXNativePiPBackdrop
        chat.view.canSnapshot=false
        check(gallery.nagramiXPrepareNativePiPBackdrop() && retained === gallery.nagramiXNativePiPBackdrop,"same source and geometry may retain valid cover")
        chat.view.coordinateOffset.y+=10
        check(!gallery.nagramiXPrepareNativePiPBackdrop(),"moved stale capture cannot stand in for current geometry")
        gallery.nagramiXFinishNativePiPBackdrop(animated:false)
        chat.view.canSnapshot=true
        check(gallery.nagramiXPrepareNativePiPBackdrop(),"fresh cover after stale geometry")
        gallery.nagramiXShowNativePiPBackdrop()
        let older=gallery.nagramiXNativePiPBackdrop!
        gallery.nagramiXFinishNativePiPBackdrop(animated:true)
        chat.view.contentMarker="New session"
        check(gallery.nagramiXPrepareNativePiPBackdrop(),"new session during old fade")
        gallery.nagramiXShowNativePiPBackdrop()
        let newer=gallery.nagramiXNativePiPBackdrop!
        AnimationClock.flush()
        check(older.superview==nil && newer.superview === gallery.view && chat.pushes.last==0,"stale fade cannot shrink new session")
        gallery.nagramiXFinishNativePiPBackdrop(animated:true)
        check(gallery.nagramiXPrepareNativePiPBackdrop(),"second rapid capture")
        gallery.nagramiXShowNativePiPBackdrop()
        gallery.nagramiXFinishNativePiPBackdrop(animated:true)
        AnimationClock.pending.removeFirst()()
        check(chat.pushes.last==0,"older completion cannot shrink a newer fading cover")
        AnimationClock.flush()
        check(chat.pushes.last==1,"newest fade restores final treatment")
        check(gallery.nagramiXPrepareNativePiPBackdrop(),"prepare before rotation")
        gallery.nagramiXShowNativePiPBackdrop()
        let portrait=gallery.nagramiXNativePiPBackdrop!
        gallery.view.frame=CGRect(x:0,y:0,width:844,height:390)
        chat.view.frame=CGRect(x:0,y:0,width:810,height:390)
        chat.view.coordinateOffset=CGPoint(x:34,y:0)
        gallery.nagramiXUpdateNativePiPBackdropLayout()
        let landscape=gallery.nagramiXNativePiPBackdrop!
        check(landscape !== portrait && portrait.superview==nil && landscape.frame==CGRect(x:34,y:0,width:810,height:390),"rotation replaces capture with new coordinates")
        gallery.nagramiXNativePiPBackdropPreparing=true
        gallery.nagramiXNativePiPBackdropBounds=nil
        gallery.nagramiXUpdateNativePiPBackdropLayout()
        check(gallery.nagramiXNativePiPBackdrop === landscape,"layout during capture cannot recurse")
        gallery.nagramiXNativePiPBackdropPreparing=false
        chat.view.canSnapshot=false
        gallery.nagramiXUpdateNativePiPBackdropLayout()
        check(gallery.nagramiXNativePiPBackdrop==nil && landscape.superview==nil,"invalid capture after rotation never stretches old pixels")
        gallery.nagramiXFinishNativePiPBackdrop(animated:false)
        let failed=makeOwner()
        failed.navigation.topViewController!.view.canSnapshot=false
        failed.pictureInPictureButtonPressed();DispatchQueue.main.flush()
        check(controller(failed).starts==0,"unavailable cover does not launch a broken native handoff")
        let restoring=makeOwner();let _=begin(restoring);controller(restoring).finishStart()
        restoring.gallery.nagramiXNativePiPBackdrop=nil
        restoring.navigation.topViewController!.view.canSnapshot=false
        var results:[Bool]=[]
        requestRestore(restoring){results.append($0)}
        check(results==[false] && controller(restoring).isPictureInPictureActive,"unavailable restore leaves PiP active")
    }
'''

CLIPPING_TESTS = r'''
    static func clippingTests(){
        let root=Layer(),parent=Layer(),inner=Layer(),video=VideoLayer(),mask=Layer()
        root.masksToBounds=true;root.mask=Layer()
        parent.masksToBounds=true;parent.mask=mask;parent.superlayer=root
        inner.superlayer=parent;video.superlayer=inner
        video.masksToBounds=true;video.mask=Layer()
        let nativeMask=video.mask,rootMask=root.mask
        for _ in 0..<8 {
            let lease=NagramiXNativePiPSourceClipping(source:video,root:root)
            check(lease != nil && !parent.masksToBounds && parent.mask==nil,"client ancestor clipping released symmetrically")
            check(video.masksToBounds && video.mask === nativeMask,"native sample layer remains untouched")
            check(root.masksToBounds && root.mask === rootMask,"root window clipping stays intact")
            lease?.restore();lease?.restore()
            check(parent.masksToBounds && parent.mask === mask,"ancestor state restored exactly once")
        }
        let unrelated=Layer()
        check(NagramiXNativePiPSourceClipping(source:video,root:unrelated)==nil && parent.masksToBounds,"foreign hierarchy cannot be altered")
        var lease=NagramiXNativePiPSourceClipping(source:video,root:root)
        let newMask=Layer();parent.mask=newMask
        lease?.restore()
        check(parent.mask === newMask && !parent.masksToBounds,"new layout mask is not overwritten")
        parent.mask=mask;parent.masksToBounds=true
        lease=NagramiXNativePiPSourceClipping(source:video,root:root)
        lease=nil
        check(parent.masksToBounds && parent.mask === mask,"deinit restores abandoned handoff")
        check(CATransaction.depth==0,"clipping transactions balanced")
        let owner=makeOwner();let _=begin(owner)
        check(!owner.videoNode!.view.layer.masksToBounds,"production start acquires clipping lease")
        controller(owner).failStart()
        check(owner.videoNode!.view.layer.masksToBounds,"failed native start restores clipping")
    }
'''


def negatives(text):
    variants = (
        ('stale-snapshot', 'source.snapshotView(afterScreenUpdates: true)', 'source.snapshotView(afterScreenUpdates: false)', 'snapshot uses committed neutral chat'),
        ('stretched-background', 'snapshot.frame = frame', 'snapshot.frame = self.view.bounds', 'snapshot preserves source coordinates and size'),
        ('duplicate-video', 'source.snapshotView(afterScreenUpdates: true)', 'source.snapshotView(afterScreenUpdates: true) ?? self.view.snapshotView(afterScreenUpdates: false)', 'missing chat snapshot rejects pre-start handoff'),
        ('early-shrink', 'self.nagramiXNativePiPBackdropActive = false', 'self.nagramiXNativePiPBackdropActive = false\n        (self.baseNavigationController?.topViewController as? ChatController)?.updatePushedTransition(1.0, transition: .immediate)', 'chat treatment waits for backdrop removal'),
        ('clip-native-layer', 'var current = source.superlayer', 'var current: CALayer? = source', 'native sample layer remains untouched'),
        ('clip-window', 'for layer in ancestors where', 'for layer in ancestors + [root] where', 'root window clipping stays intact'),
        ('restore-shrink', 'if restoreChatTransition, !previousSuppression, let chatController', 'if restoreChatTransition, let chatController', 'presentation reset cannot shrink frozen chat'),
        ('stale-fade', 'self.nagramiXNativePiPBackdropGeneration == generation', 'self.nagramiXNativePiPBackdropGeneration >= generation', 'older completion cannot shrink a newer fading cover'),
    )
    for name, old, new, diagnostic in variants:
        assert text.count(old) == 1, (name, text.count(old))
        yield name, text.replace(old, new), diagnostic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'premium_label_spelling'
    assert set(plan['inputs']) == {G, N, U}
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, value in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == value, name
    for name, markers in ((U, ('private final class NativePictureInPictureContentImpl:',
                              'private struct NagramiXNativePiPVisualState',
                              '    override func maybePerformActionForSwipeDismiss()',
                              '    @objc func pictureInPictureButtonPressed()')),
                          (N, ('func nagramiXShouldBeginFastPictureInPictureSwipe(',
                               '    private func nagramiXTryBeginNativePictureInPictureSwipe(',
                               '    open func scrollViewWillEndDragging('))):
        previous = (ROOT / 'ios' / plan['previous'][name]).read_text()
        actual = (args.source / name).read_text()
        for marker in markers:
            assert block(actual, marker) == block(previous, marker), marker
    before = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='pip-backdrop-') as tmp:
        temporary = Path(tmp)
        refused = guard_checks(args.source, STAGE, plan, temporary / 'guards')
        swift = fixture(args.source)
        runs = execute(args.swiftc, temporary, 'backdrop-stability', swift)
        for name, text, diagnostic in negatives(swift):
            runs += execute(args.swiftc, temporary, name, text, diagnostic)
        import subprocess
        for name in plan['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    assert manifest(args.source) == before
    result = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']), 'loader_refusals': len(refused), 'executions': runs, 'swift_parse': 3,
              'boundary': 'Production snapshot/scroll suppression, clipping lease, AVKit delegate/setup/start/failure/restore, visual state and acknowledgement run in explicit UIKit/layer/render-commit/coordinate/window/timer adapters. No real compositor, AVKit animation or iPhone pixels are exercised.',
              'apple_sdk': 'not_run', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
