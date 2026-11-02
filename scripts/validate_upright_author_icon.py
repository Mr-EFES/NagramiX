#!/usr/bin/env python3
"""Проверить владение потоковыми запросами PiP и подготовку AVAsset."""
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
PLAN = json.loads((OVERLAY / 'upright_author_icon_patches.json').read_text())
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
    from validate_pip_mode_label import delegate_if_applied as delegate_next
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
    from validate_pip_mode_label import delegate_if_applied as delegate_next
    if delegate_next(args, Path(__file__)): return
    verify(args.source)
    menu = (args.source / "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift").read_text()
    start = menu.index("private func nagramiXSelectByAuthorIcon")
    end = menu.index("private struct MessageContextMenuData", start)
    icon = menu[start:end]
    assert "rotatedContext:" in icon and "contextGenerator:" not in icon
    assert "strokeEllipse(in: CGRect(x: 4.4, y: 2.0" in icon
    assert "CGPoint(x: 13.0, y: 17.5)" in icon and "CGPoint(x: 17.2, y: 19.6)" in icon
    assert menu.count("return nagramiXSelectByAuthorIcon(theme.actionSheet.primaryTextColor)") == 2
    display = (args.source / "submodules/Display/Source/GenerateImage.swift").read_text()
    function = display[display.index("public func generateImage(_ size: CGSize, opaque: Bool = false, scale: CGFloat? = nil, rotatedContext:"):]
    assert "context.withContext { c in" in function[:700]
    if args.swiftc:
        subprocess.run([args.swiftc, "-frontend", "-parse", str(args.source / "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift")], check=True)
    print("upright author icon: OK")
if __name__ == "__main__": main()
