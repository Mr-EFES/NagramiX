"""Repair retained round playback, row identity, deletion notice and decoder handoff."""
import hashlib
import json
from pathlib import Path


def apply_round_video_replay_stability(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'round_video_replay_stability_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift', 'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift', 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift', 'submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift', 'submodules/TelegramUI/Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift'}
    required_guards = {'submodules/AccountContext/Sources/SharedMediaPlayer.swift', 'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/BUILD', 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift', 'submodules/TelegramUI/Sources/MediaManager.swift', 'submodules/TelegramCore/BUILD', 'submodules/TelegramUI/BUILD', 'submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoBubbleContentNode/Sources/ChatMessageInstantVideoBubbleContentNode.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Message.swift', 'submodules/FileMediaResourceStatus/Sources/FileMediaResourceStatus.swift', 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift', 'submodules/Display/Source/ContainedViewLayoutTransition.swift', 'submodules/TelegramCore/Sources/Utils/MessageUtils.swift', 'submodules/TelegramUniversalVideoContent/BUILD', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/BUILD', 'submodules/AccountContext/Sources/UniversalVideoNode.swift', 'submodules/TelegramUniversalVideoContent/Sources/ChatBubbleInstantVideoDecoration.swift', 'submodules/TelegramUniversalVideoContent/Sources/UniversalVideoContentManager.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/BUILD', 'submodules/TelegramCore/Sources/TelegramEngine/Utils/EnginePostboxCoding.swift', 'submodules/Postbox/Sources/Message.swift', 'submodules/AccountContext/BUILD', 'submodules/AccountContext/Sources/MediaManager.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'release_090_author_compile'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('round_video_replay_stability: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('round_video_replay_stability: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('round_video_replay_stability: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('round_video_replay_stability: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('round_video_replay_stability: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('round_video_replay_stability: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('round_video_replay_stability: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('round_video_replay_stability: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('round_video_replay_stability: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
