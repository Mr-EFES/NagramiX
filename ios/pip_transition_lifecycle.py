"""Дождаться остановки системного PiP перед передачей воспроизведения."""
import hashlib
import json
from pathlib import Path


def apply_pip_transition_lifecycle(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'pip_transition_lifecycle_patches.json').read_text())
    if not (plan['inputs'].keys() == plan['outputs'].keys() == plan['previous'].keys() == plan['operations'].keys()):
        raise SystemExit('PiP streaming: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('PiP streaming: unsafe path')
        if not path.is_file():
            raise SystemExit('PiP streaming: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('PiP streaming: drift ' + name)
        return data

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        checked(source, name, expected)
    prepared = {}
    for name, expected in plan['inputs'].items():
        data = checked(source, name, expected)
        if checked(overlay, plan['previous'][name], expected) != data:
            raise SystemExit('PiP streaming: wrong prior template')
        text = data.decode('utf-8')
        for operation in plan['operations'][name]:
            before, after = operation[:2]
            count = operation[2] if len(operation) == 3 else 1
            if text.count(before) != count:
                raise SystemExit('PiP streaming: anchor drift ' + name)
            text = text.replace(before, after)
        result = text.encode('utf-8')
        if hashlib.sha256(result).hexdigest() != plan['outputs'][name]:
            raise SystemExit('PiP streaming: output mismatch ' + name)
        prepared[name] = result
    for name, data in prepared.items():
        (source / name).write_bytes(data)
