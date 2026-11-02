"""Enable the native view-once default without replacing recording/send flows."""
import hashlib
import json
from pathlib import Path


def apply_once_recording(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'once_recording_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база одноразовой записи: ' + name)
        texts[name] = path.read_text()
    # NagramiXCore is copied by the existing module stage. Check that the
    # canonical helper is present unchanged; do not copy it a second time.
    for template, name in plan['provided'].items():
        if not (source / name).is_file() or (source / name).read_bytes() != (overlay / template).read_bytes():
            raise SystemExit('Изменилась интеграция helper одноразовой записи: ' + name)
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка одноразовой записи: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
