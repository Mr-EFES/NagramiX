"""Apply one counter-format preference to Telegram's shared formatters."""
import hashlib
import json
from pathlib import Path


def apply_number_rounding(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'number_rounding_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база форматирования счётчиков: ' + name)
        texts[name] = path.read_text()
    # The existing Foundation module stage already supplies this helper.
    for template, name in plan['provided'].items():
        if not (source / name).is_file() or (source / name).read_bytes() != (overlay / template).read_bytes():
            raise SystemExit('Изменилась интеграция форматирования счётчиков: ' + name)
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка форматирования счётчиков: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
