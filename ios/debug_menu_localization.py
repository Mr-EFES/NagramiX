"""Complete debug UI localization after the immutable Telegram 13.1 port.

Diagnostic payloads, destinations, settings and callbacks stay native. Validate
all source hashes, exact occurrence counts and outputs before writing any file.
"""
import hashlib
import json
from pathlib import Path


def apply_debug_menu_localization(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'debug_menu_localization_patches.json').read_text(encoding='utf-8'))
    prepared = {}
    for name, expected in plan['inputs'].items():
        relative = Path(name)
        path = source / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(source.resolve()):
            raise SystemExit('Unsafe debug localization path: ' + name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Debug localization source drift: ' + name)
        prepared[name] = path.read_text(encoding='utf-8')
    for patch in plan['patches']:
        name, old, new, count = (patch[key] for key in ('path', 'old', 'new', 'count'))
        if name not in prepared or count < 1 or prepared[name].count(old) != count:
            raise SystemExit('Debug localization anchor drift: ' + name)
        prepared[name] = prepared[name].replace(old, new)
    for name, text in prepared.items():
        if hashlib.sha256(text.encode('utf-8')).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Debug localization output drift: ' + name)
    for name, text in prepared.items():
        (source / name).write_text(text, encoding='utf-8')
