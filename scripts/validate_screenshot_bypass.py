#!/usr/bin/env python3
"""Проверка default-OFF, native screenshot hooks и live-защиты без iOS-сборки."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def manifest(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}


def validate(before, after, swiftc):
    plan = json.loads((ROOT / 'ios/screenshot_bypass_patches.json').read_text())
    old, new = manifest(before), manifest(after)
    assert new.keys() - old.keys() == set(plan['copies'].values()) and not old.keys() - new.keys()
    changed = {n for n in old if old[n] != new[n]}
    model = 'submodules/NagramiXMediaSettings/Sources/NagramiXPrivacySettings.swift'
    expected = {p[0] for p in plan['patches']} | {model, *[f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings' for lang in ['ru', 'en']]}
    assert changed == expected, changed ^ expected
    texts = {n: (before / n).read_text() for n in plan['hashes']}
    assert all(old[n] == sha for n, sha in plan['hashes'].items())
    for name, original, replacement, count in plan['patches']:
        assert texts[name].count(original) == count
        texts[name] = texts[name].replace(original, replacement, count)
    assert all(texts[n].encode() == (after / n).read_bytes() for n in texts)
    assert (after / model).read_bytes() == (ROOT / 'ios/Sources/NagramiXMediaSettings/Sources/NagramiXPrivacySettings.swift').read_bytes()
    for template, name in plan['copies'].items():
        assert (after / name).read_bytes() == (ROOT / 'ios' / template).read_bytes()

    spec = importlib.util.spec_from_file_location('screenshot', ROOT / 'ios/screenshot_bypass.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        def seed(folder):
            for name in plan['hashes']:
                path = folder / name; path.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(before / name, path)
            for name in plan['copies'].values():
                (folder / name).parent.mkdir(parents=True, exist_ok=True)
        def reject(folder, label, overlay=ROOT / 'ios'):
            saved = manifest(folder)
            try: module.apply_screenshot_bypass(folder, overlay)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError(label)
            assert manifest(folder) == saved, 'partial write: ' + label
            rejected.append(label)
        folder = base / 'valid'; seed(folder); module.apply_screenshot_bypass(folder, ROOT / 'ios')
        assert all((folder / n).read_bytes() == (after / n).read_bytes() for n in plan['hashes'])
        reject(folder, 'reapply')
        for i, name in enumerate(plan['hashes']):
            for kind in ['drift', 'missing']:
                folder = base / (kind + str(i)); seed(folder)
                if kind == 'drift': (folder / name).write_bytes((folder / name).read_bytes() + b'\n// drift\n')
                else: (folder / name).unlink()
                reject(folder, kind + ' ' + name)
        for i, (template, name) in enumerate(plan['copies'].items()):
            folder = base / ('collision' + str(i)); seed(folder); (folder / name).write_text('// collision')
            reject(folder, 'collision ' + name)
            folder = base / ('template' + str(i)); seed(folder)
            overlay = base / ('overlay' + str(i)); overlay.mkdir()
            shutil.copy2(ROOT / 'ios/screenshot_bypass_patches.json', overlay)
            for other in plan['copies']:
                if other != template:
                    path = overlay / other; path.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / 'ios' / other, path)
            reject(folder, 'missing template ' + template, overlay)
        folder = base / 'missing-parent'; seed(folder)
        (folder / 'submodules/TelegramCore/Sources/Utils').rmdir()
        reject(folder, 'missing target parent')

    execution = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        # UIKit and encrypted enqueue are the boundaries; actual production
        # registry, settings, eligibility expression and engine guard run below.
        helper = (after / 'submodules/Display/Source/NagramiXCaptureProtection.swift').read_text()
        (folder / 'Registry.swift').write_text('import Foundation\n' + '\n'.join(line for line in helper.splitlines() if not line.startswith('import ')) + '\n')
        policy = (after / 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift').read_text()
        (folder / 'Policy.swift').write_text('\n'.join(line for line in policy.splitlines() if not line.startswith('import ')) + '\n')
        engine = (after / 'submodules/TelegramCore/Sources/TelegramEngine/Messages/TelegramEngineMessages.swift').read_text()
        method = 'public func addSecretChatMessageScreenshot(peerId: PeerId) -> Signal<Never, NoError> {'
        body = engine.split(method, 1)[1].split('\n        }', 1)[0]
        (folder / 'Engine.swift').write_text('final class ProductionScreenshotEngine {\nlet account: ScreenshotAccount\ninit(account: ScreenshotAccount) { self.account = account }\n' + method + body + '\n}\n}\n')
        ui = (after / 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift').read_text()
        blocks = re.findall(r'case let \.privacyToggle\(option, _\):\s+switch option \{(.*?)\n\s+\}', ui, re.S)
        assert len(blocks) == 2
        (folder / 'UI.swift').write_text('\n'.join('func ' + name + '(_ option: NagramiXPrivacySettings.Option) -> Int32 { switch option {' + block + '\n} }' for name, block in zip(['productionPrivacyStableId', 'productionPrivacyPosition'], blocks)) + '\n')
        sources = [after / ('submodules/NagramiXMediaSettings/Sources/' + n) for n in ['NagramiXPrivacySettings.swift', 'NagramiXReadModeSettings.swift']]
        sources += [folder / n for n in ['Registry.swift', 'Policy.swift', 'Engine.swift', 'UI.swift']]
        sources += [ROOT / 'scripts/tests/NagramiXScreenshotBypassTests.swift']
        for mode in ['debug', 'optimized']:
            binary = folder / ('test-' + mode)
            command = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *map(str, sources), '-o', str(binary)]
            if mode == 'optimized': command.insert(1, '-O')
            subprocess.run(command, check=True)
            env = dict(os.environ, XDG_CONFIG_HOME=str(folder / ('preferences-' + mode)))
            execution.append(mode + ': ' + subprocess.check_output([str(binary)], env=env, text=True, timeout=30).strip())
            for value in ['true', 'false', 'true', 'false']:
                suite = 'nagramix.screenshots.cold.' + mode
                subprocess.run([str(binary), '--set', suite, value], env=env, check=True, timeout=15)
                subprocess.run([str(binary), '--cold', suite, value], env=env, check=True, timeout=15)
            execution.append(mode + ': PASS 8 separate cold processes')
        subprocess.run([str(swiftc), '-frontend', '-parse', *[str(after / n) for n in changed | set(plan['copies'].values()) if n.endswith('.swift')]], check=True)

    rows = ui.split('private func nagramiXAllSettingsEntries', 1)[1].split('private func nagramiXSettingsEntries', 1)[0]
    assert rows.count('.privacyToggle(') == 5 and rows.count('.privacyToggle(.screenshotBypass,') == 1 and '.automaticOffline' not in ui
    assert rows.index('.messagesHeader') < rows.index('.privacyHeader') < rows.index('.callsHeader')
    for lang, title in [('ru', 'Обход защиты от скриншотов'), ('en', 'Bypass screenshot protection')]:
        strings = (after / f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        assert strings.count('"NagramiX.Privacy.screenshotBypass" = "' + title + '";') == 1
        assert strings.count('"NagramiX.Privacy.screenshotBypass.Search" = ') == 1
    return {'outputs': len(new), 'changed': sorted(changed), 'added': sorted(new.keys() - old.keys()), 'unchanged': len(old)-len(changed), 'sha_guards': len(plan['hashes']), 'exact_operations': len(plan['patches']), 'fail_closed': rejected, 'execution': execution, 'apple_sdk': 'not run: no build authorization', 'physical_iphone': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']: parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.before, args.after, args.swiftc)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
