"""Сохранить штатный плеер удалённого кружка при повторных действиях."""
import hashlib
import json
from pathlib import Path


def apply_archived_round_native_controls(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'archived_round_native_controls_patches.json').read_text())
    expected_inputs = {'submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift', 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift'}
    required_guards = {'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift', 'submodules/TelegramUI/Components/ChatControllerInteraction/Sources/ChatControllerInteraction.swift', 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift', 'submodules/NagramiXTranscription/Sources/Runtime.swift', 'submodules/AccountContext/BUILD', 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift', 'submodules/TelegramUniversalVideoContent/Sources/UniversalVideoContentManager.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaFile.swift', 'submodules/TelegramUI/Sources/OpenChatMessage.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Dispatch.swift', 'submodules/TelegramUI/Sources/ChatController.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Atomic.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Subscriber.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Take.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoBubbleContentNode/Sources/ChatMessageInstantVideoBubbleContentNode.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/BUILD', 'submodules/AccountContext/Sources/SharedMediaPlayer.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Disposable.swift', 'submodules/AccountContext/Sources/MediaManager.swift', 'submodules/TelegramUI/Components/GlobalControlPanelsContext/Sources/GlobalControlPanelsContext.swift', 'submodules/MediaPlayer/Sources/MediaPlayer.swift', 'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift', 'submodules/TelegramUI/Sources/MediaManager.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Mapping.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Timing.swift', 'submodules/TelegramUI/Sources/ChatControllerOpenAttachmentMenu.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'composer_file_attachments'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('archived_round_native_controls: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('archived_round_native_controls: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('archived_round_native_controls: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('archived_round_native_controls: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('archived_round_native_controls: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('archived_round_native_controls: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('archived_round_native_controls: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('archived_round_native_controls: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('archived_round_native_controls: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
