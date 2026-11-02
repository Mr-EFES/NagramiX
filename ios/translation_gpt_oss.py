"""Добавить согласованный бесплатный GPT-OSS после translation_gpt_oss."""
import hashlib
import json
from pathlib import Path


def apply_translation_gpt_oss(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'translation_gpt_oss_patches.json').read_text())
    if plan['inputs'].keys() != plan['outputs'].keys() or plan['inputs'].keys() != plan['replacements'].keys():
        raise SystemExit('Translation GPT-OSS input/output mismatch')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Unsafe Translation GPT-OSS path: ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Translation GPT-OSS input/template drift: ' + name)
        return path.read_bytes()

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in {**plan['guards'], **plan['inputs']}.items():
        checked(source, name, expected)
    prepared = {}
    for name, template in plan['replacements'].items():
        safe(overlay, template)
        if template not in plan['templates']:
            raise SystemExit('Unknown Translation GPT-OSS template: ' + template)
        data = checked(overlay, template, plan['templates'][template])
        if hashlib.sha256(data).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Translation GPT-OSS output drift: ' + name)
        prepared[name] = data
    for name, item in plan['copies'].items():
        if safe(source, name).exists():
            raise SystemExit('Translation GPT-OSS helper collision: ' + name)
        prepared[name] = checked(overlay, item['source'], item['sha256'])
    # All source, BUILD, template, path and output checks finish before writing.
    for name, data in prepared.items():
        path = safe(source, name); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
