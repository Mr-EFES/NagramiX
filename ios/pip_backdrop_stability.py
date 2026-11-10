"""Стабильный фон чата и свободные границы исходника при native PiP."""
import hashlib
import json
from pathlib import Path


def apply_pip_backdrop_stability(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'pip_backdrop_stability_patches.json').read_text())
    expected_inputs = {'submodules/GalleryUI/Sources/GalleryController.swift', 'submodules/GalleryUI/Sources/GalleryControllerNode.swift', 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'}
    required_guards = {'submodules/GalleryUI/BUILD', 'submodules/AccountContext/Sources/MediaManager.swift', 'submodules/AccountContext/BUILD', 'submodules/TelegramUI/Sources/ChatController.swift', 'submodules/GalleryUI/Sources/ZoomableContentGalleryItemNode.swift', 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift', 'submodules/GalleryUI/Sources/GalleryVideoDecoration.swift', 'submodules/AccountContext/Sources/UniversalVideoNode.swift', 'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift', 'submodules/GalleryUI/Sources/GalleryItemNode.swift', 'submodules/MediaPlayer/Sources/MediaPlayerNode.swift', 'submodules/GalleryUI/Sources/GalleryPagerNode.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'premium_label_spelling'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('pip_backdrop_stability: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('pip_backdrop_stability: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('pip_backdrop_stability: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('pip_backdrop_stability: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('pip_backdrop_stability: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('pip_backdrop_stability: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('pip_backdrop_stability: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('pip_backdrop_stability: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('pip_backdrop_stability: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
