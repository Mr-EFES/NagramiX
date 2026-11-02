"""Install the opt-out composer formatting keyboard with exact native guards."""
import hashlib
import json
from pathlib import Path


def apply_quick_format(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'quick_format_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база быстрого форматирования: ' + name)
        texts[name] = path.read_text()
    for template, name in plan['provided'].items():
        if not (source / name).is_file() or (source / name).read_bytes() != (overlay / template).read_bytes():
            raise SystemExit('Изменилась интеграция настройки форматирования: ' + name)
    for name in plan['source_globs']:
        if 'Sources/**/*.swift' not in texts[name]:
            raise SystemExit('Отсутствует Swift glob форматирования: ' + name)
    templates = {}
    for marker, name in plan['templates'].items():
        template = (overlay / name).read_text().rstrip('\n')
        if not template.strip():
            raise SystemExit('Пустой шаблон форматирования: ' + name)
        templates[marker] = template
    copies = {}
    for template, name in plan['copies'].items():
        if (source / name).exists() or not (source / name).parent.is_dir():
            raise SystemExit('Конфликт файла панели форматирования: ' + name)
        copies[name] = (overlay / template).read_bytes()
    for name, old, new, count in plan['patches']:
        for marker, template in templates.items():
            new = new.replace(marker, template)
        if any(marker in new for marker in plan['templates']) or texts[name].count(old) != count:
            raise SystemExit('Изменилась точка быстрого форматирования: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name in {p[0] for p in plan['patches']}:
        (source / name).write_text(texts[name])
    for name, data in copies.items():
        (source / name).write_bytes(data)
