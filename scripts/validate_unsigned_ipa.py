#!/usr/bin/env python3
"""Проверить IPA и его происхождение до публикации GitHub-релиза."""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import re
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def expected_nagramix_catalogs(version: str | None = None) -> dict[str, dict[str, str]]:
    """Получить точные каталоги нужного выпуска, сохраняя контракты старых IPA."""
    plan = json.loads((ROOT / 'ios/vosk_model_naming_patches.json').read_text())
    labels = json.loads((ROOT / 'ios/vosk_model_naming/labels.json').read_text())
    codes = {item['code'] for item in json.loads((ROOT / 'ios/app_language_localization/languages.json').read_text())['languages']}
    require(set(labels) == codes, 'Неполный контракт языков IPA')
    version_parts = tuple(int(part) for part in version.split('.')) if version is not None else None
    additions = None
    if version_parts is not None and version_parts >= (0, 8, 9):
        migration = json.loads((ROOT / 'ios/upstream_13_2_release_post_patches.json').read_text())
        name = 'upstream_13_2_release/localization.json'
        data = (ROOT / 'ios' / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == migration['templates'][name], 'Контракт новых переводов IPA изменён')
        additions = json.loads(data)
        require(additions['previous_key_count'] == 613 and additions['key_count'] == migration['localization_key_count'] == 629,
                'Неверный размер каталога новых переводов IPA')
        require(set(additions['translations']) == codes and len(set(additions['keys'])) == 16,
                'Неполный контракт новых языков IPA')
    wide = None
    if version_parts is not None and version_parts >= (0, 9, 0):
        wide = json.loads((ROOT / 'ios/wide_tab_bar_setting_patches.json').read_text())
        require(wide['target_pin'] == '24638bc69bd083981b178dd1e7f921eebbf7fc46'
                and wide['overlay_base_pin'] == '279f89e4d4f63f17227bf877dc3d8990f22ecd58',
                'Неверная база новых переводов широкой панели')
        require(all(wide['inputs'].keys() == wide[field].keys() for field in ('outputs', 'previous', 'replacements')),
                'Неполный контракт переводов широкой панели')
        resources = {f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings' for code in codes}
        actual_resources = {name for name in wide['outputs'] if name.startswith('submodules/NagramiXCore/Resources/')
                            and name.endswith('.lproj/Localizable.strings')}
        require(actual_resources == resources, 'Неверный набор языков широкой панели')

    round_video = None
    round_translations = None
    if version_parts is not None and version_parts >= (0, 9, 2):
        round_video = json.loads((ROOT / 'ios/round_video_editor_patches.json').read_text())
        require(round_video['target_pin'] == '24638bc69bd083981b178dd1e7f921eebbf7fc46'
                and round_video['required_previous_stage'] == 'temporary_playback_identity',
                'Неверная база переводов круглого видео')
        resources = {f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings' for code in codes}
        actual_resources = {name for name in round_video['outputs'] if name.startswith('submodules/NagramiXCore/Resources/')
                            and name.endswith('.lproj/Localizable.strings')}
        require(actual_resources == resources, 'Неверный набор языков круглого видео')
        name = 'round_video_editor/localization.json'
        data = (ROOT / 'ios' / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == round_video['templates'][name], 'Контракт переводов круглого видео изменён')
        round_translations = json.loads(data)
        require(set(round_translations) == codes, 'Неполный контракт переводов круглого видео')

    premium = None
    premium_translations = None
    if version_parts is not None and version_parts >= (0, 9, 2):
        premium = json.loads((ROOT / 'ios/hide_premium_offers_patches.json').read_text())
        require(premium['target_pin'] == '24638bc69bd083981b178dd1e7f921eebbf7fc46'
                and premium['required_previous_stage'] == 'download_sheet_corners',
                'Неверная база переводов скрытия Premium')
        resources = {f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings' for code in codes}
        actual_resources = {name for name in premium['outputs'] if name.startswith('submodules/NagramiXCore/Resources/')
                            and name.endswith('.lproj/Localizable.strings')}
        require(actual_resources == resources, 'Неверный набор языков скрытия Premium')
        name = 'hide_premium_offers/localization.json'
        data = (ROOT / 'ios' / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == premium['templates'][name], 'Контракт переводов скрытия Premium изменён')
        premium_translations = json.loads(data)
        require(set(premium_translations) == codes, 'Неполный контракт переводов скрытия Premium')

    def catalog(text: str) -> dict[str, str]:
        pairs = re.findall(r'^"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)";', text, re.MULTILINE)
        return {json.loads('"' + key + '"'): json.loads('"' + value + '"') for key, value in pairs}

    def checked_snapshot(name: str, digest: str, contract=None, description='широкой панели') -> dict[str, str]:
        relative = Path(name)
        path = ROOT / 'ios' / relative
        require(not relative.is_absolute() and '..' not in relative.parts
                and path.resolve().is_relative_to((ROOT / 'ios').resolve()), 'Небезопасный путь каталога IPA')
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == digest, 'Исходный каталог ' + description + ' изменён: ' + name)
        contract = wide if contract is None else contract
        require(contract is not None and contract['templates'].get(name) == digest, 'Не закреплён SHA каталога ' + description + ': ' + name)
        return catalog(data.decode('utf-8'))

    consent = None
    consent_translations = None
    if version_parts is not None and version_parts >= (0, 9, 2):
        consent = json.loads((ROOT / 'ios/content_interaction_consent_patches.json').read_text())
        require(consent['target_pin'] == '24638bc69bd083981b178dd1e7f921eebbf7fc46'
                and consent['required_previous_stage'] == 'hide_premium_offers', 'Неверная база явного открытия')
        resources = {f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings' for code in codes}
        require({name for name in consent['outputs'] if name.endswith('.lproj/Localizable.strings')} == resources, 'Неверный набор языков явного открытия')
        consent_name = 'content_interaction_consent/localization.json'
        data = (ROOT / 'ios' / consent_name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == consent['templates'][consent_name], 'Изменён реестр явного открытия')
        consent_translations = json.loads(data)
        require(set(consent_translations) == codes, 'Неполный реестр явного открытия')
    premium_labels = []
    if version_parts is not None and version_parts >= (0, 9, 3):
        for stage, previous_stage in (('premium_label_cleanup', 'poll_copy_transport'), ('premium_label_spelling', 'premium_label_cleanup')):
            premium_label = json.loads((ROOT / 'ios' / (stage + '_patches.json')).read_text())
            require(premium_label['target_pin'] == '24638bc69bd083981b178dd1e7f921eebbf7fc46'
                    and premium_label['required_previous_stage'] == previous_stage, 'Неверная база названия Premium')
            resources = {'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings'}
            require({name for name in premium_label['outputs'] if name.endswith('.lproj/Localizable.strings')} == resources,
                    'Неверный набор языков названия Premium')
            label_name = stage + '/localization.json'
            data = (ROOT / 'ios' / label_name).read_bytes()
            require(hashlib.sha256(data).hexdigest() == premium_label['templates'][label_name], 'Изменён реестр названия Premium')
            label_translations = json.loads(data)
            require(set(label_translations) == {'ru'} and label_translations['ru'].strip(), 'Неполный реестр названия Premium')
            premium_labels.append((premium_label, label_translations))
    catalogs = {}
    for code in sorted(codes):
        name = f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings'
        text = (ROOT / 'ios' / plan['previous'][name]).read_text()
        expected = catalog(text)
        expected['NagramiX.Transcription.Vosk.Alternative'] = labels[code]
        if additions is not None:
            values = additions['translations'][code]
            require(len(values) == len(additions['keys']) and all(value.strip() for value in values), 'Неполные новые переводы: ' + code)
            extra = {'NagramiX.Debug.' + key: value for key, value in zip(additions['keys'], values)}
            require(not expected.keys() & extra.keys(), 'Повтор ключа перевода IPA: ' + code)
            expected.update(extra)
        expected_count = additions['key_count'] if additions is not None else 613
        require(len(expected) == expected_count, 'Неверный размер исходного каталога IPA: ' + code)
        if wide is not None:
            previous = checked_snapshot(wide['previous'][name], wide['inputs'][name])
            current = checked_snapshot(wide['replacements'][name], wide['outputs'][name])
            key = 'NagramiX.Settings.Tabs.WideBar'
            require(previous == expected and len(previous) == 629, 'Изменён прежний контракт 0.8.9: ' + code)
            require(len(current) == 630 and current.keys() - previous.keys() == {key}
                    and all(current.get(old) == value for old, value in previous.items())
                    and bool(current[key].strip()), 'Неполный каталог 0.9.0 широкой панели: ' + code)
            expected = current
        if round_video is not None:
            previous = checked_snapshot(round_video['previous'][name], round_video['inputs'][name], round_video, 'круглого видео')
            current = checked_snapshot(round_video['replacements'][name], round_video['outputs'][name], round_video, 'круглого видео')
            keys = ['NagramiX.RoundVideo.Title', 'NagramiX.RoundVideo.CropHint']
            values = round_translations[code]
            require(previous == expected and len(previous) == 630, 'Изменён прежний контракт 0.9.1: ' + code)
            require(len(values) == 2 and all(value.strip() for value in values)
                    and len(current) == 632 and current.keys() - previous.keys() == set(keys)
                    and all(current.get(old) == value for old, value in previous.items())
                    and all(current.get(key) == value for key, value in zip(keys, values)),
                    'Неполный каталог круглого видео: ' + code)
            expected = current
        if premium is not None:
            previous = checked_snapshot(premium['previous'][name], premium['inputs'][name], premium, 'скрытия Premium')
            current = checked_snapshot(premium['replacements'][name], premium['outputs'][name], premium, 'скрытия Premium')
            keys = ['NagramiX.Settings.HidePremiumOffers', 'NagramiX.Settings.HidePremiumOffersInfo']
            values = premium_translations[code]
            require(previous == expected and len(previous) == 632, 'Изменён промежуточный контракт круглого видео: ' + code)
            require(len(values) == 2 and all(value.strip() for value in values)
                    and len(current) == 634 and current.keys() - previous.keys() == set(keys)
                    and all(current.get(old) == value for old, value in previous.items())
                    and all(current.get(key) == value for key, value in zip(keys, values)),
                    'Неполный каталог скрытия Premium: ' + code)
            expected = current
        if consent is not None:
            previous = checked_snapshot(consent['previous'][name], consent['inputs'][name], consent, 'явного открытия')
            current = checked_snapshot(consent['replacements'][name], consent['outputs'][name], consent, 'явного открытия')
            key = 'NagramiX.Temporary.MarkOpened'
            values = consent_translations[code]
            require(previous == expected and len(previous) == 634, 'Изменён промежуточный контракт Premium: ' + code)
            require(len(values) == 1 and values[0].strip() and len(current) == 635
                    and current.keys() - previous.keys() == {key}
                    and all(current.get(old) == value for old, value in previous.items())
                    and current.get(key) == values[0], 'Неполный каталог явного открытия: ' + code)
            expected = current
        for premium_label, label_translations in premium_labels:
            if code not in label_translations:
                continue
            previous = checked_snapshot(premium_label['previous'][name], premium_label['inputs'][name], premium_label, 'названия Premium')
            current = checked_snapshot(premium_label['replacements'][name], premium_label['outputs'][name], premium_label, 'названия Premium')
            require(previous == expected and len(previous) == 635, 'Изменён прежний контракт 0.9.2: ' + code)
            require(current == {**expected, 'NagramiX.Settings.HidePremiumOffers': label_translations[code]},
                    'Изменены другие переводы при переименовании Premium: ' + code)
            expected = current
        catalogs[code] = expected
    if version_parts is not None and version_parts >= (0, 9, 5):
        fonts = json.loads((ROOT / 'ios/app_font_selection_patches.json').read_text())
        require(fonts['required_previous_stage'] == 'transcription_account_defaults', 'Неверная база шрифтов')
        name = 'app_font_selection/localization.json'
        data = (ROOT / 'ios' / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == fonts['templates'][name], 'Изменён реестр переводов шрифтов')
        translations = json.loads(data)
        require(set(translations['translations']) == codes and len(translations['keys']) == 12, 'Неполные переводы шрифтов')
        for code in codes:
            path = 'submodules/NagramiXCore/Resources/' + code + '.lproj/Localizable.strings'
            previous = checked_snapshot(fonts['previous'][path], fonts['inputs'][path], fonts, 'шрифтов')
            require(previous == catalogs[code], 'Изменён предыдущий каталог перед шрифтами: ' + code)
            values = translations['translations'][code]
            require(len(values) == 12 and not set(translations['keys']) & previous.keys(), 'Неверные ключи шрифтов: ' + code)
            current = checked_snapshot(fonts['replacements'][path], fonts['outputs'][path], fonts, 'шрифтов')
            require(current == {**previous, **dict(zip(translations['keys'], values))}, 'Изменены другие переводы шрифтов: ' + code)
            catalogs[code] = current
    if version_parts is not None and version_parts >= (0, 9, 6):
        preview = json.loads((ROOT / 'ios/font_preview_apply_patches.json').read_text())
        require(preview['required_previous_stage'] == 'premium_temporary_transcription', 'Неверная база предпросмотра шрифтов')
        name = 'font_preview_apply/localization.json'
        data = (ROOT / 'ios' / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == preview['templates'][name], 'Изменён реестр предпросмотра шрифтов')
        translations = json.loads(data)
        require(set(translations['translations']) == codes and len(translations['keys']) == 3, 'Неполные переводы предпросмотра')
        require(translations['replacements'] == {'ru': {'NagramiX.Fonts.Licenses': 'Лицензия шрифтов'}}, 'Изменены незапрошенные подписи шрифтов')
        for code in codes:
            path = 'submodules/NagramiXCore/Resources/' + code + '.lproj/Localizable.strings'
            previous = checked_snapshot(preview['previous'][path], preview['inputs'][path], preview, 'предпросмотра шрифтов')
            require(previous == catalogs[code] and len(previous) == 647, 'Изменён прежний каталог перед предпросмотром: ' + code)
            values = translations['translations'][code]
            require(len(values) == 3 and not set(translations['keys']) & previous.keys(), 'Неверные ключи предпросмотра: ' + code)
            current = checked_snapshot(preview['replacements'][path], preview['outputs'][path], preview, 'предпросмотра шрифтов')
            require(current == {**previous, **dict(zip(translations['keys'], values)), **translations['replacements'].get(code, {})},
                    'Изменены другие переводы предпросмотра: ' + code)
            catalogs[code] = current
    if version_parts is not None and version_parts >= (0, 9, 6):
        effects = json.loads((ROOT/'ios/input_effects_patches.json').read_text())
        require(effects['required_previous_stage'] == 'youtube_playback_policy', 'Неверная база эффектов ввода')
        name = 'input_effects/localization.json'
        data = (ROOT/'ios'/name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == effects['templates'][name], 'Изменён реестр эффектов ввода')
        loc = json.loads(data)
        require(set(loc['translations']) == codes and len(loc['keys']) == 14, 'Неполные переводы эффектов ввода')
        for code in codes:
            path = 'submodules/NagramiXCore/Resources/' + code + '.lproj/Localizable.strings'
            previous = checked_snapshot(effects['previous'][path], effects['inputs'][path], effects, 'эффектов ввода')
            require(previous == catalogs[code] and len(previous) == 650, 'Изменён каталог перед эффектами ввода: ' + code)
            values = loc['translations'][code]
            require(len(values) == 14 and not set(loc['keys']) & previous.keys(), 'Неверные ключи эффектов ввода')
            current = checked_snapshot(effects['replacements'][path], effects['outputs'][path], effects, 'эффектов ввода')
            require(current == {**previous, **dict(zip(loc['keys'], values))}, 'Изменены другие переводы эффектов ввода: ' + code)
            catalogs[code] = current
    return catalogs


def validate_settings_localizations(archive: zipfile.ZipFile, prefix: str, version: str | None = None) -> int:
    """Проверить точные переводы текущего выпуска и прежний контракт пакетов."""
    catalogs = expected_nagramix_catalogs(version)
    resource_root = prefix + 'Frameworks/TelegramUIFramework.framework/NagramiXLocalization.bundle/'
    names = archive.namelist()
    if version is not None and tuple(int(part) for part in version.split('.')) >= (0, 9, 0):
        expected_resources = {resource_root + f'{code}.lproj/Localizable.strings' for code in catalogs}
        packed_resources = [name for name in names if name.startswith(resource_root) and name.endswith('.lproj/Localizable.strings')]
        require(len(packed_resources) == len(expected_resources) and set(packed_resources) == expected_resources,
                'В IPA неполный, лишний или дублированный набор языков настроек')
    for code, expected in catalogs.items():
        resource = resource_root + f'{code}.lproj/Localizable.strings'
        require(resource in names, f'В IPA отсутствует язык настроек: {code}')
        packed = plistlib.loads(archive.read(resource))
        require(packed == expected, f'Переводы настроек/debug в IPA изменены или неполны: {code}')
    return len(catalogs)


def validate_device_compatibility(archive: zipfile.ZipFile) -> int:
    count = 0
    for entry in archive.infolist():
        if entry.is_dir():
            continue
        with archive.open(entry) as stream:
            header = stream.read(32)
            if len(header) < 32 or header[:4] != b"\xcf\xfa\xed\xfe":
                continue
            _, cpu, _, _, commands, command_bytes, _, _ = struct.unpack("<8I", header)
            require(cpu == 0x100000c, f"Не ARM64: {entry.filename}")
            data = stream.read(command_bytes)
        require(len(data) == command_bytes, f"Обрезан Mach-O: {entry.filename}")
        offset, deployment_found = 0, False
        for _ in range(commands):
            require(offset + 8 <= len(data), f"Повреждены команды Mach-O: {entry.filename}")
            command, length = struct.unpack_from("<II", data, offset)
            require(length >= 8 and offset + length <= len(data), f"Неверная команда Mach-O: {entry.filename}")
            if command == 0x32:
                require(length >= 24, f"Обрезан LC_BUILD_VERSION: {entry.filename}")
                platform, minimum = struct.unpack_from("<II", data, offset + 8)
                require(platform == 2, f"Двоичный файл не для физического iPhone: {entry.filename}")
                require(minimum <= 15 << 16, f"Двоичный файл требует iOS новее 15.0: {entry.filename}")
                deployment_found = True
            elif command == 0x25:
                require(length >= 16, f"Обрезан LC_VERSION_MIN_IPHONEOS: {entry.filename}")
                minimum = struct.unpack_from("<I", data, offset + 8)[0]
                require(minimum <= 15 << 16, f"Двоичный файл требует iOS новее 15.0: {entry.filename}")
                deployment_found = True
            offset += length
        require(deployment_found, f"Не определена минимальная iOS: {entry.filename}")
        count += 1
    require(count > 0, "В IPA нет двоичных файлов iPhoneOS")
    return count


def validate_notification_sound_resources(archive: zipfile.ZipFile, prefix: str) -> int:
    manifest = json.loads((ROOT / "ios/Resources/NotificationSounds/manifest.json").read_text())
    expected_keys = set(range(200, 211)) | set(range(100, 112)) | set(range(2, 10))
    require(len(manifest) == 31 and {row["key"] for row in manifest} == expected_keys, "Неполный исходный каталог мелодий")
    names = set(archive.namelist())
    for row in manifest:
        require(row["file"] == f'{row["key"]}.m4a', "Неверное имя встроенной мелодии")
        name = prefix + row["file"]
        require(name in names, f"В IPA отсутствует встроенная мелодия: {row['file']}")
        data = archive.read(name)
        require(hashlib.sha256(data).hexdigest() == row["sha256"], f"В IPA повреждена встроенная мелодия: {row['file']}")
    return len(manifest)


def validate_app_icons(archive: zipfile.ZipFile, prefix: str, info: dict) -> int:
    """Check the actual system declarations and home-screen PNGs, not previews."""
    expected = {f"NagramiX{index}" for index in range(2, 9)}
    names = set(archive.namelist())
    fingerprints = set()
    for key in ("CFBundleIcons", "CFBundleIcons~ipad"):
        if key.endswith("~ipad") and key not in info:
            continue
        icons = info.get(key, {})
        require(icons.get("CFBundlePrimaryIcon", {}).get("CFBundleIconName") == "NagramiX1", "Неверная основная иконка")
        alternates = icons.get("CFBundleAlternateIcons", {})
        require(set(alternates) == expected, f"Неполные системные объявления иконок: {key}")
        for name in sorted(expected):
            require(name in alternates[name].get("CFBundleIconFiles", []), f"Неверная ссылка на иконку: {key}/{name}")
            for scale, pixels in ((2, 120), (3, 180)):
                path = prefix + f"{name}@{scale}x.png"
                require(path in names, f"Нет иконки для рабочего стола: {path}")
                data = archive.read(path)
                require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"Неверный PNG иконки: {path}")
                offset, found = 8, False
                while offset + 12 <= len(data):
                    length = struct.unpack_from(">I", data, offset)[0]
                    require(offset + length + 12 <= len(data), f"Обрезан PNG иконки: {path}")
                    if data[offset + 4:offset + 8] == b"IHDR":
                        require(length == 13, f"Неверный IHDR иконки: {path}")
                        require(struct.unpack_from(">II", data, offset + 8) == (pixels, pixels), f"Неверный размер иконки: {path}")
                        found = True
                        break
                    offset += length + 12
                require(found, f"Нет размера PNG иконки: {path}")
                if key == "CFBundleIcons" and scale == 3:
                    fingerprints.add(hashlib.sha256(data).digest())
    require(len(fingerprints) == len(expected), "Варианты иконок ошибочно дублируют друг друга")
    return len(expected) + 1


def validate_onboarding_resources(archive: zipfile.ZipFile, prefix: str, russian: dict, english: dict) -> int:
    copy = json.loads((ROOT / "ios/Resources/Onboarding/copy.json").read_text())
    for language, actual in (("ru", russian), ("en", english)):
        for key, expected in copy[language].items():
            require(actual.get(key) == expected, f"Неверная строка приветствия {language}/{key}")
    manifest = json.loads((ROOT / "ios/Resources/Onboarding/manifest.json").read_text())
    names = set(archive.namelist())
    for name, entry in manifest.items():
        require(prefix + name in names, f"В IPA нет иллюстрации приветствия: {name}")
        source = (ROOT / "ios" / entry["source"]).read_bytes()
        require(hashlib.sha256(source).hexdigest() == entry["sha256"], f"Повреждён исходник иллюстрации: {name}")
        packed = archive.read(prefix + name)
        # Apple may optimize/recompress PNGs, including inserting a CgBI chunk.
        # Verify the PNG and dimensions rather than requiring identical bytes.
        def dimensions(data: bytes) -> tuple[int, int]:
            require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"Неверный PNG: {name}")
            offset = 8
            while offset + 12 <= len(data):
                length = struct.unpack_from(">I", data, offset)[0]
                require(offset + length + 12 <= len(data), f"Обрезанный PNG: {name}")
                if data[offset + 4:offset + 8] == b"IHDR":
                    require(length == 13, f"Неверный IHDR: {name}")
                    return struct.unpack_from(">II", data, offset + 8)
                offset += length + 12
            raise SystemExit(f"Нет IHDR: {name}")
        require(dimensions(packed) == dimensions(source), f"Неверный размер иллюстрации: {name}")
    return len(manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ipa", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-number", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--checksums", required=True, type=Path)
    args = parser.parse_args()

    checksum_rows = [line.split() for line in args.checksums.read_text().splitlines()]
    matches = [row[0] for row in checksum_rows if len(row) == 2 and row[1].lstrip("*") == args.ipa.name]
    require(len(matches) == 1, "Нет однозначной контрольной суммы IPA")
    with args.ipa.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    require(digest == matches[0], "Контрольная сумма IPA не совпадает")

    pin = next(line.split("=", 1)[1] for line in (ROOT / "ios/upstream.env").read_text().splitlines() if line.startswith("TELEGRAM_IOS_REF="))
    provenance = set(args.provenance.read_text().splitlines())
    for expected in (
        f"NagramiX version: {args.version}",
        f"NagramiX commit: {args.source_commit}",
        f"Telegram-iOS commit: {pin}",
    ):
        require(expected in provenance, f"Не совпадает происхождение сборки: {expected}")
    if tuple(int(part) for part in args.version.split('.')) >= (0, 8, 9):
        from fetch_upstream_submodules import load_plan, provenance_lines
        for expected in provenance_lines(load_plan()):
            require(expected in provenance, 'Не указана точная замена зависимости Telegram13.2')

    prefix = "Payload/NagramiX.app/"
    with zipfile.ZipFile(args.ipa) as archive:
        names = archive.namelist()
        info = plistlib.loads(archive.read(prefix + "Info.plist"))
        for key, expected in (
            ("CFBundleIdentifier", "com.mr-efes.nagramix"),
            ("CFBundleDisplayName", "NagramiX"),
            ("CFBundleDevelopmentRegion", "ru"),
            ("CFBundleShortVersionString", args.version),
            ("CFBundleVersion", args.build_number),
        ):
            require(info.get(key) == expected, f"Неверное значение {key}: {info.get(key)}")
        require(info.get("MinimumOSVersion") == "15.0", "Основное приложение не сохраняет поддержку iOS 15.0")
        device_binary_count = validate_device_compatibility(archive)
        require(not any("_CodeSignature/" in name or name.endswith("embedded.mobileprovision") for name in names), "В IPA остались временные подписи/профили")
        with archive.open(prefix + info["CFBundleExecutable"]) as executable:
            magic, cpu = struct.unpack("<II", executable.read(8))
        require(magic == 0xfeedfacf and cpu == 0x100000c, "Основной executable не является ARM64 Mach-O")
        sound_count = validate_notification_sound_resources(archive, prefix)
        icon_count = validate_app_icons(archive, prefix, info)
        if tuple(int(part) for part in args.version.split('.')) >= (0, 9, 5):
            from validate_ipa_fonts import validate_font_resources
            validate_font_resources(archive, prefix)


        russian = plistlib.loads(archive.read(prefix + "ru.lproj/Localizable.strings"))
        required_keys = set(re.findall(r'^"([^"\n]+)"\s*=', (ROOT / "ios/Resources/ru.lproj/Localizable.strings").read_text(), re.MULTILINE))
        require(required_keys.issubset(russian), "В основном RU ресурсе отсутствуют ключи")
        require(russian.get("Common.Edit") == "Изменить" and russian.get("Tour.StartButton") == "Начать общение", "Неверные русские строки первого запуска")
        for index in range(1, 7):
            require(bool(russian.get(f"Tour.Title{index}")) and bool(russian.get(f"Tour.Text{index}")), "Нет русского приветствия")
        if tuple(int(part) for part in args.version.split(".")) >= (0, 5, 4):
            english = plistlib.loads(archive.read(prefix + "en.lproj/Localizable.strings"))
            validate_onboarding_resources(archive, prefix, russian, english)

        custom = plistlib.loads(archive.read(prefix + "Frameworks/TelegramUIFramework.framework/NagramiXLocalization.bundle/ru.lproj/Localizable.strings"))
        custom_keys = {json.loads('"' + key + '"') for key in re.findall(r'^"((?:[^"\\]|\\.)*)"\s*=', (ROOT / "ios/Sources/NagramiXCore/Resources/ru.lproj/Localizable.strings").read_text(), re.MULTILINE)}
        require(custom_keys.issubset(custom), "В RU ресурсе NagramiX отсутствуют ключи")
        require(custom.get("NagramiX.Profiles.MutualContact") == "Взаимный контакт", "Нет русской метки взаимного контакта")
        if tuple(int(part) for part in args.version.split(".")) >= (0, 6, 7):
            english_custom = plistlib.loads(archive.read(prefix + "Frameworks/TelegramUIFramework.framework/NagramiXLocalization.bundle/en.lproj/Localizable.strings"))
            require(custom.get("NagramiX.QuickFormatting.Title") == "Быстрое форматирование", "Нет RU строки быстрого форматирования")
            require(english_custom.get("NagramiX.QuickFormatting.Title") == "Quick formatting", "Нет EN строки быстрого форматирования")
        if tuple(int(part) for part in args.version.split(".")) >= (0, 7, 0):
            plan = json.loads((ROOT / "ios/debug_menu_localization_patches.json").read_text())
            for language, packed in (("ru", custom), ("en", english_custom)):
                expected = {}
                for patch in plan["patches"]:
                    if patch["path"].endswith(f"/{language}.lproj/Localizable.strings"):
                        for key, value in re.findall(r'^"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)";', patch["new"], re.MULTILINE):
                            key, value = json.loads('"' + key + '"'), json.loads('"' + value + '"')
                            if key.startswith("NagramiX.Debug."):
                                expected[key] = value
                require(len(expected) >= 60, f"Неполный контракт переводов отладки: {language}")
                for key, value in expected.items():
                    require(packed.get(key) == value, f"Нет актуального перевода отладки: {language}/{key}")
            story_plan = json.loads((ROOT / "ios/story_profile_patches.json").read_text())
            for language, packed in (("ru", custom), ("en", english_custom)):
                expected = {}
                for patch in story_plan["patches"]:
                    if patch["path"].endswith(f"/{language}.lproj/Localizable.strings"):
                        for key, value in re.findall(r'^"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)";', patch["new"], re.MULTILINE):
                            key, value = json.loads('"' + key + '"'), json.loads('"' + value + '"')
                            if key.startswith("NagramiX.Stories.Download."):
                                expected[key] = value
                require(len(expected) == 3, f"Неполный контракт скачивания историй: {language}")
                for key, value in expected.items():
                    require(packed.get(key) == value, f"Нет перевода скачивания историй: {language}/{key}")
        if tuple(int(part) for part in args.version.split(".")) >= (0, 7, 1):
            for language, packed, title in (("ru", custom, "Быстрое форматирование"), ("en", english_custom, "Quick formatting")):
                require(packed.get("NagramiX.QuickFormatting.PanelTitle") == title, f"Неверный заголовок панели: {language}")
                require(bool(packed.get("NagramiX.Icon.ChangeFailed")), f"Нет сообщения об отказе смены иконки: {language}")

        if tuple(int(part) for part in args.version.split(".")) >= (0, 8, 6):
            language_count = validate_settings_localizations(archive, prefix, args.version)
            key_count = 635 if tuple(int(part) for part in args.version.split('.')) >= (0, 9, 2) else 630 if tuple(int(part) for part in args.version.split('.')) >= (0, 9, 0) else 629 if tuple(int(part) for part in args.version.split('.')) >= (0, 8, 9) else 613
            print(f"Переводы IPA проверены: {language_count} языков, по {key_count} ключей настроек/debug")

    print(f"IPA проверен: {args.version}, build {args.build_number}, iOS15+, ARM64/iPhoneOS файлов {device_binary_count}, RU {len(russian)}/{len(custom)}, мелодий {sound_count}, иконок {icon_count}, checksum/provenance, без профилей")
    print(f"SHA256: {digest}; размер: {args.ipa.stat().st_size} байт")


if __name__ == "__main__":
    main()
