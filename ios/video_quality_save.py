"""Fail-closed integration of compatible video-quality export."""
import hashlib
import json
from pathlib import Path


def apply_video_quality_save(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'video_quality_save_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база сохранения качества видео: ' + name)
        texts[name] = path.read_text()
    copies = {}
    for template, name in plan['copies'].items():
        if not (source / name).parent.is_dir() or (source / name).exists():
            raise SystemExit('Конфликт helper сохранения качества: ' + name)
        copies[name] = (overlay / template).read_bytes()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка сохранения качества: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
    for name, data in copies.items():
        (source / name).write_bytes(data)
