"""Единый штатный плеер кружков, исходная дымка и разрешённая запись экрана."""
import hashlib
import json
from pathlib import Path


def apply_round_native_playback(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'round_native_playback_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift', 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift', 'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift', 'submodules/TelegramUI/Sources/ChatController.swift'}
    required_guards = {'submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoBubbleContentNode/Sources/ChatMessageInstantVideoBubbleContentNode.swift', 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift', 'submodules/TelegramCore/BUILD', 'submodules/TelegramCore/Sources/State/ManagedSynchronizeConsumeMessageContentsOperations.swift', 'submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift', 'submodules/TelegramUI/Sources/OverlayInstantVideoNode.swift', 'submodules/TelegramCore/Sources/State/SynchronizePeerReadState.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/BUILD', 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift', 'submodules/TelegramUI/Sources/OverlayInstantVideoDecoration.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift', 'submodules/TelegramUniversalVideoContent/Sources/UniversalVideoContentManager.swift', 'submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift', 'submodules/TelegramUI/BUILD', 'submodules/TelegramUniversalVideoContent/BUILD', 'submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/BUILD', 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift', 'submodules/TelegramUniversalVideoContent/Sources/ChatBubbleInstantVideoDecoration.swift', 'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift', 'submodules/AccountContext/BUILD', 'submodules/TelegramCore/Sources/State/ManagedSecretChatOutgoingOperations.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift', 'submodules/AccountContext/Sources/UniversalVideoNode.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'release_092_settings_compile'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('round_native_playback: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('round_native_playback: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('round_native_playback: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('round_native_playback: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('round_native_playback: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('round_native_playback: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('round_native_playback: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('round_native_playback: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('round_native_playback: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
