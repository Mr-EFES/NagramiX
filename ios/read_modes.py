"""Fail-closed late integration of the unified independent privacy switches."""
import hashlib
import json
from pathlib import Path


def apply_read_modes(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'read_mode_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась проверенная база режимов прочтения: ' + name)
        texts[name] = path.read_text()
    for name in ['submodules/TelegramCore/BUILD', 'submodules/SettingsUI/BUILD']:
        if 'Sources/**/*.swift' not in texts[name]:
            raise SystemExit('Отсутствует native Swift glob: ' + name)
    for name in ['NagramiXReadModeSettings.swift', 'NagramiXPrivacySettings.swift']:
        model = 'Sources/NagramiXMediaSettings/Sources/' + name
        if (source / ('submodules/NagramiXMediaSettings/Sources/' + name)).read_bytes() != (overlay / model).read_bytes():
            raise SystemExit('Отсутствуют настройки приватности: ' + name)
    copies = {}
    for template, name in plan['copies'].items():
        if (source / name).exists():
            raise SystemExit('Конфликт read mode helper: ' + name)
        copies[name] = (overlay / template).read_bytes()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка интеграции режимов прочтения: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    # Validate every anchor, model, dependency and collision before writing.
    for name in {patch[0] for patch in plan['patches']}:
        (source / name).write_text(texts[name])
    for name, data in copies.items():
        (source / name).write_bytes(data)
