"""Complete startup contact denial without presenting or authorizing access."""
import hashlib
import json
from pathlib import Path


def apply_contacts_default_denial(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'contacts_default_denial_patches.json').read_text())
    texts = {}
    for name, expected in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменилась база отказа доступа к контактам: ' + name)
        texts[name] = path.read_text()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка отказа доступа к контактам: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name, text in texts.items():
        (source / name).write_text(text)
