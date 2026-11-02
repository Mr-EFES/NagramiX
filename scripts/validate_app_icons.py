#!/usr/bin/env python3
"""Run the actual icon coordinator and picker action with explicit UI boundaries."""
import argparse
import copy
import io
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import zipfile

from validate_quick_format import ROOT, manifest, block
from validate_unsigned_ipa import validate_app_icons

APP = 'submodules/TelegramUI/Sources/AppDelegate.swift'
PICKER = 'submodules/SettingsUI/Sources/Themes/ThemeSettingsController.swift'
HELPER = 'submodules/TelegramUI/Sources/NagramiXAppIconController.swift'


def guard_tests(before, plan):
    sys.path.insert(0, str(ROOT / 'ios'))
    from app_icons import apply_app_icons
    count = 0

    def rejected(change_plan=None, change_source=None, change_overlay=None):
        nonlocal count
        with tempfile.TemporaryDirectory(prefix='app-icon-guards-') as directory:
            root = Path(directory)
            source, overlay = root / 'source', root / 'overlay'
            for name in set(plan['inputs']) | set(plan['guards']):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((before / name).read_bytes())
            candidate = copy.deepcopy(plan)
            for item in plan['copies'].values():
                path = overlay / item['source']
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / 'ios' / item['source']).read_bytes())
            if change_plan:
                change_plan(candidate)
            (overlay / 'app_icons_patches.json').write_text(json.dumps(candidate))
            if change_source:
                change_source(source)
            if change_overlay:
                change_overlay(overlay)
            snapshot = manifest(source)
            try:
                apply_app_icons(source, overlay)
            except SystemExit:
                pass
            else:
                raise AssertionError('Invalid app icon plan/source was accepted')
            assert manifest(source) == snapshot, 'Partial mutation on failed guard'
            count += 1

    for name in set(plan['inputs']) | set(plan['guards']):
        rejected(change_source=lambda root, n=name: (root / n).write_bytes(b'drift'))
        rejected(change_source=lambda root, n=name: (root / n).unlink())
    for index in range(len(plan['patches'])):
        rejected(change_plan=lambda p, i=index: p['patches'][i].__setitem__(1, 'missing-anchor'))
    name = next(iter(plan['outputs']))
    rejected(change_plan=lambda p: p['outputs'].__setitem__(name, 'bad-sha'))
    rejected(change_plan=lambda p: p['outputs'].pop(name))
    rejected(change_plan=lambda p: p['inputs'].__setitem__('../escape', 'bad'))
    rejected(change_plan=lambda p: (p['inputs'].__setitem__('../escape', 'bad'), p['outputs'].__setitem__('../escape', 'bad')))
    dest, item = next(iter(plan['copies'].items()))
    rejected(change_source=lambda root: (root / dest).write_bytes(b'collision'))
    rejected(change_overlay=lambda root: (root / item['source']).unlink())
    rejected(change_overlay=lambda root: (root / item['source']).write_bytes(b'drift'))
    rejected(change_plan=lambda p: p['copies'][dest].__setitem__('source', '../escape'))
    rejected(change_plan=lambda p: p['copies'].__setitem__('/tmp/escape', p['copies'].pop(dest)))
    return count


def package_tests(path):
    prefix = 'Payload/NagramiX.app/'
    with zipfile.ZipFile(path) as archive:
        info = plistlib.loads(archive.read(prefix + 'Info.plist'))
        assert validate_app_icons(archive, prefix, info) == 8
        files = {n: archive.read(n) for n in archive.namelist()
                 if n.startswith(prefix + 'NagramiX') and n.endswith('.png')}

    def rejected(changed_info=None, changed_files=None):
        entries = files.copy()
        metadata = copy.deepcopy(info)
        if changed_info:
            changed_info(metadata)
        if changed_files:
            changed_files(entries)
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            for name, value in entries.items():
                z.writestr(name, value)
        data.seek(0)
        with zipfile.ZipFile(data) as z:
            try:
                validate_app_icons(z, prefix, metadata)
            except SystemExit:
                return
        raise AssertionError('Broken icon package passed')

    for index in range(2, 9):
        for scale in (2, 3):
            filename = prefix + f'NagramiX{index}@{scale}x.png'
            rejected(changed_files=lambda f, n=filename: f.pop(n))
        rejected(changed_info=lambda d, i=index: d['CFBundleIcons']['CFBundleAlternateIcons'].pop(f'NagramiX{i}'))
    rejected(changed_info=lambda d: d['CFBundleIcons']['CFBundleAlternateIcons']['NagramiX2'].__setitem__('CFBundleIconFiles', ['wrong']))
    rejected(changed_info=lambda d: d['CFBundleIcons~ipad']['CFBundleAlternateIcons'].pop('NagramiX2'))
    rejected(changed_files=lambda f: f.__setitem__(prefix + 'NagramiX2@3x.png', b'not a PNG'))
    rejected(changed_files=lambda f: f.__setitem__(prefix + 'NagramiX2@3x.png', f[prefix + 'NagramiX2@2x.png']))
    rejected(changed_files=lambda f: f.__setitem__(prefix + 'NagramiX2@3x.png', f[prefix + 'NagramiX3@3x.png']))
    return {'published_123_icon_resources': 'PASS; no missing icons', 'damaged_package_rejections': 26}


