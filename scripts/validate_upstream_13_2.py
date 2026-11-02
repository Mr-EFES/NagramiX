#!/usr/bin/env python3
"""Проверить точные входы и трёхсторонний перенос базы Telegram 13.1.2."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_plan(stage):
    return json.loads((OVERLAY / (stage + '_patches.json')).read_text())

def check_stage(stage, swiftc):
    plan = read_plan(stage)
    spec = importlib.util.spec_from_file_location(stage, OVERLAY / (stage + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='nagramix-upstream-132-') as folder:
        source = Path(folder)
        for name, template in plan['previous'].items():
            target = source / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((OVERLAY / template).read_bytes())
        getattr(module, 'apply_' + stage)(source, OVERLAY)
        for name, expected in plan['outputs'].items():
            assert digest((source / name).read_bytes()) == expected, name
            if swiftc and name.endswith('.swift'):
                subprocess.run([swiftc, '-frontend', '-parse', str(source / name)], check=True)
        try: getattr(module, 'apply_' + stage)(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError(stage + ': повторное применение должно отклоняться')
        # Reject source drift without writing any of the prepared files.
        for name, template in plan['previous'].items(): (source / name).write_bytes((OVERLAY / template).read_bytes())
        first = next(iter(plan['inputs'])); (source / first).write_bytes(b'invalid')
        snapshot = {name: (source / name).read_bytes() for name in plan['inputs']}
        try: getattr(module, 'apply_' + stage)(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError(stage + ': повреждение входа должно отклоняться')
        assert all((source / name).read_bytes() == data for name, data in snapshot.items())

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--swiftc'); args = parser.parse_args()
    pre = read_plan('upstream_13_2_pre'); post = read_plan('upstream_13_2_post')
    assert set(pre['inputs']) == set(post['inputs'])
    assert json.loads((OVERLAY / pre['previous']['versions.json']).read_text())['app'] == '13.1.2'
    for name in pre['inputs']:
        if name == 'versions.json': continue
        with tempfile.TemporaryDirectory(prefix='nagramix-132-merge-') as folder:
            directory = Path(folder)
            paths = [directory / label for label in ['ours', 'old', 'new']]
            paths[0].write_bytes((OVERLAY / post['previous'][name]).read_bytes())
            paths[1].write_bytes((OVERLAY / pre['replacements'][name]).read_bytes())
            paths[2].write_bytes((OVERLAY / pre['previous'][name]).read_bytes())
            result = subprocess.run(['git', 'merge-file', '-p', '--diff3', '-L', 'NagramiX', '-L', '13.1.1', '-L', '13.1.2', *map(str, paths)], capture_output=True, check=True)
            assert result.stdout == (OVERLAY / post['replacements'][name]).read_bytes(), name
    check_stage('upstream_13_2_pre', args.swiftc)
    check_stage('upstream_13_2_post', args.swiftc)
    print('PASS: Telegram 13.1.2 — точные версии, объединение и guards')

if __name__ == '__main__': main()
