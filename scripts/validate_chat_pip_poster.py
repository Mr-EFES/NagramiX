#!/usr/bin/env python3
"""Exercise chat poster visibility when the embedded player loses the decoder to PiP."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from validate_private_temporary_transcription import execute
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest

STAGE = 'chat_pip_poster'
ROOT = Path(__file__).resolve().parents[1]


def validate(source, swiftc, folder):
    plan = checked_plan(STAGE)
    name, expected = next(iter(plan['outputs'].items()))
    path = source / name if source else ROOT / 'ios' / plan['replacements'][name]
    assert digest(path) == expected
    code = path.read_text()
    subprocess.run([swiftc, '-frontend', '-parse', str(path)], check=True)
    ready = block(code, 'if let videoNode = updatedVideoNode {')
    assert 'weak strongSelf, weak videoNode' in ready
    assert 'configureInlineVideo(videoNode,' in code and 'updatedVideoNode = videoNode' in code
    assert 'webpagePoster?.abstract != currentWebpagePoster?.abstract' in code
    assert '?? webpagePoster {' in code and 'photoReference: photo,' in code
    fixture = (ROOT / 'scripts/tests/NagramiXChatPiPPoster.swift').read_text()
    fixture = fixture.replace('// POSTER', block(code, 'private func webpageVideoPoster('))
    fixture = fixture.replace('// OWNERSHIP', block(code, 'private func configureInlineVideo('))
    fixture = fixture.replace('// READY', block(ready, 'displayLinkDispatcher.dispatch {'))
    for result in execute(swiftc, folder, 'ChatPiPPoster', fixture):
        print(result['mode'], result['output'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--source', type=Path)
    group.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-chat-pip-') as directory:
        validate(args.source, args.swiftc, Path(directory))
