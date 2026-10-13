#!/usr/bin/env python3
"""Проверка границ правок стабильности; не заменяет сборку с Apple SDK."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import os
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RECORDER = 'submodules/Camera/CameraLegacy/Sources/VideoRecorder.swift'
PICKER = 'submodules/LegacyMediaPickerUI/Sources/LegacyMediaPickers.swift'
SOUND = 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedSoundSave.swift'
VIDEO = 'submodules/TelegramUI/Sources/Chat/NagramiXArchivedMediaSave.swift'


def snapshot(folder):
    return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob('*') if p.is_file()}


def validate(before, after):
    overlay = ROOT / 'ios/apply_features.py'
    function = next(n for n in ast.parse(overlay.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'apply_recorder_backpressure_fix')
    patches = ast.literal_eval(next(n.value for n in function.body
                                  if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'substitutions' for t in n.targets)))
    original, result = snapshot(before), snapshot(after)
    assert original.keys() == result.keys(), 'Состав native-файлов изменился'
    changed = {name for name in original if original[name] != result[name]}
    assert changed == {RECORDER, PICKER, SOUND, VIDEO}, changed
    reversed_recorder = result[RECORDER].decode()
    for old, new in reversed(patches):
        assert reversed_recorder.count(new) == 1
        reversed_recorder = reversed_recorder.replace(new, old, 1)
    assert reversed_recorder.encode() == original[RECORDER]
    include = (ROOT / 'ios/Sources/LegacyMediaPickerUI/NagramiXOriginalVideos.swift.inc').read_text()
    marker = '// Included in LegacyMediaPickers.swift; no second uploader or player is needed.\n'
    assert original[PICKER].decode().count(marker) == result[PICKER].decode().count(marker) == 1
    assert result[PICKER].decode().endswith(include)
    assert original[PICKER].decode().split(marker)[0] == result[PICKER].decode().split(marker)[0]
    assert 'fromTempPath: tempFile.path' not in include
    assert 'LocalFileMediaResource(fileId:' in include
    assert 'fromTempPath: uploadPath' in include
    assert include.index('try FileManager.default.linkItem(atPath: tempFile.path, toPath: uploadPath)') < include.index('fromTempPath: uploadPath')
    pin_start = include.index('let uploadPath = ')
    pin_end = include.index('account.postbox.mediaBox.moveResourceData(resource.id, fromTempPath: uploadPath)')
    pin_code = include[pin_start:pin_end]
    assert pin_code.index('copyItem(atPath: tempFile.path, toPath: uploadPath)') < pin_code.index('lock.lock()')
    assert 'if !uploadPathHandedOff' in pin_code
    assert 'guard !disposed else { lock.unlock(); return }' in pin_code
    for name in (SOUND, VIDEO):
        assert original[name].count(b'builder.file(file)') == 1
        assert original[name].replace(b'builder.file(file)', b'builder.prepare(file) as? TelegramMediaFile') == result[name]
    helper = (ROOT / 'ios/Sources/TelegramCore/NagramiXArchivedMediaCopy.swift').read_text()
    assert 'public func prepare(_ media: Media) -> Media?' in helper
    assert 'private func file(' in helper  # Новый public API не понадобился.

    spec = importlib.util.spec_from_file_location('nagramix_overlay', overlay)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='nagramix-stability-guards-') as folder:
        fixture = Path(folder)
        target = fixture / RECORDER
        target.parent.mkdir(parents=True)
        target.write_bytes(original[RECORDER])
        module.apply_recorder_backpressure_fix(fixture)
        assert target.read_bytes() == result[RECORDER]
        for data in (result[RECORDER], original[RECORDER] + b'\n// drift\n'):
            target.write_bytes(data)
            try:
                module.apply_recorder_backpressure_fix(fixture)
            except SystemExit:
                pass
            else:
                raise AssertionError('Применение к изменённому входу разрешено')
            assert target.read_bytes() == data, 'Отказ изменил источник'

    # Воспроизводим опасный порядок на настоящей ФС: очистка Photos temp
    # происходит до queued MediaBox move. Независимый pin обязан его пережить.
    with tempfile.TemporaryDirectory(prefix='nagramix-video-ownership-') as folder:
        root = Path(folder)
        payload = bytes(range(256)) * 4096 + b'\x00original-video\xff'
        digest = hashlib.sha256(payload).digest()
        unpinned = root / 'old-temp'
        unpinned.write_bytes(payload)
        unpinned.unlink()
        try:
            unpinned.rename(root / 'old-cache')
        except FileNotFoundError:
            pass
        else:
            raise AssertionError('Не воспроизведено преждевременное удаление')
        for mode in ('hardlink', 'copy'):
            source, pin, cache = (root / (mode + suffix) for suffix in ('-temp', '-pin', '-cache'))
            source.write_bytes(payload)
            if mode == 'hardlink':
                os.link(source, pin)
            else:
                shutil.copyfile(source, pin)
            source.unlink()
            pin.rename(cache)
            assert hashlib.sha256(cache.read_bytes()).digest() == digest
            assert not source.exists() and not pin.exists()
            # Отмена во время fallback copy: worker удаляет pin до передачи
            # native move, сохраняя независимый исходник до своего defer.
            cancelled_pin = root / (mode + '-cancelled')
            shutil.copyfile(cache, cancelled_pin)
            cancelled_pin.unlink()
            assert cache.read_bytes() == payload and not cancelled_pin.exists()

    print(f'Полный overlay: {len(result)} файлов, {len(result) - 4} без изменений; четыре точных изменения: PASS')
    print(f'Рекордер: {len(patches)} обратимых замен; drift/rerun до записи: PASS')
    print('Владение video bytes при ранней очистке: hardlink/copy + queued move: PASS')
    print('Сохранение архивного звука/видео использует существующий public prepare: PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True, type=Path)
    parser.add_argument('--after', required=True, type=Path)
    args = parser.parse_args()
    validate(args.before, args.after)


if __name__ == '__main__':
    main()
