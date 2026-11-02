#!/usr/bin/env python3
"""Проверить бесплатный GPT-OSS, лимиты Pollinations и точное сохранение предыдущей цепочки."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/TranslateUI/Sources/NagramiXTranslation'

def sha(data): return hashlib.sha256(data).hexdigest()
def plan(): return json.loads((ROOT / 'ios/translation_gpt_oss_patches.json').read_text())
def is_applied(source):
    return all((source / n).is_file() and sha((source / n).read_bytes()) == h for n, h in plan()['outputs'].items())

def delegate_if_applied(args):
    from validate_voice_transcription import delegate_if_applied as delegate_transcription
    if delegate_transcription(args): return True
    if not is_applied(args.source): return False
    subprocess.run([sys.executable, str(Path(__file__).resolve()), '--source', str(args.source),
                    *(['--swiftc', str(args.swiftc)] if args.swiftc else [])], check=True)
    return True

def previous_bytes(source, p):
    result = {}
    previous = json.loads((ROOT / 'ios/translation_free_modes_patches.json').read_text())
    for n, h in p['inputs'].items():
        if n in previous['replacements']:
            data = (ROOT / 'ios' / previous['replacements'][n]).read_bytes()
        else:
            value = (source / n).read_text()
            marker = 'Apple Google Яндекс Gemini ChatGPT DeepSeek язык API GPT-OSS Pollinations бесплатно температура'
            assert value.count(marker) == 1
            data = value.replace(marker, 'Apple Google Яндекс Gemini ChatGPT DeepSeek язык API').encode()
        assert sha(data) == h, n
        result[n] = data
    return result

def guards(source, p, temp):
    spec = importlib.util.spec_from_file_location('translation_gpt_oss', ROOT / 'ios/translation_gpt_oss.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    original = {n: (source / n).read_bytes() for n in p['guards']}
    original.update(previous_bytes(source, p))
    from validate_quick_format import manifest
    rejected = []

    def seed():
        root = temp / ('guard-' + str(len(rejected)))
        for n, data in original.items():
            path = root / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        return root

    def reject(root, label, overlay=ROOT / 'ios'):
        before = manifest(root)
        try: module.apply_translation_gpt_oss(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят некорректный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if overlay != ROOT / 'ios': shutil.rmtree(overlay)

    root = seed(); module.apply_translation_gpt_oss(root, ROOT / 'ios')
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
            (overlay / 'translation_gpt_oss_patches.json').write_text(json.dumps(p))
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
        (overlay / 'translation_gpt_oss_patches.json').write_text(json.dumps(value))
        for n in p['templates']:
            path = overlay / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT / 'ios' / n).read_bytes())
        reject(seed(), label, overlay)
    return rejected


def prior(source, p, temp):
    previous = previous_bytes(source, p)
    names = {'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift'}
    for stage in ['message_translation', 'translation_free_modes', 'round_video_sheet', 'round_video_page', 'round_video_refinement', 'round_video_bitrate', 'scheduled_archive_isolation']:
        value = json.loads((ROOT / 'ios' / (stage + '_patches.json')).read_text())
        for field in ['inputs', 'outputs', 'guards', 'copies']: names.update(value[field])
    root = temp / 'prior'
    for n in names:
        path = root / n; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(previous[n] if n in previous else (source / n).read_bytes())
    subprocess.run([sys.executable, str(ROOT / 'scripts/validate_translation_free_modes.py'), '--source', str(root)], check=True)
    shutil.rmtree(root)


def swift_checks(source, swiftc, temp):
    from validate_message_translation import run_swift
    tests = ROOT / 'scripts/tests'
    paths = {n: source / (PREFIX + n + '.swift') for n in ['Settings', 'Cloud', 'Web', 'TextPlan', 'Runtime']}
    core = [paths[n] for n in ['Settings', 'Cloud', 'Web', 'TextPlan']]
    # Earlier six-provider tests continue on the new implementation, with only
    # the deliberately extended provider label list updated in a temporary copy.
    old_labels = '["Apple", "Google", "Яндекс", "Gemini", "ChatGPT", "DeepSeek"]'
    new_labels = '["Apple", "Google", "Яндекс", "Gemini", "ChatGPT", "DeepSeek", "GPT-OSS · Бесплатно"]'
    free = temp / 'FreeTests.swift'; text = (tests / 'NagramiXTranslationFreeTests.swift').read_text(); assert text.count(old_labels) == 1; free.write_text(text.replace(old_labels, new_labels))
    policy = temp / 'PolicyTests.swift'; text = (tests / 'NagramiXTranslationCoreTests.swift').read_text(); assert text.count(old_labels) == 1
    policy.write_text(text.replace(old_labels, new_labels).replace('try self.codecs()', '').replace('try self.client()', ''))
    runtime = temp / 'Runtime.swift'; text = 'import Foundation\nimport FoundationNetworking\n' + '\n'.join(l for l in paths['Runtime'].read_text().splitlines() if not l.startswith('import ')).replace('public ', '')
    runtime.write_text(text)
    routed = temp / 'RoutedRuntime.swift'; routed.write_text(text.replace('private func nagramiXTranslateFragments', 'func nagramiXTranslateFragments').replace('NagramiXTranslationCloudClient.shared.translate', 'runtimeFreeClient.translate'))
    boundary = temp / 'RoutedBoundary.swift'; text = (tests / 'NagramiXTranslationRuntimeBoundary.swift').read_text()
    anchor = 'enum NagramiXTranslationKeys { static func read(_ provider: NagramiXTranslationProvider) -> NagramiXTranslationCredential? { nil } }'
    assert text.count(anchor) == 1
    boundary.write_text(text.replace(anchor, 'enum NagramiXTranslationKeys { static var reads = 0; static func read(_ provider: NagramiXTranslationProvider) -> NagramiXTranslationCredential? { reads += 1; return .init(key: "legacy-owned-key", folder: "legacy-folder") } }'))
    http = temp / 'PreviousHTTP.swift'; http.write_text(free.read_text().split('@main struct FreeTranslationTests')[0])
    harness = tests / 'NagramiXGPTOSSHarness.swift'
    runs = []
    for optimized in [False, True]:
        suffix = '-O' if optimized else '-debug'
        runs.append(run_swift(swiftc, temp, 'gptoss' + suffix, [*core, harness, tests / 'NagramiXGPTOSSTests.swift'], optimized))
        runs.append(run_swift(swiftc, temp, 'gptoss-runtime' + suffix, [*core, harness, boundary, routed, tests / 'NagramiXGPTOSSRuntimeTests.swift'], optimized))
        runs.append(run_swift(swiftc, temp, 'previous-free' + suffix, [*core, free], optimized))
        runs.append(run_swift(swiftc, temp, 'previous-policy' + suffix, [*core, policy], optimized))
        runs.append(run_swift(swiftc, temp, 'previous-runtime' + suffix, [*core, tests / 'NagramiXTranslationRuntimeBoundary.swift', runtime, tests / 'NagramiXTranslationRuntimeTests.swift'], optimized))
        runs.append(run_swift(swiftc, temp, 'previous-routing' + suffix, [*core, http, boundary, routed, tests / 'NagramiXTranslationFreeRuntimeTests.swift'], optimized))
        bad = temp / 'NoRateLimit.swift'; text = paths['Cloud'].read_text(); assert text.count('self.gptossReadyAt = time.addingTimeInterval(30)') == 1
        bad.write_text(text.replace('self.gptossReadyAt = time.addingTimeInterval(30)', 'self.gptossReadyAt = time'))
        runs.append(run_swift(swiftc, temp, 'missing-interval' + suffix, [paths['Settings'], bad, paths['Web'], paths['TextPlan'], harness, tests / 'NagramiXGPTOSSTests.swift'], optimized, '30-second free quota spans all accounts'))
    subprocess.run([str(swiftc), '-frontend', '-parse', *[str(source / n) for n in plan()['outputs']]], check=True)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True); parser.add_argument('--swiftc', type=Path); parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_voice_transcription import delegate_if_applied as delegate_transcription
    if delegate_transcription(args): return
    p = plan()
    for n, h in {**p['guards'], **p['outputs']}.items(): assert sha((args.source / n).read_bytes()) == h, n
    for n, h in p['templates'].items(): assert sha((ROOT / 'ios' / n).read_bytes()) == h, n
    ui = (args.source / (PREFIX + 'Preferences.swift')).read_text()
    assert 'case .keys: return 3' in ui and 'filter { $0.requiresAPIKey }' in ui and 'case .gptoss: return 1' in ui
    assert 'Текст передаётся Pollinations' in ui and 'case 4: self.show(.gptoss' in ui
    with tempfile.TemporaryDirectory(prefix='nagramix-gptoss-') as folder:
        temp = Path(folder); rejected = guards(args.source, p, temp); prior(args.source, p, temp)
        runs = swift_checks(args.source, args.swiftc, temp) if args.swiftc else []
    report = dict(replacements=len(p['inputs']), guards=len(p['guards']), fail_closed=rejected, runs=runs, source_hashes=p['outputs'], SDK='ожидается', iPhone='ожидается', IPA='не собиралась')
    if args.report: args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('PASS: отдельный бесплатный GPT-OSS, очередь/лимиты, прежняя строгая цепочка; SDK/iPhone ожидаются')

if __name__ == '__main__': main()
