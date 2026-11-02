"""Late, fail-closed integration of the ghost-mode policy on the pinned base."""
import hashlib
import json
from pathlib import Path

def apply_ghost_mode(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'ghost_mode_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась проверенная база режима невидимки: ' + name)
        texts[name] = path.read_text()
    for name in ['submodules/TelegramCore/BUILD', 'submodules/SettingsUI/BUILD']:
        if 'Sources/**/*.swift' not in texts[name]:
            raise SystemExit('Отсутствует native Swift glob: ' + name)
    copies = {}
    for template, name in plan['copies'].items():
        if (source/name).exists(): raise SystemExit('Конфликт ghost helper: ' + name)
        copies[name] = (overlay/template).read_bytes()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка интеграции невидимки: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    # Every dependency, template and replacement is validated before the first write.
    for name in {p[0] for p in plan['patches']}:
        (source/name).write_text(texts[name])
    for name, data in copies.items(): (source/name).write_bytes(data)
