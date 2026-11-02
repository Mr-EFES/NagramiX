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
PLAN = json.loads((OVERLAY / 'onboarding_privacy_text_patches.json').read_text())
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
    from validate_unified_temporary_messages import delegate_if_applied as delegate_next
    if delegate_next(args, script): return True
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
    spec = importlib.util.spec_from_file_location("onboarding_privacy_text", OVERLAY / "onboarding_privacy_text.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    copy = json.loads((OVERLAY / "Resources/Onboarding/copy.json").read_text())
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder)
        for name, template in PLAN["previous"].items():
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / template).read_bytes())
        module.apply_onboarding_privacy_text(source, OVERLAY); verify(source)
        for lang in ("ru", "en"):
            text = (source / f"Telegram/Telegram-iOS/{lang}.lproj/Localizable.strings").read_text()
            assert copy[lang]["Tour.Text4"].replace("\n", "\\n") in text
        try: module.apply_onboarding_privacy_text(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError("expected input guard failure")
    print("onboarding privacy text: OK")
if __name__ == "__main__": main()
