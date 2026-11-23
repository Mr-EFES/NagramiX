"""Select a stable application container for standalone installations."""
import hashlib
import json
from pathlib import Path


def apply_standalone_launch_storage(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'standalone_launch_storage_patches.json').read_text())
    native_inputs = {
        'submodules/PasscodeCore/Sources/Passcode.swift': 'd1ff0f651b44645eb6c6a7f2f3b3e7dfe26e69ae',
        'submodules/WalletContext/Sources/WalletSecurity.swift': '3d13bc4dc35a2c37e988709046bb4fd4f9dc06f0',
        'submodules/WalletContext/Sources/WalletStorage.swift': '41e6828eacd61b116ae549fb097bcb856af9f21d',
    }
    inputs = {*native_inputs, "submodules/TelegramUI/Sources/AppDelegate.swift"}
    guards = {'submodules/TelegramUI/Sources/Chat/NagramiXEditHistoryController.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan['required_previous_stage'] != 'edit_history_revision_actions'
            or any(plan[field].keys() != inputs for field in ('inputs', 'outputs', 'previous', 'replacements'))
            or any(plan[field].keys() != guards for field in ('guards', 'guard_sources'))
            or plan['native_inputs'] != native_inputs
            or any(plan[field] for field in ('copies', 'deletions', 'native_guards'))):
        raise SystemExit('standalone_launch_storage: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit(f'standalone_launch_storage: invalid file {name}')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'standalone_launch_storage: drift {name}')
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit(f'standalone_launch_storage: unregistered template {name}')
        return checked(overlay, name, expected)

    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit(f'standalone_launch_storage: guard mismatch {name}')

    outputs = {}
    for name, expected in plan['inputs'].items():
        if checked(source, name, expected) != template(plan['previous'][name], expected):
            raise SystemExit(f'standalone_launch_storage: input mismatch {name}')
        outputs[name] = template(plan['replacements'][name], plan['outputs'][name])

    for name, data in outputs.items():
        (source / name).write_bytes(data)
