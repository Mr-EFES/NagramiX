#!/usr/bin/env python3
"""Проверить стартовую геометрию архивного кружка и прежние player-контракты."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import execute, run
import round_native_playback_runtime as player
import round_replacement_geometry_runtime as geometry

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'round_replacement_geometry'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'ghostgram_authorless_transport'
    assert set(plan['outputs']) == {player.ROUND}
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    current = (args.source / player.ROUND).read_text()
    previous = (ROOT / 'ios' / plan['previous'][player.ROUND]).read_text()
    for marker in ('    private func activateVideoPlayback()', '    private func updateStatus(',
                   '    public var isPlaying:', '    private func transcribe()'):
        assert block(current, marker) == block(previous, marker), marker
    assert current.index('let previousVideoGeometry = previousVideoNode.map') < current.index('videoNode.canAttachContent = false')
    assert current.index('if nagramiXPrepareInstantVideoReplacement(videoNode,') < current.index('videoNode.canAttachContent = strongSelf.shouldAcquireVideoContext')
    marker = '                    if let videoNode = strongSelf.videoNode {'
    before = previous.index(marker, previous.index('                    if case .customChatContents'))
    after = current.index(marker, current.index('                    if case .customChatContents'))
    end = '                    animation.animator.updateFrame(layer: strongSelf.secretVideoPlaceholderBackground'
    assert previous[before:previous.index(end, before)] == current[after:current.index(end, after)]
    initial = manifest(args.source)
    fixtures = {key: getattr(player, key)(args.source) for key in ['ownership', 'recording', 'presentation', 'activation']}
    with tempfile.TemporaryDirectory(prefix='round-replacement-') as temporary:
        root = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, root / 'guards')
        text = geometry.fixture(args.source)
        results = execute(args.swiftc, root, 'geometry', text)
        for name, mutated, diagnostic in geometry.negatives(text):
            results += execute(args.swiftc, root, name, mutated, diagnostic)
        for name, fixture in fixtures.items():
            results += execute(args.swiftc, root, name, fixture)
        run([args.swiftc, '-frontend', '-parse', args.source / player.ROUND])
    assert manifest(args.source) == initial
    result = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']), 'loader_refusals': len(refusals),
              'executions': results, 'swift_parse': 1,
              'reference': {'repository': 'ichmagmaus111/ghostgram', 'commit': '2a6b08272b7da893f88986846022bafd0727df89',
                            'round_blob': '9c9c3c62f5e120e490980290afa19dc1f015fe70', 'voice_blob': 'bbf704e505d1ddac5d0c91b5402b1a4d68ea5190'},
              'boundary': 'Actual replacement snapshot/removal/preparation/attachment/final-layout code plus native content manager ownership, retained activation, capture gates and cover/footer code. UIKit layers, frame timing, network and decoder pixels are explicit adapters; physical video is pending.',
              'apple_sdk': 'not_run', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
