"""Keep complete participant names in reaction/read rows and pin actions."""
import hashlib
import json
from pathlib import Path


def apply_menu_full_names(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'menu_full_names_patches.json').read_text())
    texts = {}
    for name, digest in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit('Изменилась база полных имён в меню: ' + name)
        texts[name] = path.read_text()
    templates = {}
    for marker, name in plan['templates'].items():
        path = overlay / name
        if not path.is_file() or not path.read_text().strip():
            raise SystemExit('Нет шаблона полных имён: ' + name)
        templates[marker] = path.read_text().rstrip('\n')
    for name, old, new, count in plan['patches']:
        for marker, value in templates.items():
            new = new.replace(marker, value)
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка полных имён: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
