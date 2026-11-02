#!/usr/bin/env python3
"""Проверить удаление старых адаптеров PiP и интеграцию Ghostgram."""
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
PLAN = json.loads((OVERLAY / 'ghostgram_pip_cleanup_patches.json').read_text())
def sha(data): return hashlib.sha256(data).hexdigest()
def is_applied(source):
    expected = {**PLAN['outputs'], **{name: item['sha256'] for name, item in PLAN['copies'].items()}}
    return all((source / name).is_file() and sha((source / name).read_bytes()) == digest for name, digest in expected.items()) and all(not (source / name).exists() for name in PLAN['deletions'])
def verify(source):
    assert is_applied(source)
    for name, digest in PLAN['guards'].items():
        if name in PLAN['deletions']: continue
        assert sha((source / name).read_bytes()) == digest
    for name, digest in PLAN['templates'].items(): assert sha((OVERLAY / name).read_bytes()) == digest
def reverse(source, prior):
    names = set(PLAN['inputs'])
    for manifest in OVERLAY.glob('*_patches.json'):
        item = json.loads(manifest.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'): names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift'])
    names.add('submodules/GalleryUI/Sources/ZoomableContentGalleryItemNode.swift')
    for name in names - set(PLAN['copies']):
        old = PLAN['previous'].get(name) or PLAN['deletions'].get(name, {}).get('source'); path = OVERLAY / old if old else source / name
        if path.is_file():
            target = prior / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(path.read_bytes())
def delegate_if_applied(args, script):
    from validate_rich_content_copy import delegate_if_applied as delegate_next
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
    from validate_rich_content_copy import delegate_if_applied as delegate_next
    if delegate_next(args, Path(__file__)): return
    verify(args.source)
    root = args.source / "submodules/GalleryUI/Sources"
    text = (root / "Items/UniversalVideoGalleryItem.swift").read_text()
    assert (OVERLAY / "ghostgram_pip_replacement/GhostgramNativePiP.swift.inc").read_text() in text
    for name in ("Lifecycle", "Placeholder", "PlaceholderMethods", "Layout", "SwipeUp", "SwipeDown"):
        assert (OVERLAY / ("ghostgram_pip_gallery_exact/" + name + ".inc")).read_text() in text, name
    methods = (OVERLAY / "ghostgram_pip_replacement/GhostgramGalleryPiP.swift.inc").read_text()
    assert methods in text
    for name in ("Transitions", "OverlayReturn", "Shortcuts"):
        assert (OVERLAY / ("ghostgram_pip_cleanup/" + name + ".inc")).read_text() in text, name
    assert "nagramiXPiP" not in text and "NagramiXNativePlayerPiP" not in text
    assert "nagramiXNativePiPRequested" not in (root / "ChatItemGalleryFooterContentNode.swift").read_text()
    forbidden = ('nagramiXPiP', 'nagramiXNativePiP', 'nagramiXDirectionalPiP', 'nagramiXPictureInPicture', 'nagramiXSystemPiP', 'setNagramiXSystemPiP', 'nagramiXCancelSwipePreparation', 'prepareForPictureInPictureSwipe', 'cancelPictureInPictureSwipePreparation')
    for name in PLAN['outputs']:
        source_text = (args.source / name).read_text()
        assert not any(token in source_text for token in forbidden), name
    assert not (root / "NagramiXNativePlayerPiP.swift").exists()
    assert not (root / "NagramiXNativePlayerPiPSwipe.swift").exists()
    assert "self.addSubnode(self.scrollNode)" in text
    assert "videoSurface" not in text
    if args.swiftc:
        for path in PLAN["outputs"]:
            subprocess.run([args.swiftc, "-frontend", "-parse", str(args.source / path)], check=True)
    print("Ghostgram PiP: legacy controllers, gesture adapters and source hooks removed")
if __name__ == "__main__": main()
