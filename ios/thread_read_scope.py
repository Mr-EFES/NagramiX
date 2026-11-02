"""Apply topic-scoped private read integration to the audited final overlay."""
import hashlib
import json
from pathlib import Path


def apply_thread_read_scope(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'thread_read_scope_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база чтения тем: ' + name)
        texts[name] = path.read_text()
    for template, name in plan['provided'].items():
        if not (source / name).is_file() or (source / name).read_bytes() != (overlay / template).read_bytes():
            raise SystemExit('Изменился helper чтения тем: ' + name)
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка чтения тем: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
