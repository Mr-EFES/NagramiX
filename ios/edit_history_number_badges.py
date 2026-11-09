"""Круглые порядковые номера утверждённых карточек истории правок."""
import hashlib
import json
from pathlib import Path


def apply_edit_history_number_badges(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'edit_history_number_badges_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Sources/Chat/NagramiXEditHistoryController.swift'}
    required_guards = set(['submodules/NagramiXCore/Sources/NagramiXAppLocalization.swift', 'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift', 'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift', 'submodules/TelegramCore/Sources/State/PendingMessageManager.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift', 'submodules/TelegramUI/BUILD', 'submodules/TelegramUI/Sources/Chat/NagramiXEditHistoryForwarding.swift'])
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'copy_reference_recovery'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('edit_history_number_badges: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('edit_history_number_badges: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('edit_history_number_badges: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('edit_history_number_badges: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('edit_history_number_badges: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('edit_history_number_badges: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('edit_history_number_badges: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('edit_history_number_badges: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('edit_history_number_badges: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
