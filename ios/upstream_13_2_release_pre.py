"""Подготовить точные исторические входы overlay на закреплённой базе13.2."""
import hashlib
import json
from pathlib import Path


def apply_upstream_13_2_release_pre(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'upstream_13_2_release_pre_patches.json').read_text())
    if any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements')):
        raise SystemExit('Telegram13.2 migration pre: inconsistent manifest')
    if set(plan['copies']) & (set(plan['inputs']) | set(plan['guards'])):
        raise SystemExit('Telegram13.2 migration pre: copy collision')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Telegram13.2 migration pre: unsafe path')
        return path

    def checked(root: Path, name: str, digest: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('Telegram13.2 migration pre: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit('Telegram13.2 migration pre: drift ' + name)
        return data

    for name, digest in plan['templates'].items():
        checked(overlay, name, digest)
    for name, digest in plan['guards'].items():
        checked(source, name, digest)
    prepared = {}
    for name, digest in plan['inputs'].items():
        if checked(source, name, digest) != checked(overlay, plan['previous'][name], digest):
            raise SystemExit('Telegram13.2 migration pre: prior mismatch ' + name)
        prepared[name] = checked(overlay, plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('Telegram13.2 migration pre: existing ' + name)
        prepared[name] = checked(overlay, item['source'], item['sha256'])
    # No mutation until every dependency, destination and template is checked.
    for name, data in prepared.items():
        path = safe(source, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
