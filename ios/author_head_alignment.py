"""Выровнять голову утверждённой иконки «По автору» над плечами."""
import hashlib
import json
from pathlib import Path


def apply_author_head_alignment(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'author_head_alignment_patches.json').read_text())
    if not (plan['inputs'].keys() == plan['outputs'].keys() == plan['previous'].keys() == plan['operations'].keys()):
        raise SystemExit('Author head alignment: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Author head alignment: unsafe path')
        if not path.is_file():
            raise SystemExit('Author head alignment: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('Author head alignment: drift ' + name)
        return data

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        checked(source, name, expected)
    prepared = {}
    for name, expected in plan['inputs'].items():
        data = checked(source, name, expected)
        if checked(overlay, plan['previous'][name], expected) != data:
            raise SystemExit('Author head alignment: wrong prior template')
        text = data.decode('utf-8')
        for operation in plan['operations'][name]:
            before, after = operation[:2]
            count = operation[2] if len(operation) == 3 else 1
            if text.count(before) != count:
                raise SystemExit('Author head alignment: anchor drift ' + name)
            text = text.replace(before, after)
        result = text.encode('utf-8')
        if hashlib.sha256(result).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Author head alignment: output mismatch ' + name)
        prepared[name] = result
    for name, data in prepared.items():
        (source / name).write_bytes(data)
