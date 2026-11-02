#!/usr/bin/env python3
"""Проверить одинаковые цвета и пиктограмму сохранения в историях."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    args = parser.parse_args()
    from validate_media_privacy_fixes import delegate_if_applied
    if delegate_if_applied(args, __file__): return
    plan = json.loads((ROOT/'ios/story_icon_consistency_patches.json').read_text())
    for name, digest in {**plan['guards'], **plan['outputs']}.items():
        assert hashlib.sha256((args.source/name).read_bytes()).hexdigest() == digest, name
    name = next(iter(plan['outputs']))
    final = (args.source/name).read_text()
    old = final
    for path, a, b, count in reversed(plan['patches']):
        assert path == name and old.count(b) == count
        old = old.replace(b, a, count)
    assert hashlib.sha256(old.encode()).hexdigest() == plan['inputs'][name]
    menu = block(final, 'private func nagramiXRecordViewItem(')
    assert 'withTintColor' not in menu and '.alwaysOriginal' not in menu
    assert 'UIGraphicsImageRenderer(size: symbol.size)' in menu
    assert 'return generateTintedImage(image: image, color: theme.contextMenu.primaryColor)' in menu
    assert 'self.nagramiXStoryDownloadButton.setImage(generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Save"), color: .white), for: .normal)' in final
    assert 'self.nagramiXStoryDownloadButton.tintColor = .white' in final
    assert 'CGRect(x: headerRightOffset - 33.0, y: 12.0, width: 44.0, height: 44.0)' in final
    for marker in ['private func nagramiXRecordView(', '@objc private func nagramiXDownloadStoryPressed(', 'private func requestSave(']:
        assert block(old, marker) == block(final, marker), marker
    pdf = args.source/'submodules/TelegramUI/Images.xcassets/Chat/Context Menu/Save.imageset/ic_lt_save.pdf'
    assert re.findall(rb'/MediaBox\s*\[([^\]]+)\]', pdf.read_bytes()) == [b'0 0 24 24']
    if args.swiftc:
        subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source/name)], check=True)
    print('PASS: native tinted menu bitmap, shared24px Save glyph, unchanged44px header hit target/layout/actions; UIKit/iPhone pending')

if __name__ == '__main__': main()
