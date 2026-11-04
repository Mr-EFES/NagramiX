#!/usr/bin/env python3
"""Проверить выбранный язык, полноту каталогов и форматные аргументы."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import tempfile

from localization_literals import canonical, literals

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'app_language_localization_patches.json').read_text())
LANGUAGES = json.loads((OVERLAY / 'app_language_localization/languages.json').read_text())


def strings(path):
    pairs = re.findall(r'^"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)";', path.read_text(), re.M)
    result = [(json.loads('"' + k + '"'), json.loads('"' + v + '"')) for k, v in pairs]
    assert len(result) == len(dict(result)), str(path)
    return dict(result)


def runtime_checks(source, swiftc):
    with tempfile.TemporaryDirectory(prefix='nagramix-language-runtime-') as folder:
        temp = Path(folder)
        bundle = temp / 'NagramiXLocalization.bundle'
        bundle.mkdir()
        (bundle / 'Info.plist').write_bytes(plistlib.dumps({
            'CFBundleIdentifier': 'com.mr-efes.nagramix.localization.test',
            'CFBundleName': 'NagramiXLocalization', 'CFBundleDevelopmentRegion': 'en',
            'CFBundlePackageType': 'BNDL',
        }))
        codes = [item['code'] for item in LANGUAGES['languages']]
        for code in codes:
            path = bundle / (code + '.lproj') / 'Localizable.strings'
            path.parent.mkdir()
            production = source / ('submodules/NagramiXCore/Resources/' + code + '.lproj/Localizable.strings')
            # Explicit per-language sentinel tests routing only. It is never
            # shipped or counted as a completed production language catalog.
            data = production.read_text() if production.is_file() else ''
            path.write_text(data + '\n"NagramiX.Test.LanguageCode" = ' + json.dumps(code) + ';\n')
        # Preserve production German when available. The partial fixture only
        # supports historical source validation before the catalogs stage.
        de = {'NagramiX.Settings.Page.Other': 'Weitere',
              'NagramiX.UI.52cdc06c6e0c9608': 'Hochwertige Videonachrichten',
              'NagramiX.UI.a02ed87b286f42e7': 'Nachrichtenübersetzung'}
        path = bundle / 'de.lproj' / 'Localizable.strings'
        if not (source / 'submodules/NagramiXCore/Resources/de.lproj/Localizable.strings').is_file():
            path.write_text(''.join(json.dumps(k) + ' = ' + json.dumps(v, ensure_ascii=False) + ';\n' for k, v in de.items()) + '\n"NagramiX.Test.LanguageCode" = "de";\n')
        text = (ROOT / 'scripts/tests/NagramiXUILocalizationTests.swift').read_text()
        text += '\nlet testedLanguageCodes: [String] = ' + json.dumps(codes) + '\n'
        # Exercise every real resource value through the actual Swift resolver,
        # independent of synthetic routing sentinels.
        production = {code: strings(source / ('submodules/NagramiXCore/Resources/' + code + '.lproj/Localizable.strings'))
                      for code in codes if (source / ('submodules/NagramiXCore/Resources/' + code + '.lproj/Localizable.strings')).is_file()}
        expected = temp / 'production-catalogs.json'
        expected.write_text(json.dumps(production, ensure_ascii=False))
        text += '\nlet productionCatalogs = try! JSONDecoder().decode([String: [String: String]].self, from: Data(contentsOf: URL(fileURLWithPath: ' + json.dumps(str(expected)) + ')))\n'
        for name in ['NagramiXPresentationStrings.swift', 'NagramiXAppLocalization.swift']:
            text += '\n' + (source / 'submodules/NagramiXCore/Sources' / name).read_text().replace('import TelegramPresentationData\n', '')
        suite = temp / 'checks.swift'
        suite.write_text(text)
        for optimized in [False, True]:
            binary = temp / ('checks-O' if optimized else 'checks-debug')
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized:
                command.append('-O')
            subprocess.run([*command, str(suite), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--allow-incomplete-catalogs', action='store_true',
                        help='Локальная проверка механизма во время подготовки; не проверка готовности релиза')
    args = parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    for stage in ('vosk_model_naming', 'local_asr_memory', 'archive_post_lifecycle', 'localization_standard', 'temporary_voice_transcription'):
        if delegate_icon_stage_if_applied(args, Path(__file__), stage):
            return
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert hashlib.sha256((args.source / name).read_bytes()).hexdigest() == digest, name
    for name, item in PLAN['copies'].items():
        assert hashlib.sha256((args.source / name).read_bytes()).hexdigest() == item['sha256'], name
    resources = args.source / 'submodules/NagramiXCore/Resources'
    en = strings(resources / 'en.lproj/Localizable.strings')
    assert len(en) == LANGUAGES['keys_per_catalog']
    assert not any(re.search('[А-Яа-яЁё]', value) for value in en.values()), 'Russian text in English catalog'
    placeholders = lambda value: sorted(re.findall(r'%(?:[0-9]+\$)?[@dfius]|%%', value))
    available = {}
    for path in resources.glob('*.lproj/Localizable.strings'):
        language = path.parent.name.removesuffix('.lproj')
        values = strings(path)
        assert set(values) == set(en), 'Incomplete keys: ' + language
        for key in en:
            assert values[key].strip(), (language, key)
            assert placeholders(values[key]) == placeholders(en[key]), (language, key)
        available[language] = values
    expected = {item['code'] for item in LANGUAGES['languages']}
    missing = sorted(expected - available.keys())
    if missing and not args.allow_incomplete_catalogs:
        raise SystemExit('Локализация не готова к выпуску. Нет каталогов: ' + ', '.join(missing))
    catalog = json.loads((OVERLAY / 'app_language_localization/ui_catalog.json').read_text())
    calls = 0
    for name in PLAN['outputs']:
        if not name.endswith('.swift'):
            continue
        text = (args.source / name).read_text()
        for start, end, parts in literals(text):
            if not any(re.search('[А-Яа-яЁё]', value) for kind, value in parts if kind == 'text'):
                continue
            assert text[max(0, start - 32):start].endswith('.nagramiXUILocalized('), (name, text.count('\n', 0, start) + 1, 'Raw Russian UI string')
            value = canonical(parts)
            assert value in catalog, (name, value)
            assert catalog[value]['key'] in en, (name, value)
            calls += 1
    if args.swiftc:
        runtime_checks(args.source, args.swiftc)
        for name in PLAN['outputs']:
            if name.endswith('.swift'):
                subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    print(f'Каталоги: {len(available)}/{len(expected)}; {len(en)} ключей; {calls} UI-литералов проверены. Не готовы: {len(missing)}. Apple SDK/iPhone этой проверкой не подтверждаются.')


if __name__ == '__main__':
    main()
