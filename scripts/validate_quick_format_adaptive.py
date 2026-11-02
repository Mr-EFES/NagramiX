#!/usr/bin/env python3
"""Проверка утверждённой сетки на реальном преобразованном Swift и строгих SHA."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('adaptive', ROOT/'ios/quick_format_adaptive.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plan = json.loads((ROOT/'ios/quick_format_adaptive_patches.json').read_text())
    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        native = temp/'native'
        before = {}
        for name in plan['inputs']:
            before[name] = (args.source/name).read_bytes()
            path = native/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(before[name])
        module.apply_quick_format_adaptive(native, ROOT/'ios')
        after = {name:(native/name).read_bytes() for name in before}
        for name, data in after.items():
            assert hashlib.sha256(data).hexdigest() == plan['outputs'][name]
            restored = data.decode()
            for target, old, new, count in reversed(plan['patches']):
                if target == name:
                    assert restored.count(new) == count
                    restored = restored.replace(new, old, count)
            assert restored.encode() == before[name]
        geometry = after[PREFIX+'NagramiXFormattingGeometry.swift'].decode()
        assert geometry.split('struct NagramiXFormattingGrid')[0] == before[PREFIX+'NagramiXFormattingGeometry.swift'].decode().split('struct NagramiXFormattingGrid')[0]
        test = ROOT/'scripts/tests/NagramiXFormattingAdaptiveTests.swift'
        source = temp/'geometry.swift'
        keyboard = after[PREFIX+'NagramiXFormattingKeyboard.swift'].decode()
        band_code = keyboard.split('        let headingHeight = ceil(headingSize.height)', 1)[1].split('        let font =', 1)[0]
        band_code = '        let headingHeight = ceil(headingSize.height)' + band_code
        # Execute the actual UIKit frame arithmetic at a Foundation-only boundary.
        boundary = r'''
final class FormatFrame { var frame = CGRect.zero }
final class FormatBands {
    struct Insets { var bottom: CGFloat }
    var bounds: CGRect
    var safeAreaInsets: Insets
    let heading = FormatFrame(), scroll = FormatFrame()
    init(height: CGFloat, safeBottom: CGFloat) {
        bounds = CGRect(x: 0, y: 0, width: 390, height: height)
        safeAreaInsets = Insets(bottom: safeBottom)
    }
    func layout(landscape: Bool, textHeight: CGFloat) {
        let headingSize = CGSize(width: 300, height: textHeight)
        let headingLeft: CGFloat = 38, headingWidth: CGFloat = 314
        let left: CGFloat = 8, contentWidth: CGFloat = 374
BAND_CODE
    }
}
func verifyFormattingBands() {
    for landscape in [false, true] {
        for bottom: CGFloat in [0, 21, 34] {
            for height: CGFloat in [162, 216, 291, 346] {
                let host = FormatBands(height: height, safeBottom: bottom)
                host.layout(landscape: landscape, textHeight: 21)
                let top = host.scroll.frame.minY
                let lower = height - host.scroll.frame.maxY
                precondition(abs(top - lower) < 0.001)
                precondition(lower >= bottom + 8)
                precondition(host.heading.frame.maxY <= top)
                precondition(abs(host.heading.frame.midY - top / 2 - 2) <= 0.5)
            }
        }
    }
    print("PASS: 24 actual band layouts; equal insets, safe area once, optical title centering")
}
'''.replace('BAND_CODE', band_code)
        source.write_text(geometry + boundary)
        for flags in [[], ['-O']]:
            executable = temp/('tests-opt' if flags else 'tests')
            subprocess.run([args.swiftc, '-module-cache-path', str(temp/'cache'), *flags, str(source), str(test), '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True)
        for name in after:
            subprocess.run([args.swiftc, '-frontend', '-parse', str(native/name)], check=True)
        # Every failure must leave ALL inputs untouched, even when the second file drifts.
        def rejected(overlay):
            snapshot = {n:(native/n).read_bytes() if (native/n).exists() else None for n in before}
            try:
                module.apply_quick_format_adaptive(native, overlay)
            except SystemExit:
                pass
            else:
                raise AssertionError('drift accepted')
            assert snapshot == {n:(native/n).read_bytes() if (native/n).exists() else None for n in before}
        rejected(ROOT/'ios')
        for name in before:
            (native/name).write_bytes(before[name])
        last = list(before)[-1]
        (native/last).write_bytes(before[last]+b'\n')
        rejected(ROOT/'ios')
        (native/last).unlink()
        rejected(ROOT/'ios')
        overlay = temp/'overlay'
        overlay.mkdir()
        for kind in ['anchor','output']:
            for name,data in before.items(): (native/name).write_bytes(data)
            broken = json.loads(json.dumps(plan))
            if kind == 'anchor': broken['patches'][-1][1] += '// drift'
            else: broken['outputs'][last] = '0'*64
            (overlay/'quick_format_adaptive_patches.json').write_text(json.dumps(broken))
            rejected(overlay)
        print('PASS: native Swift parse, inverse, unchanged height cache, 5 atomic fail-closed cases')

if __name__ == '__main__':
    main()
