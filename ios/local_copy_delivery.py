"""Завершение и повтор локальных копий без зависшей очереди отправки."""
import hashlib
import json
from pathlib import Path


def apply_local_copy_delivery(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'local_copy_delivery_patches.json').read_text())
    expected_inputs = {'submodules/TelegramCore/Sources/State/PendingMessageManager.swift', 'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift'}
    required_guards = {'submodules/TelegramCore/Sources/State/AccountViewTracker.swift', 'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift', 'submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift', 'submodules/TelegramCore/Sources/State/SynchronizePeerReadState.swift', 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift', 'submodules/Postbox/Sources/Postbox.swift', 'submodules/TelegramCore/Sources/State/ManagedSynchronizeMarkAllUnseenPersonalMessagesOperations.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveMediaNode/Sources/ChatMessageInteractiveMediaNode.swift', 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift', 'submodules/GalleryUI/Sources/GalleryController.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_OutgoingContentInfoMessageAttribute.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift', 'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Polls.swift', 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaPoll.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoBubbleContentNode/Sources/ChatMessageInstantVideoBubbleContentNode.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_MediaReference.swift', 'submodules/TelegramCore/Sources/State/ManagedSynchronizeConsumeMessageContentsOperations.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_OutgoingMessageInfoAttribute.swift', 'submodules/TelegramCore/BUILD', 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift', 'submodules/Postbox/Sources/MediaBox.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaFile.swift', 'submodules/TelegramUI/Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift', 'submodules/TelegramCore/Sources/Network/FetchedMediaResource.swift', 'submodules/TelegramCore/Sources/State/ManagedAutoremoveMessageOperations.swift', 'submodules/TelegramCore/Sources/State/ManagedSecretChatOutgoingOperations.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaImage.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/ApplyMaxReadIndexInteractively.swift', 'submodules/TelegramCore/Sources/State/ManagedConsumePersonalMessagesActions.swift', 'submodules/TelegramCore/Sources/Network/Network.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift', 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'pip_visual_continuity'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('local_copy_delivery: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('local_copy_delivery: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('local_copy_delivery: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('local_copy_delivery: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('local_copy_delivery: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('local_copy_delivery: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('local_copy_delivery: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('local_copy_delivery: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('local_copy_delivery: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
