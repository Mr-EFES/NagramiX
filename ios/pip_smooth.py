"""Ease the interactive PiP source without changing AVKit window ownership."""
import hashlib
import json
from pathlib import Path


def apply_pip_smooth(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'pip_smooth_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база плавного свайпа PiP: ' + name)
        texts[name] = path.read_text()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка плавного свайпа PiP: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
