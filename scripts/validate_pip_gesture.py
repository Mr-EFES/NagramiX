#!/usr/bin/env python3
"""Execute the production PiP gesture controller with UIKit boundary doubles.

This checks handoff/cancellation control flow, not UIKit rendering or AVKit.
It does not compile an iOS application or start an IPA build.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def validate(swiftc):
    path = ROOT / 'ios/Sources/GalleryUI/NagramiXPiPGestureController.swift'
    source = path.read_text()
    # Remove only Objective-C dispatch/import boundaries unsupported on Linux.
    # The gesture's state machine, geometry and closures execute unchanged.
    for old, new in [('import UIKit\n', ''), ('import Display\n', ''),
                     ('@objc private func pan(', 'private func pan('),
                     ('#selector(self.pan(_:))', '0')]:
        assert source.count(old) == 1, old
        source = source.replace(old, new, 1)
    source += '''
extension NagramiXPiPGestureController {
    func testDrivePan() { self.pan(self.recognizer) }
}
'''
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        production = folder / path.name
        production.write_text(source)
        for mode in ['debug', 'optimized']:
            binary = folder / 'gesture-test'
            cmd = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'),
                   str(ROOT / 'scripts/tests/NagramiXPiPGestureSupport.swift'),
                   str(ROOT / 'ios/Sources/GalleryUI/NagramiXPiPReleaseDecision.swift'),
                   str(ROOT / 'ios/Sources/GalleryUI/NagramiXPiPSourceGeometry.swift'),
                   str(production), str(ROOT / 'scripts/tests/NagramiXPiPGestureTests.swift'), '-o', str(binary)]
            if mode == 'optimized': cmd.insert(1, '-O')
            subprocess.run(cmd, check=True)
            result = subprocess.check_output([str(binary)], text=True, timeout=30).strip()
            results.append(mode + ': ' + result)
    return {'production_gesture_execution': results, 'UIKit_rendering': 'requires Apple SDK/device',
            'AVKit_animation': 'requires physical iPhone', 'iOS_IPA_build': 'not started'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--swiftc', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = json.dumps(validate(args.swiftc), ensure_ascii=False, indent=2) + '\n'
    if args.report: args.report.write_text(result)
    print(result, end='')
