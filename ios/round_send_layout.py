"""Lay out the round-video preview, trim time and cover action together."""
import hashlib
import json
from pathlib import Path


def apply_round_send_layout(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'round_send_layout_patches.json').read_text())
    inputs = {
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreen.swift',
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenVideo.swift',
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenGallery.swift',
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenMute.swift',
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenSelection.swift',
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenCover.swift',
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorCover.swift',
    }
    guards = {
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenCrop.swift',
    }
    native_inputs = {
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenMute.swift': 'bc37d4eff626a267bbc6d464ea8a2ee459ff2327',
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenSelection.swift': '5127dac384c42bd13398504718b8fb48a9fc136c',
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenCover.swift': '96850f2995c95be91b7f5215ab89233d00712ca5',
        'submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorCover.swift': 'f7faf8e5563f472bbd5aeaaa0f806624cabf0491',
    }
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan['required_previous_stage'] != 'youtube_inline_playback'
            or any(plan[field].keys() != inputs for field in ('inputs', 'outputs', 'previous', 'replacements'))
            or any(plan[field].keys() != guards for field in ('guards', 'guard_sources'))
            or plan['native_inputs'] != native_inputs
            or any(plan[field] for field in ('copies', 'deletions', 'native_guards'))):
        raise SystemExit('round_send_layout: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit(f'round_send_layout: invalid file {name}')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'round_send_layout: drift {name}')
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit(f'round_send_layout: unregistered template {name}')
        return checked(overlay, name, expected)

    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit(f'round_send_layout: guard mismatch {name}')

    outputs = {}
    for name, expected in plan['inputs'].items():
        if checked(source, name, expected) != template(plan['previous'][name], expected):
            raise SystemExit(f'round_send_layout: input mismatch {name}')
        outputs[name] = template(plan['replacements'][name], plan['outputs'][name])

    for name, data in outputs.items():
        (source / name).write_bytes(data)
