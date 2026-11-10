"""Включить расшифровку по умолчанию и выбрать провайдер по Premium аккаунта."""
import hashlib
import json
from pathlib import Path


def apply_transcription_account_defaults(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'transcription_account_defaults_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift', 'submodules/NagramiXTranscription/Sources/Settings.swift', 'submodules/NagramiXTranscription/Sources/Preferences.swift', 'submodules/NagramiXTranscription/Sources/Runtime.swift', 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift', 'submodules/TelegramUI/Sources/AccountContext.swift', 'submodules/NagramiXTranscription/Sources/Coordinator.swift', 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift'}
    required_guards = {'submodules/TelegramUI/BUILD', 'submodules/NagramiXTranscription/Sources/Apple.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXLocalMessageData.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Transcription.swift', 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift', 'submodules/SettingsUI/BUILD', 'submodules/NagramiXTranscription/BUILD', 'submodules/NagramiXTranscription/Sources/Models.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift', 'submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Peers/Peer.swift', 'submodules/NagramiXTranscription/Sources/Credentials.swift', 'submodules/TelegramCore/Sources/AccountManager/AccountRecord.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'archived_round_native_controls'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('transcription_account_defaults: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('transcription_account_defaults: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('transcription_account_defaults: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('transcription_account_defaults: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('transcription_account_defaults: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('transcription_account_defaults: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('transcription_account_defaults: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('transcription_account_defaults: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('transcription_account_defaults: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
