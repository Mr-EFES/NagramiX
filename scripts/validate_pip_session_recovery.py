#!/usr/bin/env python3
"""Exercise repeated PiP entry and managed YouTube playback using the deployed Swift methods."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from late_source_stages import ROOT, verified_prefix, LATE_SOURCE_STAGES
from native_pip_refinement_runtime import lifecycle
from system_web_picture_in_picture_runtime import WEB, script
from validate_pip_swipe_handoff import U, clean
from validate_quick_format import block
from validate_youtube_pip_source import bridge_boundary
from youtube_background_continuity_apple import check as check_apple
from youtube_background_continuity_js import harness
from youtube_background_continuity_runtime import fixture

TESTS = ROOT / 'scripts/tests'
YOUTUBE = Path(WEB).with_name('YoutubeEmbedImplementation.swift')


def validate(source, swiftc, folder):
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index('pip_session_recovery') + 1
    subprocess.run([swiftc, '-frontend', '-parse', source / U, source / WEB, source / YOUTUBE], check=True)
    gallery = (source / U).read_text()
    helpers = '\n'.join(clean(block(gallery, '    private func ' + name)) for name in
                        ('nagramiXReleaseStoppedNativeSession(', 'nagramiXTryEnterEmbeddedPiP('))
    code = lifecycle(source).replace('let context=Context(),scrollNode=Scroll()', 'var context=Context(); let scrollNode=Scroll()')
    code = code.replace(' var nagramiXPiPEntryGeneration=0',
                        helpers + '\n var nagramiXWebPiPEntryAccepted = false\n var nagramiXPiPEntryGeneration=0')
    gallery_main = '@main struct Tests {static func main(){'
    assert code.count(gallery_main) == 1
    code = code.replace(gallery_main, gallery_main + '\n exerciseRepeatedEntry()')
    tests = {'Gallery': code + (TESTS / 'NagramiXPiPRepeatedEntry.swift').read_text()}

    # The web and managed-audio fixtures share the same WebKit view and callback boundary.
    ui = (TESTS / 'NagramiXYoutubePiPSource.swift').read_text().split('// ACTUAL_BRIDGE')[0]
    host = bridge_boundary()
    host = host.replace('static let willEnterForegroundNotification=', '''static let didBecomeActiveNotification=Notification.Name("fixture-active")
 static let willResignActiveNotification=Notification.Name("fixture-inactive")
 static let willEnterForegroundNotification=''')
    host = host.replace('var value:T', 'var onSet:((T)->Void)?\n var value:T').replace(
        'self.value=value}\n}', 'self.value=value;onSet?(value)}\n}', 1)
    web = fixture(source)
    web = host + ui + '\nstruct WKError: Error { enum Code { case javaScriptInvalidFrameTarget }; let code: Code }\n' + web[web.index('enum NoError:'):]
    parser = (source / YOUTUBE).read_text()
    web += '\n' + parser[parser.index('private func accumulateTimecode'):parser.index('final class YoutubeEmbedImplementation')]
    web_main = '@main struct Tests {\n static func main(){'
    assert web.count(web_main) == 1
    web = web.replace(web_main, web_main + '\n  exerciseWebRecovery()')
    tests['Web'] = web + (TESTS / 'NagramiXWebPiPRecovery.swift').read_text()
    for name, code in tests.items():
        path = folder / (name + '.swift')
        path.write_text(code)
        for flags in ([], ['-O']):
            binary = folder / name
            subprocess.run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
                            '-module-cache-path', folder / 'cache', *flags, path, '-o', binary], check=True, timeout=120)
            subprocess.run([binary], check=True, timeout=30)

    dom = folder / 'web.cjs'
    dom.write_text(harness().split('const policy=', 1)[0].replace('__SOURCE_JSON__', json.dumps(script(source)))
                   + (TESTS / 'NagramiXWebPiPRecovery.cjs').read_text())
    subprocess.run(['node', dom], check=True, timeout=30)
    print(check_apple(source, swiftc, folder / 'apple')['status'], '(iPhoneOS WebKit API typecheck)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='pip-session-recovery-') as folder:
        validate(args.source, args.swiftc, Path(folder))
