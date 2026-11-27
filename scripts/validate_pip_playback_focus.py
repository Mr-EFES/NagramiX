#!/usr/bin/env python3
"""Exercise foreground/PiP playback arbitration and asynchronous source readiness."""
import argparse
from pathlib import Path
import shutil
import sys
import tempfile

from late_source_stages import OVERLAY, ROOT
from validate_local_copy_delivery import execute, run
from validate_pip_swipe_handoff import U, clean
from validate_pip_video_replacement import gallery_host
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_video_playback_switches import player_host
from validate_youtube_pip_readiness import canonical as readiness_sources

STAGE = 'pip_playback_focus'
TESTS = ROOT / 'scripts/tests'
CONTENT = 'submodules/TelegramUniversalVideoContent/Sources/WebEmbedVideoContent.swift'


def playback_host(source):
    gallery = (source / U).read_text()
    host = gallery_host(source)
    fields = gallery[gallery.index('    private weak var nagramiXCompetingGallery:'):gallery.index('    private var nativePictureInPictureContent:')]
    methods = gallery[gallery.index('    private var nagramiXOtherPiP:'):gallery.index('    private func nagramiXYieldPiPForReplacement(')]
    host = host.replace(' var detached=0', clean(fields + methods) + '''
 var isLivePhoto = false, actionAtEnd = 0
 var nagramiXYoutubeId: String?, nagramiXYoutubeAvailability = Availability.playable
 var playerStatusValue: MediaPlayerStatus? = MediaPlayerStatus(status: .playing)
 var detached=0''')
    host = host.replace('final class WebEmbedVideoContent {}', '')
    host = host.replace('var content:AnyObject=NSObject()', 'var content:FocusVideoContent=NativeVideoContent()')
    host = host.replace('final class Manager {', 'final class Manager {let universalVideoManager = FocusContentManager(); ')
    host = host.replace(' func pause(){pauses+=1}', '''
 var position = 0.0, audible = false, soundPlays = 0, plays = 0
 func seek(_ time: Double) { position = time }
 func setSoundEnabled(_ enabled: Bool) { audible = enabled }
 func play() { plays += 1 }
 func playOnceWithSound(playAndRecord: Bool, seek: MediaPlayerSeek, actionAtEnd: Int) {
     check(seek == .none, "resuming should preserve position")
     audible = true
     soundPlays += 1
 }
 func pause() { pauses += 1; audible = false }''')
    delegate = clean(block(gallery, 'public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, setPlaying'))
    host = host.replace('final class PlaybackDelegate { var retiringForReplacement = false }', """
final class AVPictureInPictureController {}
final class PlaybackDelegate {
    var retiringForReplacement = false, setPlaying: ((Bool) -> Void)?
    let pictureInPictureController = AVPictureInPictureController()
""" + delegate + '\n}')
    host = host.replace(' var stops = 0', clean(block(gallery, '    func bindPlaybackControls(')) + '\n var stops = 0', 1)
    host = host.replace('  nativePictureInPictureContent=content',
                        '  guard let videoNode else { return }\n' + block(gallery, 'content.bindPlaybackControls {') +
                        '\n  nativePictureInPictureContent=content')
    host = host.replace('    static func main() {', '    static func main() {\n        checkPlaybackFocus()')
    host += clean(block((source / CONTENT).read_text(), 'public protocol NagramiXGalleryPlaybackPreparation:'))
    return host + '\n' + (TESTS / 'NagramiXPiPPlaybackFocus.swift').read_text()


def preroll_host(source):
    helper = block((source / CONTENT).read_text(), 'final class NagramiXGalleryPreroll')
    prepare = []
    for name in ('PlatformVideoContent.swift', 'SystemVideoContent.swift'):
        body = (source / Path(CONTENT).with_name(name)).read_text()
        prepare.append(block(body, '    func nagramiXPrepareGalleryPlayback('))
        for command in ('pause', 'play'):
            assert 'self.nagramiXGalleryPreroll.cancel()' in block(body, '    func ' + command + '() {')
    assert prepare[0] == prepare[1]
    return (TESTS / 'NagramiXPiPPreroll.swift').read_text().replace(
        '// PRODUCTION_PREROLL', helper).replace('// PRODUCTION_PREPARE', prepare[0])


def web_host(source):
    host = player_host(source, False)
    host = host.replace('final class YoutubeEmbedImplementation:EmbedImplementation {}', """
enum Availability { case loading, playable, unavailable }
final class YoutubeEmbedImplementation: EmbedImplementation {
    var availability = Availability.playable, wantsPlayingPictureInPicture = true
}""")
    content = (source / CONTENT).read_text()
    prepare = block(content, '    func nagramiXPrepareGalleryPlayback(_ ready: @escaping () -> Bool) {')
    host = host.replace('final class WebPolicy {', 'final class WebPolicy {\n var nagramiXPreparedGalleryPlay: (() -> Bool)?\n' + prepare)
    tests = (TESTS / 'NagramiXYoutubeInlineAudio.swift').read_text().replace(
        '    static func main() {', '    static func main() {\n        checkDeferredWebAudio()')
    return host + '\n' + (TESTS / 'NagramiXPiPWebFocus.swift').read_text() + '\n' + tests


def renderer_host(source):
    core = (source / 'submodules/MediaPlayer/Sources/MediaPlayer.swift').read_text()
    fixture = (OVERLAY / 'Tests/NagramiXGalleryPlaybackContinuity.swift').read_text()
    fixture = fixture[fixture.index('struct MediaPlayerLoadedState'):fixture.index('@main')]
    fixture = fixture.replace('struct MediaPlayerLoadedState {', 'final class MediaPlayerLoadedState { var lostAudioSession = false')
    fixture = fixture.replace('var audioRenderer: Int? = 1', 'var audioRenderer: RendererContext? = RendererContext()')
    members = ('private func currentVideoPosition()', 'private func audioRendererInterrupted(',
               'fileprivate func playOnceWithSound(', 'fileprivate func continuePlayingWithoutSound(')
    fixture = fixture.replace('// CORE METHODS', '\n'.join(clean(block(core, member)) for member in members))
    resume = block(core, 'if loadedState.lostAudioSession && !self.stoppedAtEnd')
    return fixture + (TESTS / 'NagramiXPiPAudioResume.swift').read_text().replace('// PRODUCTION_RESUME', resume)


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    if source is None:
        source = work / 'source'
        readiness_sources(source, checked_plan('youtube_pip_readiness'))
        for name, template in {**plan['replacements'], **plan['guard_sources']}.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OVERLAY / template, path)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    guard_checks(source, STAGE, plan, work / 'guards')
    run([swiftc, '-frontend', '-parse', *(source / name for name in plan['outputs'])])
    if sys.platform == 'darwin':
        helper = work / 'AVPlayerPreparation.swift'
        helper.write_text('import AVFoundation\n' + block((source / CONTENT).read_text(), 'final class NagramiXGalleryPreroll'))
        run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-typecheck', helper])
    for name, host in [('PiPPlaybackFocus', playback_host), ('PiPPreroll', preroll_host), ('PiPWebFocus', web_host),
                       ('PiPAudioResume', renderer_host)]:
        for result in execute(swiftc, work, name, host(source)):
            print(result['mode'], result['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-pip-focus-') as directory:
        validate(args.source, args.swiftc, Path(directory))
