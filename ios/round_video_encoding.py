"""Битрейт/FPS и проверенный размер настоящих круглых видео; весь preflight до записи."""
import hashlib
import json
from pathlib import Path


def apply_round_video_encoding(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'round_video_encoding_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorVideoStreamingWriter.swift', 'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift', 'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorVideoAVAssetWriter.swift', 'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorVideoExport.swift', 'submodules/TelegramUI/Components/Resources/FetchVideoMediaResource/Sources/FetchVideoMediaResource.swift', 'submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift', 'submodules/Camera/CameraNeo/Sources/VideoRecorder.swift'}
    required_guards = {'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendVideoThumbnail.swift', 'submodules/TelegramCore/Sources/Settings/ContentSettings.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_AppConfiguration.swift', 'submodules/TelegramCore/Sources/State/AppConfiguration.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal.swift', 'submodules/Camera/CameraNeo/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Dispatch.swift', 'submodules/Camera/Sources/NagramiXRoundVideoSettings.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Take.swift', 'submodules/Postbox/Sources/TempBox.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Utils/TempBox.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaFile.swift', 'submodules/TelegramUI/Components/Resources/FetchVideoMediaResource/BUILD', 'submodules/TelegramUI/Components/MediaEditor/BUILD', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_Namespaces.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Mapping.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Combine.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Single.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendMessages.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Atomic.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Subscriber.swift', 'submodules/NagramiXMediaSettings/Sources/NagramiXRoundVideoSettings.swift', 'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Meta.swift', 'submodules/Camera/BUILD', 'submodules/TelegramUI/Components/VideoMessageCameraScreen/BUILD', 'submodules/SettingsUI/Sources/NagramiXRoundQualityController.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Catch.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Disposable.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Queue.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Promise.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Bag.swift'}
    expected_copies = {'submodules/TelegramUI/Components/MediaEditor/Sources/NagramiXRoundVideoEncodingPolicy.swift', 'submodules/TelegramUI/Components/MediaEditor/Sources/NagramiXRoundVideoExport.swift'}
    expected_native_inputs = {'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorVideoStreamingWriter.swift': '7f3ba930c7e4cc7acc3d6f3fceb02e87bc729187'}
    expected_native_guards = {}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'round_quality_checkmark_alignment'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != expected_native_inputs
        or plan.get('native_guards', {}) != expected_native_guards):
        raise SystemExit('round_video_encoding: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('round_video_encoding: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('round_video_encoding: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('round_video_encoding: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('round_video_encoding: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('round_video_encoding: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('round_video_encoding: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('round_video_encoding: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('round_video_encoding: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('round_video_encoding: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('round_video_encoding: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('round_video_encoding: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('round_video_encoding: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
