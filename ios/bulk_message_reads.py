"""Add account-scoped local and confirmed server read actions."""
import hashlib
import json
from pathlib import Path


def apply_bulk_message_reads(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'bulk_message_reads_patches.json').read_text())
    codes = 'en af sq am ar hy az eu be bn bg my ca zh-hans zh-hant hr cs da nl eo et fil fi fr gl ka de el gu he hi hu id ga it ja kn kk km ko lv lt ms ml mt mr ne nb or fa pl pt-br pt-pt ro ru sr sk sl es sw sv tg ta te th tr tk uk ur uz vi'.split()
    inputs = {f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings' for code in codes} | {
        'submodules/TelegramCore/Sources/NagramiXGhostReadActions.swift',
        'submodules/TelegramCore/Sources/NagramiXReadModeActions.swift',
        'submodules/SettingsUI/Sources/NagramiXSettingsController.swift',
        'submodules/Postbox/Sources/Postbox.swift',
        'submodules/TelegramCore/Sources/State/Sync/StateReplay+ReadStates.swift',
        'submodules/TelegramCore/Sources/State/SynchronizePeerReadState.swift',
    }
    guards = {'submodules/PresentationDataUtils/Sources/AlertTheme.swift',
              'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift',
              'submodules/NagramiXCore/Sources/NagramiXAppLocalization.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan['required_previous_stage'] != 'message_settings_order'
            or any(plan[field].keys() != inputs for field in ('inputs', 'outputs', 'previous', 'replacements'))
            or any(plan[field].keys() != guards for field in ('guards', 'guard_sources'))
            or any(plan[field] for field in ('copies', 'deletions', 'native_inputs', 'native_guards'))):
        raise SystemExit('bulk_message_reads: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit(f'bulk_message_reads: invalid file {name}')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'bulk_message_reads: drift {name}')
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit(f'bulk_message_reads: unregistered template {name}')
        return checked(overlay, name, expected)

    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit(f'bulk_message_reads: guard mismatch {name}')

    outputs = {}
    for name, expected in plan['inputs'].items():
        if checked(source, name, expected) != template(plan['previous'][name], expected):
            raise SystemExit(f'bulk_message_reads: input mismatch {name}')
        outputs[name] = template(plan['replacements'][name], plan['outputs'][name])

    for name, data in outputs.items():
        (source / name).write_bytes(data)
