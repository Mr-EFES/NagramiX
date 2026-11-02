"""Add account-scoped re-upload of own view-once recordings, fail closed."""
import hashlib
import json
from pathlib import Path


def apply_own_once_copy(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'own_once_copy_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база повторной отправки своей записи: ' + name)
        texts[name] = path.read_text()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка повторной отправки своей записи: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
