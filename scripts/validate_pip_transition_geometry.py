#!/usr/bin/env python3
"""Проверить геометрию жеста PiP, ожидание возврата и сохранение воспроизведения."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import tempfile
from validate_quick_format import block, manifest
from validate_localization_standard import catalog_contract, source_contract
ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
STAGE='pip_transition_geometry'
PLAN=json.loads((OVERLAY/(STAGE+'_patches.json')).read_text())
FILES=list(PLAN['inputs'])
F=FILES[0]
def sha(data): return hashlib.sha256(data).hexdigest()
def clean(t): return t.replace('private ','').replace('public ','').replace('open ','').replace('@objc ','')


def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source/name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY/name).read_bytes()) == digest, name
    text=(source/FILES[0]).read_text()
    native=block(text,'private final class NativePictureInPictureContentImpl:')
    for forbidden in ['.presentation(', 'CABasicAnimation(', 'AVPlayer(', 'UIWindow(', '.cornerRadius =', '.masksToBounds =', '.videoGravity =', '.bounds =', '.flush(']:
        assert forbidden not in native, forbidden
    assert text.count('AVPictureInPictureController(contentSource:') == 1
    previous=(OVERLAY/PLAN['previous'][FILES[0]]).read_text()
    for marker in ['private func releaseSession(', 'private func restoreInterface(', 'public func pictureInPictureControllerDidStopPictureInPicture(', 'public func pictureInPictureControllerWillStartPictureInPicture(', 'override func centralityUpdated(', 'override func visibilityUpdated(']:
        assert block(text,marker) == block(previous,marker), marker
    for index, markers in enumerate([
        ['private final class NativePictureInPictureContentImpl:', 'private func setupNativePictureInPicture(', 'override var isReadyForNativePictureInPictureRestore:', 'override func maybePerformActionForSwipeDismiss('],
        ['open func containerLayoutUpdated(', 'open func scrollViewDidScroll(', 'open func scrollViewWillEndDragging('],
        ['override public func viewDidAppear('],
        []
    ]):
        before=(OVERLAY/PLAN['previous'][FILES[index]]).read_text()
        after=(source/FILES[index]).read_text()
        restored=after
        if index==0:
            for marker in ['    override var nativePictureInPictureRestoreRect:', '    override var usesNativePictureInPictureSwipe:']:
                restored=restored.replace(block(restored,marker)+'\n\n','')
            restored=restored.replace('nativePictureInPictureControlAlpha: (CGFloat?, CGFloat, UIColor?)?', 'nativePictureInPictureControlAlpha: (CGFloat?, CGFloat)?')
        elif index==1:
            start=restored.index('    private struct NativePictureInPictureAppearance')
            end=restored.index('    private var presentationState =',start)
            old_start=before.index('    private struct NativePictureInPictureAppearance')
            old_end=before.index('    private var presentationState =',old_start)
            restored=restored[:start]+before[old_start:old_end]+restored[end:]
            restored=restored.replace(block(restored,'    open func scrollViewWillBeginDragging(')+'\n\n','')
        elif index==2:
            start=restored.index('    private var nativePictureInPictureRestoreCompletion')
            end=restored.index('    private let _hiddenMedia =',start)
            old_start=before.index('    private var nativePictureInPictureRestoreCompletion')
            old_end=before.index('    private let _hiddenMedia =',old_start)
            restored=restored[:start]+before[old_start:old_end]+restored[end:]
        else:
            for marker in ['    open var usesNativePictureInPictureSwipe:', '    open var nativePictureInPictureRestoreRect:']:
                restored=restored.replace(block(restored,marker)+'\n\n','')
        for marker in markers:
            restored=restored.replace(block(restored,marker),block(before,marker))
        assert restored==before, 'Unrelated source change: '+FILES[index]
    pipeline=(OVERLAY/'apply_overlay.py').read_text()
    assert pipeline.index('    apply_transfer_consistency(')<pipeline.index('    apply_pip_transition_geometry(')
    assert catalog_contract(source)==(71,613)
    assert source_contract(source)==(111,594)

def guard_checks(source,temp):
    spec=importlib.util.spec_from_file_location(STAGE,OVERLAY/(STAGE+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    apply=getattr(module,'apply_'+STAGE)
    rejected=[]
    def seed(label):
        tree=temp/label
        for name in {**PLAN['inputs'],**PLAN['guards']}:
            p=tree/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((OVERLAY/PLAN['previous'][name] if name in PLAN['previous'] else source/name).read_bytes())
        return tree
    def reject(tree,label,overlay=OVERLAY):
        before=manifest(tree)
        try:apply(tree,overlay)
        except (SystemExit,OSError):pass
        else:raise AssertionError('Invalid input accepted: '+label)
        assert manifest(tree)==before,'Partial write: '+label
        rejected.append(label)
    valid=seed('valid');apply(valid,OVERLAY)
    assert all((valid/n).read_bytes()==(source/n).read_bytes() for n in PLAN['outputs'])
    reject(valid,'repeat')
    for i,n in enumerate({**PLAN['inputs'],**PLAN['guards']}):
        for kind in ['missing','drift']:
            tree=seed(str(i)+'-'+kind)
            if kind=='missing':(tree/n).unlink()
            else:(tree/n).write_bytes(b'drift')
            reject(tree,kind+' '+n)
    variants=[]
    for field in ['inputs','outputs','guards','templates']:
        bad=copy.deepcopy(PLAN);bad[field][next(iter(bad[field]))]='0'*64;variants.append((field,bad))
    for field in ['previous','replacements']:
        bad=copy.deepcopy(PLAN);bad[field][F]='../outside.swift';variants.append((field,bad))
    bad=copy.deepcopy(PLAN);bad['outputs'].clear();variants.append(('inconsistent',bad))
    for label,bad in variants:
        overlay=temp/('overlay-'+label)
        for name in PLAN['templates']:
            p=overlay/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OVERLAY/name).read_bytes())
        (overlay/(STAGE+'_patches.json')).write_text(json.dumps(bad))
        reject(seed('source-'+label),label,overlay)
    for i,n in enumerate([F,next(iter(PLAN['guards']))]):
        tree=seed('symlink-'+str(i));p=tree/n;outside=temp/('outside-'+str(i))
        outside.write_bytes(p.read_bytes());p.unlink();p.symlink_to(outside);reject(tree,'external symlink '+n)
    return rejected


def runtime_source(source):
    t=(source/'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift').read_text()
    node=(source/'submodules/GalleryUI/Sources/GalleryControllerNode.swift').read_text()
    gallery=(source/'submodules/GalleryUI/Sources/GalleryController.swift').read_text()
    native=clean(block(t,'private final class NativePictureInPictureContentImpl:'))
    ui=node[node.index('    private struct NativePictureInPictureAppearance'):node.index('    private var presentationState =')]
    restore=gallery[gallery.index('    private var nativePictureInPictureRestoreCompletion'):gallery.index('    private let _hiddenMedia =')]
    methods='\n'.join(block(t,m) for m in [
        'private func setupNativePictureInPicture(', 'func pictureInPictureButtonPressed(', 'func expandPIP(',
        'override func maybePerformActionForSwipeDismiss(', 'override func maybePerformActionForSwipeDownDismiss(',
        'override func centralityUpdated(', 'override func visibilityUpdated(', 'override var isReadyForNativePictureInPictureRestore:', 'override var nativePictureInPictureRestoreRect:', 'override var usesNativePictureInPictureSwipe:'])
    methods=clean(methods).replace('UniversalVideoGalleryItemNode','GalleryHarness')
    node_methods=clean('\n'.join(block(node,m) for m in ['open func scrollViewWillBeginDragging(', 'open func scrollViewDidScroll(', 'open func scrollViewWillEndDragging(']))
    appear=clean(block(gallery,'override public func viewDidAppear('))
    begin=clean(block(gallery,'self.galleryNode.beginCustomDismiss ='))
    complete=clean(block(gallery,'self.galleryNode.completeCustomDismiss ='))
    return '\n'.join([
        (ROOT/'scripts/tests/NagramiXPiPGeometryBoundary.swift').read_text(),native,
        '''final class GalleryNodeHarness {
    let view = UIView()
    let backgroundNode = VisualNode()
    let scrollView = UIScrollView()
    let pager = Pager()
    var navigationBar: VisualNode? = VisualNode()
    var statusBar: StatusBar? = StatusBar()
    var titleView: UIView? = UIView()
    let headerEdgeEffectView = UIView()
    var currentThumbnailContainerNode: GalleryThumbnailContainerNode? = GalleryThumbnailContainerNode()
    let footerNode = FooterNode()
    var overlayNode: VisualNode?
    var containerLayout: (CGFloat, ContainerViewLayout)? = (44,ContainerViewLayout())
    var areControlsHidden = false
    var isDismissed = false
    var context = AccountContext()
    var baseNavigationController: () -> NavigationController? = { nil }
    var beginCustomDismiss: (Dismiss) -> Void = { _ in }
    var completeCustomDismiss: (Bool) -> Void = { _ in }
    var dismiss: (() -> Void)?
    var transitionDataForCentralItem: (() -> ((VisualNode,CGRect,Int)?,Int)?)?
    var normalAnimations = 0
    func setControlsHidden(_ hidden: Bool, animated: Bool) { areControlsHidden = hidden }
    func updateThumbnailContainerNodeAlpha(_ transition: ContainedViewLayoutTransition) { currentThumbnailContainerNode?.alpha = areControlsHidden ? 0 : 1 }
    func updateDismissTransition(_ value: CGFloat) {}
    func updateDistanceFromEquilibrium(_ value: CGFloat) {}
    func animateIn(animateContent: Bool, useSimpleAnimation: Bool) { normalAnimations += 1 }
    func animateOut(animateContent: Bool, completion: () -> Void) { isDismissed = true; normalAnimations += 1; completion() }
''',clean(ui),node_methods,'}',
        '''final class GalleryController: BaseController {
    let galleryNode = GalleryNodeHarness()
    var context = AccountContext()
    var baseNavigationController: NavigationController?
    var entries = [Entry()]
    let _hiddenMedia = Signal<(MessageId,Media)?,NoError>(nil)
    var hiddenMediaManagerIndex: Int?
    let accountInUseDisposable = Sink()
    var actionInteraction: ActionInteraction? = ActionInteraction()
    let centralItemTitle = Sink(), centralItemTitleContent = Sink(), centralItemRightBarButtonItem = Sink(), centralItemRightBarButtonItems = Sink(), centralItemNavigationStyle = Sink(), centralItemFooterContentNode = Sink()
    var onDidAppear: (() -> Void)?
    var useSimpleAnimation = false
    var dismissals = 0
    func isPresentedInPreviewingContext() -> Bool { false }
    func dismiss(forceAway: Bool) { dismissals += 1; detach() }
    func attach(to window: Window) {
        view.window = window; galleryNode.view.window = window
        galleryNode.pager.central?.view.window = window
        (galleryNode.pager.central as? GalleryHarness)?.videoNode?.view.window = window
    }
    func detach() {
        view.window = nil; galleryNode.view.window = nil
        galleryNode.pager.central?.view.window = nil
        (galleryNode.pager.central as? GalleryHarness)?.videoNode?.view.window = nil
    }
    func installCallbacks() {
''',begin,complete,'}',clean(restore),appear,'}',
        '''final class GalleryHarness: GalleryBase {
    let context = AccountContext()
    let footerContentNode = Footer()
    let gallery = GalleryController()
    let navigation = NavigationController()
    let parent = ParentController()
    let chat = ChatController()
    var item: Item? = Item()
    var videoNode: UniversalVideoNode? = UniversalVideoNode()
    var nativePictureInPictureContent: AnyObject?
    var activePictureInPictureController: BaseController?
    var activePictureInPictureNavigationController: NavigationController?
    var isCentral: Bool?
    var _isVisible: Bool? = true
    var hasPictureInPicture = true
    var settingsButtonState = 0
    var displayStickersButton = false
    var disablePictureInPicturePlaceholder = false
    var nativePictureInPicturePrepared = false
    var nativePictureInPictureWasSwipe = false
    var nativePictureInPictureControlAlpha: (CGFloat?,CGFloat,UIColor?)?
    let playbackControls = Controls()
    let statusButtonNode = VisualNode()
    var validLayout: ValidLayout? = ValidLayout()
    var dismissals = 0
    var hideStatusNodeUntilCentrality = false, statusNodeShouldBeHidden = false
    var initiallyActivated = true, playOnContentOwnership = false, isPlaying = false
    let isPlayingPromise = Sink()
    var dismissOnOrientationChange = false, isLivePhoto = false, skipInitialPause = false, ignorePauseStatus = false
    var playbackRate: Double?
    let actionAtEnd = 0
    var videoNodeUserInteractionEnabled = true
    var playerStatusValue: MediaPlayerStatus?
    override init() {
        super.init()
        navigation.topViewController = chat
        gallery.context = context; gallery.baseNavigationController = navigation
        gallery.galleryNode.context = context; gallery.galleryNode.pager.central = self
        gallery.galleryNode.baseNavigationController = { [weak self] in self?.navigation }
        gallery.presentingViewController = parent
        parent.onDismiss = { [weak self] in self?.gallery.detach() }
        gallery.installCallbacks()
        gallery.hiddenMediaManagerIndex = context.sharedContext.mediaManager.galleryHiddenMediaManager.addSource(.single(.chat(1,1,TelegramMediaFile())))
    }
    func galleryController() -> BaseController? { gallery }
    func baseNavigationController() -> NavigationController? { navigation }
    func beginCustomDismiss(_ type: Dismiss) { gallery.galleryNode.beginCustomDismiss(type) }
    func completeCustomDismiss(_ active: Bool) { dismissals += 1; gallery.galleryNode.completeCustomDismiss(active) }
    func updateControlsVisibility(_ visible: Bool) {}
    func updateDisplayPlaceholder(_ value: Bool = false) {}
    func containerLayoutUpdated(_ layout: ContainerViewLayout, navigationBarHeight: CGFloat, transition: ContainedViewLayoutTransition) {}
    func resetLivePhotoPlayback() {}
    func shouldAutoplayOnCentrality() -> Bool { false }
    func playLivePhotoAutoplayIfNeeded(videoNode: UniversalVideoNode) -> Bool { false }
    func maybeStorePlaybackStatus(status: MediaPlayerStatus) {}
''',methods,'}',(ROOT/'scripts/tests/NagramiXPiPGeometryTests.swift').read_text()])


def variant(source, label):
    text=runtime_source(source)
    def change(old,new):
        nonlocal text
        assert text.count(old)==1, (label,old[:90],text.count(old))
        text=text.replace(old,new)
    if label=='displaced-swipe':
        change('if scrollView.contentOffset != centre { scrollView.setContentOffset(centre, animated: false) }','let _ = centre')
    elif label=='early-start':
        change('hasGeometry, sourceReady, layer ===','hasGeometry, layer ===')
    elif label=='moving-restore':
        change('if self.nativePictureInPictureRestoreRect == rect && self.nativePictureInPictureRestoreRectConfirmed {','if rect.width > 0 {')
    elif label=='offscreen-restore':
        change('rect.width > 0.0, rect.height > 0.0, rect.intersects(window.bounds)', 'rect.width > 0.0, rect.height > 0.0')
    elif label=='opaque-host':
        change('                self.videoNode?.backgroundColor = .clear','                self.videoNode?.backgroundColor = .black')
    elif label=='early-chrome':
        change('self.galleryNode.startNativePictureInPictureRestore()', 'self.galleryNode.startNativePictureInPictureRestore()\n                self.galleryNode.navigationBar?.alpha = 1.0')
    elif label=='server-close':
        change('        guard self.usesNativePictureInPictureSwipe else { return false }', '        guard self.usesNativePictureInPictureSwipe else { return false }\n        if self.context.currentAppConfiguration.with({ $0 }).data?["video_swipe_up_to_close"] as? Bool == true { return false }')
    elif label=='high-threshold':
        change('distance > min(80.0, scrollView.bounds.height / 8.0)', 'distance > scrollView.contentSize.height / 12.0')
    elif label=='no-rollback':
        change(block(text,'    func resetNativePictureInPictureTransition('), '    func resetNativePictureInPictureTransition(unlock: Bool) {}')
    elif label in ['sample-presentation','sample-animation']:
        unsafe='let _ = layer?.presentation()' if label=='sample-presentation' else 'layer?.add(CABasicAnimation(keyPath: "cornerRadius"), forKey: "unsafePiP")'
        change('        controller.startPictureInPicture()', '        '+unsafe+'\n        controller.startPictureInPicture()')
    return text


def execute(source, swiftc, temp):
    runs=[]
    for label in ['current','displaced-swipe','early-start','moving-restore','offscreen-restore','opaque-host','early-chrome','server-close','high-threshold','no-rollback','sample-presentation','sample-animation']:
        suite=temp/(label+'.swift');suite.write_text(variant(source,label))
        for optimized in [False,True]:
            name=label+('-O' if optimized else '-debug');binary=temp/name
            subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),str(suite),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if label=='current':
                assert result.returncode==0,result.stdout+result.stderr
                status=result.stdout.strip()
            else:
                assert result.returncode!=0 and ('PiP geometry regression:' in result.stderr or 'first PiP regression:' in result.stderr),label+result.stdout+result.stderr
                status='regression reproduced and rejected'
            runs.append(name+': '+status);print(runs[-1],flush=True)
    return runs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_playback_commands'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'round_caption_transport'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'repost_copy_integrity'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'native_pip_baseline'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'copy_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'rich_draft_upload_retry'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-pip-geometry-') as folder:
        temp=Path(folder)
        rejected=guard_checks(args.source,temp/'guards')
        runtime=temp/'runtime';runtime.mkdir()
        runs=execute(args.source,args.swiftc,runtime) if args.swiftc else []
        if args.swiftc:
            for name in PLAN['outputs']:
                subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/name)],check=True)
    report={'replacements':len(PLAN['outputs']),'guards':len(PLAN['guards']),'fail_closed':len(rejected),'executions':runs,'localization':'71 catalogs unchanged, no new strings','sdk':'not run','device':'pending','boundaries':'Production gesture/native-controller/restore logic is extracted verbatim. UIKit geometry/conversion, compositor, AVKit timing/KVO and window presentation are boundaries. Checks do not prove animation frame pacing on a physical iPhone.'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
