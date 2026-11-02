"""Repair single view-once forwarding and retain broadcast destinations."""
import hashlib
import json
from pathlib import Path


def apply_transfer_routing(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'transfer_routing_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база адресации пересылки: ' + name)
        texts[name] = path.read_text()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка адресации пересылки: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    # Validate every input and anchor before writing any native file.
    for name, text in texts.items():
        (source / name).write_text(text)
