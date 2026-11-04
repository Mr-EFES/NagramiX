"""Добавить утверждённое название второй модели Vosk во все языки."""
import hashlib
import json
from pathlib import Path

KEY = 'NagramiX.Transcription.Vosk.Alternative'
PREFERENCES = 'submodules/NagramiXTranscription/Sources/Preferences.swift'
ANCHOR = 'Row(title:$0.title,subtitle:NagramiXVoskModels.shared.status($0),action:.voskModel($0.name))'
REPLACEMENT = 'Row(title:$0.name == "vosk-model-ru-0.10-lgraph" ? self.presentationData.strings.nagramiXLocalized("' + KEY + '") : $0.title,subtitle:NagramiXVoskModels.shared.status($0),action:.voskModel($0.name))'


def apply_vosk_model_naming(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'vosk_model_naming_patches.json').read_text())
    codes = {item['code'] for item in json.loads((overlay / 'app_language_localization/languages.json').read_text())['languages']}
    names = {f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings' for code in codes} | {PREFERENCES}
    if any(set(plan[field]) != names for field in ('inputs', 'outputs', 'previous')) or plan['copies']:
        raise SystemExit('Vosk naming: inconsistent destinations')

    def checked(root, name, digest):
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Vosk naming: unsafe path ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit('Vosk naming: hash drift ' + name)
        return data

    for name, digest in plan['templates'].items():
        checked(overlay, name, digest)
    for name, digest in plan['guards'].items():
        checked(source, name, digest)
    labels = json.loads((overlay / 'vosk_model_naming/labels.json').read_text())
    if set(labels) != codes or any(not label.strip() or any(c in label for c in '\n\r%') for label in labels.values()):
        raise SystemExit('Vosk naming: incomplete translations')
    prepared = {}
    for name, digest in plan['inputs'].items():
        data = checked(source, name, digest)
        if checked(overlay, plan['previous'][name], digest) != data:
            raise SystemExit('Vosk naming: prior mismatch ' + name)
        text = data.decode('utf-8')
        if name == PREFERENCES:
            if text.count(ANCHOR) != 1:
                raise SystemExit('Vosk naming: ambiguous row anchor')
            text = text.replace(ANCHOR, REPLACEMENT)
        else:
            if KEY in text or not text.endswith('\n'):
                raise SystemExit('Vosk naming: existing key or malformed catalog')
            code = Path(name).parent.name.removesuffix('.lproj')
            text += json.dumps(KEY) + ' = ' + json.dumps(labels[code], ensure_ascii=False) + ';\n'
        prepared[name] = text.encode('utf-8')
        if hashlib.sha256(prepared[name]).hexdigest() != plan['outputs'][name]:
            raise SystemExit('Vosk naming: output drift ' + name)
    # Check every source, template, language and output before the first write.
    for name, data in prepared.items():
        (source / name).write_bytes(data)
