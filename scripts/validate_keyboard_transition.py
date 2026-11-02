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
PLAN = json.loads((OVERLAY / 'keyboard_transition_patches.json').read_text())

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
    from validate_pip_readiness_fix import delegate_if_applied as delegate_latest
    if delegate_latest(args, script): return True
    source = args.source
    if not is_applied(source): return False
    verify(source)
    with tempfile.TemporaryDirectory(prefix='keyboard-prior-') as folder:
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
        with tempfile.TemporaryDirectory(prefix='keyboard-swift-') as temp:
            swift = Path(temp) / 'ChatControllerNode.swift'
            swift.write_bytes((OVERLAY / 'keyboard_transition/After.swift.inc').read_bytes())
            subprocess.run([args.swiftc, '-frontend', '-parse', str(swift)], check=True)
    spec = importlib.util.spec_from_file_location('keyboard_transition', OVERLAY / 'keyboard_transition.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert PLAN['inputs'].keys() == PLAN['outputs'].keys() == PLAN['previous'].keys() == PLAN['replacements'].keys()
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest
    before = {name: (OVERLAY / template).read_bytes() for name, template in PLAN['previous'].items()}
    path = next(iter(before))
    after = (OVERLAY / PLAN['replacements'][path]).read_text()
    for text in ['textNode.isInputFirstResponder, textNode.keyboardInputView == nil',
                 '!layout.inputHeightIsInteractivellyChanging', 'if case .media(_, nil, _) = self.chatPresentationInterfaceState.inputMode',
                 'inputNodeForState.followsDefaultHeight, !inputNodeForState.hideInput',
                 'self.nagramiXSystemKeyboardSize == layout.size',
                 'inputPanelBottomInsetTerm = max(insets.bottom, resolvedStandardInputHeight)',
                 'min(heightAndOverflow.0, resolvedStandardInputHeight)',
                 'standardInputHeight: inputHeight']:
        assert text in after, text
    with tempfile.TemporaryDirectory(prefix='keyboard-transition-') as temp:
        source = Path(temp)
        for name, data in before.items():
            target = source / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        build = (OVERLAY / 'keyboard_transition/TelegramUI.BUILD.inc').read_bytes()
        for name in PLAN['guards']:
            target = source / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(build)
        module.apply_keyboard_transition(source, OVERLAY)
        assert sha((source / path).read_bytes()) == PLAN['outputs'][path]
        try: module.apply_keyboard_transition(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError('повторное применение не отклонено')
        for name in list(PLAN['inputs']) + list(PLAN['guards']):
            for n, data in before.items(): (source / n).write_bytes(data)
            for n in PLAN['guards']: (source / n).write_bytes(build)
            target = source / name; target.write_bytes(target.read_bytes() + b'\n// drift')
            snapshot = (source / path).read_bytes()
            try: module.apply_keyboard_transition(source, OVERLAY)
            except SystemExit: pass
            else: raise AssertionError('изменённый вход не отклонён: ' + name)
            assert (source / path).read_bytes() == snapshot
    print('Keyboard transition: overlay и проверки целостности пройдены')

if __name__ == '__main__': main()
