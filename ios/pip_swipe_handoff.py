"""Ранний свайп PiP и передача живого источника после готовности окна AVKit."""
import hashlib
import json
from pathlib import Path


WIDE_SETTINGS = 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift'
WIDE_SETTINGS_SHA = '70fac4e58cb33b69abc9a60098cb114a9396c03e39d02569f6bdbad5296d07fb'


def apply_pip_swipe_handoff(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'pip_swipe_handoff_patches.json').read_text())
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan.get('required_previous_stage') != 'wide_tab_bar_setting'
            or any(plan['inputs'].keys() != plan[field].keys()
                   for field in ('outputs', 'previous', 'replacements'))
            or len(plan['inputs']) != 4
            or set(plan['inputs']) & set(plan['guards'])
            or plan['guards'].get(WIDE_SETTINGS) != WIDE_SETTINGS_SHA
            or plan['copies'] or plan['deletions']):
        raise SystemExit('PiP swipe handoff: inconsistent manifest or missing prior settings')

    def checked(root: Path, name: str, digest: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts
                or not path.resolve().is_relative_to(root.resolve())):
            raise SystemExit('PiP swipe handoff: unsafe path')
        if not path.is_file():
            raise SystemExit('PiP swipe handoff: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit('PiP swipe handoff: drift ' + name)
        return data

    for name, digest in plan['templates'].items():
        checked(overlay, name, digest)
    for name, digest in plan['guards'].items():
        checked(source, name, digest)
    prepared = {}
    for name, digest in plan['inputs'].items():
        if checked(source, name, digest) != checked(overlay, plan['previous'][name], digest):
            raise SystemExit('PiP swipe handoff: prior mismatch ' + name)
        prepared[name] = checked(overlay, plan['replacements'][name], plan['outputs'][name])

    # Validate every dependency and destination before the first mutation.
    for name, data in prepared.items():
        (source / name).write_bytes(data)
