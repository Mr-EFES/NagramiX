"""Системный PiP и фоновое воспроизведение существующих web/AVPlayer видео."""
import hashlib
import json
from pathlib import Path


def apply_system_web_picture_in_picture(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'system_web_picture_in_picture_patches.json').read_text())
    expected_inputs = {
        'submodules/AccountContext/Sources/UniversalVideoNode.swift',
        'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift',
        'submodules/TelegramUI/Sources/MediaManager.swift',
        'submodules/TelegramUniversalVideoContent/BUILD',
        'submodules/TelegramUniversalVideoContent/Sources/PlatformVideoContent.swift',
        'submodules/TelegramUniversalVideoContent/Sources/SystemVideoContent.swift',
        'submodules/TelegramUniversalVideoContent/Sources/WebEmbedPlayerNode.swift',
        'submodules/TelegramUniversalVideoContent/Sources/WebEmbedVideoContent.swift',
    }
    required_guards = {
        'Telegram/BUILD',
        'submodules/NagramiXCore/BUILD',
        'submodules/NagramiXMediaSettings/BUILD',
        'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift',
        'submodules/TelegramUI/Sources/NagramiXVideoNowPlaying.swift',
        'submodules/TelegramUI/BUILD',
        'submodules/GalleryUI/BUILD',
        'submodules/GalleryUI/Sources/GalleryController.swift',
        'submodules/GalleryUI/Sources/GalleryControllerNode.swift',
        'submodules/GalleryUI/Sources/GalleryItemNode.swift',
        'submodules/AccountContext/BUILD',
        'submodules/AccountContext/Sources/MediaManager.swift',
        'submodules/TelegramUniversalVideoContent/Sources/UniversalVideoContentManager.swift',
        'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift',
        'submodules/TelegramUniversalVideoContent/Sources/HLSVideoNativeContentNode.swift',
        'submodules/TelegramUniversalVideoContent/Sources/YoutubeEmbedImplementation.swift',
        'submodules/TelegramUniversalVideoContent/Sources/GenericEmbedImplementation.swift',
        'submodules/TelegramUniversalVideoContent/Sources/VimeoEmbedImplementation.swift',
        'submodules/TelegramAudio/Sources/ManagedAudioSession.swift',
        'submodules/TelegramUI/Resources/WebEmbed/YoutubeUserScript.js',
        'submodules/TelegramUI/Resources/WebEmbed/Youtube.html',
        'submodules/TelegramUniversalVideoContent/Sources/OverlayUniversalVideoNode.swift',
    }
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'font_theme_contrast'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])
        or plan.get('native_guards', {})):
        raise SystemExit('system_web_picture_in_picture: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('system_web_picture_in_picture: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('system_web_picture_in_picture: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('system_web_picture_in_picture: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('system_web_picture_in_picture: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('system_web_picture_in_picture: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('system_web_picture_in_picture: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('system_web_picture_in_picture: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('system_web_picture_in_picture: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('system_web_picture_in_picture: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
