"""Применить согласованный режим взаимодействия с временными сообщениями."""
import hashlib
import json
from pathlib import Path


def apply_temporary_message_interaction(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'temporary_message_interaction_patches.json').read_text())
    helper = 'submodules/TelegramUI/Sources/Chat/NagramiXTemporaryReplySend.swift'
    build = 'submodules/TelegramUI/BUILD'
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'pip_swipe_handoff'
        or not plan['inputs']
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != {helper}
        or set(plan['copies']) & (set(plan['inputs']) | set(plan['guards']))
        or plan['deletions']
        or plan['guards'].get(build) != 'c819263cd1c2d6407308fe3f172f9f564b40e26f3b688da39739577bae792f52'
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('temporary_message_interaction: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('temporary_message_interaction: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('temporary_message_interaction: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('temporary_message_interaction: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('temporary_message_interaction: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('temporary_message_interaction: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('temporary_message_interaction: guard mismatch ' + name)
    if b'"Sources/**/*.swift"' not in checked(source, build, plan['guards'][build]):
        raise SystemExit('temporary_message_interaction: helper outside native source glob')

    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('temporary_message_interaction: prior mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('temporary_message_interaction: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        path = safe(source, name)
        if path.exists() or path.is_symlink():
            raise SystemExit('temporary_message_interaction: existing helper ' + name)
        prepared[name] = template(item['source'], item['sha256'])

    # No source mutation until every input, dependency, template, origin and
    # destination has passed. Published historical snapshots remain unchanged.
    for name, data in prepared.items():
        path = safe(source, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
