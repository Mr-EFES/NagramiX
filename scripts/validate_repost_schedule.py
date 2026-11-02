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
PLAN = json.loads((OVERLAY / 'repost_schedule_patches.json').read_text())

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
    from validate_file_bubble_spacing import delegate_if_applied as delegate_latest
    if delegate_latest(args, script): return True
    source = args.source
    if not is_applied(source): return False
    verify(source)
    with tempfile.TemporaryDirectory(prefix='transcription-refresh-prior-') as folder:
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
    parser=argparse.ArgumentParser();parser.add_argument('--swiftc');args=parser.parse_args()
    if args.swiftc:
        with tempfile.TemporaryDirectory(prefix='repost-swift-') as temp:
            swift=Path(temp)/'ChatControllerForwardMessages.swift'
            swift.write_bytes((OVERLAY/'repost_schedule/After.swift.inc').read_bytes())
            subprocess.run([args.swiftc,'-frontend','-parse',str(swift)],check=True)
    spec=importlib.util.spec_from_file_location('repost_schedule',OVERLAY/'repost_schedule.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    before={n:(OVERLAY/f).read_bytes() for n,f in PLAN['previous'].items()}
    after=(OVERLAY/'repost_schedule/After.swift.inc').read_text()
    selection=after[after.index('controller.peerSelected ='):]
    assert 'peerId == strongSelf.context.account.peerId && !transferMode.singleRecipient' not in selection
    assert 'enqueueMessages(account:' not in selection
    assert 'withUpdatedForwardMessageIds(messages.map { $0.id })' in selection
    assert 'case .schedule:' in after and 'presentScheduleTimePicker' in after
    with tempfile.TemporaryDirectory(prefix='repost-guards-') as temp:
        source=Path(temp)
        def seed():
            for n,data in before.items():
                target=source/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            for n in PLAN['guards']:
                target=source/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((OVERLAY/'repost_schedule/BUILD.inc').read_bytes())
        seed();module.apply_repost_schedule(source,OVERLAY);verify(source)
        try: module.apply_repost_schedule(source,OVERLAY)
        except SystemExit: pass
        else: raise AssertionError('Повторное применение допущено')
        for n in list(before)+list(PLAN['guards']):
            seed();target=source/n;target.write_bytes(target.read_bytes()+b'drift')
            snapshot={name:(source/name).read_bytes() for name in before}
            try: module.apply_repost_schedule(source,OVERLAY)
            except SystemExit: pass
            else: raise AssertionError('Изменённый вход допущен')
            assert snapshot=={name:(source/name).read_bytes() for name in before}
    print('Репост: черновик и проверки целостности пройдены')

if __name__ == '__main__':main()
