#!/usr/bin/env python3
"""Native Telegram PiP fade, independent surface swipe and YouTube button capability."""
import argparse
import json
import tempfile
from pathlib import Path
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from late_source_stages import verified_prefix, LATE_SOURCE_STAGES
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from validate_pip_swipe_handoff import U, G, N
from system_web_picture_in_picture_runtime import WEB, script
from pip_transition_coordinator_runtime import poster_fixture, native_fixture
from youtube_background_continuity_js import check as youtube_js_check
from native_pip_refinement_apple import check as apple_check
import native_pip_refinement_runtime as rt

STAGE = 'native_pip_refinement'


def contracts(source):
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'tab_visibility_sync'
    assert set(plan['inputs']) == {U, WEB} and len(plan['guards']) == 22
    assert not plan['copies'] and not plan['deletions']
    u = (source / U).read_text()
    before = (OVERLAY / plan['previous'][U]).read_text()
    # Decode, audio commands, playback identity, preview and return readiness stay native/existing.
    for marker in ['@available(iOS 15.0, *)\nprivate final class NativePictureInPictureContentImpl:',
                   'private enum NagramiXPiPVideoGeometry', 'private struct NagramiXNativePiPVisualState',
                   'private final class UniversalVideoGalleryItemPictureInPictureNode:',
                   '    private func nagramiXUpdateBackgroundVideoPlayback()',
                   '    private func nagramiXApplyVideoDimensions(',
                   '    private func nagramiXCanUsePiPSourceLayer(',
                   '    private func nagramiXAwaitNativePiPPresentation(']:
        assert block(u, marker) == block(before, marker), marker
    web_before = (OVERLAY / plan['previous'][WEB]).read_text()
    assert (source / WEB).read_text() == web_before.replace('pipEnabled: NagramiXTabSettings.videoPiPSwipeEnabled', 'pipEnabled: true')
    assert script(source) == script_from_text(web_before), 'JS or source extraction changed'
    assert 'videoPiPSwipeEnabled' not in block(u, 'private func nagramiXCanOfferWebPictureInPicture(')
    assert 'videoPiPSwipeEnabled' in block(u, '    override var usesNativePictureInPictureSwipe:')
    for marker in ['    @objc func pictureInPictureButtonPressed()', '    override func maybePerformActionForSwipeDismiss()', '    @objc private func nagramiXUpwardPiPSwipe(']:
        assert 'self.nagramiXRequestPictureInPicture()' in block(u, marker)
    assert 'nagramiXShowNativePiPBackdrop' not in block(u, '    private func nagramiXCommitPiPHandoff(')
    assert 'nagramiXBeginPiPHandoff(controller)' not in block(u, '    private func nagramiXBeginWebPictureInPicture()')
    assert 'self.nagramiXBeginPiPHandoff(controller)' in block(block(u, '    private func setupNativePictureInPicture()'), 'willBegin: {')
    assert 'isPictureInPicturePossible' in block(u, '    var canBeginPictureInPicture:')
    assert 'nagramiXCanUsePiPSourceLayer' not in block(u, '    private func nagramiXTryStartPictureInPicture()')
    assert 'self.scrollNode.view.addGestureRecognizer(pipSwipe)' in u
    assert 'snapshotView' not in block(u, '    private func nagramiXBeginPiPHandoff(')
    return {'existing_players_and_decoder_unchanged': True, 'native_will_start_fade_duration_seconds': 0.2,
            'one_button_swipe_request': True, 'surface_gesture_independent_of_outer_scroll_offset': True,
            'root_and_inner_clipping_restored': True, 'avkit_admits_all_source_aspect_ratios': True,
            'entry_does_not_wait_for_restore_snapshot_readiness': True, 'youtube_button_independent_of_swipe_preference': True,
            'background_audio_pause_interruption_and_js_policy_unchanged': True,
            'new_strings_dependencies_and_app_files': 0, 'server_drm_entitlement_bypass': False}


def script_from_text(text):
    return text.split('    private static let script = #"""\n', 1)[1].split('\n"""#', 1)[0]


