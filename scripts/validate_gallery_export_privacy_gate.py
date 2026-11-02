#!/usr/bin/env python3
"""Проверить единое разрешение защищённого экспорта из галереи."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'gallery_export_privacy_gate_patches.json').read_text())
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
    from validate_ghostgram_pip_compile_fix import delegate_if_applied as delegate_next
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
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc')
    args = parser.parse_args()
    from validate_ghostgram_pip_compile_fix import delegate_if_applied as delegate_next
    if delegate_next(args, Path(__file__)): return
    verify(args.source)
    root = args.source / 'submodules/GalleryUI'
    policy = (root / 'Sources/NagramiXGallerySavePolicy.swift').read_text()
    assert 'return NagramiXPrivacySettings.current.bypassScreenshots' in policy
    assert '&& (settings.showForwardWithoutAuthor || settings.showBroadcastMessages)' in policy
    assert '&& message.nagramiXAllowsContentCopy' in policy
    assert 'import NagramiXMediaSettings' in policy
    assert '"//submodules/NagramiXMediaSettings:NagramiXMediaSettings"' in (root / 'BUILD').read_text()
    image = (root / 'Sources/Items/ChatImageGalleryItem.swift').read_text()
    video = (root / 'Sources/Items/UniversalVideoGalleryItem.swift').read_text()
    # The action handlers already recheck the common policy after menu creation,
    # including the quality submenu, before beginning the save.
    assert image.count('nagramiXCanSaveGalleryMedia(message, peerIsCopyProtected: self.peerIsCopyProtected)') == 2
    assert video.count('nagramiXCanSaveGalleryMedia(message, peerIsCopyProtected: item.peerIsCopyProtected)') == 5
    if args.swiftc:
        subprocess.run([args.swiftc, '-frontend', '-parse', str(root / 'Sources/NagramiXGallerySavePolicy.swift')], check=True)
        with tempfile.TemporaryDirectory(prefix='gallery-export-gate-swift-') as folder:
            folder = Path(folder)
            production = folder / 'Policy.swift'
            production.write_text('\n'.join(line for line in policy.splitlines() if not line.startswith('import ')))
            for mode in ([], ['-O']):
                binary = folder / 'test'
                subprocess.run([args.swiftc, *mode, '-module-cache-path', str(folder / 'cache'), str(production), str(ROOT / 'scripts/tests/NagramiXGalleryExportPrivacyTests.swift'), '-o', str(binary)], check=True)
                subprocess.run([str(binary)], check=True, timeout=30)
    print('Gallery export privacy: common gate and save-action rechecks OK')

if __name__ == '__main__': main()
