"""Preserve copy-picker folder selection and address forum copies on the wire."""
import hashlib
import json
from pathlib import Path


def apply_broadcast_topics(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'broadcast_topics_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база адресатов рассылки: ' + name)
        texts[name] = path.read_text()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка адресатов рассылки: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    # Every input and replacement is validated before the first native write.
    for name, text in texts.items():
        (source / name).write_text(text)