def validate(args):
    plan = json.loads((ROOT / 'ios/app_icons_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    assert set(before) - set(after) == set()
    assert set(after) - set(before) == set(plan['copies'])
    changed = {n for n in before if before[n] != after[n]}
    assert changed == set(plan['inputs'])
    assert all(before[n] == sha for n, sha in plan['inputs'].items())
    assert all(after[n] == sha for n, sha in plan['outputs'].items())
    old_picker, picker = (args.before / PICKER).read_text(), (args.after / PICKER).read_text()
    assert 'currentAppIconName.set(icon.name)' in old_picker
    assert 'requestSetAlternateIconName(icon.isDefault ? nil : icon.name, { _ in' in old_picker
    assert 'currentAppIconName.set(icon.name)' not in picker
    start = picker.index('                guard !nagramiXIsChangingAppIcon else {')
    end = picker.index('\n            }\n        })\n    }, editTheme:', start)
    action = picker[start:end]
    assert action.count('currentAppIconName.set(') == 1
    app = (args.after / APP).read_text()
    assert 'self.nagramiXAppIconController.request(name, completion: completion)' in app
    assert block(app, 'func handleDidBecomeActive()').count('nagramiXAppIconController.restoreIfNeeded()') == 1
    assert app.count('setAlternateIconName(name, completionHandler:') == 1
    for guard in plan['guards']:
        assert before[guard] == after[guard]
    assert '"Sources/**/*.swift"' in (args.after / 'submodules/TelegramUI/BUILD').read_text()
    executions = []
    with tempfile.TemporaryDirectory(prefix='app-icon-runtime-') as directory:
        tmp = Path(directory)
        tests = (ROOT / 'scripts/tests/NagramiXAppIconTests.swift').read_text()
        tests = tests.replace('NAGRAMIX_NATIVE_PICKER_ACTION', action, 1)
        (tmp / 'Tests.swift').write_text(tests)
        for mode in ['debug', 'optimized']:
            binary = tmp / mode
            command = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(tmp / 'cache'),
                       str(args.after / HELPER), str(ROOT / 'scripts/tests/NagramiXAppIconBoundary.swift'),
                       str(tmp / 'Tests.swift'), '-o', str(binary)]
            if mode == 'optimized':
                command.insert(1, '-O')
            subprocess.run(command, check=True)
            def run(arguments, settings):
                result = subprocess.run([str(binary), *arguments], text=True, capture_output=True,
                    env=dict(os.environ, XDG_CONFIG_HOME=str(settings)), timeout=30)
                assert result.returncode == 0, result.stdout + result.stderr
                return result.stdout.strip()
            output = run([], tmp / (mode + '-runtime'))
            cold = [run(['fresh'], tmp / (mode + '-fresh'))]
            for index in range(1, 9):
                name = f'NagramiX{index}'
                settings = tmp / (mode + '-' + name)
                cold.append(run(['write', name], settings))
                cold.append(run(['read', name], settings))
            executions.append(dict(mode=mode, output=output, cold_processes=len(cold), cold_results=cold))
        swift = [str(args.after / n) for n in list(plan['inputs']) + list(plan['copies']) if n.endswith('.swift')]
        subprocess.run([str(args.swiftc), '-frontend', '-parse', *swift], check=True)
    return dict(execution=executions, guards_rejected_without_writes=guard_tests(args.before, plan),
                package=package_tests(args.ipa), changed=sorted(changed), added=sorted(plan['copies']),
                other_files_byte_identical=len(before) - len(changed),
                baseline='optimistic selection; callback success discarded; no saved choice or restore',
                UIKit_SpringBoard_signing='not executed; physical device confirmation pending', Apple_SDK='pending separate build')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'ipa', 'report']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
