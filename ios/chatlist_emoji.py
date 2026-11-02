"""Resolve custom emoji in chat-list previews with the existing native renderer."""
import hashlib
import json
from pathlib import Path


def apply_chatlist_emoji(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'chatlist_emoji_patches.json').read_text())
    texts = {}
    for name, digest in plan['hashes'].items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit('Изменилась база эмодзи в списке чатов: ' + name)
        texts[name] = path.read_text()
    if 'Sources/**/*.swift' not in texts['submodules/ChatListUI/BUILD']:
        raise SystemExit('Отсутствует ChatListUI Swift glob')
    copies = {}
    for origin, name in plan['copies'].items():
        if (source / name).exists() or not (source / name).parent.is_dir() or not (overlay / origin).is_file():
            raise SystemExit('Конфликт helper эмодзи списка чатов: ' + name)
        copies[name] = (overlay / origin).read_bytes()
    for name, old, new, count in plan['patches']:
        if texts[name].count(old) != count:
            raise SystemExit('Изменилась точка эмодзи списка чатов: ' + name)
        texts[name] = texts[name].replace(old, new, count)
    for name in {p[0] for p in plan['patches']}:
        (source / name).write_text(texts[name])
    for name, data in copies.items():
        (source / name).write_bytes(data)
