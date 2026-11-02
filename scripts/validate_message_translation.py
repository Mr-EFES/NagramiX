#!/usr/bin/env python3
"""Проверить согласованный перевод, провайдеры, форматирование и безопасную запись результата."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile

from validate_quick_format import manifest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/TranslateUI/Sources/NagramiXTranslation'


def sha(data): return hashlib.sha256(data).hexdigest()
def plan(): return json.loads((ROOT / 'ios/message_translation_patches.json').read_text())
def is_applied(source):
    return all((source / n).is_file() and sha((source / n).read_bytes()) == h for n, h in plan()['outputs'].items())


def delegate_if_applied(args):
    from validate_translation_free_modes import delegate_if_applied as delegate_free
    if delegate_free(args): return True
    if not is_applied(args.source): return False
    subprocess.run([sys.executable, str(Path(__file__).resolve()), '--source', str(args.source),
                    *(['--swiftc', str(args.swiftc)] if args.swiftc else [])], check=True)
    return True


def previous_files(source, p):
    result = {n: (source / n).read_bytes() for n in p['inputs']}
    for n, old, new, count in reversed(p['patches']):
        value = result[n].decode()
        assert value.count(new) == count, n
        result[n] = value.replace(new, old, count).encode()
    for n, data in result.items(): assert sha(data) == p['inputs'][n], n
    return result


def guard_tests(source, p, previous, temp):
    spec = importlib.util.spec_from_file_location('message_translation', ROOT / 'ios/message_translation.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    original = {**{n: (source / n).read_bytes() for n in p['guards']}, **previous}
    rejected = []
    def seed(label):
        root = temp / label
        for n, data in original.items():
            path = root / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        return root
    def overlay(label, value):
        root = temp / ('overlay-' + label); root.mkdir()
        (root / 'message_translation_patches.json').write_text(json.dumps(value))
        for n in p['templates']:
            path = root / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT / 'ios' / n).read_bytes())
        return root
    def reject(root, label, templates=ROOT / 'ios'):
        before = manifest(root)
        try: module.apply_message_translation(root, templates)
        except SystemExit: pass
        else: raise AssertionError('Принят некорректный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if templates != ROOT / 'ios': shutil.rmtree(templates)
    good = seed('good'); module.apply_message_translation(good, ROOT / 'ios')
    for n in {*p['outputs'], *p['copies']}: assert (good / n).read_bytes() == (source / n).read_bytes(), n
    reject(good, 'reapply')
    for n in original:
        for mode in ['missing', 'drift']:
            root = seed('root-' + str(len(rejected))); path = root / n
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes() + b'\n// drift')
            reject(root, mode + ' ' + n)
    for n in p['templates']:
        for mode in ['missing', 'drift']:
            label = 'template-' + str(len(rejected)); templates = overlay(label, p); path = templates / n
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes() + b'\n// drift')
            reject(seed('root-' + label), mode + ' ' + n, templates)
    for n in p['copies']:
        root = seed('collision-' + str(len(rejected))); path = root / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('collision')
        reject(root, 'collision ' + n)
    mutations = []
    for i in range(len(p['patches'])):
        value = copy.deepcopy(p); value['patches'][i][1] += ' bad'; mutations.append(('anchor-' + str(i), value))
    for field in ['inputs', 'outputs', 'guards']:
        value = copy.deepcopy(p); value[field][next(iter(value[field]))] = '0' * 64; mutations.append((field + '-sha', value))
    for n in p['copies']:
        value = copy.deepcopy(p); value['copies'][n]['sha256'] = '0' * 64; mutations.append(('copy-sha-' + str(len(mutations)), value))
    value = copy.deepcopy(p); value['inputs']['../outside'] = '0' * 64; value['outputs']['../outside'] = '0' * 64; mutations.append(('traversal', value))
    for label, value in mutations: reject(seed('root-' + label), label, overlay(label, value))
    return rejected


def prior_checks(source, previous, p, temp, swiftc):
    names = set(p['inputs']) | set(p['guards']) | {'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift'}
    for stage in ['round_video_sheet', 'round_video_page', 'round_video_refinement', 'round_video_bitrate', 'scheduled_archive_isolation']:
        old = json.loads((ROOT / 'ios' / (stage + '_patches.json')).read_text())
        for field in ['inputs', 'outputs', 'guards', 'copies']: names.update(old[field])
    scope = temp / 'prior'
    for n in names:
        path = scope / n; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(previous[n] if n in previous else (source / n).read_bytes())
    for name in ['validate_round_video_bitrate.py', 'validate_scheduled_archive_isolation.py']:
        subprocess.run([sys.executable, str(ROOT / 'scripts' / name), '--source', str(scope), *(['--swiftc', str(swiftc)] if swiftc else [])], check=True)


def run_swift(swiftc, temp, label, files, optimized, failure=None):
    binary = temp / label
    subprocess.run([str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'),
                    *(['-O'] if optimized else []), *map(str, files), '-o', str(binary)], check=True)
    result = subprocess.run([str(binary)], text=True, capture_output=True, timeout=30,
                            env=dict(os.environ, XDG_CONFIG_HOME=str(temp / (label + '-prefs'))),
                            preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
    if failure:
        assert result.returncode != 0 and failure in result.stderr, result.stdout + result.stderr
        output = label + ': прежняя ошибка воспроизведена и отклонена'
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        output = label + ': ' + result.stdout.strip()
    print(output, flush=True); binary.unlink(); return output


def swift_checks(source, swiftc, temp):
    paths = {name: source / (PREFIX + name + '.swift') for name in ['Settings', 'Cloud', 'TextPlan', 'Credentials', 'Runtime']}
    runtime = 'import Foundation\n' + '\n'.join(line for line in paths['Runtime'].read_text().splitlines() if not line.startswith('import ')).replace('public ', '')
    runtime_path = temp / 'Runtime.swift'; runtime_path.write_text(runtime)
    credentials = temp / 'Credentials.swift'; credentials.write_text(paths['Credentials'].read_text().replace('import Security\n', ''))
    core = [paths['Settings'], paths['Cloud'], paths['TextPlan']]
    tests = ROOT / 'scripts/tests'
    runtime_files = [*core, tests / 'NagramiXTranslationRuntimeBoundary.swift', runtime_path, tests / 'NagramiXTranslationRuntimeTests.swift']
    variants = []
    settings = paths['Settings'].read_text()
    old = temp / 'NoLanguageGate.swift'; old.write_text(settings.replace('code != self.base(interface),', 'true,'))
    variants.append(('same-language-menu', [old, paths['Cloud'], paths['TextPlan'], tests / 'NagramiXTranslationCoreTests.swift'], 'app language suppresses translate action'))
    old = temp / 'WrongProvider.swift'; old.write_text(paths['Cloud'].read_text().replace('https://api.openai.com/v1/chat/completions', 'https://api.deepseek.com/chat/completions'))
    variants.append(('wrong-provider', [paths['Settings'], old, paths['TextPlan'], tests / 'NagramiXTranslationCoreTests.swift'], 'selected provider gets its own endpoint and key'))
    old = temp / 'NoProtection.swift'; old.write_text(paths['TextPlan'].read_text().replace('if !protected && chunk.', 'if chunk.').replace('            let protected = ', '            _ = '))
    variants.append(('unprotected-fragments', [paths['Settings'], paths['Cloud'], old, tests / 'NagramiXTranslationCoreTests.swift'], 'protected fragments never sent to cloud'))
    for label, anchor, message in [
        ('stale-provider', 'currentConfig.revision == configuration.revision,', 'provider/key revision change rejects an in-flight write'),
        ('stale-edit', 'self.fingerprint(current) == self.fingerprint(message),', 'edit during translation is never overwritten'),
        ('chat-off', 'currentChoice.enabled ?? currentConfig.automatic,', 'chat OFF rejects an in-flight write'),
    ]:
        old = temp / (label + '.swift'); assert runtime.count(anchor) == 1; old.write_text(runtime.replace(anchor, 'true,'))
        variants.append((label, [*core, tests / 'NagramiXTranslationRuntimeBoundary.swift', old, tests / 'NagramiXTranslationRuntimeTests.swift'], message))
    runs = []
    for optimized in [False, True]:
        suffix = '-O' if optimized else '-debug'
        runs.append(run_swift(swiftc, temp, 'core' + suffix, [*core, tests / 'NagramiXTranslationCoreTests.swift'], optimized))
        runs.append(run_swift(swiftc, temp, 'runtime' + suffix, runtime_files, optimized))
        runs.append(run_swift(swiftc, temp, 'keychain' + suffix, [paths['Settings'], paths['Cloud'], credentials, tests / 'NagramiXTranslationKeychainBoundary.swift', tests / 'NagramiXTranslationKeychainTests.swift'], optimized))
        for label, files, failure in variants: runs.append(run_swift(swiftc, temp, label + suffix, files, optimized, failure))
    p = plan()
    subprocess.run([str(swiftc), '-frontend', '-parse', *[str(source / n) for n in {*p['outputs'], *p['copies']} if n.endswith('.swift')]], check=True)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True); parser.add_argument('--swiftc', type=Path); parser.add_argument('--report', type=Path)
    args = parser.parse_args(); p = plan()
    from validate_translation_free_modes import delegate_if_applied as delegate_free
    if delegate_free(args): return
    for n, h in {**p['outputs'], **p['guards']}.items(): assert sha((args.source / n).read_bytes()) == h, n
    for n, item in p['copies'].items(): assert sha((args.source / n).read_bytes()) == item['sha256'], n
    for n, h in p['templates'].items(): assert sha((ROOT / 'ios' / n).read_bytes()) == h, n
    runtime = (args.source / (PREFIX + 'Runtime.swift')).read_text()
    assert 'context.engine.messages.translateMessages' not in runtime
    assert 'currentConfig.revision == configuration.revision' in runtime and 'self.fingerprint(current) == self.fingerprint(message)' in runtime
    assert 'text: value.text, attributes: attributes, media: value.media' in runtime
    keys = (args.source / (PREFIX + 'Credentials.swift')).read_text()
    assert 'kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly' in keys and 'UserDefaults' not in keys
    cloud = (args.source / (PREFIX + 'Cloud.swift')).read_text()
    assert 'completionHandler(nil)' in cloud and 'URLSessionConfiguration.ephemeral' in cloud and 'URLSession.shared' not in cloud
    assert 'translate_a' not in cloud
    calls = [n.func.id for n in ast.walk(ast.parse((ROOT / 'ios/apply_overlay.py').read_text())) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert calls.index('apply_pip_native_entry') < calls.index('apply_message_translation')
    with tempfile.TemporaryDirectory(prefix='nagramix-translation-') as folder:
        temp = Path(folder); previous = previous_files(args.source, p)
        rejected = guard_tests(args.source, p, previous, temp); prior_checks(args.source, previous, p, temp, args.swiftc)
        runs = swift_checks(args.source, args.swiftc, temp) if args.swiftc else []
    result = dict(files=len(p['outputs']), helpers=len(p['copies']), operations=len(p['patches']), guards=len(p['guards']), fail_closed=rejected, runs=runs,
                  limits='Apple ML/Translation, Security/Keychain, UIKit and Postbox delivery are explicit boundaries; live providers not called',
                  source_hashes={**p['outputs'], **{n: v['sha256'] for n,v in p['copies'].items()}},
                  prior='точное восстановление входов; строгие проверки прежних кружков и отложенной отправки пройдены', SDK='ожидается', iPhone='ожидается', IPA='не собиралась')
    if args.report: args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
