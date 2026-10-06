#!/usr/bin/env python3
"""Проверить IPA и его происхождение до публикации GitHub-релиза."""

from __future__ import annotations

import argparse
import hashlib
import plistlib
import re
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


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
        require(not any("_CodeSignature/" in name or name.endswith("embedded.mobileprovision") for name in names), "В IPA остались временные подписи/профили")
        with archive.open(prefix + info["CFBundleExecutable"]) as executable:
            magic, cpu = struct.unpack("<II", executable.read(8))
        require(magic == 0xfeedfacf and cpu == 0x100000c, "Основной executable не является ARM64 Mach-O")

        russian = plistlib.loads(archive.read(prefix + "ru.lproj/Localizable.strings"))
        required_keys = set(re.findall(r'^"([^"\n]+)"\s*=', (ROOT / "ios/Resources/ru.lproj/Localizable.strings").read_text(), re.MULTILINE))
        require(required_keys.issubset(russian), "В основном RU ресурсе отсутствуют ключи")
        require(russian.get("Common.Edit") == "Изменить" and russian.get("Tour.StartButton") == "Начать общение", "Неверные русские строки первого запуска")
        for index in range(1, 7):
            require(bool(russian.get(f"Tour.Title{index}")) and bool(russian.get(f"Tour.Text{index}")), "Нет русского приветствия")

        custom = plistlib.loads(archive.read(prefix + "Frameworks/TelegramUIFramework.framework/NagramiXLocalization.bundle/ru.lproj/Localizable.strings"))
        custom_keys = set(re.findall(r'^"([^"\n]+)"\s*=', (ROOT / "ios/Sources/NagramiXCore/Resources/ru.lproj/Localizable.strings").read_text(), re.MULTILINE))
        require(custom_keys.issubset(custom), "В RU ресурсе NagramiX отсутствуют ключи")
        require(custom.get("NagramiX.Profiles.MutualContact") == "Взаимный контакт", "Нет русской метки взаимного контакта")

    print(f"IPA проверен: {args.version}, build {args.build_number}, ARM64, RU {len(russian)}/{len(custom)}, checksum/provenance, без профилей")
    print(f"SHA256: {digest}; размер: {args.ipa.stat().st_size} байт")


if __name__ == "__main__":
    main()
