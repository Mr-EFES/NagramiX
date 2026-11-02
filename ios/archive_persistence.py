"""Install archive persistence failure presentation against the final overlay."""
import hashlib
import json
from pathlib import Path


def apply_archive_persistence(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'archive_persistence_patches.json').read_text())
    texts, copies = {}, {}
    for name, sha in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise SystemExit('Изменилась база сохранения архива: ' + name)
        texts[name] = path.read_text()
    for template, name in plan['provided'].items():
        if not (source / name).is_file() or (source / name).read_bytes() != (overlay / template).read_bytes():
            raise SystemExit('Изменился шаблон архива: ' + name)
    for template, name in plan['copies'].items():
        if (source / name).exists() or not (source / name).parent.is_dir():
            raise SystemExit('Конфликт helper сохранения архива: ' + name)
        copies[name] = (overlay / template).read_bytes()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка сохранения архива: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, value in texts.items(): (source / name).write_text(value)
    for name, data in copies.items(): (source / name).write_bytes(data)
