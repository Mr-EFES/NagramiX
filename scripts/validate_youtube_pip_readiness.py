#!/usr/bin/env python3
"""Check the released gallery transition and YouTube transport with controlled iOS callbacks."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from late_source_stages import ROOT, OVERLAY
from system_web_picture_in_picture_runtime import AV, CONTENT, GALLERY, WEB, script
from validate_local_copy_delivery import execute, run
from validate_pip_swipe_handoff import N
from validate_pip_video_replacement import gallery_host
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_video_playback_switches import player_host
from youtube_background_continuity_js import harness

STAGE = 'youtube_pip_readiness'
TESTS = ROOT / 'scripts/tests'
MEDIA = 'submodules/MediaPlayer/Sources/MediaPlayer.swift'
RESOURCES = Path('submodules/TelegramUI/Resources/WebEmbed')


def canonical(source, plan):
    templates = {**plan['replacements'], **plan['guard_sources']}
    for path, stage in [(AV, 'video_playback_switches'), (MEDIA, 'gallery_playback_continuity'), (N, 'gallery_playback_continuity')]:
        templates[path] = checked_plan(stage)['replacements'][path]
    user_script = str(RESOURCES / 'YoutubeUserScript.js')
    templates[user_script] = checked_plan('youtube_inline_playback')['guard_sources'][user_script]
    for name, template in templates.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OVERLAY / template, path)


def youtube_controller_host(page):
    ui = (TESTS / 'NagramiXGalleryPlaybackRecovery.swift').read_text()
    controller = ui[:ui.index('class UIGestureRecognizer')] + ui[ui.index('enum MediaPlayerPlaybackStatus:'):ui.index('// YOUTUBE CONTROLLER')]
    controller += block((TESTS / 'NagramiXYoutubeEmbedStartup.swift').read_text(), 'final class Logger')
    controller += '\n' + page[page.index('private func accumulateTimecode'):page.index('public struct YoutubeEmbedStoryboardMediaResourceId')].replace(
        'Bundle.main.bundleIdentifier', 'getAppBundle().bundleIdentifier')
    return controller + '\n' + (TESTS / 'NagramiXYoutubeDeadlineClock.swift').read_text()


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
        if name.endswith('.swift'):
            run([swiftc, '-frontend', '-parse', source / name])
    guard_checks(source, STAGE, plan, work / 'guards')
    for name in ('Youtube.html', 'YoutubeUserScript.js'):
        shutil.copy(source / RESOURCES / name, work / name)
    print(run(['node', TESTS / 'NagramiXYoutubePiPReadiness.cjs', work / 'Youtube.html']).stdout.strip())
    page = (source / Path(WEB).with_name('YoutubeEmbedImplementation.swift')).read_text()
    controller = youtube_controller_host(page)
    audio = player_host(source, False).replace('final class YoutubeEmbedImplementation:EmbedImplementation {}',
        'final class YoutubeEmbedImplementation:EmbedImplementation { var wantsPlayingPictureInPicture = true }')
    audio_tests = (TESTS / 'NagramiXYoutubeInlineAudio.swift').read_text().replace(
        '    static func main() {', '    static func main() {\n        checkYouTubeBufferingIntent()')
    audio += '\n' + (TESTS / 'NagramiXYoutubeBufferingIntent.swift').read_text() + '\n' + audio_tests
    item = (source / GALLERY).read_text()
    content = (source / CONTENT).read_text()
    controls = (TESTS / 'NagramiXYoutubeGalleryReadiness.swift').read_text()
    controls = controls.replace('// MODEL', block(page, 'public enum NagramiXYoutubeAvailability:'))
    controls = controls.replace('// SOURCE INTERFACE', block(content, 'public protocol NagramiXYoutubePlaybackSource:').replace('public protocol', 'protocol'))
    members = [block(item, marker) for marker in ('    private var hasPictureInPicture:', '    private func nagramiXBindYoutubePlayback(',
        '    private func nagramiXSetYoutubeAvailability(', '    @objc private func nagramiXRetryYoutube(')]
    controls = controls.replace('// GALLERY MEMBERS', '\n'.join(members).replace('private ', '').replace('@objc ', ''))
    toolbar = block(item, '    private func nagramiXRefreshPiPControls(')
    assert 'self.nagramiXYoutubeAvailability == .unavailable' in toolbar
    assert '#selector(self.nagramiXRetryYoutube)' in toolbar and '#selector(self.nagramiXOpenYoutube)' in toolbar
    assert 'forceExternal: true' in block(item, '    @objc private func nagramiXOpenYoutube(')
    gallery = gallery_host(source)
    gallery = gallery.replace('finish(first)\n                advance(0.3)', '''finish(first)
                check(first.detached == 1 && first.controller!.view.alpha == 0, "confirmed handoff reveals chat without another animation frame")
                advance(0.3)''')
    for name, host in [('YoutubeReadiness', controller + (TESTS / 'NagramiXYoutubePiPReadiness.swift').read_text()),
                       ('YoutubeAudio', audio),
                       ('YoutubeControls', controls), ('PiPHandoff', gallery)]:
        for result in execute(swiftc, work, name, host):
            print(result['mode'], result['output'], flush=True)
    dom = harness().split('const policy=', 1)[0].replace('__SOURCE_JSON__', json.dumps(script(source).replace('__PIP_ENABLED__', 'true')))
    dom += '''
const f = fixture({blocked: false, hasFrame: false, seedYouTube: false});
f.dispatch({command:'probe', request:'play'});
const first = f.messages.find(m => m.kind === 'candidate');
f.video.paused = true;
f.dispatch({command:'enter', request:'play', video:first.video, requiresPlaying:true});
check(f.messages.at(-1).kind === 'unavailable', 'a play request cannot hand off a paused frame');
f.dispatch({command:'probe', request:'paused'});
const second = f.messages.filter(m => m.kind === 'candidate').at(-1);
check(f.dispatch({command:'enter', request:'paused', video:second.video, requiresPlaying:false}), 'manual pause permits paused PiP');
check(f.video.paused, 'PiP itself does not start a paused video');
console.log('PASS: a paused source is eligible only when requested');
'''
    path = work / 'readiness.cjs'
    path.write_text(dom)
    print(run(['node', path]).stdout.strip())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='youtube-readiness-') as directory:
        work = Path(directory)
        source = args.source or work / 'source'
        if args.canonical:
            canonical(source, checked_plan(STAGE))
        validate(source, args.swiftc, work)
