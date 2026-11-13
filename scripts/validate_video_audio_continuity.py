#!/usr/bin/env python3
"""Check video audio activation, output restoration and system YouTube PiP continuity."""
import argparse
import json
import tempfile
from pathlib import Path

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_quick_format import manifest
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from system_web_picture_in_picture_runtime import WEB
from video_audio_continuity_apple import check as apple_check
from youtube_playback_policy_js import check as policy_js
from video_audio_continuity_js import check as continuity_js
from video_audio_continuity_runtime import fixture, AUDIO

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'video_audio_continuity'


def negatives(code):
    for name, old, new, diagnostic in [
        ('clock-before-audio', '&& !nagramiXWaitingForAudio', '&& (nagramiXWaitingForAudio || true)', 'shared video clock waits for enabled audio'),
        ('cached-route-only', '|| nagramiXPlaybackNeedsConfiguration {', '|| (nagramiXPlaybackNeedsConfiguration && false) {', 'actual session drift must repair cached playback mode'),
        ('stale-web-activation', 'self.nagramiXAudioGeneration == generation, self.nagramiXHasManagedAudio', 'generation > 0, self.nagramiXHasManagedAudio', 'old lease callback cannot start a new request'),
        ('stale-native-activation', 'self.nagramiXAudioSessionGeneration == generation', 'generation > 0', 'stale audio acquisition cannot resurrect old renderer'),
        ('idle-drop-during-pip', 'value && strongSelf.nagramiXMayReleaseIdleAudio', 'value', 'delayed idle release rechecks current PiP and background ownership'),
        ('separate-category-mode', 'if case .play = type {', 'if case .record(false, false, false) = type {', 'playback restores incompatible category and mode atomically'),
        ('preload-audio-takeover', 'self.nagramiXPlaybackRequested && whilePlaying', 'whilePlaying', "initial preload buffering cannot steal another video's audio"),
        ('paused-ordinary-audio-lease', 'nagramiXVideoNowPlayingRegistry.preferred(backgroundEnabled: false)', 'nagramiXVideoNowPlayingRegistry.preferred(backgroundEnabled: true)', 'paused ordinary Now Playing entry cannot retain an idle session'),
    ]:
        assert code.count(old) == 1, (name, code.count(old))
        yield name, code.replace(old, new, 1), diagnostic


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--swiftc', type=Path, required=True)
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'font_apply_node_lifecycle'
    assert len(plan['inputs']) == 5 and len(plan['guards']) == 16 and not plan['copies']
    assert verified_prefix(a.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(a.source / name) == expected, name
    snapshot = manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='video-audio-continuity-') as d:
        folder = Path(d)
        refusals = guard_checks(a.source, STAGE, plan, folder / 'guards')
        code = fixture(a.source)
        runs = execute(a.swiftc, folder, 'video-audio-continuity', code)
        for name, mutated, diagnostic in negatives(code):
            runs += execute(a.swiftc, folder, name, mutated, diagnostic)
        javascript = continuity_js(a.source, folder)
        before = (ROOT / 'ios' / plan['previous'][WEB]).read_text()
        marker = '    private static let script = #"""\n'
        old_script = before.split(marker, 1)[1].split('\n"""#', 1)[0]
        regression = continuity_js(a.source, folder, old_script)
        previous = policy_js(a.source, folder)
        apple = apple_check(a.source, a.swiftc, folder)
        for name in plan['outputs']:
            run([a.swiftc, '-frontend', '-parse', a.source / name])
        # This stage deliberately does not alter the voice/round-specific route.
        old = (ROOT / 'ios' / plan['previous'][AUDIO]).read_text()
        new = (a.source / AUDIO).read_text()
        assert old.split('    private func setupOutputMode(', 1)[1] == new.split('    private func setupOutputMode(', 1)[1]
    assert snapshot == manifest(a.source)
    report = {'stage': STAGE, 'loader_refusals': len(refusals), 'executions': runs,
              'javascript': javascript, 'original54_regression': regression,
              'previous_youtube_contracts': previous, 'real_avkit_webkit': apple,
              'source_unchanged_by_checks': True, 'voice_round_output_routing_unchanged': True,
              'boundary': 'Actual production ownership/clock/configuration fragments in Swift debug and optimized runs, with explicit scheduler/audio/renderer adapters. Actual full injected script in Node. UIKit/AVFoundation hardware, real streams and physical iPhone not exercised on Linux.',
              'full_application_sdk': 'pending', 'device': 'pending'}
    if a.report:
        a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
