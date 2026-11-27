#!/usr/bin/env python3
"""Check the embedded-to-watch handoff, gallery layout and real WebKit bridge."""
import argparse
from pathlib import Path
import shutil
import sys
import tempfile

from late_source_stages import OVERLAY
from system_web_picture_in_picture_runtime import CONTENT, GALLERY, WEB
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_youtube_pip_readiness import TESTS, youtube_controller_host
from validate_youtube_replay import CONTROLLER

STAGE = 'youtube_watch_fallback'


def validate(source, swiftc, work, stage=STAGE, fixture='NagramiXYoutubeWatchFallback.swift'):
    plan = checked_plan(stage)
    if source is None:
        source = work / 'source'
        for name, template in {**plan['replacements'], **plan['guard_sources']}.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OVERLAY / template, path)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
        if name.endswith('.swift'):
            run([swiftc, '-frontend', '-parse', source / name])
    guard_checks(source, stage, plan, work / 'guards')
    for name in plan['guards']:
        shutil.copy(source / name, work)
    gallery = (source / GALLERY).read_text()
    assert 'nagramiXRetryYoutube' not in gallery
    assert gallery.count('#selector(self.nagramiXOpenYoutube)') == 1
    assert 'playbackControlsIsVisible = false' in block(gallery, 'if !self.controlsVisibility() || hideControls ||')
    assert 'self.statusButtonNode.alpha = self.nagramiXUsesWatchControls ? 0.0 : 1.0' in gallery
    assert 'self?.playerNode.updateYoutubeSurface(value)' in (source / CONTENT).read_text()
    controller = youtube_controller_host((source / CONTROLLER).read_text())
    geometry = '\n'.join(block(gallery, '    private static func ' + name).replace('private static', 'static', 1)
                         for name in ('nagramiXWatchViewport', 'nagramiXFeedbackFrame'))
    host = '#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n' + controller + '\nenum Feedback {\n' + geometry + '\n}\n'
    for result in execute(swiftc, work, 'WatchFallback', host + (TESTS / fixture).read_text()):
        print(result['mode'], result['output'], flush=True)
    print(run(['node', TESTS / 'NagramiXYoutubeWatchPage.cjs', source / WEB]).stdout.strip())
    if sys.platform == 'darwin':
        web = (source / WEB).read_text()
        bridge = web[web.index('private final class NagramiXWebSystemPictureInPicture:'):]
        path = work / 'WebKitBridge.swift'
        path.write_text('import UIKit\nimport WebKit\nfinal class ValuePromise<T> { init(_ value: T, ignoreRepeated: Bool) {}\nfunc set(_ value: T) {} }\n' + bridge)
        sdk = run(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path']).stdout.strip()
        run([swiftc, '-swift-version', '5', '-typecheck', '-sdk', sdk, '-target', 'arm64-apple-ios15.0', path])

    return source


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='youtube-watch-fallback-') as directory:
        validate(args.source, args.swiftc, Path(directory))
