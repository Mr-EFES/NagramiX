#!/usr/bin/env python3
"""Проверить системный PiP, rollback свайпа и фактическую готовность возврата."""
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

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'pip_visual_handoff_patches.json').read_text())
FILES = list(PLAN['inputs'])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name

    # Revert only the approved regions, then compare the whole files. Export,
    # archive, captions, download settings and all other gallery code stay exact.
    for index, name in enumerate(FILES):
        before = (OVERLAY / PLAN['previous'][name]).read_text()
        after = (source / name).read_text()
        restored = after
        if index == 0:
            markers = ['private final class NativePictureInPictureContentImpl:', 'private func setupNativePictureInPicture(',
                       'func pictureInPictureButtonPressed(', 'override func maybePerformActionForSwipeDismiss(',
                       'override func centralityUpdated(', 'override func visibilityUpdated(']
            for marker in markers:
                restored = restored.replace(block(restored, marker), block(before, marker))
            readiness = block(restored, '    override var isReadyForNativePictureInPictureRestore:')
            restored = restored.replace(readiness + '\n\n', '')
            for line in ['    private var nativePictureInPicturePrepared = false\n',
                         '    private var nativePictureInPictureWasSwipe = false\n',
                         '    private var nativePictureInPictureControlAlpha: (CGFloat?, CGFloat)?\n']:
                assert restored.count(line) == 1
                restored = restored.replace(line, '')
            restored = restored.replace(' || self.nativePictureInPicturePrepared', '')
        elif index == 1:
            start = restored.index('    private struct NativePictureInPictureAppearance')
            end = restored.index('    private var presentationState =', start)
            restored = restored[:start] + restored[end:]
            for marker in ['open func containerLayoutUpdated(', 'open func scrollViewDidScroll(', 'open func scrollViewWillEndDragging(']:
                restored = restored.replace(block(restored, marker), block(before, marker))
        elif index == 2:
            start = restored.index('    private var nativePictureInPictureRestoreCompletion')
            end = restored.index('    private let _hiddenMedia =', start)
            restored = restored[:start] + restored[end:]
            for marker in ['deinit {', 'self.galleryNode.completeCustomDismiss =', 'override public func viewDidAppear(', 'override public func containerLayoutUpdated(']:
                restored = restored.replace(block(restored, marker), block(before, marker))
        else:
            readiness = block(restored, '    open var isReadyForNativePictureInPictureRestore:')
            restored = restored.replace(readiness + '\n\n', '')
        assert restored == before, 'Unrelated code changed: ' + name

    text = (source / FILES[0]).read_text()
    native = block(text, 'private final class NativePictureInPictureContentImpl:')
    assert text.count('AVPictureInPictureController(contentSource:') == 1
    for forbidden in ['SourceAppearance', '.presentation(', 'CABasicAnimation(', 'AVPlayer(', 'UIWindow(', '.cornerRadius =', '.masksToBounds =', '.videoGravity =', '.bounds =', '.flush(']:
        assert forbidden not in native, forbidden
    assert 'layer.superlayer != nil' in native and 'self.node.view.window != nil' in native
    assert 'init(layer:' not in block((source / 'submodules/MediaPlayer/Sources/MediaPlayerNode.swift').read_text(), 'private final class MediaPlayerNodeLayer:')
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_local_model_menu(') < pipeline.index('    apply_pip_visual_handoff(')
    assert catalog_contract(source) == (71, 613)
    source_contract(source)


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('pip_visual_handoff', OVERLAY / 'pip_visual_handoff.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []

    def seed(label):
        tree = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name).read_bytes())
        return tree

    def reject(tree, label, overlay=OVERLAY):
        previous = manifest(tree)
        try:
            module.apply_pip_visual_handoff(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == previous, 'Partial mutation: ' + label
        rejected.append(label)

    valid = seed('valid')
    module.apply_pip_visual_handoff(valid, OVERLAY)
    for name in PLAN['outputs']:
        assert (valid / name).read_bytes() == (source / name).read_bytes()
    reject(valid, 'repeat')
    for i, name in enumerate({**PLAN['inputs'], **PLAN['guards']}):
        for kind in ['missing', 'drift']:
            tree = seed(str(i) + '-' + kind)
            if kind == 'missing': (tree / name).unlink()
            else: (tree / name).write_bytes(b'changed')
            reject(tree, kind + ' ' + name)
    variants = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        variants.append((field, bad))
    for field in ['previous', 'replacements']:
        bad = copy.deepcopy(PLAN); bad[field][FILES[0]] = '../outside.swift'
        variants.append((field, bad))
    bad = copy.deepcopy(PLAN); bad['outputs'].clear(); variants.append(('inconsistent', bad))
    for label, bad in variants:
        overlay = temp / ('overlay-' + label)
        for name in PLAN['templates']:
            path = overlay / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / name).read_bytes())
        (overlay / 'pip_visual_handoff_patches.json').write_text(json.dumps(bad))
        reject(seed('source-' + label), label, overlay)
    for i, name in enumerate([FILES[0], next(iter(PLAN['guards']))]):
        tree = seed('symlink-' + str(i)); path = tree / name
        outside = temp / ('external-' + str(i)); outside.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(outside)
        reject(tree, 'external symlink ' + name)
    return rejected