def check(source, swiftc, folder):
    folder.mkdir(parents=True, exist_ok=True)
    contract = contracts(source)
    api = apple_check(source, swiftc, folder / 'apple')
    bodies = {'transition': rt.lifecycle(source), 'clipping': rt.clipping(source), 'gesture': rt.gesture(source),
              'youtube': rt.youtube(source), 'eligibility': rt.eligibility(source),
              'native-delegates': native_fixture(source), 'poster': poster_fixture(source)}
    runs = []
    for name, code in bodies.items():
        runs += execute(swiftc, folder, 'native-pip-' + name, code)
    variants = [
        ('late-native-fade', 'transition', 'didExpand = false\n                self.nagramiXBeginPiPHandoff(controller)', 'didExpand = false', 'native fade starts before DidStart'),
        ('invisible-web-probe', 'transition', 'guard videoNode.enterNativePictureInPicture() else {\n            self.nagramiXFinishSystemWebPiP(stop: true)\n            return false\n        }', 'guard videoNode.enterNativePictureInPicture() else {\n            self.nagramiXFinishSystemWebPiP(stop: true)\n            return false\n        }\n        self.nagramiXBeginPiPHandoff(controller)', 'WebKit source stays visible during asynchronous probe'),
        ('snapshot-gates-entry', 'transition', 'self.videoNode?.getVideoLayer() != nil else { return }', 'self.videoNode?.getVideoLayer()?.isReadyForDisplay == true else { return }', 'native fade starts before DidStart'),
        ('early-detach', 'transition', 'self.nagramiXPiPHandoffFadeFinished, !self.nagramiXPiPHandoffCompleted,', 'true, !self.nagramiXPiPHandoffCompleted,', 'DidStart alone does not cut off native fade'),
        ('stale-fade', 'transition', 'generation == self.nagramiXPiPHandoffGeneration,\n                  self.nagramiXPiPHandoffStarted', 'generation >= 0,\n                  true', 'failed native/web start restores'),
        ('root-still-clips', 'clipping', 'ancestors.append(root)', 'if false { ancestors.append(root) }', 'root and inner upper/lower edges'),
        ('root-not-restored', 'clipping', '(!entry.requiresSameParent || layer.superlayer === entry.parent)', '(layer.superlayer === entry.parent)', 'root restored even after gallery reparenting'),
        ('downward-swipe', 'gesture', 'velocity.y < 0.0 && -velocity.y', 'velocity.y > 0.0 && -velocity.y', 'upward vertical pan admitted'),
        ('cancel-native-touches', 'gesture', 'self.cancelsTouchesInView = false', 'self.cancelsTouchesInView = true', 'one-finger observer does not cancel'),
        ('repeated-pan-request', 'gesture', 'guard !recognizer.requested else { return }', 'if recognizer.requested {}', 'one pan submits at most one request'),
        ('active-pan-reset', 'transition', 'if self.nagramiXPiPVisualState.phase == .active || self.nagramiXPiPVisualState.phase == .restoring { return false }', '', 'ongoing swipe after DidStart cannot reset source geometry'),
        ('control-interception', 'gesture', 'if current is UIControl { return false }', 'if current is UIControl { return true }', 'native button descendants excluded'),
        ('swipe-revokes-button', 'youtube', 'pipEnabled: true', 'pipEnabled: NagramiXTabSettings.videoPiPSwipeEnabled', 'only YouTube receives client PiP override'),
    ]
    negatives = []
    for name, body, old, new, diagnostic in variants:
        code = bodies[body]
        assert old in code, name
        negatives += execute(swiftc, folder, name, code.replace(old, new), diagnostic)
    javascript = youtube_js_check(source, folder / 'youtube-dom')
    for path in checked_plan(STAGE)['inputs']:
        run([swiftc, '-frontend', '-parse', source / path])
    return {'contracts': contract, 'executions': runs, 'semantic_negatives': negatives,
            'youtube_document_start_script': javascript, 'apple_api': api,
            'boundary': 'Actual handlers/delegates/bridge/DOM script; controllable UIKit/AVKit/navigation/clock and image hosts. No pixel or live iPhone/YouTube claim.',
            'full_application_sdk': 'not_run', 'physical_iphone': 'pending'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    before = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='native-pip-check-') as temporary:
        folder = Path(temporary)
        refused = guard_checks(args.source, STAGE, checked_plan(STAGE), folder / 'guards')
        result = check(args.source, args.swiftc, folder / 'runtime')
    assert before == manifest(args.source)
    report = {'stage': 104, 'name': STAGE, 'loader_refusals': len(refused), 'checks': result, 'source_unchanged_by_checks': True}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
