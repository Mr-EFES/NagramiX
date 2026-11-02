#!/usr/bin/env python3
"""Проверить каталоги моделей и точные границы применения overlay."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'remote_model_catalog_patches.json').read_text())
def sha(data): return hashlib.sha256(data).hexdigest()
def is_applied(source):
    expected = {**PLAN['outputs'], **{name: item['sha256'] for name, item in PLAN['copies'].items()}}
    return all((source / name).is_file() and sha((source / name).read_bytes()) == digest for name, digest in expected.items())
def verify(source):
    assert is_applied(source)
    for name, digest in PLAN['guards'].items(): assert sha((source / name).read_bytes()) == digest
    for name, digest in PLAN['templates'].items(): assert sha((OVERLAY / name).read_bytes()) == digest
def reverse(source, prior):
    names = set(PLAN['inputs'])
    for manifest in OVERLAY.glob('*_patches.json'):
        item = json.loads(manifest.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'): names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift'])
    for name in names - set(PLAN['copies']):
        old = PLAN['previous'].get(name); path = OVERLAY / old if old else source / name
        if path.is_file():
            target = prior / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(path.read_bytes())
def delegate_if_applied(args, script):
    from validate_chat_russian_language_guard import delegate_if_applied as delegate_language
    if delegate_language(args, script): return True
    source = args.source
    if not is_applied(source): return False
    verify(source)
    with tempfile.TemporaryDirectory(prefix='catalog-prior-') as folder:
        prior = Path(folder); reverse(source, prior); arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None: arguments += ['--upstream', str(source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--swiftc'); args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('remote_model_catalog', OVERLAY / 'remote_model_catalog.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    before = {name: (OVERLAY / path).read_bytes() for name, path in PLAN['previous'].items()}
    speech = (OVERLAY / 'remote_model_catalog/After0.inc').read_text()
    translation = (OVERLAY / 'remote_model_catalog/After1.inc').read_text()
    cloud = (OVERLAY / 'remote_model_catalog/After2.inc').read_text()
    catalog = (OVERLAY / 'remote_model_catalog/Catalog.swift').read_text()
    for ui in (speech, translation):
        assert 'controller.loadCatalog(provider, openPicker: false)' in ui
        assert 'self.loadCatalog(provider, openPicker: true)' in ui
        assert 'self.catalogGeneration == generation' in ui and 'currentKey' in ui
    assert 'subtitle:self.selectedModel,action:.wheel' in speech
    assert '"whisper-large-v3-turbo", "whisper"' in cloud and 'application/octet-stream' in cloud
    assert 'generation["temperature"]' in cloud and 'geminiSupportsTemperature' in speech
    assert 'completionHandler(nil)' in catalog and 'nextPageToken' in catalog and 'pageNumber + 1' in catalog
    assert 'grok-voice-transcribe-2.0' in catalog and 'return .failure' not in catalog
    if args.swiftc:
        with tempfile.TemporaryDirectory(prefix='catalog-swift-') as folder:
            temp = Path(folder)
            for i, name in enumerate(list(PLAN['replacements'].values()) + ['remote_model_catalog/Catalog.swift']):
                file = temp / f'{i}.swift'; file.write_bytes((OVERLAY / name).read_bytes())
                subprocess.run([args.swiftc, '-frontend', '-parse', str(file)], check=True)
            helper = temp / 'Catalog.swift'; helper.write_bytes((OVERLAY / 'remote_model_catalog/Catalog.swift').read_bytes())
            mainfile = temp / 'main.swift'; mainfile.write_bytes((ROOT / 'scripts/tests/NagramiXRemoteModelCatalogTests.swift').read_bytes())
            binary = temp / 'catalog-tests'
            subprocess.run([args.swiftc, str(helper), str(mainfile), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
    with tempfile.TemporaryDirectory(prefix='catalog-guards-') as folder:
        source = Path(folder)
        def seed():
            for name in PLAN['copies']: (source / name).unlink(missing_ok=True)
            for name, data in before.items():
                target = source / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            for i, name in enumerate(PLAN['guards']):
                target = source / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((OVERLAY / f'remote_model_catalog/Guard{i}.inc').read_bytes())
        seed(); module.apply_remote_model_catalog(source, OVERLAY); verify(source)
        try: module.apply_remote_model_catalog(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError('Повторное применение допущено')
        for name in list(before) + list(PLAN['guards']):
            seed(); target = source / name; target.write_bytes(target.read_bytes() + b'drift')
            snapshot = {n: (source / n).read_bytes() for n in before}
            try: module.apply_remote_model_catalog(source, OVERLAY)
            except SystemExit: pass
            else: raise AssertionError('Изменённый вход допущен')
            assert snapshot == {n: (source / n).read_bytes() for n in before}
            assert not any((source / n).exists() for n in PLAN['copies'])
    print('Каталоги моделей и защитные проверки пройдены')
if __name__ == '__main__': main()
