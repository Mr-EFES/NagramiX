#!/usr/bin/env python3
"""Подключить оригиналы пользователя без перерисовки или изменения пикселей.

Размеры задаются штатными viewport Telegram и aspectFit в приложении.
Пять прежних неиспользуемых сцен сохраняются для совместимости manifest.
"""
from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / 'ios/branding/OnboardingMasters'
DEST = ROOT / 'ios/Resources/Onboarding'


def main():
    originals = json.loads((MASTER / 'archive-originals.json').read_text())
    manifest = json.loads((DEST / 'manifest.json').read_text())
    active = {'NagramiXOnboardingLogo.png', 'NagramiXOnboardingPhone.png'}
    if set(originals['files']) != active or not active <= manifest.keys():
        raise SystemExit('Неверный список оригиналов приветствия')
    copies = []
    for name, entry in manifest.items():
        if name in active:
            source = MASTER / originals['files'][name]['master']
            expected = originals['files'][name]['sha256']
            with Image.open(source) as image:
                if image.mode != 'RGBA':
                    raise SystemExit('Нужен исходный прозрачный PNG: ' + name)
        else:
            source, expected = DEST / name, entry['sha256']
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise SystemExit('Изменился исходный файл: ' + name)
        if name in active:
            copies.append((source, DEST / name))
            entry['sha256'] = expected
    # Validate every original and retained legacy asset before any write.
    for source, target in copies:
        shutil.copyfile(source, target)
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Подключены 2 точных оригинала из архива; масштабирование только в native UI.')


if __name__ == '__main__':
    main()
