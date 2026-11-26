#!/usr/bin/env python3
"""Exercise gallery PiP replacement with independently delivered system callbacks."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from late_source_stages import ROOT, OVERLAY
from native_pip_refinement_runtime import lifecycle
from system_web_picture_in_picture_runtime import WEB, script
from validate_local_copy_delivery import execute, run
from validate_pip_swipe_handoff import N, U, clean
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from youtube_background_continuity_js import harness

TESTS = ROOT / 'scripts/tests'
STAGE = 'pip_video_replacement'


def gallery_host(source):
    gallery = (source / U).read_text()
    host = lifecycle(source).split('@main struct Tests', 1)[0]
    helpers = ('nagramiXReleaseStoppedNativeSession', 'nagramiXYieldPiPForReplacement', 'nagramiXTryEnterEmbeddedPiP')
    methods = '\n'.join(clean(block(gallery, '    private func ' + name + '(')) for name in helpers)
    fields = '\n'.join(clean(line) for line in gallery.splitlines() if any(
        line.strip().startswith('private ' + prefix) for prefix in (
            'static weak var nagramiXPendingPiPRequest:', 'var nagramiXRetiringPiP =', 'var nagramiXWebPiPEntryAccepted =')))
    host = host.replace(' var nagramiXPiPEntryGeneration=0', methods + '\n' + fields + '\n var isAnimatingOut = false\n var nagramiXPiPEntryGeneration=0')
    host = host.replace('let context=Context(),scrollNode=Scroll()', 'var context=Context(); let scrollNode=Scroll()')
    # Requesting system stop and receiving its completion are separate events on iOS.
    host = host.replace('func stop(){isActive=false;isStarting=false;end(self)}', '''
 var stops = 0
 var contentDelegate: PlaybackDelegate? = PlaybackDelegate()
 // PRODUCTION_RETIRE_CONTROLS
 func stop() { stops += 1 }
 func confirmStop() { isActive = false; isStarting = false; end(self) }''')
    host = host.replace('stops+=1;isNativePictureInPictureActive.set(false)', 'stops+=1')
    host = host.replace('typealias GalleryItemNode=GalleryLifecycleBoundary', 'class GalleryItemNode {}')
    host = host.replace('final class GalleryLifecycleBoundary {', 'final class GalleryLifecycleBoundary: GalleryItemNode {')
    host = host.replace('func centralItemNode()->GalleryLifecycleBoundary?', 'func centralItemNode()->GalleryItemNode?')
    host = host.replace('var nagramiXNativePictureInPictureItem:GalleryLifecycleBoundary?', 'var nagramiXNativePictureInPictureItem:GalleryItemNode?')
    host = host.replace('// PRODUCTION_RETIRE_CONTROLS', clean(block(gallery, '    func setRetiringForReplacement(')))
    host += (TESTS / 'NagramiXPiPReplacement.swift').read_text()
    host = host.replace('var isAnimatingOut = false', 'var isAnimatingOut = false; var nagramiXPiPPresentationWindow: WindowHost?')
    host = host.replace('init(){controller!.galleryNode', 'override init(){super.init();controller!.galleryNode')
    return host


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
        run([swiftc, '-frontend', '-parse', source / name])
    print("Stage guard checks:", len(guard_checks(source, STAGE, plan, work / 'guards')))
    for result in execute(swiftc, work, 'PiPReplacement', gallery_host(source)):
        print(result['mode'], result['output'], flush=True)
    web = (source / WEB).read_text()
    assert 'self.nagramiXSystemPiP.requestExit()' in block(web, '    func exitNativePictureInPicture()')
    bridge = block(web, '    func requestExit()')
    bridge_host = (TESTS / 'NagramiXWebPiPReplacement.swift').read_text().replace('// PRODUCTION_EXIT', bridge)
    for result in execute(swiftc, work, 'WebExit', bridge_host):
        print(result['mode'], result['output'], flush=True)
    dom = work / 'replacement.cjs'
    dom.write_text(harness().split('const policy=', 1)[0].replace('__SOURCE_JSON__', json.dumps(script(source).replace('__PIP_ENABLED__', 'true')))
                   + (TESTS / 'NagramiXWebPiPReplacement.cjs').read_text())
    print(run(['node', dom]).stdout.strip())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='pip-replacement-') as tmp:
        work = Path(tmp)
        source = args.source
        if source is None:
            source = work / 'source'
            plan = checked_plan(STAGE)
            paths = {**plan['replacements'], **plan['guard_sources']}
            paths[N] = checked_plan('gallery_playback_continuity')['replacements'][N]
            for name, template in paths.items():
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(OVERLAY / template, target)
        validate(source, args.swiftc, work)
