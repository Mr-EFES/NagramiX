#!/usr/bin/env python3
"""Validate the historical read_modes stage before privacy_actions, without an iOS build."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'submodules/NagramiXMediaSettings/Sources/NagramiXReadModeSettings.swift'
GHOST = 'submodules/NagramiXMediaSettings/Sources/NagramiXGhostSettings.swift'
PRIVACY = 'submodules/NagramiXMediaSettings/Sources/NagramiXPrivacySettings.swift'
STORY = 'submodules/NagramiXMediaSettings/Sources/NagramiXStorySettings.swift'
LEDGER = 'submodules/TelegramCore/Sources/NagramiXGhostReadActions.swift'
HELPER = 'submodules/TelegramCore/Sources/NagramiXReadModeActions.swift'


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def validate(before, after, stage_before, swiftc):
    plan = json.loads((ROOT / 'ios/read_mode_patches.json').read_text())
    a, b = manifest(before), manifest(after)
    retired = 'submodules/SettingsUI/Sources/NagramiXGhostSettingsController.swift'
    assert b.keys() - a.keys() == {PRIVACY} and a.keys() - b.keys() == {retired}
    extras = {GHOST, MODEL, STORY, LEDGER, 'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift',
              *[f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings' for lang in ['ru', 'en']]}
    changed = {name for name in a.keys() & b.keys() if a[name] != b[name]}
    assert changed == {'submodules/SettingsUI/Sources/NagramiXSettingsController.swift', 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift'} | extras, changed
    for template, native in plan['copies'].items():
        assert (after / native).read_bytes() == (ROOT / 'ios' / template).read_bytes()
    for native, template in [(MODEL, 'Sources/NagramiXMediaSettings/Sources/NagramiXReadModeSettings.swift'),
                             (PRIVACY, 'Sources/NagramiXMediaSettings/Sources/NagramiXPrivacySettings.swift'),
                             (GHOST, 'Sources/NagramiXMediaSettings/Sources/NagramiXGhostSettings.swift'),
                             (LEDGER, 'Sources/TelegramCore/NagramiXGhostReadActions.swift')]:
        assert (after / native).read_bytes() == (ROOT / 'ios' / template).read_bytes()
    restored = {name: (after / name).read_text() for name in plan['hashes']}
    for name, old, new, count in reversed(plan['patches']):
        assert restored[name].count(new) == count, (name, new[:80])
        restored[name] = restored[name].replace(new, old, count)
    assert all(restored[name].encode() == (stage_before / name).read_bytes() for name in restored)
    assert all(hashlib.sha256((stage_before / name).read_bytes()).hexdigest() == expected for name, expected in plan['hashes'].items())
    spec = importlib.util.spec_from_file_location('read_modes', ROOT / 'ios/read_modes.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []
    with tempfile.TemporaryDirectory() as folder:
        native, overlay = Path(folder) / 'native', Path(folder) / 'ios'

        def seed():
            for path in [native, overlay]:
                if path.exists():
                    shutil.rmtree(path)
            for name in [*plan['hashes'], MODEL, PRIVACY]:
                target = native / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(stage_before / name, target)
            for name in ['read_mode_patches.json', 'Sources/NagramiXMediaSettings/Sources/NagramiXReadModeSettings.swift', 'Sources/NagramiXMediaSettings/Sources/NagramiXPrivacySettings.swift', *plan['copies']]:
                target = overlay / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / 'ios' / name, target)

        def reject(label):
            old = manifest(native)
            try:
                module.apply_read_modes(native, overlay)
            except (SystemExit, FileNotFoundError):
                pass
            else:
                raise AssertionError(label)
            assert manifest(native) == old, label
            rejected.append(label)

        seed()
        module.apply_read_modes(native, overlay)
        assert all((native / name).read_bytes() == (after / name).read_bytes() for name in [*plan['hashes'], HELPER])
        reject('reapply')
        for name in plan['hashes']:
            seed(); (native / name).write_bytes((native / name).read_bytes() + b'\n// drift'); reject('drift ' + name)
            seed(); (native / name).unlink(); reject('missing ' + name)
        seed(); (native / MODEL).write_text('// drift'); reject('wrong settings model')
        seed(); (native / MODEL).unlink(); reject('missing settings model')
        seed(); (native / PRIVACY).write_text('// drift'); reject('wrong privacy model')
        seed(); (native / PRIVACY).unlink(); reject('missing privacy model')
        seed(); target = native / HELPER; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('collision'); reject('helper collision')
        for name in plan['copies']:
            seed(); (overlay / name).unlink(); reject('missing template ' + name)
    execution = []
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        env = dict(os.environ)
        # Linux Foundation persists under XDG_CONFIG_HOME, inside the workspace
        # sandbox. No HOME or developer preferences are changed.
        env['XDG_CONFIG_HOME'] = str(folder / 'preferences')
        ledger = (after / LEDGER).read_text()
        for name, text in [('ProductionPrivateReadLedger.swift', ledger), ('ProductionReadModeActions.swift', (after / HELPER).read_text())]:
            (folder / name).write_text('import Foundation\n' + '\n'.join(line for line in text.splitlines() if not line.startswith('import ')) + '\n')
        models = [after / MODEL, after / PRIVACY, after / GHOST, after / STORY]
        suites = {
            'independent privacy/presence': [ROOT / 'scripts/tests/NagramiXGhostSettingsTests.swift'],
            'legacy privacy migration': [ROOT / 'scripts/tests/NagramiXPrivacySettingsTests.swift'],
            'mode persistence': [ROOT / 'scripts/tests/NagramiXReadModeTests.swift'],
            'production read contract with doubles': [folder / 'ProductionPrivateReadLedger.swift', folder / 'ProductionReadModeActions.swift', ROOT / 'scripts/tests/NagramiXReadModeActionTests.swift'],
        }
        for mode in ['debug', 'optimized']:
            for name, tests in suites.items():
                binary = folder / 'test'
                command = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *map(str, models + tests), '-o', str(binary)]
                if mode == 'optimized':
                    command.insert(1, '-O')
                subprocess.run(command, check=True, cwd=folder, env=env)
                result = subprocess.check_output([str(binary)], text=True, env=env, cwd=folder, timeout=40).strip()
                execution.append(f'{mode} {name}: {result}')
        files = [after / name for name in changed | {PRIVACY, HELPER} if name.endswith('.swift')]
        subprocess.run([str(swiftc), '-frontend', '-parse', *map(str, files)], check=True, cwd=folder)
    for lang in ['ru', 'en']:
        text = (after / f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        for suffix in ['Local', 'Local.Search']:
            assert text.count(f'"NagramiX.ReadMode.{suffix}" = ') == 1
        for suffix in ['Title', *[s for option in ['storyReads', 'online', 'typing', 'automaticOffline', 'readOnAction'] for s in [option, option + '.Search']]]:
            assert text.count(f'"NagramiX.Privacy.{suffix}" = ') == 1
    ui = (after / 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift').read_text()
    assert all(name not in ui for name in ['ghostMode', 'openGhostSettings', 'nagramiXGhostSettingsController', 'anonymousStoryViewing'])
    rows = ui.split('private func nagramiXAllSettingsEntries', 1)[1].split('private func nagramiXSettingsEntries', 1)[0]
    assert rows.index('.messagesHeader') < rows.index('.clearMessageArchive') < rows.index('.privacyHeader') < rows.index('.callsHeader')
    assert rows.count('.privacyHeader') == 1 and rows.count('.readLocally(') == 1 and rows.count('.readOnServer(') == 1 and rows.count('.privacyToggle(') == 5
    assert 'case let .privacyToggle(option, value):\n            return ItemListSwitchItem' in ui
    assert 'nagramiXPrivacySettingsSignal()' in ui
    tabs = (after / 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift').read_text()
    assert 'if previousAnonymousStoryViewing != value.anonymousStoryViewing {' in tabs
    return {'outputs': len(b), 'changed': sorted(changed), 'new': sorted(b.keys() - a.keys()), 'removed': sorted(a.keys() - b.keys()), 'unchanged': len(a.keys() & b.keys()) - len(changed),
            'sha_guards': len(plan['hashes']), 'reverse_patches': len(plan['patches']), 'guard_cases': rejected,
            'execution': execution, 'apple_sdk': 'not run; requires separate build authorization', 'physical_iphone': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--stage-before', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.before, args.after, args.stage_before, args.swiftc)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
