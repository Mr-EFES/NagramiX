"""Add native pull-quote/select-all and share the panel with the article editor."""
import hashlib
import json
from pathlib import Path


def apply_quick_format_expanded(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'quick_format_expanded_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база расширенного форматирования: ' + name)
        texts[name] = path.read_text()
    templates = {}
    for marker, name in plan['templates'].items():
        value = (overlay / name).read_text().rstrip('\n')
        if not value.strip():
            raise SystemExit('Пустой шаблон расширенного форматирования: ' + name)
        templates[marker] = value
    for name in plan['source_globs']:
        if 'Sources/**/*.swift' not in texts[name]:
            raise SystemExit('Отсутствует Swift glob форматирования: ' + name)
    for name, old, new, count in plan['patches']:
        for marker, value in templates.items():
            new = new.replace(marker, value)
        if any(marker in new for marker in templates) or texts[name].count(old) != count:
            raise SystemExit('Изменилась точка расширенного форматирования: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name in {p[0] for p in plan['patches']}:
        (source / name).write_text(texts[name])
