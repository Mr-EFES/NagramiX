#!/usr/bin/env python3
"""Exercise the round-message editor geometry and verify the native controls use it."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

from late_source_stages import OVERLAY, ROOT
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest


def validate(source, swiftc, work):
    plan = checked_plan('round_send_layout')
    files = {}
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        template = plan['replacements'].get(name) or plan['guard_sources'][name]
        path = source / name if source else OVERLAY / template
        assert digest(path) == expected, name
        body = path.read_text()
        files[Path(name).stem.removeprefix('ChatMediaEditor')] = body
        swift_file = work / Path(name).name
        swift_file.write_text(body)
        run([swiftc, '-frontend', '-parse', swift_file])

    video = files['ScreenVideo']
    rows = block(video, 'struct NagramiXRoundSendRows {')
    mute_size = next(line for line in files['ScreenMute'].splitlines() if line.startswith('public let chatMediaEditorMuteButtonSize:'))
    fixture = (ROOT / 'scripts/tests/NagramiXRoundSendLayout.swift').read_text()
    host = 'import Foundation\n#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n' + mute_size + '\n' + rows + '\n' + fixture
    for result in execute(swiftc, work, 'RoundSendLayout', host):
        print(result['mode'], result['output'], flush=True)

    measure = block(video, '    func nagramiXMeasureRoundSendRows(')
    assert 'nagramiXCanEditRoundVideo' in measure and 'layout.inputHeight' in measure
    assert 'chatMediaEditorScrubberFrame(' in measure and 'label.sizeThatFits(' in measure
    assert 'self.isCoverButtonVisible' in measure and 'nagramiXRoundSize(title:' in measure
    assert 'UIContentSizeCategory.didChangeNotification' in video
    assert 'self?.nagramiXRoundTrimChanged()' in block(video, '                trackTrimUpdated: ')
    screen = files['Screen']
    layout = block(screen, '        func containerLayoutUpdated(layout:')
    assert layout.index('self.nagramiXMeasureRoundSendRows(') < layout.index('self.updatePagerLayout(') < layout.index('self.previewFrame(')
    assert 'return rows.preview' in block(screen, '        func restingPreviewFrame(')
    assert 'currentPage: false' in block(files['ScreenGallery'], '    private func pageMediaFrame(')
    assert 'rows?.time' in block(video, '    func nagramiXUpdateRoundVideoPresentation(')
    assert 'rows.controlsY - frame.height / 2.0' in files['ScreenMute']
    assert 'chatMediaEditorCounterCircleFrame.midY' in files['ScreenSelection']
    assert 'roundRows?.cover ?? chatMediaEditorCoverButtonFrame' in files['ScreenCover']
    assert '#selector(self.coverButtonPressed)' in files['ScreenCover']
    if sys.platform == 'darwin':
        # Compile the actual button (measurement, wrapping, thumbnail, arrow and tap handling) against UIKit.
        cover = files['Cover']
        constants = '\n'.join(line for line in cover.splitlines() if line.startswith(('let chatMediaEditorCoverButton', 'public let chatMediaEditorCoverButton')))
        font = 'enum Font { static func bold(_ size: CGFloat) -> UIFont { .boldSystemFont(ofSize: size) } }'
        probe = work / 'RoundCoverUIKit.swift'
        probe.write_text('import UIKit\n' + constants + '\nprivate let chatMediaEditorCoverArrowImage: UIImage? = nil\n' + font + '\n' + block(cover, 'final class ChatMediaEditorCoverButton:'))
        sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
        run([swiftc, '-swift-version', '5', '-sdk', sdk, '-target', 'arm64-apple-ios15.0', '-typecheck', probe])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='round-send-layout-') as tmp:
        validate(args.source, args.swiftc, Path(tmp))
