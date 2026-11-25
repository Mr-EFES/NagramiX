#!/usr/bin/env python3
"""Exercise the shipped iframe controller and audio ownership at the iOS host boundaries."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from late_source_stages import ROOT
from system_web_picture_in_picture_runtime import AV, GALLERY, WEB, script
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, OVERLAY
from validate_video_playback_switches import player_host
from youtube_background_continuity_js import harness


STAGE = 'youtube_inline_playback'
TESTS = ROOT / 'scripts/tests'
RESOURCES = Path('submodules/TelegramUI/Resources/WebEmbed')


def canonical(source, plan):
    templates = {**plan['guard_sources'], **plan['replacements']}
    for name, stage in [(AV, 'video_playback_switches'), ('submodules/MediaPlayer/Sources/MediaPlayer.swift', 'gallery_playback_continuity')]:
        templates[name] = checked_plan(stage)['replacements'][name]
    for name, template in templates.items():
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OVERLAY / template, destination)


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
        if name.endswith('.swift'):
            subprocess.run([swiftc, '-frontend', '-parse', source / name], check=True)
    html = source / RESOURCES / 'Youtube.html'
    run(['node', TESTS / 'NagramiXYoutubeEmbedStartup.cjs', html])
    for resource in ['Youtube.html', 'YoutubeUserScript.js']:
        shutil.copy(source / RESOURCES / resource, work / resource)
    previous = (TESTS / 'NagramiXGalleryPlaybackRecovery.swift').read_text()
    host = previous[:previous.index('class UIGestureRecognizer')]
    host += previous[previous.index('enum MediaPlayerPlaybackStatus:'):previous.index('// YOUTUBE CONTROLLER')]
    host += block((TESTS / 'NagramiXYoutubeEmbedStartup.swift').read_text(), 'final class Logger')
    controller = (source / Path(WEB).with_name('YoutubeEmbedImplementation.swift')).read_text()
    host += '\n' + controller[controller.index('private func accumulateTimecode'):controller.index('public struct YoutubeEmbedStoryboardMediaResourceId')].replace('Bundle.main.bundleIdentifier', 'getAppBundle().bundleIdentifier')
    # Compile the real URL classifier and gallery selection conditions with small metadata values.
    web = (source / WEB).read_text()
    host += '\n' + block(web, 'public enum WebEmbedType').replace('public ', '') + '\n'
    host += block(web, 'public func webEmbedType(').replace('public func', 'func', 1) + '\n'
    selector = (source / 'submodules/GalleryUI/Sources/GalleryController.swift').read_text()
    start = selector.index('            let isYouTube: Bool')
    end = selector.index('            if content == nil, let webEmbedContent', start)
    branches = selector[start:end].splitlines()
    for index, line in enumerate(branches):
        if line.lstrip().startswith('content = NativeVideoContent('):
            branches[index] = '                return "native"'
        elif line.lstrip().startswith('content = SystemVideoContent('):
            branches[index] = '                _ = image; return "system"'
    host += 'func select(_ webpageContent: TelegramMediaWebpageLoadedContent) -> String {\n' + '\n'.join(branches) + '\nreturn "embed"\n}\n'
    for name, prefix in [('NagramiXYoutubeInlinePlayback', host), ('NagramiXYoutubeInlineAudio', player_host(source, False))]:
        for result in execute(swiftc, work, name, prefix + '\n' + (TESTS / (name + '.swift')).read_text()):
            print(result['mode'], result['output'], flush=True)
    dom = harness().split('const policy=', 1)[0]
    dom = dom.replace('vm.createContext({window,document,', 'vm.createContext({navigator: {audioSession: audioSession},window,document,')
    dom = dom.replace('__SOURCE_JSON__', json.dumps(script(source).replace('__PIP_ENABLED__', 'true')))
    dom += (TESTS / 'NagramiXYoutubeInlineAudio.cjs').read_text()
    (work / 'audio.cjs').write_text(dom)
    print(run(['node', work / 'audio.cjs']).stdout.strip())
    gallery = (source / GALLERY).read_text()
    assert 'case .youtube = webEmbedType' in block(gallery, 'private func shouldAutoplayOnCentrality()')
    assert '(active || ownsYouTubePlayer)' in block(gallery, 'private func nagramiXUpdateBackgroundVideoPlayback()')
    run(['node', TESTS / 'NagramiXYoutubeInlinePlayback.cjs', html])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='youtube-inline-') as temporary:
        work = Path(temporary)
        source = args.source or work / 'source'
        if args.canonical:
            canonical(source, checked_plan(STAGE))
        validate(source, args.swiftc, work)
