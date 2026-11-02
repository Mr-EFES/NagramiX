"""Retain profile story presentation and add opt-in story downloads.

This final stage preserves the canonical overlays and Telegram 13.1 port. Validate
every input, build contract, helper and output before touching the native tree.
"""
import hashlib
import json
from pathlib import Path


def apply_story_profile(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'story_profile_patches.json').read_text(encoding='utf-8'))

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Unsafe story path: ' + name)
        return path

    prepared = {}
    for name, expected in plan['templates'].items():
        path = safe(overlay, name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Story template drift: ' + name)
        if not any(path.read_text(encoding='utf-8') in patch['new'] for patch in plan['patches']):
            raise SystemExit('Unused story template: ' + name)
    for name, expected in {**plan['guards'], **plan['inputs']}.items():
        path = safe(source, name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Story profile input drift: ' + name)
        if name in plan['inputs']:
            prepared[name] = path.read_text(encoding='utf-8')
    for patch in plan['patches']:
        name, old, new, count = (patch[key] for key in ('path', 'old', 'new', 'count'))
        if name not in prepared or count < 1 or prepared[name].count(old) != count:
            raise SystemExit('Story profile anchor drift: ' + name)
        prepared[name] = prepared[name].replace(old, new)
    for name, text in prepared.items():
        if hashlib.sha256(text.encode('utf-8')).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Story profile output drift: ' + name)
    copies = {}
    for name, item in plan['copies'].items():
        destination, origin = safe(source, name), safe(overlay, item['source'])
        if destination.exists() or not origin.is_file():
            raise SystemExit('Story helper collision/missing: ' + name)
        data = origin.read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise SystemExit('Story helper drift: ' + name)
        copies[name] = data
    for name, text in prepared.items():
        safe(source, name).write_text(text, encoding='utf-8')
    for name, data in copies.items():
        path = safe(source, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
