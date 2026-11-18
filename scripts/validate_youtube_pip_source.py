#!/usr/bin/env python3
"""Exercise the YouTube iframe and its native PiP source through gallery dismissal."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, ROOT, verified_prefix
from system_web_picture_in_picture_runtime import BOUNDARY, WEB, script
from validate_quick_format import block
from youtube_background_continuity_apple import check as apple_check
from youtube_background_continuity_js import harness, check as check_legacy_dom


def validate(source: Path, swiftc: Path, folder: Path) -> None:
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index('youtube_pip_source') + 1
    subprocess.run([swiftc, '-frontend', '-parse', source / WEB], check=True)
    bridge = block((source / WEB).read_text(), 'private final class NagramiXWebSystemPictureInPicture:')
    boundary = BOUNDARY.split('enum NoError{}', 1)[0].replace('case atDocumentEnd', 'case atDocumentEnd, atDocumentStart')
    boundary = boundary.replace('final class WKWebView {', 'final class WKWebView: UIView {')
    boundary = boundary.replace(' var calls:', ' var reply: ((Result<Any, Error>) -> Void)?\n var calls:')
    boundary = boundary.replace('completionHandler:Any?) {', 'completionHandler:((Result<Any, Error>) -> Void)?) {\n  if let completionHandler { reply = completionHandler }')
    tests = ROOT / 'scripts/tests'
    code = folder / 'PiPSource.swift'
    code.write_text(boundary + (tests / 'NagramiXYoutubePiPSource.swift').read_text().replace('// ACTUAL_BRIDGE', bridge))
    for flags in ([], ['-O']):
        binary = folder / 'source-test'
        subprocess.run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
                        '-module-cache-path', folder / 'cache', *flags, code, '-o', binary], check=True, timeout=120)
        subprocess.run([binary], check=True, timeout=20)
    print(apple_check(source, swiftc, folder / 'sdk')['status'], '(iPhoneOS API typecheck)')
    print(check_legacy_dom(source, folder / 'legacy')['output'])
    standard = harness().split('const policy=', 1)[0].replace('seedYouTube=true', 'standardOnly=false,seedYouTube=true')
    standard = standard.replace('const nativePause=Video.prototype.pause;', '''
        if (standardOnly) {
            delete Video.prototype.webkitSetPresentationMode;
            Video.prototype.requestPictureInPicture = async function() { document.pictureInPictureElement = this; };
            document.exitPictureInPicture = async () => { document.pictureInPictureElement = null; };
        }
        const nativePause=Video.prototype.pause;
    ''')
    dom = folder / 'standard.cjs'
    dom.write_text(standard.replace('__SOURCE_JSON__', json.dumps(script(source))) + (tests / 'NagramiXYoutubePiPSource.cjs').read_text())
    subprocess.run(['node', dom], check=True, timeout=30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='youtube-pip-source-') as directory:
        validate(args.source, args.swiftc, Path(directory))
