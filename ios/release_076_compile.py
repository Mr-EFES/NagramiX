"""Исправить три подтверждённые ошибки компиляции SDK137."""
import hashlib
import json
from pathlib import Path


def apply_release_076_compile(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'release_076_compile_patches.json').read_text())
    if not (plan['inputs'].keys() == plan['outputs'].keys() == plan['replacements'].keys() == plan['previous'].keys()):
        raise SystemExit('Release compilation input/output mismatch')
    if set(plan['copies']) & (set(plan['inputs']) | set(plan['guards'])):
        raise SystemExit('Release compilation destination collision')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Unsafe release compilation path: ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file(): raise SystemExit('Missing release compilation input: ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('Release compilation input/template drift: ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('Unregistered release compilation template: ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items(): checked(overlay, name, expected)
    for name, expected in {**plan['guards'], **plan['inputs']}.items(): checked(source, name, expected)
    prepared = {}
    for name, old in plan['previous'].items(): template(old, plan['inputs'][name])
    for name, item in plan['replacements'].items(): prepared[name] = template(item, plan['outputs'][name])
    for name, item in plan['copies'].items():
        if safe(source, name).exists(): raise SystemExit('Release compilation helper collision: ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    for name in prepared: safe(source, name)
    # Every input, BUILD, third-party pin, template and destination checked first.
    for name, data in prepared.items():
        path = safe(source, name); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
