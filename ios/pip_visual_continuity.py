"""Согласованный переход между нативным PiP, галереей и перепиской."""
import hashlib
import json
from pathlib import Path


def apply_pip_visual_continuity(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'pip_visual_continuity_patches.json').read_text())
    expected_inputs = {'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift', 'submodules/GalleryUI/Sources/GalleryController.swift'}
    required_guards = {'submodules/GalleryUI/Sources/GalleryPagerNode.swift', 'submodules/GalleryUI/Sources/ZoomableContentGalleryItemNode.swift', 'submodules/GalleryUI/Sources/GalleryItemNode.swift', 'submodules/TelegramUniversalVideoContent/Sources/SystemVideoContent.swift', 'submodules/AccountContext/BUILD', 'submodules/AccountContext/Sources/UniversalVideoNode.swift', 'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift', 'submodules/TelegramUniversalVideoContent/Sources/HLSVideoNativeContentNode.swift', 'submodules/MediaPlayer/Sources/MediaPlayerNode.swift', 'submodules/GalleryUI/Sources/GalleryControllerNode.swift', 'submodules/GalleryUI/BUILD', 'submodules/AccountContext/Sources/MediaManager.swift', 'submodules/GalleryUI/Sources/GalleryVideoDecoration.swift', 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift', 'submodules/TelegramUI/Sources/Chat/NagramiXEditHistoryController.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'edit_history_number_badges'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('pip_visual_continuity: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('pip_visual_continuity: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('pip_visual_continuity: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('pip_visual_continuity: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('pip_visual_continuity: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('pip_visual_continuity: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('pip_visual_continuity: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('pip_visual_continuity: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('pip_visual_continuity: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
