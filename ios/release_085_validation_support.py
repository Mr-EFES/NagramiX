"""Сохранить неизменяемые входы проверок при обратном снятии overlay."""
import hashlib
import json
from pathlib import Path


def apply_release_085_validation_support(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'release_085_validation_support_patches.json').read_text())
    for name, expected in plan['guards'].items():
        relative = Path(name)
        path = source / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(source.resolve()):
            raise SystemExit('Release validation: unsafe path')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Release validation: missing or changed support input ' + name)
