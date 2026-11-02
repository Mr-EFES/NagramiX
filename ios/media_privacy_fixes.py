"""Исправить приватность захвата и сохранение медиа."""
import hashlib
import json
from pathlib import Path


def apply_media_privacy_fixes(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'media_privacy_fixes_patches.json').read_text())
    if plan['inputs'].keys() != plan['outputs'].keys():
        raise SystemExit('Media privacy fixes input/output mismatch')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Unsafe story icon consistency path: ' + name)
        return path

    for name, expected in plan['templates'].items():
        if hashlib.sha256(safe(overlay, name).read_bytes()).hexdigest() != expected:
            raise SystemExit('Media privacy fixes template drift: ' + name)
    prepared = {}
    for name, expected in {**plan['guards'], **plan['inputs']}.items():
        path = safe(source, name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Media privacy fixes input drift: ' + name)
        if name in plan['inputs']:
            prepared[name] = path.read_text()
    for name, old, new, count in plan['patches']:
        if name not in prepared or prepared[name].count(old) != count:
            raise SystemExit('Media privacy fixes anchor drift: ' + name)
        prepared[name] = prepared[name].replace(old, new, count)
    for name, text in prepared.items():
        if hashlib.sha256(text.encode()).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Media privacy fixes output drift: ' + name)
    copies = {}
    for name, item in plan['copies'].items():
        path, origin = safe(source, name), safe(overlay, item['source'])
        if path.exists() or not origin.is_file():
            raise SystemExit('Media privacy fixes helper collision/missing: ' + name)
        data = origin.read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise SystemExit('Media privacy fixes helper drift: ' + name)
        copies[name] = data
    for name, text in prepared.items():
        safe(source, name).write_text(text)
    for name, data in copies.items():
        path = safe(source, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
