"""Исправить ссылки на реальные native строки ошибок вложений после SDK200."""
import hashlib
import json
from pathlib import Path


def apply_release_095_composer_strings_compile(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'release_095_composer_strings_compile_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Sources/ChatControllerOpenAttachmentMenu.swift'}
    required_guards = {'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentModel.swift', 'submodules/SettingsUI/Sources/NagramiXFontsController.swift', 'Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TextFormat/Sources/ChatComposerSendPlan.swift', 'Telegram/BUILD', 'build-system/GenerateStrings/GenerateStrings.py'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'release_095_fonts_compile'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])
        or set(plan.get('native_guards', {})) != {'build-system/GenerateStrings/GenerateStrings.py'}):
        raise SystemExit('release_095_composer_strings_compile: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('release_095_composer_strings_compile: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('release_095_composer_strings_compile: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('release_095_composer_strings_compile: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('release_095_composer_strings_compile: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('release_095_composer_strings_compile: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('release_095_composer_strings_compile: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('release_095_composer_strings_compile: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('release_095_composer_strings_compile: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('release_095_composer_strings_compile: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
