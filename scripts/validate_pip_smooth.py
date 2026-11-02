#!/usr/bin/env python3
"""Execute final PiP geometry/gesture tests; AVKit placement remains system-owned."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from validate_quick_format import manifest

ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = 'submodules/GalleryUI/Sources/NagramiXPiPSourceGeometry.swift'
GESTURE = 'submodules/GalleryUI/Sources/NagramiXPiPGestureController.swift'


def validate(args):
    plan = json.loads((ROOT / 'ios/pip_smooth_patches.json').read_text())
    a, b = manifest(args.before), manifest(args.after)
    assert a.keys() == b.keys()
    assert {n for n in a if a[n] != b[n]} == {GEOMETRY}
    assert plan['hashes'] == {GEOMETRY: a[GEOMETRY]}
    spec = importlib.util.spec_from_file_location('pip_smooth', ROOT / 'ios/pip_smooth.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected, results = [], []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        def seed(name):
            tree = folder / name; (tree / GEOMETRY).parent.mkdir(parents=True)
            shutil.copyfile(args.before / GEOMETRY, tree / GEOMETRY)
            return tree
        def reject(tree, label, overlay=ROOT / 'ios'):
            prior = manifest(tree)
            try: module.apply_pip_smooth(tree, overlay)
            except SystemExit: pass
            else: raise AssertionError(label)
            assert manifest(tree) == prior; rejected.append(label)
        tree = seed('valid'); module.apply_pip_smooth(tree, ROOT / 'ios')
        assert (tree / GEOMETRY).read_bytes() == (args.after / GEOMETRY).read_bytes()
        reject(tree, 'reapply')
        tree = seed('missing'); (tree / GEOMETRY).unlink(); reject(tree, 'missing')
        tree = seed('drift'); (tree / GEOMETRY).write_text('// drift'); reject(tree, 'drift')
        for index in range(len(plan['patches'])):
            invalid = json.loads(json.dumps(plan)); invalid['patches'][index][1] += '// drift'
            overlay = folder / ('overlay' + str(index)); overlay.mkdir()
            (overlay / 'pip_smooth_patches.json').write_text(json.dumps(invalid))
            reject(seed('anchor' + str(index)), 'anchor ' + str(index), overlay)
        # Execute the unchanged production gesture against final generated geometry.
        gesture = (args.after / GESTURE).read_text()
        for old, new in [('import UIKit\n', ''), ('import Display\n', ''), ('@objc private func pan(', 'private func pan('), ('#selector(self.pan(_:))', '0')]:
            assert gesture.count(old) == 1; gesture = gesture.replace(old, new, 1)
        gesture += '\nextension NagramiXPiPGestureController { func testDrivePan() { self.pan(self.recognizer) } }\n'
        native = folder / 'Gesture.swift'; native.write_text(gesture)
        release = args.after / 'submodules/GalleryUI/Sources/NagramiXPiPReleaseDecision.swift'
        suites = {
            'geometry': [release, args.after / GEOMETRY, ROOT / 'scripts/tests/NagramiXPiPSourceGeometryTests.swift'],
            'continuity': [release, args.after / GEOMETRY, ROOT / 'scripts/tests/NagramiXPiPHandoffContinuityTests.swift'],
            'smooth': [release, args.after / GEOMETRY, ROOT / 'scripts/tests/NagramiXPiPSmoothTests.swift'],
            'gesture': [ROOT / 'scripts/tests/NagramiXPiPGestureSupport.swift', release, args.after / GEOMETRY, native, ROOT / 'scripts/tests/NagramiXPiPGestureTests.swift'],
        }
        for mode in ['debug', 'optimized']:
            for label, paths in suites.items():
                binary = folder / (mode + label)
                cmd = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *map(str, paths), '-o', str(binary)]
                if mode == 'optimized': cmd.insert(1, '-O')
                subprocess.run(cmd, check=True)
                results.append(mode + ' ' + label + ': ' + subprocess.check_output([str(binary)], text=True, timeout=30).strip())
        subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.after / GEOMETRY)], check=True)
    for n in ['ios/pip_smooth.py', 'ios/apply_features.py', 'scripts/validate_pip_smooth.py']: ast.parse((ROOT / n).read_text())
    return dict(outputs=len(b), changed=[GEOMETRY], unchanged=len(b)-1, guards=1, operations=len(plan['patches']), fail_closed=rejected, runtime=results, UIKit_AVKit='boundaries; final window placement cannot be specified through public AVKit API', SDK_IPA='not started', device='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ['before', 'after', 'swiftc', 'report']: parser.add_argument('--'+n, type=Path, required=True)
    args = parser.parse_args(); result = validate(args)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
