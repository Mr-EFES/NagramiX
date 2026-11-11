"""Keep remote media consumption separate from actual message deletion."""
import hashlib
import json
from pathlib import Path


def apply_temporary_expiration_semantics(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'temporary_expiration_semantics_patches.json').read_text())
    expected_inputs = {'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift', 'submodules/TelegramCore/Sources/State/ManagedAutoremoveMessageOperations.swift', 'submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift'}
    required_guards = {'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift', 'submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift', 'submodules/TelegramCore/Sources/State/ManagedSecretChatOutgoingOperations.swift', 'submodules/TelegramCore/BUILD', 'submodules/TelegramCore/Sources/State/Sync/StateReplay+ReadStates.swift', 'submodules/TelegramCore/Sources/State/ManagedSynchronizeConsumeMessageContentsOperations.swift', 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_AutoremoveTimeoutMessageAttribute.swift', 'submodules/TelegramCore/Sources/State/Sync/StateReplay+Messages.swift', 'submodules/Postbox/Sources/PeerReadState.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/DeleteMessages.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift', 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Transcription.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXArchivePersistence.swift', 'submodules/Postbox/Sources/MessageHistoryView.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift', 'submodules/Postbox/Sources/Message.swift', 'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'web_video_picture_in_picture'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('temporary_expiration_semantics: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('temporary_expiration_semantics: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('temporary_expiration_semantics: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('temporary_expiration_semantics: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('temporary_expiration_semantics: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('temporary_expiration_semantics: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('temporary_expiration_semantics: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('temporary_expiration_semantics: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('temporary_expiration_semantics: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
