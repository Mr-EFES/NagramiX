"""Fail-closed integration of opt-in screenshot protection bypass."""
import hashlib
import json
from pathlib import Path


def apply_screenshot_bypass(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'screenshot_bypass_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась проверенная база скриншотов: ' + name)
        texts[name] = path.read_text()
    copies = {}
    for template, name in plan['copies'].items():
        if not (source / name).parent.is_dir():
            raise SystemExit('Отсутствует каталог screenshot helper: ' + name)
        if (source / name).exists():
            raise SystemExit('Конфликт screenshot helper: ' + name)
        copies[name] = (overlay / template).read_bytes()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка интеграции скриншотов: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    # Check every input, collision and anchor before the first mutation.
    for name, text in texts.items():
        (source / name).write_text(text)
    for name, data in copies.items():
        (source / name).write_bytes(data)
