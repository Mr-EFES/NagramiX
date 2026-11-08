"""Добавить удаление чата с ботом без изменения его блокировки."""
import hashlib
import json
from pathlib import Path


def apply_bot_delete_without_block(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'bot_delete_without_block_patches.json').read_text())
    if (plan.get('target_pin') != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan.get('overlay_base_pin') != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan.get('required_previous_stage') != 'extended_poll_integrity'
            or any(plan['inputs'].keys() != plan[key].keys() for key in ('outputs', 'previous', 'replacements'))
            or len(plan['inputs']) != 1 or len(plan['guards']) != 8
            or set(plan['inputs']) & set(plan['guards'])
            or plan['copies'] or plan['deletions']):
        raise SystemExit('Bot delete without block: inconsistent manifest')

    def checked(root: Path, name: str, digest: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts
                or not path.resolve().is_relative_to(root.resolve())):
            raise SystemExit('Bot delete without block: unsafe path')
        if not path.is_file():
            raise SystemExit('Bot delete without block: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit('Bot delete without block: drift ' + name)
        return data

    for name, digest in plan['templates'].items():
        checked(overlay, name, digest)
    for name, digest in plan['guards'].items():
        checked(source, name, digest)
    prepared = {}
    for name, digest in plan['inputs'].items():
        if checked(source, name, digest) != checked(overlay, plan['previous'][name], digest):
            raise SystemExit('Bot delete without block: prior mismatch ' + name)
        prepared[name] = checked(overlay, plan['replacements'][name], plan['outputs'][name])
    # Every input, dependency and destination has been checked before mutation.
    for name, data in prepared.items():
        (source / name).write_bytes(data)
