"""Целые расширенные опросы при копировании и локальном удалении."""
import hashlib
import json
from pathlib import Path


def apply_extended_poll_integrity(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'extended_poll_integrity_patches.json').read_text())
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or any(plan['inputs'].keys() != plan[field].keys()
                   for field in ('outputs', 'previous', 'replacements'))
            or not plan['inputs'] or set(plan['inputs']) & set(plan['guards'])
            or plan['copies'] or plan['deletions']):
        raise SystemExit('Extended poll integrity: inconsistent manifest')

    def checked(root: Path, name: str, digest: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts
                or not path.resolve().is_relative_to(root.resolve())):
            raise SystemExit('Extended poll integrity: unsafe path')
        if not path.is_file():
            raise SystemExit('Extended poll integrity: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit('Extended poll integrity: drift ' + name)
        return data

    for name, digest in plan['templates'].items():
        checked(overlay, name, digest)
    for name, digest in plan['guards'].items():
        checked(source, name, digest)
    prepared = {}
    for name, digest in plan['inputs'].items():
        if checked(source, name, digest) != checked(overlay, plan['previous'][name], digest):
            raise SystemExit('Extended poll integrity: previous mismatch ' + name)
        prepared[name] = checked(overlay, plan['replacements'][name], plan['outputs'][name])
    for name, data in prepared.items():
        (source / name).write_bytes(data)