def clean(t):
    return t.replace('private ','').replace('public ','').replace('open ','').replace('@objc ','')

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
        'override func centralityUpdated(', 'override func visibilityUpdated(', 'override var isReadyForNativePictureInPictureRestore:'])
    methods=clean(methods).replace('UniversalVideoGalleryItemNode','GalleryHarness')
    node_methods=clean('\n'.join(block(node,m) for m in ['open func scrollViewDidScroll(', 'open func scrollViewWillEndDragging(']))
    appear=clean(block(gallery,'override public func viewDidAppear('))
    begin=clean(block(gallery,'self.galleryNode.beginCustomDismiss ='))
    complete=clean(block(gallery,'self.galleryNode.completeCustomDismiss ='))
    return '\n'.join([
        (ROOT/'scripts/tests/NagramiXPiPVisualTransitionBoundary.swift').read_text(),native,
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
    var nativePictureInPictureControlAlpha: (CGFloat?,CGFloat)?
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
''',methods,'}',(ROOT/'scripts/tests/NagramiXPiPVisualTransitionTests.swift').read_text()])


def runtime_variant(source, label):
    text = runtime_source(source)

    def change(old, new):
        nonlocal text
        assert text.count(old) == 1, (label, old[:80], text.count(old))
        text = text.replace(old, new)

    if label == 'no-freeze':
        change('                controller.prepareNativePictureInPictureTransition()', '')
    elif label == 'pre-frame':
        change(' && self.hasVisibleSource($0)', '')
    elif label == 'forced-clip':
        change('        controller.startPictureInPicture()', '        layer?.cornerRadius = 6.0\n        layer?.masksToBounds = true\n        controller.startPictureInPicture()')
    elif label == 'early-restore':
        change(block(text, '    func tryCompleteNativePictureInPictureRestore()'), '    func tryCompleteNativePictureInPictureRestore() { self.completeNativePictureInPictureRestore(true) }')
    elif label == 'root-fade':
        change('                self.beginCustomDismiss(.pip)', '                self.activePictureInPictureController?.view.alpha = 0.0\n                self.beginCustomDismiss(.pip)')
    elif label == 'lost-hidden':
        change('if self.hiddenMediaManagerIndex == nil, let hiddenMedia', 'if !"".isEmpty, self.hiddenMediaManagerIndex == nil, let hiddenMedia')
    elif label == 'toggle':
        marker = 'func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, setPlaying playing: Bool)'
        change(block(text, marker), marker + ' { self.node.togglePlayPause() }')
    elif label == 'no-rollback':
        change(block(text, '    func resetNativePictureInPictureTransition('), '    func resetNativePictureInPictureTransition(unlock: Bool) {}')
    elif label == 'detach-active':
        assert text.count('content.keepsVideoAttached {') == 2
        text = text.replace('content.keepsVideoAttached {', 'content.hasPendingPictureInPictureStart {')
    elif label == 'late-appearance':
        change(block(text, 'if self.nativePictureInPictureRestoreAbandoned {'), 'if self.nativePictureInPictureRestoreAbandoned { self.nativePictureInPictureRestoreAbandoned = false }')
    elif label == 'stale-layout':
        change('guard self.nativePictureInPictureRestoreCompletion != nil, !self.nativePictureInPictureRestoreCheckingLayout else { return }',
               'guard self.nativePictureInPictureRestoreCompletion != nil else { return }')
        change(block(text, 'if self.nativePictureInPictureRestoreAppeared, self.view.window != nil {'), '')
        change('            self.completeNativePictureInPictureRestore(true)',
               '            self.view.layoutIfNeeded()\n            self.completeNativePictureInPictureRestore(true)')
    elif label in ['sample-presentation', 'sample-animation']:
        unsafe = 'let _ = layer?.presentation()' if label == 'sample-presentation' else 'layer?.add(CABasicAnimation(keyPath: "cornerRadius"), forKey: "unsafePiP")'
        change('        controller.startPictureInPicture()', '        ' + unsafe + '\n        controller.startPictureInPicture()')
    return text


def execute(source, swiftc, temp):
    runs = []
    modes = ['current', 'no-freeze', 'pre-frame', 'forced-clip', 'early-restore', 'root-fade', 'lost-hidden', 'toggle', 'no-rollback', 'detach-active', 'late-appearance', 'stale-layout', 'sample-presentation', 'sample-animation']
    for mode in modes:
        suite = temp / (mode + '.swift'); suite.write_text(runtime_variant(source, mode))
        for optimized in [False, True]:
            name = mode + ('-O' if optimized else '-debug'); binary = temp / name
            subprocess.run([str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), *(['-O'] if optimized else []), str(suite), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if mode == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                message = result.stdout.strip()
            else:
                assert result.returncode != 0 and ('PiP visual transition regression:' in result.stderr or 'first PiP regression:' in result.stderr), mode + result.stdout + result.stderr
                if mode.startswith('sample-'):
                    assert 'unsupported' in result.stderr and 'copy' in result.stderr, result.stderr
                message = 'regression reproduced and rejected'
            print(name + ': ' + message, flush=True)
            runs.append(name + ': ' + message)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'rich_draft_upload_retry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_transition_geometry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'transfer_consistency'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'editor_attachment_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_size'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_effect'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-pip-visual-handoff-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp)
        runs = execute(args.source, args.swiftc, temp) if args.swiftc else []
        if args.swiftc:
            for name in PLAN['outputs']:
                subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'replacements': len(PLAN['outputs']), 'guards': len(PLAN['guards']), 'fail_closed': len(rejected), 'executions': runs,
              'localization': '71 languages × 613 keys, no new strings', 'sdk': 'not run', 'device': 'pending',
              'boundaries': 'Actual native controller, playback delegate, setup/button/swipe/centrality/visibility, full scroll delegates, visual rollback, gallery restore helpers/viewDidAppear and hidden-media release closures. UIKit rendering, AVKit/KVO, scheduler, account/window IO and player are doubles. Source layer appearance/geometry is never mutated.'}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
