"""Install the opt-out native silent-send default without changing other settings."""
import hashlib
import json
from pathlib import Path


def apply_silent_send(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'silent_send_patches.json').read_text())
    texts = {}
    for name, digest in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit('Изменилась база тихой отправки: ' + name)
        texts[name] = path.read_text()
    for name in plan['source_globs']:
        if 'Sources/**/*.swift' not in texts[name]:
            raise SystemExit('Отсутствует Swift glob тихой отправки: ' + name)
    for name, target in plan['provided'].items():
        path = overlay / name
        if not path.is_file() or not path.read_text().strip() or not (source / target).is_file() or (source / target).read_bytes() != path.read_bytes():
            raise SystemExit('Конфликт helper тихой отправки: ' + name)
    copies = {}
    for name, target in plan['copies'].items():
        path = overlay / name
        if not path.is_file() or not path.read_text().strip() or (source / target).exists() or not (source / target).parent.is_dir():
            raise SystemExit('Конфликт нового helper тихой отправки: ' + name)
        copies[target] = path.read_bytes()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка тихой отправки: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name in {p[0] for p in plan['patches']}:
        (source / name).write_text(texts[name])
    for name, data in copies.items():
        (source / name).write_bytes(data)
