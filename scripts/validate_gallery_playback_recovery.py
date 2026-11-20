#!/usr/bin/env python3
"""Exercise gallery paging during PiP restore and the provider's playback state."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from late_source_stages import ROOT
from system_web_picture_in_picture_runtime import GALLERY, WEB, script
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest
from validate_video_playback_switches import player_host
from youtube_background_continuity_js import harness


def validate(source, swiftc, folder):
    stage = checked_plan('gallery_playback_recovery')
    for name, expected in {**stage['outputs'], **stage['guards']}.items():
        assert digest(source / name) == expected, name
    tests = ROOT / 'scripts/tests'
    node = (source / 'submodules/GalleryUI/Sources/GalleryControllerNode.swift').read_text()
    gallery = (source / GALLERY).read_text()
    yt = (source / Path(WEB).with_name('YoutubeEmbedImplementation.swift')).read_text()
    html = (source / 'submodules/TelegramUI/Resources/WebEmbed/Youtube.html').read_text()
    assert 'self.scrollView = GalleryDismissScrollView()' in node
    assert 'self.nagramiXNativePiPBackdropOwner === owner' in node
    assert 'failed = true' in block(html, 'function onPlayerError')
    assert 'webView.loadHTMLString(html, baseURL: origin)' in yt and 'playerVars["origin"] = origin.absoluteString' in yt
    gesture = block(node, 'private final class GalleryDismissScrollView:')
    controller = block(yt, 'final class YoutubeEmbedImplementation:')
    controller = controller.replace('Bundle.main.bundleIdentifier', 'getAppBundle().bundleIdentifier')
    resources = source / 'submodules/TelegramUI/Resources/WebEmbed'
    for resource in ('Youtube.html', 'YoutubeUserScript.js'):
        shutil.copyfile(resources / resource, folder / resource)
    host = (tests / 'NagramiXGalleryPlaybackRecovery.swift').read_text()
    for marker, body in [
        ('// DISMISS SCROLL VIEW', gesture),
        ('// VISUAL STATE', block(gallery, 'private struct NagramiXNativePiPVisualState')),
        ('// FINISH RESTORE', block(gallery, '    private func nagramiXTryFinishNativePiPRestore(')),
        ('// YOUTUBE CONTROLLER', controller),
    ]:
        host = host.replace(marker, re.sub(r'\bprivate ', 'fileprivate ', body))
    for result in execute(swiftc, folder, 'GalleryRecovery', host):
        print(result['mode'], result['output'], flush=True)

    viewport = player_host(source, False) + '\n' + (tests / 'NagramiXWebPiPViewport.swift').read_text()
    for result in execute(swiftc, folder, 'WebViewport', viewport):
        print(result['mode'], result['output'], flush=True)

    dom = harness().split('const policy=', 1)[0]
    marker = 'vm.createContext({window,document,'
    assert dom.count(marker) == 1
    dom = dom.replace(marker, 'vm.createContext({navigator: {audioSession: mockAudioSession},window,document,')
    dom = dom.replace('__SOURCE_JSON__', json.dumps(script(source).replace('__PIP_ENABLED__', 'true')))
    callbacks = '\n'.join(block(html, '        function ' + name) for name in ('onPlayerError', 'onStateChange', 'updateState'))
    scenarios = (tests / 'NagramiXGalleryPlaybackRecovery.cjs').read_text().replace(
        '// PROVIDER CALLBACKS', 'const providerCallbacks = ' + json.dumps(callbacks) + ';')
    path = folder / 'gallery.cjs'
    path.write_text('const mockAudioSession = {type: "auto"};\n' + dom + '\n' + scenarios)
    print(run(['node', path], timeout=30).stdout.strip(), flush=True)
    run([swiftc, '-frontend', '-parse', *[source / name for name in stage['outputs'] if name.endswith('.swift')]])
    if sys.platform == 'darwin':
        sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
        cls = folder / 'Gesture.swift'
        cls.write_text('import UIKit\n' + gesture)
        run([swiftc, '-swift-version', '5', '-sdk', sdk, '-target', 'arm64-apple-ios15.0',
             '-module-cache-path', folder / 'cache', '-warnings-as-errors', '-typecheck', cls])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gallery-recovery-') as temporary:
        validate(args.source, args.swiftc, Path(temporary))
