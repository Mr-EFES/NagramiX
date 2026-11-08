"""Передать действие ответа из предпросмотра до открытия обычной переписки."""
import hashlib
import json
from pathlib import Path


def apply_preview_reply_intent(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'preview_reply_intent_patches.json').read_text())
    expected = {
        'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift',
        'submodules/TelegramUI/Sources/ChatController.swift',
    }
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan.get('required_previous_stage') != 'author_selection_no_restore'
            or set(plan['inputs']) != expected
            or any(plan['inputs'].keys() != plan[field].keys()
                   for field in ('outputs', 'previous', 'replacements'))
            or len(plan['guards']) != 12
            or set(plan['inputs']) & set(plan['guards'])
            or plan['copies'] or plan['deletions']):
        raise SystemExit('Preview reply intent: inconsistent manifest')

    def checked(root: Path, name: str, expected_hash: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit('Preview reply intent: unsafe or missing path ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise SystemExit('Preview reply intent: drift ' + name)
        return data

    for name, expected_hash in plan['templates'].items():
        checked(overlay, name, expected_hash)
    for name, expected_hash in plan['guards'].items():
        checked(source, name, expected_hash)
    prepared = {}
    for name, expected_hash in plan['inputs'].items():
        if checked(source, name, expected_hash) != checked(overlay, plan['previous'][name], expected_hash):
            raise SystemExit('Preview reply intent: prior mismatch ' + name)
        prepared[name] = checked(overlay, plan['replacements'][name], plan['outputs'][name])
    # All templates and native dependencies are validated before the first write.
    for name, data in prepared.items():
        (source / name).write_bytes(data)
