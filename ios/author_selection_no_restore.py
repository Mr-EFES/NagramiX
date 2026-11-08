"""Выбор автора только из существующей истории, без восстановления сообщений."""
import hashlib
import json
from pathlib import Path


def apply_author_selection_no_restore(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'author_selection_no_restore_patches.json').read_text())
    if (plan.get('target_pin') != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan.get('overlay_base_pin') != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or any(plan['inputs'].keys() != plan[field].keys()
                   for field in ('outputs', 'previous', 'replacements'))
            or len(plan['inputs']) != 2
            or set(plan['inputs']) & set(plan['guards'])
            or plan['guards'].keys() != plan['guard_sources'].keys()
            or plan['copies'] or plan['deletions']):
        raise SystemExit('Author selection: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts
                or not path.resolve().is_relative_to(root.resolve())):
            raise SystemExit('Author selection: unsafe path')
        if not path.is_file():
            raise SystemExit('Author selection: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('Author selection: drift ' + name)
        return data

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != checked(overlay, plan['guard_sources'][name], expected):
            raise SystemExit('Author selection: dependency mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        if checked(source, name, expected) != checked(overlay, plan['previous'][name], expected):
            raise SystemExit('Author selection: prior mismatch ' + name)
        replacement = plan['replacements'][name]
        if plan['templates'].get(replacement) != plan['outputs'][name]:
            raise SystemExit('Author selection: unregistered replacement')
        prepared[name] = checked(overlay, replacement, plan['outputs'][name])
    # Every source, snapshot, dependency and destination is checked before writes.
    for name, data in prepared.items():
        (source / name).write_bytes(data)
