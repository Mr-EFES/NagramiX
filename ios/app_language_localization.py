"""Применить локализацию интерфейса после всех прежних immutable стадий."""
import hashlib
import json
from pathlib import Path


def apply_app_language_localization(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'app_language_localization_patches.json').read_text())
    if not (plan['inputs'].keys() == plan['outputs'].keys() == plan['previous'].keys() == plan['replacements'].keys()):
        raise SystemExit('App localization: inconsistent manifest')
    if set(plan['copies']) & (set(plan['inputs']) | set(plan['guards'])):
        raise SystemExit('App localization: destination collision')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('App localization: unsafe path ' + name)
        if not path.is_file():
            raise SystemExit('App localization: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('App localization: drift ' + name)
        return data

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        checked(source, name, expected)
    prepared = {}
    for name, expected in plan['inputs'].items():
        data = checked(source, name, expected)
        if checked(overlay, plan['previous'][name], expected) != data:
            raise SystemExit('App localization: wrong prior template')
        prepared[name] = checked(overlay, plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        relative = Path(name)
        path = source / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(source.resolve()) or path.exists():
            raise SystemExit('App localization: copy collision or unsafe path ' + name)
        prepared[name] = checked(overlay, item['source'], item['sha256'])
    for name, data in prepared.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
