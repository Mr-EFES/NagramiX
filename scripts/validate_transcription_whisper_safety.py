#!/usr/bin/env python3
"""Проверить видимость Telegram по Premium и индексы остальных сервисов."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'transcription_whisper_safety_patches.json').read_text())


def sha(data): return hashlib.sha256(data).hexdigest()


def is_applied(source):
    expected = {**PLAN['outputs'], **{n: item['sha256'] for n, item in PLAN['copies'].items()}}
    return all((source / n).is_file() and sha((source / n).read_bytes()) == h for n, h in expected.items()) and not any((source / n).exists() for n in PLAN['deletions'])


def reverse(source, target):
    names = set(PLAN['inputs']) | set(PLAN['deletions'])
    for manifest in OVERLAY.glob('*_patches.json'):
        item = json.loads(manifest.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift'])
    for name in names - set(PLAN['copies']):
        original = PLAN['previous'].get(name) or PLAN['deletions'].get(name, {}).get('source')
        path = OVERLAY / original if original else source / name
        if not path.is_file(): continue
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())


def delegate_if_applied(args, script):
    from validate_transcription_cloud_ui import delegate_if_applied as delegate_latest
    if delegate_latest(args, script): return True
    if not is_applied(args.source): return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='before-whisper-safety-') as folder:
        prior = Path(folder)
        reverse(args.source, prior)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None:
            arguments += ['--upstream', str(args.source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def verify(source):
    assert is_applied(source)
    for n, h in PLAN['guards'].items(): assert sha((source / n).read_bytes()) == h
    for n, h in PLAN['templates'].items(): assert sha((OVERLAY / n).read_bytes()) == h
    files = {Path(n).name:(source/n).read_text() for n in PLAN['outputs']}
    ui = files['Preferences.swift']
    assert '[NagramiXWhisperModel.base_full, .small_full, .medium, .large_v3]' in ui
    for title in ['Базовая', 'Малая', 'Средняя', 'Максимальная']: assert title in ui
    assert 'NagramiXWhisperModel.allCases.map' not in ui
    whisper = files['Whisper.swift']
    assert whisper.count('os_proc_available_memory() >= required') == 2
    assert whisper.index('os_proc_available_memory() >= required') < whisper.index('media.pcm(cancellation: cancellation)') < whisper.index('nx_whisper_transcribe(')
    assert 'NagramiXTranscriptionFailure.insufficientMemory' in whisper
    assert 'case .insufficientMemory:' in files['Settings.swift']
    assert 'public var whisper: NagramiXWhisperModel = .base_full' in files['Settings.swift']


def guard_tests(source):
    spec = importlib.util.spec_from_file_location('transcription_whisper_safety', OVERLAY / 'transcription_whisper_safety.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    originals = {n: (OVERLAY / f).read_bytes() for n, f in PLAN['previous'].items()}
    for n, item in PLAN['deletions'].items(): originals[n] = (OVERLAY / item['source']).read_bytes()
    originals.update({n: (source / n).read_bytes() for n in PLAN['guards'] if n not in PLAN['deletions']})
    with tempfile.TemporaryDirectory(prefix='whisper-safety-guards-') as folder:
        temp = Path(folder)
        def seed():
            base = temp / 'input'
            for n, data in originals.items():
                path = base / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            return base
        def snapshot(base): return {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}
        def reject(base, overlay=OVERLAY):
            old = snapshot(base)
            try: module.apply_transcription_whisper_safety(base, overlay)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError('Принят дрейф')
            assert snapshot(base) == old, 'Частичная запись/удаление'
            shutil.rmtree(base)
        base = seed(); module.apply_transcription_whisper_safety(base, OVERLAY); verify(base); reject(base)
        rejected = 1
        for n in originals:
            for missing in (False, True):
                base = seed()
                if missing: (base / n).unlink()
                else: (base / n).write_bytes(b'// drift')
                reject(base); rejected += 1
        for n in PLAN['templates']:
            base = seed(); overlay = temp / 'overlay'; overlay.mkdir()
            for name in PLAN['templates']:
                path = overlay / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / name).read_bytes())
            (overlay / n).write_bytes(b'// drift')
            (overlay / 'transcription_whisper_safety_patches.json').write_text(json.dumps(PLAN))
            reject(base, overlay); shutil.rmtree(overlay); rejected += 1
    print(f'PASS: {rejected} fail-closed cases, no partial writes/deletion')


def execute_swift(source, compiler):
    subprocess.run([str(compiler), '-frontend', '-parse', str(source / next(iter(PLAN['outputs'])))], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--standalone', action='store_true')
    parser.add_argument('--swiftc', type=Path)
    args = parser.parse_args()
    from validate_transcription_cloud_ui import delegate_if_applied as delegate_latest
    if delegate_latest(args, Path(__file__)): return
    verify(args.source); guard_tests(args.source)
    if args.swiftc: execute_swift(args.source, args.swiftc)
    if not args.standalone:
        with tempfile.TemporaryDirectory(prefix='whisper-safety-prior-') as folder:
            prior = Path(folder); reverse(args.source, prior)
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_broadcast_stable_order.py'), '--source', str(prior)], check=True)
    print('PASS: four full Whisper models and memory guard; SDK and iPhone pending')


if __name__ == '__main__': main()
