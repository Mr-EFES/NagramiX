#!/usr/bin/env python3
"""Check held video limits, completed preview and exactly-once round-video sends."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from round_recording_completion_runtime import CHAT, PANEL, SCREEN, fixture
from validate_private_temporary_transcription import execute
from validate_quick_format import block
from validate_release_095_apple_preflight import canonical_projection
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks

STAGE = 'round_recording_completion'


def validate(source, swiftc, folder):
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'youtube_watch_replacement'
    assert set(plan['inputs']) == {SCREEN, PANEL, CHAT}
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    for name in plan['outputs']:
        subprocess.run([str(swiftc), '-frontend', '-parse', str(source / name)], check=True)
    rejected = guard_checks(source, STAGE, plan, folder / 'guards')
    before = {n: (OVERLAY / t).read_text() for n, t in plan['previous'].items()}
    after = {n: (source / n).read_text() for n in plan['outputs']}

    # The hardware recorder, encoding settings, duration limit, result snapshots
    # and export/enqueue algorithm keep their real bodies at this stage.
    for marker in ['private func nagramiXStopWriter(', 'private func nagramiXFinishStop(',
                   'func startVideoRecording(pressing:', 'func addCaptureResult(',
                   'private var currentResults:', 'public func takenRecordedData()']:
        assert block(before[SCREEN], marker) == block(after[SCREEN], marker), marker
    send = '    public func sendVideoRecording('
    boundary = '            var videoPaths: [String] = []'
    assert block(before[SCREEN], send).split(boundary, 1)[1] == block(after[SCREEN], send).split(boundary, 1)[1]
    assert after[SCREEN].count('if duration > 59.5 { controller.onStop() }') == 1
    assert 'if totalDuration > 59.5 {' in after[SCREEN]
    assert block(before[CHAT], '    func sendMediaRecording(') == block(after[CHAT], '    func sendMediaRecording(')

    for group, diagnostic in [('release', 'late touch preserves the video at the limit'),
                              ('stop', 'repeated stop is ignored while finalizing'),
                              ('send', 'Send immediately after stop is accepted')]:
        for result in execute(swiftc, folder, 'Previous-' + group, fixture(source, group, before), diagnostic):
            print(result['mode'], group, 'previous regression reproduced', flush=True)
    for result in execute(swiftc, folder, 'RoundRecordingCompletion', fixture(source)):
        print(result['mode'], result['output'], flush=True)
    print('Guard checks passed:', len(rejected), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='round-recording-completion-') as temporary:
        folder = Path(temporary)
        source = args.source
        if args.canonical:
            source = folder / 'source'
            canonical_projection(source, STAGE)
        validate(source, args.swiftc, folder)


if __name__ == '__main__':
    main()
