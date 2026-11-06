"""Завершить полный перенос доработок на закреплённую базу13.2."""
import hashlib
import json
from pathlib import Path


def apply_upstream_13_2_release_post(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'upstream_13_2_release_post_patches.json').read_text())
    if any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements')):
        raise SystemExit('Telegram13.2 migration post: inconsistent manifest')
    if set(plan['copies']) & (set(plan['inputs']) | set(plan['guards'])):
        raise SystemExit('Telegram13.2 migration post: copy collision')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Telegram13.2 migration post: unsafe path')
        return path

    def checked(root: Path, name: str, digest: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('Telegram13.2 migration post: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit('Telegram13.2 migration post: drift ' + name)
        return data

    for name, digest in plan['templates'].items():
        checked(overlay, name, digest)
    for name, digest in plan['guards'].items():
        checked(source, name, digest)
    prepared = {}
    for name, digest in plan['inputs'].items():
        if checked(source, name, digest) != checked(overlay, plan['previous'][name], digest):
            raise SystemExit('Telegram13.2 migration post: prior mismatch ' + name)
        prepared[name] = checked(overlay, plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('Telegram13.2 migration post: existing ' + name)
        prepared[name] = checked(overlay, item['source'], item['sha256'])
    for name, item in plan.get('deletions', {}).items():
        if name not in plan['guards'] or name in prepared or item['sha256'] != plan['guards'][name]:
            raise SystemExit('Telegram13.2 migration post: invalid deletion ' + name)
        if checked(overlay, item['source'], item['sha256']) != checked(source, name, item['sha256']):
            raise SystemExit('Telegram13.2 migration post: deletion mismatch ' + name)
    # No mutation until every dependency, destination and template is checked.
    for name, data in prepared.items():
        path = safe(source, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    for name in plan.get('deletions', {}):
        safe(source, name).unlink()
