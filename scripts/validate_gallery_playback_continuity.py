#!/usr/bin/env python3
"""Exercise the gallery playback callbacks and the receiver repair on the Swift host."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from validate_private_temporary_transcription import execute
from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest


def validate(source, swiftc, root):
    plan = checked_plan('gallery_playback_continuity')
    files = {}
    for name, expected in plan['outputs'].items():
        path = source / name if source else OVERLAY / plan['replacements'][name]
        assert digest(path) == expected, name
        text = path.read_text()
        files[Path(name).stem] = text
        local = root / Path(name).name
        local.write_text(text)
        subprocess.run([swiftc, '-frontend', '-parse', local], check=True)
    item = files['UniversalVideoGalleryItem']
    gallery = files['GalleryControllerNode']
    audio = files['ManagedAudioSession']
    fixture = (OVERLAY / 'Tests/NagramiXGalleryPlaybackContinuity.swift').read_text()
    core = files['MediaPlayer']
    fixture = fixture.replace('// CORE METHODS', '\n'.join(block(core, method).removeprefix('private ') for method in (
        'private func currentVideoPosition()', 'private func audioRendererInterrupted(',
        'fileprivate func playOnceWithSound(', 'fileprivate func continuePlayingWithoutSound(')))
    fixture = fixture.replace('// GALLERY METHODS', '\n'.join(block(item, method) for method in (
        'override func activateAsInitial()', 'override func visibilityUpdated(isVisible: Bool)')))
    fixture = fixture.replace('// DISMISS GESTURE', block(gallery, 'private func nagramiXIsVideoDismissSwipe('))
    fixture = fixture.replace('// AUDIO METHOD', block(audio, 'private func reconcilePlaybackReceiver()').removeprefix('private '))
    execute(swiftc, root, 'GalleryPlaybackContinuity', fixture)
    ownership = block(item, 'videoNode.ownsContentNodeUpdated =')
    assert 'if value && strongSelf.playOnContentOwnership' in ownership and 'strongSelf.activateAsInitial()' in ownership
    assert 'setForceAudioToSpeaker(true)' in ownership and '!media.fileReference.media.isInstantVideo' in ownership
    pager = block(files['GalleryPagerNode'], 'public func containerLayoutUpdated(')
    assert pager.index('self.ignoreDidScroll = true') < pager.index('self.scrollView.frame =') < pager.index('self.scrollView.contentOffset =') < pager.index('self.ignoreDidScroll = wasIgnoringScroll')
    assert 'expandIntoCustomPiP' not in item
    poster = block(item, 'func nagramiXMakePiPPreviewPoster()')
    assert poster.index('phase == .restoring') < poster.index('return backdrop') < poster.index('UniversalVideoGalleryItemPictureInPictureNode(')
    assert 'backdrop.frame = controller.view.bounds' in poster
    for name in ('GalleryController', 'InstantPageGalleryController'):
        close = block(files[name], 'func dismiss(forceAway: Bool)')
        assert 'guard !self.galleryNode.isDismissed' in close and 'forceAway || isVideo' in close
        assert 'dismiss(forceAway: true)' in block(files[name], 'self.galleryNode.dismissVideo =')
    drag = block(gallery, 'open func scrollViewWillEndDragging(')
    assert drag.index('dismissVideo()') < drag.index('if let distance = self.nagramiXNativePictureInPictureDistance')
    assert 'self.reconcilePlaybackReceiver()' in block(audio, 'private func updateCurrentAudioRouteInfo()')
    print('PASS: gallery activation, pause, timecode, rotation, PiP, dismissal and media routing')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        validate(args.source, args.swiftc, Path(tmp))
