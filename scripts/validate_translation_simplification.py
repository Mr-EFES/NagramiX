#!/usr/bin/env python3
"""Проверить согласованный переводчик, сохранение и миграцию конфигурации."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'translation_simplification_patches.json').read_text())


def sha(data): return hashlib.sha256(data).hexdigest()


def is_applied(source):
    expected = {**PLAN['outputs'], **{n: item['sha256'] for n, item in PLAN['copies'].items()}}
    return all((source / n).is_file() and sha((source / n).read_bytes()) == h for n, h in expected.items()) and not any((source / n).exists() for n in PLAN['deletions'])


def reverse(source, target):
    names = set(PLAN['inputs']) | set(PLAN['deletions'])
    for manifest in OVERLAY.glob('*_patches.json'):
        item = json.loads(manifest.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift'])
    for name in names - set(PLAN['copies']):
        original = PLAN['previous'].get(name) or PLAN['deletions'].get(name, {}).get('source')
        path = OVERLAY / original if original else source / name
        if not path.is_file(): continue
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())


def delegate_if_applied(args, script):
    from validate_translation_inline_telegram import delegate_if_applied as delegate_latest
    if delegate_latest(args, script): return True
    if not is_applied(args.source): return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='before-simple-translation-') as folder:
        prior = Path(folder)
        reverse(args.source, prior)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None:
            arguments += ['--upstream', str(args.source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def verify(source):
    assert is_applied(source)
    for n, h in PLAN['guards'].items():
        if n not in PLAN['deletions']: assert sha((source / n).read_bytes()) == h, n
    for n, h in PLAN['templates'].items(): assert sha((OVERLAY / n).read_bytes()) == h, n
    files = {Path(n).name: (source / n).read_text() for n in PLAN['outputs']}
    for name, text in files.items():
        assert 'gptoss' not in text.lower() and 'pollinations' not in text.lower(), name
    ui = files['NagramiXTranslationPreferences.swift']
    assert '[.apple, .google, .yandex]' in ui and '[.gemini, .chatgpt, .deepseek]' in ui
    assert 'provider.requiresAPIKey && NagramiXTranslationSettings.current.provider == provider' in ui
    assert 'self.show(.credential(item.0), title: item.0.title)' in ui
    for text in ['Язык перевода исключается автоматически', 'Apple — на устройстве', 'Для нейросетей нужен личный API-ключ', 'Удалить ключ', 'Готово', 'Настройки Apple']:
        assert text not in ui, text
    footer = block(ui, 'public func tableView(_ tableView: UITableView, titleForFooterInSection')
    assert 'if case .credential = self.page' in footer and 'return nil' in footer
    assert 'Как в приложении' in ui and 'Предпочитаемые языки' in ui
    assert 'case .languages: return section == 0 ? 1 : self.languages.count' in ui
    save = block(ui, '@objc private func saveCredentials()')
    assert 'provider: provider, notify: false' in save and 'value.models[provider.rawValue] = model' in save
    assert 'value.temperatures = temperatures' in save and 'value.revision = UUID().uuidString' in save
    moved = block(ui, '@objc private func temperatureMoved(')
    assert 'NagramiXTranslationSettings.update' not in moved and 'self.draftTemperature' in moved
    picker = (source / next(iter(PLAN['copies']))).read_text()
    assert 'UIPickerView' in picker and 'selectedRow(inComponent: 0)' in picker
    assert 'self.backgroundButton.addTarget' in picker and 'NagramiXTranslationSettings.update' not in picker
    assert 'Готово' not in picker and 'Сохранить' not in picker
    model = files['NagramiXTranslationSettings.swift']
    assert 'case apple, google, yandex, gemini, chatgpt, deepseek\n' in model
    assert 'public init(from decoder: Decoder) throws' in model
    assert 'self.automatic = false' in model and 'provider-migration:' in model
    assert 'func effectiveIgnored(' in model and 'self.ignored.map(NagramiXTranslationLanguage.base)' in model
    runtime = files['NagramiXTranslationRuntime.swift']
    assert 'appleSource' not in runtime and 'let providerSource = detected ?? source' in runtime
    assert runtime.count('effectiveIgnored(') >= 3
    assert 'currentConfig.revision == configuration.revision' in runtime
    assert 'self.fingerprint(current) == self.fingerprint(message)' in runtime
    before = (OVERLAY / PLAN['previous'][next(n for n in PLAN['outputs'] if n.endswith('/NagramiXTranslationRuntime.swift'))]).read_text()
    assert block(runtime, 'private func nagramiXTranslationSpans(') == block(before, 'private func nagramiXTranslationSpans(')
    cloud = files['NagramiXTranslationCloud.swift']
    assert 'guard provider.requiresAPIKey, !credential.key.isEmpty' in cloud
    assert 'credential.key' not in block(cloud, 'private func pump()')
    keys = files['NagramiXTranslationCredentials.swift']
    assert keys.count('guard provider.requiresAPIKey else') == 2
    assert 'if notify { NagramiXTranslationSettings.credentialsChanged() }' in keys
    translate = files['Translate.swift']
    assert 'try await session.prepareTranslation()' in translate
    assert 'nagramiXConfiguration.provider == .apple' in translate
    assert 'source: firstTaskLanguagePair.0 == "auto" ? nil' in translate
    controller_name = next(n for n in PLAN['outputs'] if n.endswith('/NagramiXSettingsController.swift'))
    before_controller = (OVERLAY / PLAN['previous'][controller_name]).read_text()
    assert files['NagramiXSettingsController.swift'] == before_controller.replace('API GPT-OSS Pollinations бесплатно температура', 'API температура')


def guard_tests(source):
    spec = importlib.util.spec_from_file_location('translation_simplification', OVERLAY / 'translation_simplification.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    originals = {n: (OVERLAY / f).read_bytes() for n, f in PLAN['previous'].items()}
    for n, item in PLAN['deletions'].items(): originals[n] = (OVERLAY / item['source']).read_bytes()
    originals.update({n: (source / n).read_bytes() for n in PLAN['guards'] if n not in PLAN['deletions']})
    with tempfile.TemporaryDirectory(prefix='simple-translation-guards-') as folder:
        temp = Path(folder)
        def seed():
            base = temp / 'input'
            for n, data in originals.items():
                path = base / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            return base
        def snapshot(base): return {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}
        def reject(base, overlay=OVERLAY):
            old = snapshot(base)
            try: module.apply_translation_simplification(base, overlay)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError('Принят дрейф')
            assert snapshot(base) == old, 'Частичная запись/удаление'
            shutil.rmtree(base)
        base = seed(); module.apply_translation_simplification(base, OVERLAY); verify(base); reject(base)
        rejected = 1
        for n in originals:
            for missing in (False, True):
                base = seed()
                if missing: (base / n).unlink()
                else: (base / n).write_bytes(b'// drift')
                reject(base); rejected += 1
        for n in PLAN['templates']:
            base = seed(); overlay = temp / 'overlay'; overlay.mkdir()
            for name in PLAN['templates']:
                path = overlay / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / name).read_bytes())
            (overlay / n).write_bytes(b'// drift')
            (overlay / 'translation_simplification_patches.json').write_text(json.dumps(PLAN))
            reject(base, overlay); shutil.rmtree(overlay); rejected += 1
        base = seed(); collision = base / next(iter(PLAN['copies'])); collision.parent.mkdir(parents=True, exist_ok=True); collision.write_bytes(b'// existing'); reject(base); rejected += 1
    print(f'PASS: {rejected} fail-closed cases, no partial writes/deletion')


def execute_swift(source, compiler):
    prefix = source / 'submodules/TranslateUI/Sources'
    ui = (prefix / 'NagramiXTranslationPreferences.swift').read_text()
    with tempfile.TemporaryDirectory(prefix='simple-translation-swift-') as folder:
        temp = Path(folder)
        boundary = (ROOT / 'scripts/tests/NagramiXTranslationSimplificationBoundary.swift').read_text()
        boundary = boundary.replace('// SAVE_METHOD', block(ui, '@objc private func saveCredentials()').replace('@objc private func', 'func'))
        harness = temp / 'Boundary.swift'; harness.write_text(boundary)
        files = [prefix / n for n in ('NagramiXTranslationSettings.swift', 'NagramiXTranslationCloud.swift', 'NagramiXTranslationWeb.swift')]
        for flags in ([], ['-O']):
            binary = temp / 'tests'
            subprocess.run([str(compiler), '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), *flags,
                *map(str, files), str(harness), str(ROOT / 'scripts/tests/NagramiXTranslationSimplificationTests.swift'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=30)
        subprocess.run([str(compiler), '-frontend', '-parse', *[str(source / n) for n in [*PLAN['outputs'], *PLAN['copies']]]], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--standalone', action='store_true')
    parser.add_argument('--swiftc', type=Path)
    args = parser.parse_args()
    from validate_translation_inline_telegram import delegate_if_applied as delegate_latest
    if delegate_latest(args, Path(__file__)): return
    verify(args.source); guard_tests(args.source)
    if args.swiftc: execute_swift(args.source, args.swiftc)
    if not args.standalone:
        with tempfile.TemporaryDirectory(prefix='simple-translation-prior-') as folder:
            prior = Path(folder); reverse(args.source, prior)
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_media_privacy_fixes.py'), '--source', str(prior)], check=True)
    print('PASS: translation simplification / config migration / exact prior chain; SDK and iPhone pending')


if __name__ == '__main__': main()
