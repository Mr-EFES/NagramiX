"""Checked final privacy behavior on the audited Telegram overlay."""
import hashlib
import json
from pathlib import Path


def apply_privacy_actions(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'privacy_actions_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась проверенная база приватности: ' + name)
        texts[name] = path.read_text()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка интеграции приватности: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    # All hashes and anchors must match before any native file is changed.
    for name, value in texts.items():
        (source / name).write_text(value)
