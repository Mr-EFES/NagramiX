#!/usr/bin/env python3
"""Exercise the bundled web page and its Swift IFrame API error consumer."""
import argparse
from pathlib import Path
import shutil
import tempfile

from late_source_stages import ROOT
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks


def validate(source, swiftc, folder):
    stage = 'youtube_embed_startup'
    plan = checked_plan(stage)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    guard_checks(source, stage, plan, folder)
    resources = source / 'submodules/TelegramUI/Resources/WebEmbed'
    scripts = ROOT / 'scripts/tests'
    print(run(['node', scripts / 'NagramiXYoutubeEmbedStartup.cjs', resources / 'Youtube.html']).stdout.strip(), flush=True)

    # Reuse the same host WebKit boundary as the preceding gallery regression.
    prior = (scripts / 'NagramiXGalleryPlaybackRecovery.swift').read_text()
    types = prior[prior.index('enum MediaPlayerPlaybackStatus:'):prior.index('// YOUTUBE CONTROLLER')]
    controller = (source / 'submodules/TelegramUniversalVideoContent/Sources/YoutubeEmbedImplementation.swift').read_text()
    controller = block(controller, 'final class YoutubeEmbedImplementation:').replace('Bundle.main.bundleIdentifier', 'getAppBundle().bundleIdentifier')
    assert controller.index('userContentController.addUserScript') < controller.index('webView.loadHTMLString')
    for name in ('Youtube.html', 'YoutubeUserScript.js'):
        shutil.copy(resources / name, folder / name)
    fixture = (scripts / 'NagramiXYoutubeEmbedStartup.swift').read_text()
    imports = prior[:prior.index('class UIGestureRecognizer')]
    host = imports + types + '\n' + controller + '\n' + fixture
    for result in execute(swiftc, folder, 'YoutubeEmbedStartup', host):
        print(result['mode'], result['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='youtube-startup-') as temporary:
        validate(args.source, args.swiftc, Path(temporary))
