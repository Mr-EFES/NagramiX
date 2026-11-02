"""Match the approved formatting panel to native keyboard geometry and color."""
import hashlib
import json
from pathlib import Path


def apply_quick_format_visual(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'quick_format_visual_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база оформления форматирования: ' + name)
        texts[name] = path.read_text()
    for name in plan['source_globs']:
        if 'Sources/**/*.swift' not in texts[name]:
            raise SystemExit('Отсутствует Swift glob оформления: ' + name)
    templates = {}
    for marker, name in plan['templates'].items():
        value = (overlay / name).read_text().rstrip('\n')
        if not value.strip():
            raise SystemExit('Пустой шаблон оформления: ' + name)
        templates[marker] = value
    writes = {}
    for template, name in plan['replacements'].items():
        value = (overlay / template).read_text()
        if not value.strip() or name not in texts:
            raise SystemExit('Неверная замена оформления: ' + name)
        writes[name] = value
    for template, name in plan['copies'].items():
        path = source / name
        value = (overlay / template).read_text()
        if path.exists() or not path.parent.is_dir() or not value.strip():
            raise SystemExit('Конфликт геометрии форматирования: ' + name)
        writes[name] = value
    for name, old, new, count in plan['patches']:
        for marker, value in templates.items():
            new = new.replace(marker, value)
        if any(marker in new for marker in templates) or texts[name].count(old) != count:
            raise SystemExit('Изменилась точка оформления: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name in {p[0] for p in plan['patches']}:
        writes[name] = texts[name]
    for name, text in writes.items():
        (source / name).write_text(text)
