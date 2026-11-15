"""Отложенное обновление действий редактора DoH; весь preflight до записи."""
import hashlib
import json
from pathlib import Path


def apply_doh_clear_input_lifecycle(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'doh_clear_input_lifecycle_patches.json').read_text())
    expected_inputs = {'submodules/SettingsUI/Sources/NagramiXCustomDohController.swift'}
    required_guards = {'submodules/ComponentFlow/Source/Host/ComponentHostView.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Dispatch.swift', 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Combine.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Subscriber.swift', 'submodules/SettingsUI/BUILD', 'submodules/TelegramUI/Components/AlertComponent/AlertInputFieldComponent/Sources/AlertInputFieldComponent.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Promise.swift', 'submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift', 'submodules/ComponentFlow/Source/Base/Component.swift', 'submodules/TelegramUI/Components/AlertComponent/Sources/AlertComponent.swift', 'submodules/TelegramUI/Components/AlertComponent/Sources/AlertActionComponent.swift', 'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Queue.swift'}
    expected_copies = set()
    expected_native_inputs = {}
    expected_native_guards = {}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'release_098_compile_compatibility'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != expected_native_inputs
        or plan.get('native_guards', {}) != expected_native_guards):
        raise SystemExit('doh_clear_input_lifecycle: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('doh_clear_input_lifecycle: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('doh_clear_input_lifecycle: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('doh_clear_input_lifecycle: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('doh_clear_input_lifecycle: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('doh_clear_input_lifecycle: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('doh_clear_input_lifecycle: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('doh_clear_input_lifecycle: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('doh_clear_input_lifecycle: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('doh_clear_input_lifecycle: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('doh_clear_input_lifecycle: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('doh_clear_input_lifecycle: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('doh_clear_input_lifecycle: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
