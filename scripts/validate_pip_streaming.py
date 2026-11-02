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
PLAN = json.loads((OVERLAY / 'pip_streaming_patches.json').read_text())
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
    from validate_translation_manual_always import delegate_if_applied as delegate_next
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
    spec = importlib.util.spec_from_file_location("pip_streaming", OVERLAY / "pip_streaming.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder)
        for name, template in PLAN["previous"].items():
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / template).read_bytes())
        for i, name in enumerate(PLAN["guards"]):
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / f"pip_streaming/Guard{i}.inc").read_bytes())
        # Drift in one input must fail before any other file is written.
        bad = source / next(iter(PLAN["inputs"]))
        original = bad.read_bytes()
        bad.write_bytes(original + b"\n// drift\n")
        untouched = {name: (source / name).read_bytes() for name in PLAN["inputs"]}
        try: module.apply_pip_streaming(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError("expected drift guard failure")
        assert all((source / name).read_bytes() == data for name, data in untouched.items())
        bad.write_bytes(original)
        module.apply_pip_streaming(source, OVERLAY); verify(source)
        player=(OVERLAY / "pip_streaming/After0.inc").read_text()
        gallery=(OVERLAY / "pip_streaming/After1.inc").read_text()
        loader=gallery
        assert "AVPlayerItem(asset: resourceLoader.asset)" in player
        assert "self.resourceLoader.cancelAll()" in player
        assert player.count("timeControlStatus != .paused") == 2
        assert "self?.nagramiXRequestPlayerPiP()" in gallery and "commit: { [weak self] in self?.nagramiXRequestPlayerPiP() }" in gallery
        assert "filter { $0.complete }" not in gallery[gallery.index("private func nagramiXRequestPlayerPiP()"):gallery.index("private var nagramiXNativeSwipe:")]
        assert "nagramiXPiPReturn = NagramiXNativePlayerPiP.ReturnState" in gallery
        assert "resourceData(self.reference.resource, size: self.length, in: range, mode: .complete)" in loader
        assert "didCancel loadingRequest" in loader and "range: (range, .elevated)" in loader
        if args.swiftc:
            for name in list(PLAN["outputs"]) + list(PLAN["copies"]): subprocess.run([args.swiftc, "-frontend", "-parse", str(source / name)], check=True)
        try: module.apply_pip_streaming(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError("expected input guard failure")
    print("pip streaming: OK")
if __name__ == "__main__": main()
