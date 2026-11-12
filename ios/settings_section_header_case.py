"""Единый верхний регистр заголовков категорий настроек."""
import hashlib
import json
from pathlib import Path


def apply_settings_section_header_case(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'settings_section_header_case_patches.json').read_text())
    expected_inputs = {'submodules/SettingsUI/Sources/NagramiXSettingsController.swift'}
    required_guards = {
        'submodules/SettingsUI/BUILD',
        'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift',
        'submodules/NagramiXCore/Sources/NagramiXAppLocalization.swift',
    }
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'wide_panel_consistency'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])
        or plan.get('native_guards', {})):
        raise SystemExit('settings_section_header_case: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('settings_section_header_case: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('settings_section_header_case: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('settings_section_header_case: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('settings_section_header_case: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('settings_section_header_case: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('settings_section_header_case: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('settings_section_header_case: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('settings_section_header_case: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('settings_section_header_case: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
