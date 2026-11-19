#!/usr/bin/env python3
"""Exercise the independent PiP and background playback switches at the player boundary."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from late_source_stages import ROOT
from system_web_picture_in_picture_runtime import AV, CONTENT, GALLERY, WEB, script
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan
from validate_youtube_pip_source import bridge_boundary
from youtube_background_continuity_js import harness
from youtube_background_continuity_runtime import fixture


TESTS = ROOT / 'scripts/tests'


def player_host(source, apple):
    web = fixture(source, apple=apple).split('@main struct Tests', 1)[0]
    if not apple:
        host = bridge_boundary().replace('case automatic,continuesIfPossible', 'case automatic,continuesIfPossible,pauses')
        host = host.replace('final class WKWebView: UIView {', 'final class WKWebView: UIView {\n func pauseAllMediaPlayback(completionHandler: (() -> Void)?) { completionHandler?() }')
        host = host.replace('static let willEnterForegroundNotification=', 'static let didBecomeActiveNotification=Notification.Name("active")\n static let willResignActiveNotification=Notification.Name("inactive")\n static let willEnterForegroundNotification=')
        host = host.replace('var value:T', 'var onSet: ((T) -> Void)?\n var value:T').replace('self.value=value}\n}', 'self.value=value;onSet?(value)}\n}', 1)
        ui = (TESTS / 'NagramiXYoutubePiPSource.swift').read_text().split('// ACTUAL_BRIDGE')[0]
        web = host + ui + '\nstruct WKError: Error { enum Code { case javaScriptInvalidFrameTarget }; let code: Code }\n' + web[web.index('enum NoError:'):]
    web = web.replace('enum NagramiXTabSettings {', 'enum NagramiXTabSettings { static var videoPictureInPictureEnabled = true; ')
    web = web.replace('final class YoutubeEmbedImplementation:', 'final class GenericEmbedImplementation: EmbedImplementation {}\nfinal class YoutubeEmbedImplementation:')
    web = web.replace(' let impl:EmbedImplementation', ' var webView: WKWebView { view }\n let impl:EmbedImplementation')
    web = web.replace('():EmbedImplementation()', '():GenericEmbedImplementation()')
    return web + '\n' + block((source / AV).read_text(), 'final class NagramiXAVPlayerPictureInPicture:')


def validate(source, swiftc, folder):
    plan = checked_plan('video_playback_switches')
    for name in plan['outputs']:
        run([swiftc, '-frontend', '-parse', source / name], timeout=60)
    gallery = (source / GALLERY).read_text()
    page = (source / 'submodules/InstantPageUI/Sources/InstantPageGalleryController.swift').read_text()
    assert 'self.galleryNode.galleryController = { [weak self] in self }' in page
    for entry in ['    private func nagramiXRequestPictureInPicture(', '    private func nagramiXBeginWebPictureInPicture(',
                  '    private func nagramiXBeginNativePiPVisualTransition(', '    private func nagramiXRestoreSystemWebPiP(']:
        section = block(gallery, entry)
        assert 'nagramiXPiPGalleryNode' in section and 'as? GalleryController ' not in section
    for entry in ['    @objc func pictureInPictureButtonPressed()', '    @objc private func nagramiXUpwardPiPSwipe(']:
        assert 'nagramiXRequestPictureInPicture()' in block(gallery, entry)
    assert 'videoNode.pause()' in block(gallery, '        self.nagramiXDidEnterBackgroundObserver = NotificationCenter')
    assert 'return !NagramiXTabSettings.backgroundVideoPlaybackEnabled' in block(gallery, '        public func pictureInPictureControllerShouldProhibitBackgroundAudioPlayback(')
    assert 'displayPictureInPictureButton: self.hasPictureInPicture' in block(gallery, '    private func nagramiXUpdatePlaybackSettings(')
    assert 'pipEnabled: true' not in (source / WEB).read_text()
    assert 'func nagramiXUpdateManagedPlayback' in (source / CONTENT).read_text()
    availability = '\n'.join(block(gallery, 'private func ' + marker) for marker in
                              ['nagramiXUsesEmbeddedPictureInPicture(', 'nagramiXCanOfferPictureInPicture('])
    controls = block(gallery, '    private func nagramiXRefreshPiPControls(').replace('private func', 'func', 1)
    controls = controls.replace('#selector(self.pictureInPictureButtonPressed)', '"pictureInPictureButtonPressed"')
    has_pip = block(gallery, '    private var hasPictureInPicture:').replace('private var', 'var', 1)
    swipe = block(gallery, '    override var usesNativePictureInPictureSwipe:').replace('override var', 'var', 1)
    gallery_host = (TESTS / 'NagramiXVideoPlaybackSwitches.swift').read_text().replace(
        '// GALLERY CONTROLS', '\n'.join([has_pip, swipe, controls]))
    code = folder / 'Players.swift'
    code.write_text(player_host(source, False) + '\n' + availability + '\n' + gallery_host)
    for flags in ([], ['-O']):
        binary = folder / 'players'
        run([swiftc, '-swift-version', '5', '-parse-as-library', '-warnings-as-errors',
             '-module-cache-path', folder / 'cache', *flags, code, '-o', binary], timeout=180)
        print(run([binary], timeout=30).stdout.strip(), flush=True)

    dom = harness().split('const policy=', 1)[0].replace('__SOURCE_JSON__', json.dumps(script(source).replace('__PIP_ENABLED__', 'true')))
    path = folder / 'switches.cjs'
    path.write_text(dom + (TESTS / 'NagramiXVideoPlaybackSwitches.cjs').read_text())
    run(['node', path], timeout=30)

    if sys.platform == 'darwin':
        code.write_text('import AVKit\n' + player_host(source, True))
        sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
        run([swiftc, '-swift-version', '5', '-typecheck', '-warnings-as-errors', '-sdk', sdk,
             '-target', 'arm64-apple-ios15.0', '-module-cache-path', folder / 'apple-cache', code], timeout=180)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='video-playback-switches-') as temp:
        validate(args.source, args.swiftc, Path(temp))
