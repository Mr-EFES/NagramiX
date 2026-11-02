#!/usr/bin/env python3
"""Verify guarded debug presentation changes and real Foundation localization.

UIKit/controllers are parsed, not executed; Apple SDK and device checks remain
separate. The runtime test compiles the actual Core localization accessor with
only the external PresentationStrings data boundary supplied by the harness.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile

from validate_debug_localization import strings

ROOT = Path(__file__).resolve().parents[1]


def validate(args):
    plan = json.loads((ROOT / 'ios/debug_menu_localization_patches.json').read_text())
    names = set(plan['inputs'])
    assert names == set(plan['outputs'])
    assert names == {p['path'] for p in plan['patches']}
    for name in names:
        assert hashlib.sha256((args.before / name).read_bytes()).hexdigest() == plan['inputs'][name]
        assert hashlib.sha256((args.after / name).read_bytes()).hexdigest() == plan['outputs'][name]
    spec = importlib.util.spec_from_file_location('debug_overlay', ROOT / 'ios/debug_menu_localization.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    failures, runtime = [], []
    with tempfile.TemporaryDirectory(prefix='nagramix-debug-menu-') as directory:
        tmp = Path(directory)

        def seed(target):
            for name in names:
                dest = target / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(args.before / name, dest)

        def snapshot(target):
            return {str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in target.rglob('*') if p.is_file()}

        def reject(target, label, overlay=ROOT / 'ios'):
            saved = snapshot(target)
            try:
                module.apply_debug_menu_localization(target, overlay)
            except SystemExit:
                pass
            else:
                raise AssertionError(label)
            assert snapshot(target) == saved, label
            failures.append(label)

        replay = tmp / 'replay'
        seed(replay)
        module.apply_debug_menu_localization(replay, ROOT / 'ios')
        assert snapshot(replay) == plan['outputs']
        reject(replay, 'reapply')
        for index, name in enumerate(sorted(names)):
            for kind in ['missing', 'drift']:
                target = tmp / (kind + str(index))
                seed(target)
                if kind == 'missing':
                    (target / name).unlink()
                else:
                    (target / name).write_bytes((target / name).read_bytes() + b'\n// drift')
                reject(target, kind + ' ' + name)
        for kind in ['anchor', 'output', 'unsafe']:
            target, overlay = tmp / kind, tmp / (kind + '-overlay')
            seed(target)
            overlay.mkdir()
            custom = json.loads(json.dumps(plan))
            if kind == 'anchor':
                custom['patches'][-1]['old'] += '// missing'
            elif kind == 'output':
                custom['outputs'][next(iter(custom['outputs']))] = '0' * 64
            else:
                custom['inputs']['../escape.swift'] = '0' * 64
            (overlay / 'debug_menu_localization_patches.json').write_text(json.dumps(custom))
            reject(target, kind, overlay)

        resource_path = args.after / 'submodules/NagramiXCore/Resources'
        bundle = tmp / 'NagramiXLocalization.bundle'
        shutil.copytree(resource_path, bundle)
        (bundle / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': 'local.validation.localization',
            'CFBundleName': 'NagramiXLocalization', 'CFBundleDevelopmentRegion': 'en'}))
        ru = strings(bundle / 'ru.lproj/Localizable.strings')
        en = strings(bundle / 'en.lproj/Localizable.strings')
        keys = sorted(k for k in ru if k.startswith('NagramiX.Debug.'))
        fixture = tmp / 'labels.json'
        fixture.write_text(json.dumps([[k[len('NagramiX.Debug.'):], ru[k], en.get(k, k[len('NagramiX.Debug.'):])]
                                      for k in keys], ensure_ascii=False))
        helper = (args.helper).read_text().replace('import TelegramPresentationData\n', '')
        (tmp / 'Core.swift').write_text('''import Foundation
public struct PresentationStrings {
    public struct Component { public let languageCode: String }
    public let primaryComponent: Component
}
''' + helper)
        controller = (args.after / 'submodules/DebugSettingsUI/Sources/DebugController.swift').read_text()
        header = re.search(r'text: \.plain\((String\(format: .*?)\), sectionId: self.section, textAlignment: \.center\)', controller).group(1)
        (tmp / 'main.swift').write_text('''import Foundation
let rows = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))) as! [[String]]
var count = 0
for language in ["ru", "ru-RU", "RU", "en", "de"] {
    let strings = PresentationStrings(primaryComponent: .init(languageCode: language))
    for row in rows {
        let expected = language.lowercased().hasPrefix("ru") ? row[1] : row[2]
        precondition(strings.nagramiXDebugLocalized(row[0]) == expected, row[0])
        count += 1
    }
    precondition(strings.nagramiXDebugLocalized("Unknown debug label") == "Unknown debug label")
}
struct PresentationData { let strings: PresentationStrings }
let presentationData = PresentationData(strings: PresentationStrings(primaryComponent: .init(languageCode: "ru")))
let bundleVersion: Any = "0.6.9"
let bundleBuild: Any = 122
let bundleId = "com.example.nagramix"
let header = ''' + header + '''
precondition(header == "NagramiX для iOS 0.6.9 (122)\\ncom.example.nagramix")
let sensitive = "Имя %@ 😀"
precondition(String(format: presentationData.strings.nagramiXDebugLocalized("Engine: %@"), sensitive) == "Сетевой движок: " + sensitive)
precondition(String(format: presentationData.strings.nagramiXDebugLocalized("Open @%@ and unblock it before sending the log."), "iOSCrashReportsBot").contains("@iOSCrashReportsBot"))
print("PASS \\(count) real bundle lookups, language fallback and dynamic branding/format templates")
''')
        for mode in ['debug', 'optimized']:
            binary = tmp / mode
            command = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(tmp / 'cache'),
                       str(tmp / 'Core.swift'), str(tmp / 'main.swift'), '-o', str(binary)]
            if mode == 'optimized':
                command.insert(1, '-O')
            subprocess.run(command, check=True)
            env = dict(os.environ, XDG_CONFIG_HOME=str(tmp / 'prefs'))
            runtime.append(mode + ': ' + subprocess.check_output([str(binary), str(fixture)], env=env, text=True).strip())
        native = [str(args.after / n) for n in names if n.endswith('.swift')]
        subprocess.run([str(args.swiftc), '-frontend', '-parse', *native], check=True)
        coverage = subprocess.check_output(['python3', str(ROOT / 'scripts/validate_debug_localization.py'),
                                           '--source', str(args.after)], text=True).strip()
    return dict(files=sorted(names), operations=len(plan['patches']), fail_closed=failures,
                execution=runtime, coverage=coverage, Apple_SDK='pending', UIKit='not executed', iPhone='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'helper', 'swiftc', 'report']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    result = validate(args)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
