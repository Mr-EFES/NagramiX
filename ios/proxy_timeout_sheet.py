"""Apply the proxy timeout sheet after verifying all source and catalog inputs."""
import hashlib
import json
from pathlib import Path


def apply_proxy_timeout_sheet(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'proxy_timeout_sheet_patches.json').read_text())
    languages = json.loads((overlay / 'app_language_localization/languages.json').read_text())['languages']
    resources = {f"submodules/NagramiXCore/Resources/{item['code']}.lproj/Localizable.strings" for item in languages}
    expected_inputs = resources | {
        'submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift',
        'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift',
    }
    expected_guards = {
        'submodules/SettingsUI/Sources/NagramiXOptionSheet.swift',
        'submodules/NagramiXCore/Sources/NagramiXAppLocalization.swift',
        'submodules/SettingsUI/BUILD',
        'submodules/NagramiXCore/BUILD',
    }
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan['required_previous_stage'] != 'file_caption_wire_spacing'
            or len(resources) != 71
            or any(plan[field].keys() != expected_inputs for field in ('inputs', 'outputs', 'previous', 'replacements'))
            or any(plan[field].keys() != expected_guards for field in ('guards', 'guard_sources'))
            or any(plan[field] for field in ('copies', 'deletions', 'native_inputs', 'native_guards'))):
        raise SystemExit('proxy_timeout_sheet: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit(f'proxy_timeout_sheet: invalid file {name}')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'proxy_timeout_sheet: drift {name}')
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit(f'proxy_timeout_sheet: unregistered template {name}')
        return checked(overlay, name, expected)

    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit(f'proxy_timeout_sheet: guard mismatch {name}')

    outputs = {}
    for name, expected in plan['inputs'].items():
        if checked(source, name, expected) != template(plan['previous'][name], expected):
            raise SystemExit(f'proxy_timeout_sheet: input mismatch {name}')
        outputs[name] = template(plan['replacements'][name], plan['outputs'][name])

    for name, data in outputs.items():
        (source / name).write_bytes(data)
