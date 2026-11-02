"""Replace historical PiP runtime paths with one lifecycle and one gesture owner."""
import hashlib
import json
from pathlib import Path


def apply_pip_runtime(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'pip_runtime_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась проверенная база системного PiP: ' + name)
        texts[name] = path.read_text()
    if 'Sources/**/*.swift' not in texts['submodules/GalleryUI/BUILD']:
        raise SystemExit('Отсутствует GalleryUI Swift glob')
    templates = {marker: (overlay / name).read_text().rstrip('\n')
                 for marker, name in plan['templates'].items()}
    copies = {}
    for template, name in plan['copies'].items():
        if (source / name).exists():
            raise SystemExit('Конфликт нового PiP: ' + name)
        copies[name] = (overlay / template).read_bytes()
    for name, old, new, count in plan['patches']:
        for marker, value in templates.items():
            new = new.replace(marker, value)
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка интеграции нового PiP: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name in plan['remove']:
        if name not in plan['hashes']:
            raise SystemExit('Удаляемый прежний PiP helper не защищён SHA: ' + name)
        symbol = Path(name).stem
        if any(symbol in text for path, text in texts.items() if path != name):
            raise SystemExit('Осталась ссылка на прежний PiP helper: ' + symbol)
    # All inputs/anchors/resources are checked before the first mutation.
    for name in {p[0] for p in plan['patches']}:
        (source / name).write_text(texts[name])
    for name, data in copies.items():
        (source / name).write_bytes(data)
    for name in plan['remove']:
        (source / name).unlink()
