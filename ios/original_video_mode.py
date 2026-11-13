"""Разделение оригинального видео и штатного сжатия в отправке из галереи."""
import hashlib
import json
from pathlib import Path


def apply_original_video_mode(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'original_video_mode_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendRender.swift', 'submodules/TelegramUI/Components/ChatMediaSend/BUILD', 'submodules/LegacyMediaPickerUI/Sources/LegacyMediaPickers.swift'}
    required_guards = {'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Single.swift', 'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaEditorItemStore.swift', 'submodules/NagramiXMediaSettings/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Take.swift', 'submodules/LegacyComponents/Sources/TGMediaVideoConverter.m', 'submodules/SSignalKit/SwiftSignalKit/Source/Subscriber.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Combine.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendItem.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Catch.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendVideoThumbnail.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendMessages.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Meta.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Disposable.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Dispatch.swift', 'submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift', 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendPlan.swift', 'submodules/LegacyMediaPickerUI/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Atomic.swift', 'submodules/MediaPickerUI/Sources/MediaPickerScreen.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Queue.swift', 'submodules/TelegramUI/Components/Resources/FetchVideoMediaResource/Sources/FetchVideoMediaResource.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Mapping.swift'}
    expected_copies = {'submodules/TelegramUI/Components/ChatMediaSend/Sources/NagramiXOriginalVideoSend.swift'}
    expected_native_inputs = {'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendRender.swift': 'dae033d53acacb1d6b96c10ffb8ab9f13f91b621'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'selection_scroll_continuity'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != expected_native_inputs
        or plan.get('native_guards', {})):
        raise SystemExit('original_video_mode: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('original_video_mode: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('original_video_mode: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('original_video_mode: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('original_video_mode: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('original_video_mode: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('original_video_mode: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('original_video_mode: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('original_video_mode: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('original_video_mode: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('original_video_mode: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('original_video_mode: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('original_video_mode: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
