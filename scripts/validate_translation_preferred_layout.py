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
PLAN = json.loads((OVERLAY / 'translation_preferred_layout_patches.json').read_text())
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
    from validate_translation_speech_text_only import delegate_if_applied as delegate_text
    if delegate_text(args, script): return True
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
    spec = importlib.util.spec_from_file_location('translation_preferred_layout', OVERLAY / 'translation_preferred_layout.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    before = {name: (OVERLAY / path).read_bytes() for name, path in PLAN['previous'].items()}
    ui = (OVERLAY / 'translation_preferred_layout/After.inc').read_text()
    assert 'value.effectiveIgnored(interface: self.interfaceLanguage).filter { $0 != targetCode }' in ui
    assert '([targetCode] + others).map(self.languageTitle).joined(separator: ", ")' in ui
    assert 'self.search.searchTextField.convert(self.search.searchTextField.bounds, to: self.table)' in ui
    assert 'self.table.visibleCells.first.map' in ui
    assert 'if case .preferred = self.page { self.alignPreferredSearch() }' in ui
    if args.swiftc:
        with tempfile.TemporaryDirectory(prefix='preferred-parse-') as folder:
            source = Path(folder) / 'Settings.swift'
            source.write_bytes((OVERLAY / 'translation_preferred_layout/After.inc').read_bytes())
            subprocess.run([args.swiftc, '-frontend', '-parse', str(source)], check=True)
    with tempfile.TemporaryDirectory(prefix='catalog-guards-') as folder:
        source = Path(folder)
        def seed():
            for name in PLAN['copies']: (source / name).unlink(missing_ok=True)
            for name, data in before.items():
                target = source / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            for i, name in enumerate(PLAN['guards']):
                target = source / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((OVERLAY / f'translation_preferred_layout/Guard{i}.inc').read_bytes())
        seed(); module.apply_translation_preferred_layout(source, OVERLAY); verify(source)
        try: module.apply_translation_preferred_layout(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError('Повторное применение допущено')
        for name in list(before) + list(PLAN['guards']):
            seed(); target = source / name; target.write_bytes(target.read_bytes() + b'drift')
            snapshot = {n: (source / n).read_bytes() for n in before}
            try: module.apply_translation_preferred_layout(source, OVERLAY)
            except SystemExit: pass
            else: raise AssertionError('Изменённый вход допущен')
            assert snapshot == {n: (source / n).read_bytes() for n in before}
            assert not any((source / n).exists() for n in PLAN['copies'])
    print('Отображение предпочитаемых языков: проверки пройдены')
if __name__ == '__main__': main()
