"""Retain approved sent messages and render archive direction accurately."""
import hashlib
import json
from pathlib import Path


def apply_outgoing_archive(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'outgoing_archive_patches.json').read_text())
    texts = {}
    for name, digest in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit('Изменилась база двустороннего архива: ' + name)
        texts[name] = path.read_text()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка двустороннего архива: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
