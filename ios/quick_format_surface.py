"""Give the shared formatting panel its approved surface and complete title.

Run after story_profile; earlier overlays and their SHA chain stay unchanged.
Validate all three files and replacement results before writing native sources.
"""
import hashlib
import json
from pathlib import Path


def apply_quick_format_surface(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'quick_format_surface_patches.json').read_text())
    if plan['inputs'].keys() != plan['outputs'].keys():
        raise SystemExit('Formatting surface input/output mismatch')
    prepared = {}
    for name, expected in plan['inputs'].items():
        relative = Path(name)
        path = source / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(source.resolve()):
            raise SystemExit('Unsafe formatting surface path: ' + name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Formatting surface input drift: ' + name)
        prepared[name] = path.read_text()
    for name, old, new in plan['patches']:
        if name not in prepared or prepared[name].count(old) != 1:
            raise SystemExit('Formatting surface anchor drift: ' + name)
        prepared[name] = prepared[name].replace(old, new, 1)
    for name, text in prepared.items():
        if hashlib.sha256(text.encode()).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Formatting surface output drift: ' + name)
    for name, text in prepared.items():
        (source / name).write_text(text)
