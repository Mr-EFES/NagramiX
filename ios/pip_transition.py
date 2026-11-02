"""Keep the real PiP source visible; hand off one settled transition to AVKit."""
import hashlib
import json
from pathlib import Path


def apply_pip_transition(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'pip_transition_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась проверенная база PiP transition: ' + name)
        texts[name] = path.read_text()
    if 'Sources/**/*.swift' not in texts['submodules/GalleryUI/BUILD']:
        raise SystemExit('Отсутствует GalleryUI Swift glob')
    copies = {}
    for template, name in plan['copies'].items():
        if (source / name).exists():
            raise SystemExit('Конфликт PiP transition helper: ' + name)
        copies[name] = (overlay / template).read_bytes()
    templates = {marker: (overlay / name).read_text().rstrip('\n')
                 for marker, name in plan['templates'].items()}
    for name, old, new, count in plan['patches']:
        for marker, value in templates.items():
            new = new.replace(marker, value)
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка интеграции PiP transition: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    # Check every full hash, anchor, dependency and helper before the first write.
    for name in {p[0] for p in plan['patches']}:
        (source / name).write_text(texts[name])
    for name, data in copies.items():
        (source / name).write_bytes(data)
