#!/usr/bin/env python3
"""Проверить значки и отправку локальных копий."""
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
PLAN = json.loads((OVERLAY / 'emoji_keyboard_stability_patches.json').read_text())
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
    from validate_story_preview_copy import delegate_if_applied as delegate_next
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
    parser = argparse.ArgumentParser(); parser.add_argument("--swiftc"); args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("emoji_keyboard_stability", OVERLAY / "emoji_keyboard_stability.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder)
        for name, template in PLAN["previous"].items():
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / template).read_bytes())
        for i, name in enumerate(PLAN["guards"]):
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / f"emoji_keyboard_stability/Guard{i}.inc").read_bytes())
        # Drift in one input must fail before any other file is written.
        bad = source / next(iter(PLAN["inputs"]))
        original = bad.read_bytes()
        bad.write_bytes(original + b"\n// drift\n")
        untouched = {name: (source / name).read_bytes() for name in PLAN["inputs"]}
        try: module.apply_emoji_keyboard_stability(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError("expected drift guard failure")
        assert all((source / name).read_bytes() == data for name, data in untouched.items())
        bad.write_bytes(original)
        module.apply_emoji_keyboard_stability(source, OVERLAY); verify(source)
        chat=(source / "submodules/TelegramUI/Sources/ChatControllerNode.swift").read_text()
        assert "let height = measuredHeight ?? emojiHeight" in chat
        assert "self.derivedLayoutState?.inputNodeAdditionalHeight" in chat
        assert "self.nagramiXKeyboardHandoffSize == layout.size" in chat
        assert "max(120.0, height * 0.75)" in chat
        assert "emojiNode.followsDefaultHeight, !emojiNode.hideInput" in chat
        assert "nagramiXFormattingPanelView(for: self.chatPresentationInterfaceState)" in chat
        # The boundary must retain the previous panel for empty and partial
        # keyboard frames and let the final measured keyboard take ownership.
        for prior, incoming, held in [(320.0, 0.0, True), (320.0, 150.0, True), (320.0, 320.0, False), (250.0, 250.0, False)]:
            assert (incoming < max(120.0, prior * 0.75)) == held
        if args.swiftc:
            for name in list(PLAN["outputs"]) + list(PLAN["copies"]): subprocess.run([args.swiftc, "-frontend", "-parse", str(source / name)], check=True)
        try: module.apply_emoji_keyboard_stability(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError("expected input guard failure")
    print("emoji keyboard stability: OK")
if __name__ == "__main__": main()
