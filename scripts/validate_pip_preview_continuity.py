#!/usr/bin/env python3
"""Check poster-only PiP backing, source geometry and reliable first restore/Back."""
import argparse
import json
import tempfile
from pathlib import Path

from validate_quick_format import block, manifest
from validate_pip_swipe_handoff import clean, G, U
from validate_private_temporary_transcription import execute
from validate_upstream_13_2_release import checked_plan, guard_checks, digest
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from pip_preview_continuity_runtime import poster_fixture, restore_fixture, D
from pip_preview_continuity_gallery import fixture as gallery_fixture
from pip_preview_continuity_apple import check as apple_check

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'pip_preview_continuity'


def negatives(poster, restore, gallery, previous):
    variants = [
        ('source-relayout', poster, 'guard !self.nagramiXPiPTransitionActive else { return }', 'guard !self.nagramiXPiPTransitionActive || self.validLayout != nil else { return }', 'PiP lease prevents client source rectangle animation'),
        ('corner-mask-during-handoff', poster, 'if self.nagramiXPiPTransitionActive {\n            self.nagramiXDeferredCorners', 'if self.nagramiXPiPTransitionActive && self.contentNode == nil {\n            self.nagramiXDeferredCorners', 'PiP lease cannot reintroduce a client corner mask'),
        ('missing-layer-completion', poster, 'guard !self.nagramiXPiPTransitionActive, let contentNode = self.contentNode else {\n            completion?()', 'guard !self.nagramiXPiPTransitionActive, let contentNode = self.contentNode else {\n            if self.contentNode != nil { completion?() }', 'missing content must complete gallery dismissal'),
        ('stale-restore-ack', restore, 'self.nagramiXRestoreGeneration == generation', 'generation > 0', 'old acknowledgement cannot finish a new restore'),
        ('early-source-cover', gallery, 'self.activePictureInPictureNavigationController = navigationController', '(controller as? GalleryController)?.nagramiXShowNativePiPBackdrop()\n                self.activePictureInPictureNavigationController = navigationController', 'live source stays uncovered until AVKit DidStart'),
        ('hidden-post-in-snapshot', gallery, 'self._hiddenMedia.set(.single(nil))\n        self.galleryNode.nagramiXSetNativePictureInPictureChatTransitionSuppressed(true)', 'self.galleryNode.nagramiXSetNativePictureInPictureChatTransitionSuppressed(true)', 'original post thumbnail is unhidden before screen capture'),
        ('preview-live-dismissal', gallery, 'let forceAway = forceAway || (self.galleryNode.pager.centralItemNode() as? UniversalVideoGalleryItemNode)?.nagramiXCanAnimateVideoDismissal == false', 'let forceAway = forceAway', 'preview Back does not animate or detach the active PiP source'),
        ('stale-dismissal-state', gallery, 'self.isDismissed = false', 'self.isDismissed = true', 'restored gallery clears old dismissal and scroll lock'),
    ]
    for name, code, old, new, diagnostic in variants:
        assert code.count(old) == 1, (name, code.count(old))
        yield name, code.replace(old, new, 1), diagnostic
    old = clean(block(previous, '    public func requestExpand()'))
    current = block(restore, '    func requestExpand()')
    yield 'original65-stop-without-ui', restore.replace(current, old, 1), 'first tap presents original gallery before stopping PiP'
    old = '            if self.nagramiXPreparePiPPreviewFallback() { return true }\n'
    assert gallery.count(old) == 3
    yield 'no-poster-fallback', gallery.replace(old, ''), 'uncapturable chat can use an actual poster-backed page'
    old = 'attemptSynchronously: true'
    assert poster.count(old) >= 3
    yield 'late-poster-render', poster.replace(old, 'attemptSynchronously: false'), 'cached poster requested synchronously before native animation'


def check(source, native, swiftc, folder, previous):
    fixtures = {'poster': poster_fixture(source), 'restore': restore_fixture(source), 'gallery': gallery_fixture(source)}
    runs = []
    for name, code in fixtures.items():
        runs += execute(swiftc, folder, 'pip-preview-' + name, code)
    for name, code, diagnostic in negatives(fixtures['poster'], fixtures['restore'], fixtures['gallery'], previous):
        runs += execute(swiftc, folder, name, code, diagnostic)
    framework = apple_check(source, swiftc, folder, native=native)
    u = (source / U).read_text()
    # Bind the tested lease to the real native entry, renderer return and cleanup.
    begin = block(u, '    private func nagramiXBeginNativePiPVisualTransition()')
    finish = block(u, '    private func nagramiXFinishNativePiPVisualTransition(')
    returned = block(u, '    private func nagramiXTryFinishNativePiPRestore()')
    assert begin.index('setNagramiXPiPTransitionActive(true)') < begin.index('NagramiXNativePiPSourceClipping(')
    assert finish.index('nagramiXPiPSourceClipping?.restore()') < finish.index('setNagramiXPiPTransitionActive(false)')
    assert returned.index('setNagramiXPiPTransitionActive(false)') < returned.index('canReveal(')
    assert 'presentationComplete && self.nagramiXPiPVisualState.hasStopped' in returned
    expand = block(u, '    func expandPIP()')
    assert 'nagramiXRestoreSystemWebPiP' in expand and 'if restored { self?.videoNode?.exitNativePictureInPicture() }' in expand
    native_expand = u[u.index('expand: { [weak self] completion in'):]
    native_expand = block(native_expand, 'expand: {')
    assert 'gallery.nagramiXPrepareNativePiPBackdrop()' not in native_expand
    assert native_expand.index('gallery.nagramiXPrepareNativePiPRestore()') < native_expand.index('window.present(')
    poster = block(u, 'private final class UniversalVideoGalleryItemPictureInPictureNode:')
    assert not any(marker in poster for marker in ['Embed_PlayingInPIP', 'ASTextNode', 'AVPlayer(', 'makeContentNode(', '.play(', '.seek('])
    return {'executions': runs, 'semantic_negative_variants': 11, 'native_lifecycle_bindings': 'passed', 'real_framework_probe': framework,
            'boundary': 'Actual full poster/decoration, restore transaction, native entry callbacks, backdrop preparation, dismissal and restored controls in Swift debug/optimized. UI, image decoding, animation and AVKit event delivery are explicit adapters. Pixel shape, actual PiP animation and physical iPhone remain unverified.',
            'full_application_sdk': 'pending', 'device': 'pending'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--swiftc', type=Path, required=True)
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'video_audio_continuity' and len(plan['inputs']) == 4 and not plan['copies']
    assert verified_prefix(a.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(a.source / name) == expected, name
    before = manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='pip-preview-continuity-') as d:
        folder = Path(d)
        refused = guard_checks(a.source, STAGE, plan, folder / 'guards')
        previous = (ROOT / 'ios' / plan['previous'][U]).read_text()
        result = check(a.source, a.source, a.swiftc, folder, previous)
        for name in plan['outputs']:
            import subprocess
            subprocess.run([str(a.swiftc), '-frontend', '-parse', str(a.source / name)], check=True)
    assert before == manifest(a.source)
    result.update(stage=STAGE, loader_refusals=len(refused), source_unchanged_by_checks=True)
    if a.report:
        a.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
