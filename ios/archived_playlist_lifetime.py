"""Сохранённый native-плейлист не следит за удалённым исходником в Postbox."""
import hashlib
import json
from pathlib import Path


def apply_archived_playlist_lifetime(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'archived_playlist_lifetime_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift'}
    required_guards = {'submodules/SSignalKit/SwiftSignalKit/Source/Disposable.swift', 'submodules/AccountContext/Sources/MediaManager.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Subscriber.swift', 'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift', 'submodules/AccountContext/Sources/SharedMediaPlayer.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Bag.swift', 'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/BUILD', 'submodules/TelegramUI/Sources/OpenChatMessage.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Take.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Queue.swift', 'submodules/TelegramUI/Sources/MediaManager.swift', 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift', 'submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Dispatch.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Promise.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Mapping.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Atomic.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift'}
    expected_copies = set()
    expected_native_inputs = {}
    expected_native_guards = {}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'doh_empty_action'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != expected_native_inputs
        or plan.get('native_guards', {}) != expected_native_guards):
        raise SystemExit('archived_playlist_lifetime: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('archived_playlist_lifetime: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('archived_playlist_lifetime: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('archived_playlist_lifetime: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('archived_playlist_lifetime: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('archived_playlist_lifetime: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('archived_playlist_lifetime: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('archived_playlist_lifetime: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('archived_playlist_lifetime: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('archived_playlist_lifetime: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('archived_playlist_lifetime: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('archived_playlist_lifetime: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('archived_playlist_lifetime: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
