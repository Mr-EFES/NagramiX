"""Изолировать архив обычного чата от списка отложенных сообщений."""
import hashlib
import json
from pathlib import Path


def apply_scheduled_archive_isolation(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'scheduled_archive_isolation_patches.json').read_text())
    if plan['inputs'].keys() != plan['outputs'].keys():
        raise SystemExit('Scheduled archive isolation input/output mismatch')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Unsafe scheduled archive isolation path: ' + name)
        return path

    for name, expected in plan['templates'].items():
        if hashlib.sha256(safe(overlay, name).read_bytes()).hexdigest() != expected:
            raise SystemExit('Scheduled archive isolation template drift: ' + name)
    prepared = {}
    for name, expected in {**plan['guards'], **plan['inputs']}.items():
        path = safe(source, name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Scheduled archive isolation input drift: ' + name)
        if name in plan['inputs']:
            prepared[name] = path.read_text()
    for name, old, new, count in plan['patches']:
        if name not in prepared or prepared[name].count(old) != count:
            raise SystemExit('Scheduled archive isolation anchor drift: ' + name)
        prepared[name] = prepared[name].replace(old, new, count)
    for name, text in prepared.items():
        if hashlib.sha256(text.encode()).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Scheduled archive isolation output drift: ' + name)
    copies = {}
    for name, item in plan['copies'].items():
        path, origin = safe(source, name), safe(overlay, item['source'])
        if path.exists() or not origin.is_file():
            raise SystemExit('Scheduled archive isolation helper collision/missing: ' + name)
        data = origin.read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise SystemExit('Scheduled archive isolation helper drift: ' + name)
        copies[name] = data
    for name, text in prepared.items():
        safe(source, name).write_text(text)
    for name, data in copies.items():
        path = safe(source, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
