#!/usr/bin/env python3
"""Проверить бесплатные Google/Яндекс, температуру и сохранность предыдущей цепочки."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/TranslateUI/Sources/NagramiXTranslation'


def sha(data): return hashlib.sha256(data).hexdigest()
def plan(): return json.loads((ROOT / 'ios/translation_free_modes_patches.json').read_text())
def is_applied(source):
    return all((source / n).is_file() and sha((source / n).read_bytes()) == h for n, h in plan()['outputs'].items())


def delegate_if_applied(args):
    from validate_translation_gpt_oss import delegate_if_applied as delegate_gptoss
    if delegate_gptoss(args): return True
    if not is_applied(args.source): return False
    subprocess.run([sys.executable, str(Path(__file__).resolve()), '--source', str(args.source),
                    *(['--swiftc', str(args.swiftc)] if args.swiftc else [])], check=True)
    return True


def guards(source, p, temp):
    spec = importlib.util.spec_from_file_location('translation_free_modes', ROOT / 'ios/translation_free_modes.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    previous = json.loads((ROOT / 'ios/message_translation_patches.json').read_text())
    original = {n: (source / n).read_bytes() for n in p['guards']}
    for n in p['inputs']:
        item = previous['copies'][n]
        original[n] = (ROOT / 'ios' / item['source']).read_bytes()
        assert sha(original[n]) == p['inputs'][n]
    from validate_quick_format import manifest
    rejected = []

    def seed():
        root = temp / ('guard-' + str(len(rejected)))
        for n, data in original.items():
            path = root / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        return root

    def reject(root, label, overlay=ROOT / 'ios'):
        before = manifest(root)
        try: module.apply_translation_free_modes(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят некорректный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if overlay != ROOT / 'ios': shutil.rmtree(overlay)

    root = seed(); module.apply_translation_free_modes(root, ROOT / 'ios')
    for n in {*p['outputs'], *p['copies']}: assert (root / n).read_bytes() == (source / n).read_bytes(), n
    reject(root, 'повторное применение')
    for n in original:
        for mode in ['missing', 'drift']:
            root = seed(); path = root / n
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes() + b'\n// drift')
            reject(root, mode + ' ' + n)
    for n in p['copies']:
        root = seed(); path = root / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('collision')
        reject(root, 'helper collision ' + n)
    for name in p['templates']:
        for mode in ['missing', 'drift']:
            overlay = temp / 'bad-overlay'; overlay.mkdir()
            (overlay / 'translation_free_modes_patches.json').write_text(json.dumps(p))
            for n in p['templates']:
                path = overlay / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT / 'ios' / n).read_bytes())
            if mode == 'missing': (overlay / name).unlink()
            else: (overlay / name).write_bytes((overlay / name).read_bytes() + b'\n// drift')
            reject(seed(), mode + ' template ' + name, overlay)
    mutations = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        changed = copy.deepcopy(p); changed[field][next(iter(changed[field]))] = '0' * 64; mutations.append((field + ' SHA', changed))
    changed = copy.deepcopy(p); changed['replacements'][next(iter(changed['inputs']))] = '../outside'; mutations.append(('traversal', changed))
    for label, value in mutations:
        overlay = temp / 'bad-overlay'; overlay.mkdir()
        (overlay / 'translation_free_modes_patches.json').write_text(json.dumps(value))
        for n in p['templates']:
            path = overlay / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT / 'ios' / n).read_bytes())
        reject(seed(), label, overlay)
    return rejected


def prior(source, p, temp):
    restored = temp / 'prior'
    previous = json.loads((ROOT / 'ios/message_translation_patches.json').read_text())
    names = {'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift'}
    for stage in ['message_translation', 'round_video_sheet', 'round_video_page', 'round_video_refinement', 'round_video_bitrate', 'scheduled_archive_isolation']:
        old = json.loads((ROOT / 'ios' / (stage + '_patches.json')).read_text())
        for field in ['inputs', 'outputs', 'guards', 'copies']: names.update(old[field])
    for n in names:
        path = restored / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((source / n).read_bytes())
    for n in p['inputs']:
        data = (ROOT / 'ios' / previous['copies'][n]['source']).read_bytes()
        assert sha(data) == p['inputs'][n]; (restored / n).write_bytes(data)
    subprocess.run([sys.executable, str(ROOT / 'scripts/validate_message_translation.py'), '--source', str(restored)], check=True)
    shutil.rmtree(restored)


def swift(source, swiftc, temp):
    from validate_message_translation import run_swift
    paths = {name: source / (PREFIX + name + '.swift') for name in ['Settings', 'Cloud', 'Web', 'TextPlan', 'Runtime']}
    core = [paths[n] for n in ['Settings', 'Cloud', 'Web', 'TextPlan']]
    tests = ROOT / 'scripts/tests'
    runtime = temp / 'Runtime.swift'
    runtime.write_text('import Foundation\nimport FoundationNetworking\n' + '\n'.join(line for line in paths['Runtime'].read_text().splitlines() if not line.startswith('import ')).replace('public ', ''))
    routed_runtime = temp / 'RoutedRuntime.swift'
    routed_runtime.write_text(runtime.read_text().replace('private func nagramiXTranslateFragments', 'func nagramiXTranslateFragments').replace('NagramiXTranslationCloudClient.shared.translate', 'runtimeFreeClient.translate'))
    boundary = temp / 'RoutedBoundary.swift'
    old = (tests / 'NagramiXTranslationRuntimeBoundary.swift').read_text()
    anchor = 'enum NagramiXTranslationKeys { static func read(_ provider: NagramiXTranslationProvider) -> NagramiXTranslationCredential? { nil } }'
    assert old.count(anchor) == 1
    boundary.write_text(old.replace(anchor, 'enum NagramiXTranslationKeys { static var reads = 0; static func read(_ provider: NagramiXTranslationProvider) -> NagramiXTranslationCredential? { reads += 1; return .init(key: "legacy-owned-key", folder: "legacy-folder") } }'))
    http = temp / 'HTTPBoundary.swift'
    http.write_text((tests / 'NagramiXTranslationFreeTests.swift').read_text().split('@main struct FreeTranslationTests')[0])
    routing = [boundary, http, routed_runtime, tests / 'NagramiXTranslationFreeRuntimeTests.swift']
    # Retain all previous language, UTF-16 and setting tests. API routing/client
    # contracts changed explicitly and are exercised by the new production tests.
    legacy = temp / 'LegacyPolicy.swift'
    text = (tests / 'NagramiXTranslationCoreTests.swift').read_text()
    assert text.count('try self.codecs()') == 1 and text.count('try self.client()') == 1
    legacy.write_text(text.replace('try self.codecs()', '').replace('try self.client()', ''))
    runs = []
    for optimized in [False, True]:
        suffix = '-O' if optimized else '-debug'
        runs.append(run_swift(swiftc, temp, 'free' + suffix, [*core, tests / 'NagramiXTranslationFreeTests.swift'], optimized))
        runs.append(run_swift(swiftc, temp, 'policy' + suffix, [*core, legacy], optimized))
        runs.append(run_swift(swiftc, temp, 'runtime' + suffix, [*core, tests / 'NagramiXTranslationRuntimeBoundary.swift', runtime, tests / 'NagramiXTranslationRuntimeTests.swift'], optimized))
        runs.append(run_swift(swiftc, temp, 'routing' + suffix, [*core, *routing], optimized))
        bad_cloud = temp / 'WrongTemperature.swift'
        text = paths['Cloud'].read_text(); assert text.count('generation["temperature"] = temperature') == 1
        bad_cloud.write_text(text.replace('generation["temperature"] = temperature', 'generation["temperature"] = 0.0'))
        runs.append(run_swift(swiftc, temp, 'lost-temperature' + suffix, [paths['Settings'], bad_cloud, paths['Web'], paths['TextPlan'], tests / 'NagramiXTranslationFreeTests.swift'], optimized, 'selected temperature reaches selected LLM'))
        bad_runtime = temp / 'LegacyKeyRead.swift'
        text = routed_runtime.read_text(); anchor = 'if configuration.provider.isFreeWeb { credentials = .init(key: "", folder: "") }'
        assert text.count(anchor) == 1
        bad_runtime.write_text(text.replace(anchor, 'if configuration.provider.isFreeWeb { _ = NagramiXTranslationKeys.read(configuration.provider); credentials = .init(key: "", folder: "") }'))
        runs.append(run_swift(swiftc, temp, 'legacy-key-read' + suffix, [*core, boundary, http, bad_runtime, tests / 'NagramiXTranslationFreeRuntimeTests.swift'], optimized, 'Google and Yandex do not even read previously saved keys'))
    subprocess.run([str(swiftc), '-frontend', '-parse', *[str(source / n) for n in {*plan()['outputs'], *plan()['copies']}]], check=True)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True); parser.add_argument('--swiftc', type=Path); parser.add_argument('--report', type=Path)
    args = parser.parse_args(); p = plan()
    from validate_translation_gpt_oss import delegate_if_applied as delegate_gptoss
    if delegate_gptoss(args): return
    for n, h in {**p['guards'], **p['outputs']}.items(): assert sha((args.source / n).read_bytes()) == h, n
    for n, h in p['templates'].items(): assert sha((ROOT / 'ios' / n).read_bytes()) == h, n
    for n, item in p['copies'].items(): assert sha((args.source / n).read_bytes()) == item['sha256'], n
    settings = (args.source / 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift').read_text()
    assert 'case .translationHeader, .translationEnabled, .translationOptions: return NagramiXSettingsSection.translationSettings.rawValue' in settings
    assert '.translationOptions, .roundQualityHeader' in settings and 'return .other' in settings
    assert 'title: "Перевод сообщений"' in settings and 'title: "Настройки перевода"' in settings
    cloud = (args.source / (PREFIX + 'Cloud.swift')).read_text()
    assert 'translation.googleapis.com/language/translate' not in cloud and 'translate.api.cloud.yandex.net' not in cloud
    assert 'completionHandler(nil)' in cloud and 'URLSessionConfiguration.ephemeral' in cloud
    ui = (args.source / (PREFIX + 'Preferences.swift')).read_text()
    assert 'case .keys: return 3' in ui and 'filter { $0.isLanguageModel }' in ui and 'Температура: ' in ui
    with tempfile.TemporaryDirectory(prefix='nagramix-translation-free-') as folder:
        temp = Path(folder); rejected = guards(args.source, p, temp); prior(args.source, p, temp)
        runs = swift(args.source, args.swiftc, temp) if args.swiftc else []
    result = dict(replacements=len(p['inputs']), helpers=len(p['copies']), guards=len(p['guards']), fail_closed=rejected, runs=runs,
                  source_hashes={**p['outputs'], **{n: i['sha256'] for n, i in p['copies'].items()}},
                  limits='SDK, UIKit, Apple Translation и iPhone ожидаются; HTTP fixtures не являются live API')
    if args.report: args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('PASS: бесплатные переводчики, температура, прежняя строгая цепочка; SDK/iPhone ожидаются')


if __name__ == '__main__': main()
