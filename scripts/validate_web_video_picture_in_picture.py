#!/usr/bin/env python3
"""Verify shared YouTube policy, retained web-player handoff and native isolation."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import web_video_picture_in_picture_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'web_video_picture_in_picture'
P = 'submodules/InstantPageUI/Sources/InstantPageGalleryController.swift'


def source_contract(source, plan):
    assert plan['required_previous_stage'] == 'app_font_selection'
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    assert set(plan['outputs']) == {runtime.G, runtime.U, P}
    assert not plan['copies'] and not plan['deletions']
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    before = {n: (ROOT / 'ios' / plan['previous'][n]).read_text() for n in plan['outputs']}
    after = {n: (source / n).read_text() for n in plan['outputs']}
    gallery_before, gallery_after = before[runtime.G], after[runtime.G]
    configuration = block(gallery_after, 'public struct GalleryConfiguration')
    original_configuration = block(gallery_before, 'public struct GalleryConfiguration')
    force = '''        // The existing PiP switch also overrides Telegram's YouTube server gate.
        if NagramiXTabSettings.videoPiPSwipeEnabled {
            return GalleryConfiguration(youtubePictureInPictureEnabled: true)
        }
'''
    assert configuration.replace(force, '', 1) == original_configuration
    assert gallery_after.replace(configuration, original_configuration, 1).replace('import NagramiXCore\n', '', 1) == gallery_before
    assert '"//submodules/NagramiXCore:NagramiXCore"' in (source / 'submodules/GalleryUI/BUILD').read_text()

    item_before, item_after = before[runtime.U], after[runtime.U]
    # The decoder, AVKit transaction/delegates, source clipping, background
    # capture, bounds and native transition state keep their exact prior bodies.
    for header in [
        'private final class NativePictureInPictureContentImpl',
        'private final class NagramiXNativePiPSourceClipping',
        'private struct NagramiXNativePiPVisualState',
        '    private func setupNativePictureInPicture()',
        '    override var usesNativePictureInPictureSwipe:',
        '    override func prepareForNativePictureInPictureSwipe()',
        '    private func nagramiXBeginNativePiPVisualTransition()',
        '    private func nagramiXFinishNativePiPVisualTransition(',
        '    private func nagramiXAwaitNativePiPPresentation(',
        '    override func centralityUpdated(',
        '    override func visibilityUpdated(',
    ]:
        assert block(item_after, header) == block(item_before, header), header

    for header, start, end in [
        ('    @objc func pictureInPictureButtonPressed()', '        if nagramiXUsesEmbeddedPictureInPicture(self.item) {', '        if self.nativePictureInPictureContent == nil'),
        ('    override func maybePerformActionForSwipeDismiss()', '        if NagramiXTabSettings.videoPiPSwipeEnabled, nagramiXUsesEmbeddedPictureInPicture(self.item) {', '        guard #available'),
        ('    override func activateAsInitial()', '        if self.item?.fromPlayingVideo == true, nagramiXUsesEmbeddedPictureInPicture(self.item) {', '        if let videoNode = self.videoNode'),
    ]:
        current, previous = block(item_after, header), block(item_before, header)
        begin, stop = current.index(start), current.index(end)
        assert current[:begin] + current[stop:] == previous, header
    current, previous = block(item_after, '    override func animateIn(from node:'), block(item_before, '    override func animateIn(from node:')
    addition = block(current, 'if nagramiXUsesEmbeddedPictureInPicture(self.item) {\n                self.skipInitialPause = true')
    assert current.replace('            ' + addition + '\n', '', 1) == previous

    transfer = block(item_after, '    private func expandIntoCustomPiP()')
    assert transfer.count('OverlayUniversalVideoNode(') == 1
    assert 'manager: context.sharedContext.mediaManager.universalVideoManager, content: item.content' in transfer
    assert 'mediaManager.hasOverlayVideoNode(overlayNode)' in transfer
    assert 'fromPlayingVideo: nagramiXUsesEmbeddedPictureInPicture(item)' in transfer
    assert 'self.beginCustomDismiss(nagramiXUsesEmbeddedPictureInPicture(item) ? .simpleAnimation : .default)' in transfer
    assert 'self.animateOut(toOverlay: overlayNode' in transfer
    start = block(item_after, '    private func nagramiXBeginWebPictureInPicture()')
    assert start.index('PlaceholderSuppressed(true)') < start.index('self.expandIntoCustomPiP()')
    assert 'DispatchQueue' not in start and 'WKWebView(' not in start and 'seek(' not in start
    assert 'self.context.sharedContext.mediaManager.overlayMediaManager.controller != nil' in start
    assert 'sharedContext.overlayMediaManager' not in start
    assert 'var mediaManager: MediaManager { get }' in (source / 'submodules/AccountContext/Sources/AccountContext.swift').read_text()
    assert 'var overlayMediaManager: OverlayMediaManager { get }' in (source / 'submodules/AccountContext/Sources/MediaManager.swift').read_text()
    animation = block(item_after, '    func animateOut(toOverlay node:')
    assert 'snapshotContentTree()!' not in animation
    assert 'let copyView = node.view.snapshotContentTree() else' in animation
    assert 'videoNode.bounds.width > 0.0' in animation
    assert 'transformedSelfFrame.height > 0.0' in animation

    # The instant-page restoration callback reuses its existing platform-video
    # API; it carries the live-playing flag, same entry and protection value.
    page = after[P]
    assert page.count('contentInfo: .webPage(webPage, embedWebpage, nil),') == 0
    assert page.count('centralIndex: 0, fromPlayingVideo: true, captureProtected: captureProtected') == 1
    assert page.count('InstantPageGalleryControllerPresentationArguments(transitionArguments:') == before[P].count('InstantPageGalleryControllerPresentationArguments(transitionArguments:') + 1
    assert 'open var hasAttachedContext: Bool = false' in (source / 'submodules/AccountContext/Sources/OverlayMediaItemNode.swift').read_text()
    manager = (source / 'submodules/TelegramUniversalVideoContent/Sources/UniversalVideoContentManager.swift').read_text()
    assert 'public func withUniversalVideoContent(id: AnyHashable, _ f: ((UniversalVideoContentNode & ASDisplayNode)?) -> Void)' in manager
    overlay = (source / 'submodules/TelegramUniversalVideoContent/Sources/OverlayUniversalVideoNode.swift').read_text()
    assert 'public var customClose: (() -> Void)?' in overlay
    assert 'priority: .overlay' in overlay
    assert 'contentNode.pause()' in (source / 'submodules/AccountContext/Sources/UniversalVideoNode.swift').read_text()
    flag = (source / 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift').read_text()
    assert 'UserDefaults.standard.object(forKey: Key.videoPiPSwipe) as? Bool ?? true' in flag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    source_contract(args.source, plan)
    initial = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='web-video-pip-') as temporary:
        folder = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, folder / 'guards')
        code = runtime.fixture(args.source)
        runs = execute(args.swiftc, folder, 'web-video-pip', code)
        for name, mutated, diagnostic in runtime.negatives(code):
            runs += execute(args.swiftc, folder, name, mutated, diagnostic)
        for name in plan['outputs']:
            run([args.swiftc, '-frontend', '-parse', args.source / name])
    assert manifest(args.source) == initial
    report = {
        'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
        'loader_refusals': len(refusals), 'executions': runs, 'swift_parse': len(plan['outputs']),
        'source_files': len(initial), 'source_unchanged_by_checks': True,
        'ghostgram_reference': 'ichmagmaus111/ghostgram@2a6b08272b7da893f88986846022bafd0727df89',
        'boundary': 'Real GalleryConfiguration and web policy, complete start method, button/swipe dispatch prefixes, close closure and restore activation guards execute unchanged with explicit media-manager, ownership and UIKit IO adapters. Native AVKit/delegates/backdrop/clipping/visibility bodies remain byte-identical; web content is handed to the existing in-app overlay with the same content ID. WebKit frame rendering, background OS PiP, network playback and touch animations require Apple SDK/device validation.',
        'apple_sdk': 'not_run', 'device': 'pending',
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
