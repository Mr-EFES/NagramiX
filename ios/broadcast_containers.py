"""Allow broadcast pickers to open forum/community destinations in multi-select.

Apply after quick_format_surface without changing earlier canonical overlays.
"""
import hashlib
import json
from pathlib import Path


def apply_broadcast_containers(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'broadcast_containers_patches.json').read_text())
    if plan['inputs'].keys() != plan['outputs'].keys():
        raise SystemExit('Broadcast containers input/output mismatch')
    prepared = {}
    for name, expected in plan['inputs'].items():
        relative = Path(name)
        path = source / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(source.resolve()):
            raise SystemExit('Unsafe broadcast containers path: ' + name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Broadcast containers input drift: ' + name)
        prepared[name] = path.read_text()
    for name, old, new in plan['patches']:
        if name not in prepared or prepared[name].count(old) != 1:
            raise SystemExit('Broadcast containers anchor drift: ' + name)
        prepared[name] = prepared[name].replace(old, new, 1)
    for name, text in prepared.items():
        if hashlib.sha256(text.encode()).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Broadcast containers output drift: ' + name)
    for name, text in prepared.items():
        (source / name).write_text(text)
