"""Unhide only the gallery's source preview during system PiP handoff."""
import hashlib
import json
from pathlib import Path


def apply_pip_visual(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'pip_visual_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база отображения исходного видео PiP: ' + name)
        texts[name] = path.read_text()
    if 'Sources/**/*.swift' not in texts['submodules/GalleryUI/BUILD']:
        raise SystemExit('Отсутствует GalleryUI Swift glob')
    templates = {marker: (overlay / name).read_text().rstrip('\n')
                 for marker, name in plan['templates'].items()}
    copies = {}
    for template, name in plan['copies'].items():
        if (source / name).exists() or not (source / name).parent.is_dir():
            raise SystemExit('Конфликт visual PiP helper: ' + name)
        copies[name] = (overlay / template).read_bytes()
    for name, old, new, count in plan['patches']:
        for marker, template in templates.items():
            new = new.replace(marker, template)
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка отображения исходного видео PiP: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name in {p[0] for p in plan['patches']}:
        (source / name).write_text(texts[name])
    for name, data in copies.items():
        (source / name).write_bytes(data)
