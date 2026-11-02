"""Integrate IPv6 preference while preserving IPv4 and native retry paths."""
import hashlib
import json
from pathlib import Path


def apply_prefer_ipv6(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'prefer_ipv6_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база приоритета IPv6: ' + name)
        texts[name] = path.read_text()
    for template, name in plan['provided'].items():
        if not (source / name).is_file() or (source / name).read_bytes() != (overlay / template).read_bytes():
            raise SystemExit('Изменилась интеграция настроек IPv6: ' + name)
    copies = {}
    for template, name in plan['copies'].items():
        if not (source / name).parent.is_dir() or (source / name).exists():
            raise SystemExit('Конфликт helper IPv6: ' + name)
        copies[name] = (overlay / template).read_bytes()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка приоритета IPv6: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
    for name, data in copies.items():
        (source / name).write_bytes(data)
