"""Keep the media gallery heading inside the space reserved by the navigation bar."""
import hashlib
import json
from pathlib import Path


def apply_gallery_header_layout(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'gallery_header_layout_patches.json').read_text())
    inputs = {
        'submodules/GalleryUI/Sources/GalleryController.swift',
        'submodules/GalleryUI/Sources/GalleryControllerNode.swift',
        'submodules/GalleryUI/Sources/GalleryTitleView.swift',
    }
    guards = {
        'submodules/TelegramUI/Components/NavigationBarNode/Sources/NavigationBarNode.swift',
        'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift',
        'submodules/Display/Source/NavigationBarTitlePlacement.swift',
    }
    native_inputs = {'submodules/GalleryUI/Sources/GalleryTitleView.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan['required_previous_stage'] != 'youtube_watch_fallback'
            or any(plan[field].keys() != inputs for field in ('inputs', 'outputs', 'previous', 'replacements'))
            or any(plan[field].keys() != guards for field in ('guards', 'guard_sources'))
            or plan['native_inputs'].keys() != native_inputs
            or plan['native_guards'] != {'submodules/Display/Source/NavigationBarTitlePlacement.swift': '344a5bbcfb483f971208bff2f942d0960de2f1b5'}
            or any(plan[field] for field in ('copies', 'deletions'))):
        raise SystemExit('gallery_header_layout: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit(f'gallery_header_layout: invalid file {name}')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'gallery_header_layout: drift {name}')
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit(f'gallery_header_layout: unregistered template {name}')
        return checked(overlay, name, expected)

    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit(f'gallery_header_layout: guard mismatch {name}')

    outputs = {}
    for name, expected in plan['inputs'].items():
        data = checked(source, name, expected)
        if data != template(plan['previous'][name], expected):
            raise SystemExit(f'gallery_header_layout: input mismatch {name}')
        if name in native_inputs:
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit(f'gallery_header_layout: native input origin {name}')
        outputs[name] = template(plan['replacements'][name], plan['outputs'][name])

    for name, data in outputs.items():
        (source / name).write_bytes(data)
