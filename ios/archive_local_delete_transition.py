"""Keep retained archive rows in place during delete-for-me Undo."""
import hashlib
import json
from pathlib import Path


def apply_archive_local_delete_transition(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'archive_local_delete_transition_patches.json').read_text())
    inputs = {
        'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift',
        'submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift',
        'submodules/TelegramUI/Sources/ChatHistoryListNode.swift',
    }
    guards = {
        'submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift',
        'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift',
        'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift',
        'submodules/TelegramCore/Sources/TelegramEngine/Messages/DeleteMessages.swift',
    }
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan['required_previous_stage'] != 'round_quality_sheet_navigation'
            or any(plan[field].keys() != inputs for field in ('inputs', 'outputs', 'previous', 'replacements'))
            or any(plan[field].keys() != guards for field in ('guards', 'guard_sources'))
            or any(plan[field] for field in ('copies', 'deletions', 'native_inputs', 'native_guards'))):
        raise SystemExit('archive_local_delete_transition: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit(f'archive_local_delete_transition: invalid file {name}')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'archive_local_delete_transition: drift {name}')
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit(f'archive_local_delete_transition: unregistered template {name}')
        return checked(overlay, name, expected)

    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit(f'archive_local_delete_transition: guard mismatch {name}')

    outputs = {}
    for name, expected in plan['inputs'].items():
        if checked(source, name, expected) != template(plan['previous'][name], expected):
            raise SystemExit(f'archive_local_delete_transition: input mismatch {name}')
        outputs[name] = template(plan['replacements'][name], plan['outputs'][name])

    for name, data in outputs.items():
        (source / name).write_bytes(data)
