"""Общий прозрачный стеклянный бегунок настроек; весь preflight до записи."""
import hashlib
import json
from pathlib import Path


def apply_settings_glass_sliders(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'settings_glass_sliders_patches.json').read_text())
    expected_inputs = {'submodules/SettingsUI/Sources/NagramiXSnowDensityItem.swift', 'submodules/SettingsUI/Sources/NagramiXPercentageItem.swift', 'submodules/NagramiXTranscription/Sources/Preferences.swift', 'submodules/SettingsUI/Sources/NagramiXRoundQualityController.swift', 'submodules/TranslateUI/Sources/NagramiXTranslationPreferences.swift'}
    required_guards = {'submodules/SettingsUI/BUILD', 'submodules/LegacyComponents/PublicHeaders/LegacyComponents/TGPhotoEditorSliderView.h', 'submodules/LegacyComponents/Sources/TGPhotoEditorSliderView.m', 'submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift', 'submodules/NagramiXTranscription/BUILD', 'submodules/NagramiXMediaSettings/Sources/NagramiXRoundVideoSettings.swift', 'submodules/TranslateUI/BUILD', 'submodules/NagramiXCore/BUILD', 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift', 'submodules/TelegramPresentationData/Sources/PresentationTheme.swift', 'submodules/NagramiXCore/Sources/NagramiXSnowSettings.swift'}
    expected_copies = {'submodules/NagramiXCore/Sources/NagramiXGlassSlider.swift', 'submodules/SettingsUI/Sources/NagramiXLegacyGlassSliderView.swift'}
    expected_native_inputs = {}
    expected_native_guards = {}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'snow_density_glass'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != expected_native_inputs
        or plan.get('native_guards', {}) != expected_native_guards):
        raise SystemExit('settings_glass_sliders: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('settings_glass_sliders: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('settings_glass_sliders: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('settings_glass_sliders: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('settings_glass_sliders: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('settings_glass_sliders: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('settings_glass_sliders: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('settings_glass_sliders: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('settings_glass_sliders: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('settings_glass_sliders: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('settings_glass_sliders: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('settings_glass_sliders: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('settings_glass_sliders: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
