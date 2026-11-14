"""Именные ссылки и копии без автокарточек; весь preflight до записи."""
import hashlib
import json
from pathlib import Path


def apply_named_link_preview(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'named_link_preview_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Sources/ChatInterfaceStateContextQueries.swift', 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift', 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift', 'submodules/TelegramCore/Sources/PendingMessages/RequestEditMessage.swift', 'submodules/TelegramUI/Sources/Chat/UpdateChatPresentationInterfaceState.swift', 'submodules/TelegramUI/Sources/ChatControllerNode.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift'}
    required_guards = {'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Dispatch.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Take.swift', 'submodules/TextFormat/Sources/ChatTextInputAttributes.swift', 'submodules/TelegramCore/Sources/ApiUtils/TelegramMediaWebpage.swift', 'submodules/TelegramUI/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal.swift', 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Subscriber.swift', 'submodules/TelegramUI/Sources/ChatControllerOpenAttachmentMenu.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Disposable.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaPoll.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Promise.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Combine.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TextEntitiesMessageAttribute.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendVideoThumbnail.swift', 'submodules/TextFormat/Sources/GenerateTextEntities.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Mapping.swift', 'submodules/TelegramCore/Sources/State/PendingMessageManager.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_OutgoingContentInfoMessageAttribute.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Meta.swift', 'submodules/TelegramUI/Sources/Chat/NagramiXCopyDelivery.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Single.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Bag.swift', 'submodules/TelegramCore/BUILD', 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Atomic.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Queue.swift'}
    expected_copies = set()
    expected_native_inputs = {'submodules/TelegramUI/Sources/ChatInterfaceStateContextQueries.swift': '2b3f3484ea73431dae350a8228d9ed30c0b12e7e'}
    expected_native_guards = {}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'original_video_media'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != expected_native_inputs
        or plan.get('native_guards', {}) != expected_native_guards):
        raise SystemExit('named_link_preview: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('named_link_preview: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('named_link_preview: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('named_link_preview: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('named_link_preview: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('named_link_preview: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('named_link_preview: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('named_link_preview: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('named_link_preview: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('named_link_preview: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('named_link_preview: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('named_link_preview: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('named_link_preview: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
