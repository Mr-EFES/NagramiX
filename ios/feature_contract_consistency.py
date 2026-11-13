"""Единые настройки качества фото, широких постов и выключения расшифровки."""
import hashlib
import json
from pathlib import Path


def apply_feature_contract_consistency(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'feature_contract_consistency_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageItemView/BUILD', 'submodules/TelegramUI/Components/Chat/ChatMessageStickerItemNode/Sources/ChatMessageStickerItemNode.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendLivePhoto.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendRender.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendMessages.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendSingleItem.swift', 'submodules/LegacyMediaPickerUI/Sources/LegacyMediaPickers.swift', 'submodules/NagramiXTranscription/Sources/Runtime.swift', 'submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageAnimatedStickerItemNode/Sources/ChatMessageAnimatedStickerItemNode.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendPlan.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageItemView/Sources/ChatMessageItemView.swift'}
    required_guards = {'submodules/MediaPickerUI/Sources/MediaPickerScreen.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Catch.swift', 'submodules/NagramiXTranscription/Sources/Coordinator.swift', 'submodules/TelegramAudio/Sources/ManagedAudioSession.swift', 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift', 'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageItemImpl/Sources/ChatMessageItemImpl.swift', 'submodules/LocalMediaResources/Sources/FetchPhotoLibraryImageResource.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendVideoThumbnail.swift', 'submodules/WallpaperBackgroundNode/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Single.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/TelegramEngineMessages.swift', 'submodules/TelegramUI/Components/ChatMediaSend/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Disposable.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageDateAndStatusNode/Sources/ChatMessageDateAndStatusNode.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Atomic.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendItem.swift', 'submodules/NagramiXMediaSettings/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Meta.swift', 'submodules/ChatMessageBackground/BUILD', 'submodules/ImageCompression/Sources/ImageCompression.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/NagramiXOriginalVideoSend.swift', 'submodules/NagramiXTranscription/Sources/Settings.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageItemCommon/Sources/ChatMessageBubblelessSelection.swift', 'submodules/NagramiXTranscription/BUILD', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaEditorItemStore.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift', 'submodules/TelegramUI/Sources/MediaManager.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Subscriber.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageItemCommon/Sources/ChatMessageItemCommon.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Combine.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Dispatch.swift', 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift', 'submodules/NagramiXTranscription/Sources/MediaPreparation.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageItemCommon/Sources/ChatMessageBubblelessMetrics.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Take.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Queue.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Mapping.swift', 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift', 'submodules/ChatMessageBackground/Sources/ChatMessageBackground.swift', 'submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift'}
    expected_copies = set()
    expected_native_inputs = {'submodules/TelegramUI/Components/Chat/ChatMessageItemView/BUILD': 'eba7dfef21900a0e77c477de3dee643b4cff695d', 'submodules/TelegramUI/Components/Chat/ChatMessageItemView/Sources/ChatMessageItemView.swift': '9e5716f8212e754cac11511d0d9406b01f53649a', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendLivePhoto.swift': '4e4ed5d5c6d2a51d957fe73d6bc285d2bdc02b68'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'original_video_mode'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != expected_native_inputs
        or plan.get('native_guards', {})):
        raise SystemExit('feature_contract_consistency: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('feature_contract_consistency: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('feature_contract_consistency: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('feature_contract_consistency: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('feature_contract_consistency: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('feature_contract_consistency: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('feature_contract_consistency: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('feature_contract_consistency: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('feature_contract_consistency: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('feature_contract_consistency: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('feature_contract_consistency: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('feature_contract_consistency: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('feature_contract_consistency: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
