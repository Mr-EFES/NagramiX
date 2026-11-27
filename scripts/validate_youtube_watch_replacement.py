#!/usr/bin/env python3
"""Check delayed PiP entry and sound continuity when YouTube replaces the watch player."""
import argparse
from pathlib import Path
import tempfile

from system_web_picture_in_picture_runtime import WEB
from validate_local_copy_delivery import run
from validate_youtube_pip_readiness import TESTS
from validate_youtube_watch_fallback import validate


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='youtube-watch-replacement-') as directory:
        source = validate(args.source, args.swiftc, Path(directory), 'youtube_watch_replacement',
                          'NagramiXYoutubeWatchContinuity.swift')
        print(run(['node', TESTS / 'NagramiXYoutubeWatchContinuity.cjs', source / WEB]).stdout.strip())
        print(run(['node', TESTS / 'NagramiXYoutubeWatchReplacement.cjs', source / WEB]).stdout.strip())
