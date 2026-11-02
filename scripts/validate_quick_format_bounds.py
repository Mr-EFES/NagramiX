#!/usr/bin/env python3
"""Reproduce stale formatting bounds and verify the actual native adapter.

UIKit/Texture are interface boundaries here, not a simulated iPhone renderer.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from validate_quick_format import ROOT, HELPER, manifest, block
from validate_quick_format_visual import GEOMETRY, KEYBOARD
from validate_quick_format_panel import FACTORY, boundaries


def validate(args):
    plan = json.loads((ROOT / 'ios/quick_format_surface_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    assert before.keys() == after.keys()
    assert {n for n in before if before[n] != after[n]} == set(plan['inputs'])
    assert all(before[n] == sha for n, sha in plan['inputs'].items())
    assert all(after[n] == sha for n, sha in plan['outputs'].items())
    a, b = (args.before / FACTORY).read_text(), (args.after / FACTORY).read_text()
    for marker in ['func inputNodeForChatPresentationIntefaceState(', 'override func updateLayout(']:
        assert block(a, marker) == block(b, marker), marker
    executions = []
    with tempfile.TemporaryDirectory(prefix='format-bounds-') as directory:
        tmp = Path(directory)
        for label, source in [('baseline', args.before), ('fixed', args.after)]:
            first, second = boundaries(source)
            second = second.replace('class ChatInputNode {', '''class ChatInputNode {
    var bounds = CGRect.zero
    func layout() {}
''', 1)
            (tmp / 'Boundary.swift').write_text(first)
            (tmp / 'NativeBoundary.swift').write_text(second)
            for name, declaration in [('NagramiXQuickFormattingTests.swift', 'QuickFormattingTests'),
                                      ('NagramiXFormattingPanelTests.swift', 'FormattingPanelTests')]:
                text = (ROOT / 'scripts/tests' / name).read_text()
                assert text.count('@main struct ' + declaration) == 1
                (tmp / name).write_text(text.replace('@main struct ' + declaration, 'struct ' + declaration, 1))
            modes = ['debug'] if label == 'baseline' else ['debug', 'optimized']
            for mode in modes:
                binary = tmp / (label + '-' + mode)
                command = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(tmp / 'cache'),
                    str(tmp / 'Boundary.swift'), str(tmp / 'NativeBoundary.swift'),
                    str(tmp / 'NagramiXQuickFormattingTests.swift'), str(tmp / 'NagramiXFormattingPanelTests.swift'),
                    str(source / HELPER), str(source / GEOMETRY),
                    str(ROOT / 'scripts/tests/NagramiXFormattingBoundsTests.swift'), '-o', str(binary)]
                if mode == 'optimized':
                    command.insert(1, '-O')
                subprocess.run(command, check=True)
                run = subprocess.run([str(binary)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env=dict(os.environ, XDG_CONFIG_HOME=str(tmp / (label + mode))), timeout=30)
                if label == 'baseline':
                    assert run.returncode == 1 and 'FAIL: formatting must fill the actual visible host' in run.stdout
                else:
                    assert run.returncode == 0, run.stdout + run.stderr
                    assert 'PASS 74 formatting bounds/resize regression checks' in run.stdout
                executions.append(dict(source=label, mode=mode, exit=run.returncode, output=run.stdout.strip()))
        subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.after / FACTORY), str(args.after / KEYBOARD)], check=True)
    return dict(execution=executions, native_factory_and_preferred_height='unchanged',
        UIKit='not executed; native lifecycle/API boundaries', Apple_SDK='pending separate build', physical_iPhone='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
