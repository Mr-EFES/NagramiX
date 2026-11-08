"""Пользовательские ключи интернет-провайдеров и обновление списка моделей."""
import hashlib
import json
from pathlib import Path


def apply_cloud_credential_entry(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'cloud_credential_entry_patches.json').read_text())
    if (plan.get('target_pin') != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan.get('overlay_base_pin') != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan.get('required_previous_stage') != 'preview_reply_intent'
            or any(plan['inputs'].keys() != plan[field].keys()
                   for field in ('outputs', 'previous', 'replacements'))
            or len(plan['inputs']) != 4
            or set(plan['inputs']) & set(plan['guards'])
            or plan['copies'] or plan['deletions']):
        raise SystemExit('Cloud credential entry: inconsistent manifest')

    def checked(root: Path, name: str, digest: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts
                or not path.resolve().is_relative_to(root.resolve())):
            raise SystemExit('Cloud credential entry: unsafe path')
        if not path.is_file():
            raise SystemExit('Cloud credential entry: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit('Cloud credential entry: drift ' + name)
        return data

    for name, digest in plan['templates'].items():
        checked(overlay, name, digest)
    for name, digest in plan['guards'].items():
        checked(source, name, digest)
    prepared = {}
    for name, digest in plan['inputs'].items():
        before = checked(source, name, digest)
        if before != checked(overlay, plan['previous'][name], digest):
            raise SystemExit('Cloud credential entry: prior mismatch ' + name)
        prepared[name] = checked(overlay, plan['replacements'][name], plan['outputs'][name])
    # No writes until all inputs, guards, templates and destinations are checked.
    for name, data in prepared.items():
        (source / name).write_bytes(data)
