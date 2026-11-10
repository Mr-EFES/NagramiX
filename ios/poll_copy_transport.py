"""Самостоятельные опросы с полными вложениями через обновляемые медиассылки."""
import hashlib
import json
from pathlib import Path


def apply_poll_copy_transport(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'poll_copy_transport_patches.json').read_text())
    expected_inputs = {'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift', 'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift'}
    required_guards = {'submodules/TelegramCore/Sources/SyncCore/SyncCore_OutgoingContentInfoMessageAttribute.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift', 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift', 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift', 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_OutgoingMessageInfoAttribute.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Timing.swift', 'submodules/TelegramApi/swift_scheme.tl', 'submodules/TelegramCore/BUILD', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Polls.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Meta.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Combine.swift', 'submodules/TelegramCore/Sources/State/PendingMessageManager.swift', 'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift', 'submodules/TelegramUI/Sources/Chat/NagramiXCopyDelivery.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaImage.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaPoll.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Catch.swift', 'submodules/MtProtoKit/PublicHeaders/MtProtoKit/MTRpcError.h', 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift', 'submodules/TelegramUI/Sources/ChatController.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaFile.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'round_native_playback'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('poll_copy_transport: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('poll_copy_transport: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('poll_copy_transport: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('poll_copy_transport: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('poll_copy_transport: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('poll_copy_transport: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('poll_copy_transport: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('poll_copy_transport: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('poll_copy_transport: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
