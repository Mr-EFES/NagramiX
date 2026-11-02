"""Apply the approved 4x3 panel and native-host transition after the 13.1 port.

Earlier canonical overlays and migration hashes remain immutable. Prepare every
replacement and verify final digests before writing any application source.
"""
import hashlib
import json
from pathlib import Path


def apply_quick_format_panel(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'quick_format_panel_patches.json').read_text())
    prepared = {}
    for name, expected in plan['inputs'].items():
        relative = Path(name)
        path = source / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(source.resolve()):
            raise SystemExit('Unsafe formatting panel path: ' + name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Formatting panel source drift: ' + name)
        prepared[name] = path.read_text()
    for name, old, new in plan['patches']:
        if name not in prepared or prepared[name].count(old) != 1:
            raise SystemExit('Formatting panel anchor drift: ' + name)
        prepared[name] = prepared[name].replace(old, new, 1)
    for name, text in prepared.items():
        if hashlib.sha256(text.encode()).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Formatting panel output drift: ' + name)
    for name, text in prepared.items():
        (source / name).write_text(text)
