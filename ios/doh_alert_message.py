"""Apply the standard-width DoH error message and its localized line breaks."""
import hashlib
import json
from pathlib import Path


def apply_doh_alert_message(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'doh_alert_message_patches.json').read_text())
    languages = json.loads((overlay / 'app_language_localization/languages.json').read_text())['languages']
    resources = {f"submodules/NagramiXCore/Resources/{item['code']}.lproj/Localizable.strings" for item in languages}
    expected_inputs = resources | {
        'submodules/SettingsUI/Sources/NagramiXCustomDohController.swift',
        'submodules/TelegramUI/Components/AlertComponent/Sources/AlertComponent.swift',
    }
    expected_guards = {'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan['required_previous_stage'] != 'youtube_embed_startup'
            or len(resources) != 71
            or any(plan[field].keys() != expected_inputs for field in ('inputs', 'outputs', 'previous', 'replacements'))
            or any(plan[field].keys() != expected_guards for field in ('guards', 'guard_sources'))
            or any(plan[field] for field in ('copies', 'deletions', 'native_inputs', 'native_guards'))):
        raise SystemExit('doh_alert_message: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit(f'doh_alert_message: invalid file {name}')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'doh_alert_message: drift {name}')
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit(f'doh_alert_message: unregistered template {name}')
        return checked(overlay, name, expected)

    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit(f'doh_alert_message: guard mismatch {name}')

    outputs = {}
    for name, expected in plan['inputs'].items():
        if checked(source, name, expected) != template(plan['previous'][name], expected):
            raise SystemExit(f'doh_alert_message: input mismatch {name}')
        outputs[name] = template(plan['replacements'][name], plan['outputs'][name])

    for name, data in outputs.items():
        (source / name).write_bytes(data)
