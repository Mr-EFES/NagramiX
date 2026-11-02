#!/usr/bin/env python3
"""Проверка согласования высоты клавиатуры и guarded overlay."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'pip_readiness_fix_patches.json').read_text())

def sha(data):
    return hashlib.sha256(data).hexdigest()

def is_applied(source):
    return all((source / n).is_file() and sha((source / n).read_bytes()) == digest for n, digest in PLAN['outputs'].items())


def verify(source):
    assert is_applied(source)
    for name, digest in PLAN['guards'].items():
        assert sha((source / name).read_bytes()) == digest
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest


def reverse(source, prior):
    names = set(PLAN['inputs'])
    for manifest in OVERLAY.glob('*_patches.json'):
        item = json.loads(manifest.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift'])
    for name in names:
        old = PLAN['previous'].get(name)
        path = OVERLAY / old if old else source / name
        if path.is_file():
            dest = prior / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(path.read_bytes())


def delegate_if_applied(args, script):
    from validate_keyboard_handoff import delegate_if_applied as delegate_latest
    if delegate_latest(args, script): return True
    source = args.source
    if not is_applied(source): return False
    verify(source)
    with tempfile.TemporaryDirectory(prefix='pip-ready-prior-') as folder:
        prior = Path(folder)
        reverse(source, prior)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None:
            arguments += ['--upstream', str(source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--swiftc')
    args = parser.parse_args()
    if args.swiftc:
        with tempfile.TemporaryDirectory(prefix='pip-ready-swift-') as temp:
            for i in range(2):
                swift = Path(temp) / (str(i) + '.swift')
                swift.write_bytes((OVERLAY / ('pip_readiness_fix/After%d.swift.inc' % i)).read_bytes())
                subprocess.run([args.swiftc, '-frontend', '-parse', str(swift)], check=True)
    spec = importlib.util.spec_from_file_location('pip_readiness_fix', OVERLAY / 'pip_readiness_fix.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    player = (OVERLAY / 'pip_readiness_fix/After0.swift.inc').read_text()
    view = (OVERLAY / 'pip_readiness_fix/After1.swift.inc').read_text()
    assert 'self.audioReady, self.player.currentItem?.status == .readyToPlay' in player
    assert player.index('self.seekStarted = true') < player.index('self.player.seek(to:') < player.index('self.player.playImmediately(atRate: self.rate)')
    assert 'detail.domain' in player and 'detail.code' in player
    assert 'UIPasteboard.general.string = diagnostic' in view
    before = {n: (OVERLAY / f).read_bytes() for n, f in PLAN['previous'].items()}
    with tempfile.TemporaryDirectory(prefix='pip-ready-guards-') as temp:
        source = Path(temp)
        def seed():
            for n, data in before.items():
                path = source / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        seed(); module.apply_pip_readiness_fix(source, OVERLAY); verify(source)
        try: module.apply_pip_readiness_fix(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError('Повторное применение допущено')
        for name in before:
            seed(); (source / name).write_bytes(before[name] + b'drift')
            snapshot = {n: (source / n).read_bytes() for n in before}
            try: module.apply_pip_readiness_fix(source, OVERLAY)
            except SystemExit: pass
            else: raise AssertionError('Изменённый вход допущен')
            assert snapshot == {n: (source / n).read_bytes() for n in before}
    print('PiP readiness: порядок подготовки и проверки целостности пройдены')

if __name__ == '__main__': main()
