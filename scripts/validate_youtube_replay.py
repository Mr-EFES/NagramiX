#!/usr/bin/env python3
"""Exercise the current YouTube controller through a complete second playback."""
import argparse
from pathlib import Path
import shutil
import tempfile

from late_source_stages import OVERLAY
from validate_local_copy_delivery import execute, run
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_youtube_pip_readiness import TESTS, youtube_controller_host

STAGE = 'youtube_replay'
CONTROLLER = 'submodules/TelegramUniversalVideoContent/Sources/YoutubeEmbedImplementation.swift'


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    if source is None:
        source = work / 'source'
        for name, template in {**plan['replacements'], **plan['guard_sources']}.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OVERLAY / template, path)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    guard_checks(source, STAGE, plan, work / 'guards')
    run([swiftc, '-frontend', '-parse', source / CONTROLLER])
    for name in plan['guards']:
        shutil.copy(source / name, work)
    controller = youtube_controller_host((source / CONTROLLER).read_text())
    for suite in ('NagramiXYoutubeReplay', 'NagramiXYoutubePiPReadiness'):
        for result in execute(swiftc, work, suite, controller + (TESTS / (suite + '.swift')).read_text()):
            print(result['mode'], result['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='youtube-replay-') as directory:
        validate(args.source, args.swiftc, Path(directory))
