#!/usr/bin/env python3
"""Check resuming two gallery/PiP videos and closing the video on its real end event."""
import argparse
from pathlib import Path
import shutil
import tempfile

from pip_playback_completion_runtime import TESTS, YOUTUBE, fixture
from validate_local_copy_delivery import execute, run
from validate_pip_playback_focus import renderer_host
from validate_pip_swipe_handoff import U, clean
from validate_quick_format import block
from validate_release_095_apple_preflight import canonical_projection
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks
from validate_youtube_pip_readiness import youtube_controller_host

STAGE = 'pip_playback_completion'
SYSTEM = 'submodules/TelegramUniversalVideoContent/Sources/SystemVideoContent.swift'
WEB = 'submodules/TelegramUniversalVideoContent/Sources/WebEmbedVideoContent.swift'
PLAYER = 'submodules/TelegramUniversalVideoContent/Sources/WebEmbedPlayerNode.swift'


def end_policy_host(source):
    text = (TESTS / 'NagramiXVideoEndPolicy.swift').read_text()
    observer = block((source / SYSTEM).read_text(), '        self.didPlayToEndTimeObserver = NotificationCenter.default.addObserver(') + ')'
    return text.replace('// PRODUCTION_OBSERVER', observer).replace(
        '// PRODUCTION_POLICY', clean(block((source / U).read_text(), '    private var actionAtEnd:')))


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'round_recording_completion'
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    for name in plan['outputs']:
        run([swiftc, '-frontend', '-parse', source / name])
    print('Stage guard checks:', len(guard_checks(source, STAGE, plan, work / 'guards')), flush=True)

    gallery = (source / U).read_text()
    completed = block(gallery, '            videoNode.playbackCompleted = {')
    assert 'self.videoNode === videoNode' in completed
    assert completed.count('self.nagramiXFinishPlayback(videoNode)') == 1
    assert 'guard !isAnimated' in completed and 'self.isLivePhoto' in completed
    assert '.nagramiXResumePlayback(' in block(gallery, '    @objc func statusButtonPressed()')
    assert '.nagramiXResumePlayback(' in block(gallery, '    private func nagramiXUpdateBackgroundVideoPlayback()')
    content = (source / WEB).read_text()
    assert 'youtube.onPlaybackCompleted = { [weak self] in' in content
    assert 'for listener in self.playbackCompletedListeners.copyItems() { listener() }' in content

    old_footer = block((OVERLAY / plan['previous'][U]).read_text(), '        self.footerContentNode.playbackControl = {')
    diagnostic = 'fullscreen Play after a competing video resumes the first'
    for result in execute(swiftc, work, 'PreviousPlay', fixture(source, old_footer), diagnostic, failure_code=96):
        print(result['mode'], 'previous Play blockage reproduced', flush=True)
    for name, host in [('PiPPlaybackCompletion', fixture(source)),
                       ('VideoEndPolicy', end_policy_host(source)),
                       ('PiPAudioResume', renderer_host(source))]:
        for result in execute(swiftc, work, name, host):
            print(result['mode'], result['output'], flush=True)

    for name in ('Youtube.html', 'YoutubeUserScript.js'):
        shutil.copy(source / ('submodules/TelegramUI/Resources/WebEmbed/' + name), work / name)
    controller = youtube_controller_host((source / YOUTUBE).read_text())
    for suite in ('NagramiXYoutubePlaybackCompletion', 'NagramiXYoutubeWatchContinuity'):
        for result in execute(swiftc, work, suite, controller + (TESTS / (suite + '.swift')).read_text()):
            print(result['mode'], result['output'], flush=True)
    print(run(['node', TESTS / 'NagramiXYoutubePlaybackCompletion.cjs', source / PLAYER]).stdout.strip(), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='pip-playback-completion-') as temporary:
        work = Path(temporary)
        source = args.source
        if args.canonical:
            source = work / 'source'
            canonical_projection(source, STAGE)
            plan = checked_plan(STAGE)
            for name in ('Youtube.html', 'YoutubeUserScript.js'):
                path = 'submodules/TelegramUI/Resources/WebEmbed/' + name
                target = source / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(OVERLAY / plan['guard_sources'][path], target)
        validate(source, args.swiftc, work)


if __name__ == '__main__':
    main()
