#!/usr/bin/env python3
"""Страница кружков: точные исходники, стабильное обновление и round metadata."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from validate_quick_format import block
ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/SettingsUI/Sources/'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    args = parser.parse_args()
    from validate_round_video_bitrate import delegate_if_applied
    if delegate_if_applied(args): return
    plan = json.loads((ROOT/'ios/round_video_page_patches.json').read_text())
    refinement = json.loads((ROOT/'ios/round_video_refinement_patches.json').read_text())
    refined = all(hashlib.sha256((args.source/name).read_bytes()).hexdigest() == digest for name,digest in refinement['outputs'].items())
    expected = {**plan['guards'], **plan['outputs']}
    if refined: expected.update(refinement['outputs'])
    for name, digest in expected.items():
        assert hashlib.sha256((args.source/name).read_bytes()).hexdigest() == digest, name
    for name, digest in plan['templates'].items():
        assert hashlib.sha256((ROOT/'ios'/name).read_bytes()).hexdigest() == digest, name
    controller = (args.source/PREFIX/'NagramiXRoundQualityController.swift').read_text()
    parent = (args.source/PREFIX/'NagramiXSettingsController.swift').read_text()
    assert 'ActionSheetController' not in controller
    assert all(token not in controller for token in ['reloadData(', 'reloadRows(', 'setItemGroups('])
    assert 'pushControllerImpl?(NagramiXRoundQualityController(' in parent
    assert 'presentControllerImpl?(nagramiXRoundQualitySheet(' not in parent
    assert 'case .roundQuality: return 5000' in parent and 'case .roundQualityOptions: return 5001' in parent
    assert 'case .roundQualityHeader: return 5002' in parent
    assert 'return NagramiXSettingsSection.roundQualitySettings.rawValue' in parent
    if refined:
        subprocess.run(['python3', str(ROOT/'scripts/validate_round_video_refinement.py'), '--source', str(args.source),
            *(['--swiftc',str(args.swiftc)] if args.swiftc else [])], check=True)
        print('PASS: page/group/metadata guards retained; current refinement checked')
        return
    assert 'value.frameRate = .standard' in controller and 'Включить при 30 FPS' in controller
    if args.swiftc:
        model = args.source/'submodules/NagramiXMediaSettings/Sources/NagramiXRoundVideoSettings.swift'
        methods = [block(controller, marker).replace('private func', 'func', 1) for marker in
                   ['private func supports(', 'private func enabled(', 'private func commit(']]
        page = '''import Foundation
final class PageHarness {
 let table = PageTable()
 var cinematicModes: [Int: Bool] = [:]
 var changedCount = 0
 lazy var changed: () -> Void = { [unowned self] in self.changedCount += 1 }
 func configure(_ cell: PageCell, at path: IndexPath) { cell.value = NagramiXRoundVideoSettings.current }
''' + '\n'.join(methods) + '\n}\n'
        camera = (args.source/'submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift').read_text()
        line = next(line for line in camera.splitlines() if 'let media = TelegramMediaFile(' in line and 'duration: finalDuration' in line)
        attributes = line.split('attributes: ', 1)[1].rsplit(', alternativeRepresentations:', 1)[0]
        page += '''final class SourceHost {
 let node = SourceNode()
 func attributes(finalDuration: Double) -> [TelegramMediaFileAttribute] {
 let side = self.node.nagramiXQuality?.quality.rawValue ?? 480
 let outputDimensions = PixelDimensions(width: side, height: side)
 return ''' + attributes + '\n}\n}\n'
        upload = (args.source/'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift').read_text()
        body = upload.split('case let .Video(duration, size, videoFlags, preloadSize, coverTime, videoCodec):', 1)[1].split('attributes.append(.documentAttributeVideo', 1)[0]
        page += 'func apiVideoFlags(videoFlags: TelegramMediaVideoFlags, preloadSize: Int?, coverTime: Double?, videoCodec: String?) -> Int32 {' + body + '\nreturn flags\n}\n'
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            source = temp/'Page.swift'; source.write_text(page)
            for mode in [[], ['-O']]:
                subprocess.run([str(args.swiftc), '-parse-as-library', '-module-cache-path', str(temp/'cache'),
                    *mode, str(model), str(ROOT/'scripts/tests/NagramiXRoundPageBoundary.swift'), str(source),
                    str(ROOT/'scripts/tests/NagramiXRoundPageBehaviorTests.swift'), '-o', str(temp/'test')], check=True)
                env = os.environ.copy(); env['XDG_CONFIG_HOME'] = str(temp/'preferences')
                subprocess.run([str(temp/'test')], env=env, check=True)
            subprocess.run([str(args.swiftc), '-frontend', '-parse', *[str(args.source/name) for name in plan['outputs']]], check=True)
    print('PASS: page/group/capture/export/metadata source guards; Apple SDK/camera/server pending')

if __name__ == '__main__':
    main()
