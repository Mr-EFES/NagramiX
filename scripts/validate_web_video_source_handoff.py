#!/usr/bin/env python3
"""Run the production WebKit bridge through document, element and audio handoffs."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import ROOT
from system_web_picture_in_picture_runtime import GALLERY, WEB, script
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_video_playback_switches import player_host, validate as validate_switches
from youtube_background_continuity_js import harness


def validate(source, swiftc, folder):
    validate_switches(source, swiftc, folder)
    gallery = (source / GALLERY).read_text()
    begin = block(gallery, '    private func nagramiXBeginWebPictureInPicture(')
    active = block(begin, '            if active {')
    assert begin.count('nagramiXBeginNativePiPVisualTransition()') == 1
    assert active.index('nagramiXBeginNativePiPVisualTransition()') < active.index('nagramiXCommitPiPHandoff(')
    assert 'nagramiXSystemWebPiPWatchdog' not in gallery
    assert 'documentDidChange(continuingPlayback: continuing)' in block((source / WEB).read_text(), '    func webView(_ webView: WKWebView, didCommit')
    tests = ROOT / 'scripts/tests'
    gallery_node = (source / 'submodules/GalleryUI/Sources/GalleryControllerNode.swift').read_text()
    swipe = block(gallery_node, '    func nagramiXLockNativePictureInPictureSwipe(')
    body = (tests / 'NagramiXWebVideoHandoff.swift').read_text().replace('// SWIPE LOCK', swipe)
    code = folder / 'Handoff.swift'
    code.write_text(player_host(source, False) + '\n' + body)
    for flags in ([], ['-O']):
        binary = folder / 'handoff'
        run([swiftc, '-swift-version', '5', '-parse-as-library', '-warnings-as-errors', '-module-cache-path',
             folder / 'cache', *flags, code, '-o', binary], timeout=180)
        print(run([binary], timeout=30).stdout.strip(), flush=True)
    manager_path = 'submodules/TelegramUniversalVideoContent/Sources/UniversalVideoContentManager.swift'
    manager = (source / manager_path).read_text()
    callbacks = (tests / 'NagramiXVideoSubscriptions.swift').read_text().replace(
        '// PRODUCTION CALLBACK BAGS', block(manager, 'private final class UniversalVideoContentHolderCallbacks'))
    functions = ('addPlaybackCompleted', 'removePlaybackCompleted', 'statusSignal', 'bufferingStatusSignal',
                 'isNativePictureInPictureActiveSignal')
    methods = [block(manager, '    public func ' + name + '(').replace('public func', 'func', 1) for name in functions]
    code.write_text(callbacks.replace('// PRODUCTION SUBSCRIPTION METHODS', '\n'.join(methods)))
    bag = source / 'submodules/SSignalKit/SwiftSignalKit/Source/Bag.swift'
    binary = folder / 'subscriptions'
    run([swiftc, '-swift-version', '5', '-parse-as-library', '-warnings-as-errors', '-O', '-module-cache-path',
         folder / 'cache', code, bag, '-o', binary], timeout=180)
    print(run([binary], timeout=30).stdout.strip(), flush=True)
    dom = harness().split('const policy=', 1)[0]
    dom = dom.replace('__SOURCE_JSON__', json.dumps(script(source).replace('__PIP_ENABLED__', 'true')))
    path = folder / 'handoff.cjs'
    path.write_text(dom + (tests / 'NagramiXWebVideoHandoff.cjs').read_text())
    print(run(['node', path], timeout=30).stdout.strip(), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='web-video-handoff-') as temporary:
        validate(args.source, args.swiftc, Path(temporary))
