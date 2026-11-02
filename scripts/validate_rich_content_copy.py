#!/usr/bin/env python3
"""Проверить пересылку и рассылку структурированных постов."""
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
PLAN = json.loads((OVERLAY / 'rich_content_copy_patches.json').read_text())

def run_swift_regressions(source, swiftc):
    # Reuse the established API doubles, with the actual current copier,
    # resource stager and fetcher. No production implementation is mocked.
    boundary = (ROOT / 'scripts/tests/NagramiXContentCopyTests.swift').read_text().split('@main struct ContentCopyTests', 1)[0]
    with tempfile.TemporaryDirectory(prefix='rich-copy-swift-') as folder:
        folder = Path(folder)
        (folder / 'Boundary.swift').write_text(boundary)
        paths = []
        for name in ('NagramiXOutgoingCopy.swift', 'NagramiXContentCopy.swift', 'NagramiXArchivedMediaCopy.swift'):
            text = (source / 'submodules/TelegramCore/Sources/Utils' / name).read_text()
            path = folder / name
            path.write_text('import Foundation\n' + '\n'.join(line for line in text.splitlines() if not line.startswith('import ')).replace('public ', ''))
            paths.append(path)
        for mode in ([], ['-O']):
            binary = folder / 'test'
            subprocess.run([str(swiftc), *mode, '-module-cache-path', str(folder / 'cache'), str(folder / 'Boundary.swift'), *map(str, paths), str(ROOT / 'scripts/tests/NagramiXRichContentCopyTests.swift'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=30)
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
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift', 'submodules/GalleryUI/Sources/ZoomableContentGalleryItemNode.swift'])
    for name in names - set(PLAN['copies']):
        old = PLAN['previous'].get(name); path = OVERLAY / old if old else source / name
        if path.is_file():
            target = prior / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(path.read_bytes())
def delegate_if_applied(args, script):
    from validate_gallery_export_privacy_gate import delegate_if_applied as delegate_next
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--swiftc")
    args = parser.parse_args()
    from validate_gallery_export_privacy_gate import delegate_if_applied as delegate_next
    if delegate_next(args, Path(__file__)): return
    verify(args.source)
    core = args.source / "submodules/TelegramCore/Sources/Utils"
    copier = (core / "NagramiXOutgoingCopy.swift").read_text()
    fetcher = (core / "NagramiXContentCopy.swift").read_text()
    assert "copiedMedia[id] = localMedia" in copier
    assert "mediaReference == nil && copiedRichText == nil" in copier
    assert "account == nil || page.isComplete" in copier
    assert "mediaToFetch.append(contentsOf: page.rawMedia.values)" in fetcher
    if args.swiftc:
        for name in PLAN['outputs']:
            subprocess.run([args.swiftc, '-frontend', '-parse', str(args.source / name)], check=True)
        run_swift_regressions(args.source, args.swiftc)
    print('Rich content copy: source, structure, full-page and resource guards OK')
if __name__ == '__main__': main()
