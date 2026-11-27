#!/usr/bin/env python3
"""Run the real watch-page bridge, playback controller and gallery replacement handshake."""
import argparse
from pathlib import Path
import tempfile

from system_web_picture_in_picture_runtime import CONTENT, GALLERY, WEB
from validate_local_copy_delivery import execute, run
from validate_pip_playback_focus import playback_host
from validate_quick_format import block
from validate_youtube_pip_readiness import TESTS
from validate_youtube_replay import CONTROLLER
from validate_youtube_watch_fallback import validate as validate_watch_page


def validate(source, swiftc, work):
    source = validate_watch_page(source, swiftc, work, 'youtube_watch_playback', 'NagramiXYoutubeWatchPlayback.swift')
    print(run(['node', TESTS / 'NagramiXYoutubeWatchPlayback.cjs', source / WEB]).stdout.strip(), flush=True)
    host = playback_host(source)
    availability = block((source / CONTROLLER).read_text(), 'public enum NagramiXYoutubeAvailability:')
    host = host.replace('enum Availability { case loading, playable, unavailable }',
                        availability.replace('public enum NagramiXYoutubeAvailability:', 'enum Availability:'))
    interface = block((source / CONTENT).read_text(), 'public protocol NagramiXYoutubePlaybackSource:')
    host += '\n' + interface.replace('public protocol', 'protocol').replace('NagramiXYoutubeAvailability, NoError', 'Availability')
    gallery = (source / GALLERY).read_text()
    properties = block(gallery, '    private var nagramiXUsesWatchControls:').replace('private var', 'var')
    source_field = next(line.strip() for line in gallery.splitlines() if 'weak var nagramiXYoutubeSource:' in line)
    host = host.replace(' var isLivePhoto', properties + '\n' + source_field.replace('private ', '') + '\n var isLivePhoto', 1)
    host = host.replace('        checkPlaybackFocus()', '        checkWatchReplacement()\n        checkPlaybackFocus()', 1)
    host += '\n' + (TESTS / 'NagramiXYoutubeWatchReplacement.swift').read_text()
    for result in execute(swiftc, work, 'WatchReplacement', host):
        print(result['mode'], result['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='youtube-watch-playback-') as directory:
        validate(args.source, args.swiftc, Path(directory))
