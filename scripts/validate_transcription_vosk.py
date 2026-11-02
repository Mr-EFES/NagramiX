#!/usr/bin/env python3
"""Проверить native Vosk, каталог, установку, UI и прежнюю цепочку."""
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
PLAN = json.loads((OVERLAY / 'transcription_vosk_patches.json').read_text())


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
    from validate_keyboard_transition import delegate_if_applied as delegate_latest
    if delegate_latest(args, script): return True
    if not is_applied(args.source): return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='before-transcription-vosk-') as folder:
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
    for n,h in PLAN['guards'].items(): assert sha((source/n).read_bytes()) == h
    for n,h in PLAN['templates'].items(): assert sha((OVERLAY/n).read_bytes()) == h
    prefix=source/'submodules/NagramiXTranscription/Sources'
    ui=(prefix/'Preferences.swift').read_text();runtime=(prefix/'Runtime.swift').read_text()
    assert 'case .vosk:' in ui and 'case .voskLanguages:' in ui
    assert 'Row(title:$0.title,subtitle:NagramiXVoskModels.shared.status($0)' in ui
    assert 'NagramiXVoskModels.shared.remove(model)' in ui
    assert 'NagramiXVoskModels.shared.download(model)' in ui
    assert 'NagramiXTranscriptionSettings.current.revision == revision' in ui
    assert 'NagramiXTranscriptionVosk.transcribe(media: media' in runtime
    assert '[NagramiXTranscriptionProvider.apple, .whisper, .vosk]' in runtime
    assert 'index == 0 && provider.cloud' in runtime
    models=(prefix/'VoskModels.swift').read_text();recognizer=(prefix/'VoskRecognizer.swift').read_text()
    assert 'parts.contains("..")' in models and 'entry.uncompressedSize' in models
    assert 'hash.finalize()' in models and 'model.md5' in models
    assert 'SSZipArchive.extractFileFromArchive' in models and 'self.leases' in models
    assert 'volumeAvailableCapacityForImportantUsage' in models
    assert 'os_proc_available_memory() >= required' in recognizer
    assert 'nx_vosk_transcribe(' in recognizer and 'nx_vosk_free_text(output)' in recognizer
    assert 'sample_rate' in (source/'submodules/NagramiXTranscription/Vosk/vosk_api.h').read_text()
    assert '13348851e77887fec83631e1651655057801677472dfd0a53f1670cbe06eb735' in (source/'MODULE.bazel').read_text()
    catalog=json.loads((OVERLAY/'vosk_runtime/catalog.json').read_text())
    assert len(catalog)==52 and len({m['lang'] for m in catalog})==30
    assert all(m['license']=='Apache 2.0' and m['obsolete']=='false' for m in catalog)


def guard_tests(source):
    spec = importlib.util.spec_from_file_location('transcription_vosk', OVERLAY / 'transcription_vosk.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    originals = {n: (OVERLAY / f).read_bytes() for n, f in PLAN['previous'].items()}
    for n, item in PLAN['deletions'].items(): originals[n] = (OVERLAY / item['source']).read_bytes()
    originals.update({n: (source / n).read_bytes() for n in PLAN['guards'] if n not in PLAN['deletions']})
    with tempfile.TemporaryDirectory(prefix='transcription-vosk-guards-') as folder:
        temp = Path(folder)
        def seed():
            base = temp / 'input'
            for n, data in originals.items():
                path = base / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            return base
        def snapshot(base): return {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}
        def reject(base, overlay=OVERLAY):
            old = snapshot(base)
            try: module.apply_transcription_vosk(base, overlay)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError('Принят дрейф')
            assert snapshot(base) == old, 'Частичная запись/удаление'
            shutil.rmtree(base)
        base = seed(); module.apply_transcription_vosk(base, OVERLAY); verify(base); reject(base)
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
            (overlay / 'transcription_vosk_patches.json').write_text(json.dumps(PLAN))
            reject(base, overlay); shutil.rmtree(overlay); rejected += 1
    print(f'PASS: {rejected} fail-closed cases, no partial writes/deletion')


def execute_swift(source, compiler):
    names=[n for n in [*PLAN['outputs'],*PLAN['copies']] if n.endswith('.swift')]
    subprocess.run([str(compiler), '-frontend', '-parse', *[str(source/n) for n in names]],check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--standalone', action='store_true')
    parser.add_argument('--swiftc', type=Path)
    args = parser.parse_args()
    from validate_keyboard_transition import delegate_if_applied as delegate_latest
    if delegate_latest(args, Path(__file__)): return
    verify(args.source); guard_tests(args.source)
    compiler=shutil.which('clang++') or shutil.which('g++')
    if compiler:
        with tempfile.TemporaryDirectory(prefix='vosk-bridge-tests-') as folder:
            native=args.source/'submodules/NagramiXTranscription/Vosk'
            binary=Path(folder)/'tests'
            subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I',str(native),str(native/'Bridge.cpp'),str(ROOT/'scripts/tests/NagramiXVoskBridgeTests.cpp'),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True,timeout=30)
            print('PASS: actual Vosk C++ bridge against C API boundary (not Apple SDK)')
    if args.swiftc: execute_swift(args.source, args.swiftc)
    if not args.standalone:
        with tempfile.TemporaryDirectory(prefix='transcription-vosk-prior-') as folder:
            prior = Path(folder); reverse(args.source, prior)
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_transcription_cloudflare.py'), '--source', str(prior)], check=True)
    print('PASS: Vosk native linkage / catalog / installation / recognition / settings / local fallback; SDK and iPhone pending')


if __name__ == '__main__': main()
