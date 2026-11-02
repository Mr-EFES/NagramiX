#!/usr/bin/env python3
"""Проверка оформления моделей и защищённого применения стадии."""
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
PLAN = json.loads((OVERLAY / 'pip_transition_surface_patches.json').read_text())
def sha(data): return hashlib.sha256(data).hexdigest()
def is_applied(source):
    return all((source / n).is_file() and sha((source / n).read_bytes()) == digest for n, digest in PLAN['outputs'].items())
def verify(source):
    assert is_applied(source)
    for n, digest in PLAN['guards'].items(): assert sha((source / n).read_bytes()) == digest
    for n, digest in PLAN['templates'].items(): assert sha((OVERLAY / n).read_bytes()) == digest
def reverse(source, prior):
    names = set(PLAN['inputs'])
    for manifest in OVERLAY.glob('*_patches.json'):
        item = json.loads(manifest.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'): names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift'])
    for n in names:
        old = PLAN['previous'].get(n); path = OVERLAY / old if old else source / n
        if path.is_file():
            dest = prior / n; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(path.read_bytes())
def delegate_if_applied(args, script):
    from validate_round_slider_touch import delegate_if_applied as delegate_latest
    if delegate_latest(args, script): return True
    source = args.source
    if not is_applied(source): return False
    verify(source)
    with tempfile.TemporaryDirectory(prefix='speech-model-prior-') as folder:
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
    spec = importlib.util.spec_from_file_location('speech_model_display', OVERLAY / 'pip_transition_surface.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    before = {n: (OVERLAY / f).read_bytes() for n, f in PLAN['previous'].items()}
    player = (OVERLAY / 'pip_transition_surface/After.inc').read_text()
    start = player.split('    static func start(', 1)[1].split('    private init(', 1)[0]
    update = player.split('    private func update() {', 1)[1].split('    func stop()', 1)[0]
    assert start.index('session.view.alpha = 0.001') < start.index('host.addSubview(session.view)')
    assert update.index('self.view.playerLayer.isReadyForDisplay, self.view.alpha < 1') < update.index('self.view.alpha = 1')
    assert update.index('self.view.alpha = 1') < update.rindex('self.controller?.isPictureInPicturePossible == true')
    assert update.rindex('self.controller?.isPictureInPicturePossible == true') < update.index('startPictureInPicture()')
    if args.swiftc:
        with tempfile.TemporaryDirectory(prefix='speech-model-parse-') as temp:
            for i, name in enumerate(PLAN['replacements'].values()):
                file = Path(temp) / f'{i}.swift'; file.write_bytes((OVERLAY / name).read_bytes())
                subprocess.run([args.swiftc, '-frontend', '-parse', str(file)], check=True)
    with tempfile.TemporaryDirectory(prefix='speech-model-guards-') as temp:
        source = Path(temp)
        def seed():
            for n, data in before.items():
                target = source / n; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            for n in PLAN['guards']:
                target = source / n; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((OVERLAY / 'pip_transition_surface/Guard.inc').read_bytes())
        seed(); module.apply_pip_transition_surface(source, OVERLAY); verify(source)
        try: module.apply_pip_transition_surface(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError('Повторное применение допущено')
        for n in list(before) + list(PLAN['guards']):
            seed(); target = source / n; target.write_bytes(target.read_bytes() + b'drift')
            snapshot = {name: (source / name).read_bytes() for name in before}
            try: module.apply_pip_transition_surface(source, OVERLAY)
            except SystemExit: pass
            else: raise AssertionError('Изменённый вход допущен')
            assert snapshot == {name: (source / name).read_bytes() for name in before}
    print('Системный PiP: видимость готового кадра проверена')
if __name__ == '__main__': main()
