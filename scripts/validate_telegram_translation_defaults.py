#!/usr/bin/env python3
"""Проверить владение потоковыми запросами PiP и подготовку AVAsset."""
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
PLAN = json.loads((OVERLAY / 'telegram_translation_defaults_patches.json').read_text())
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
    from validate_single_player_pip import delegate_if_applied as delegate_next
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
    parser = argparse.ArgumentParser(); parser.add_argument("--source", type=Path, required=True); parser.add_argument("--swiftc"); args = parser.parse_args()
    verify(args.source)
    pref = (args.source / "submodules/TelegramUIPreferences/Sources/TranslationSettings.swift").read_text()
    ui = (args.source / "submodules/SettingsUI/Sources/Language Selection/LocalizationListControllerNode.swift").read_text()
    assert "TranslationSettings(showTranslate: false, translateChats: false, ignoredLanguages: nil)" in pref
    assert "translateChats = isPremium\n" not in ui
    if args.swiftc:
        for name in PLAN["outputs"]: subprocess.run([args.swiftc, "-frontend", "-parse", str(args.source / name)], check=True)
        with tempfile.TemporaryDirectory(prefix="translation-defaults-test-") as folder:
            path = Path(folder) / "main.swift"
            structure = pref[pref.index("public struct TranslationSettings:"):pref.index("public func updateTranslationSettingsInteractively")]
            path.write_text("import Foundation\n" + (ROOT / "ios/Tests/TranslationDefaultsTests.swift").read_text().replace("// STRUCTURE", structure))
            binary = Path(folder) / "probe"
            subprocess.run([args.swiftc, str(path), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
    print("Telegram translation defaults: OK")
if __name__ == "__main__": main()
