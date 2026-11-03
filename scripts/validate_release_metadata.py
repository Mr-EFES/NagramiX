#!/usr/bin/env python3
"""Проверить согласованность текущей версии и её документации без сборки."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    version = json.loads((ROOT / "product/features/registry.json").read_text())["release"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit("Некорректная версия в реестре функций")
    errors: list[str] = []
    workflow = ROOT / ".github/workflows/build-unsigned-ipa.yml"
    match = re.search(r"^\s+NAGRAMIX_VERSION:\s*([^\s]+)\s*$", workflow.read_text(), re.MULTILINE)
    if match is None or match.group(1) != version:
        errors.append("Версия workflow не совпадает с реестром")
    releases = sorted(p.name for p in (ROOT / "product/releases").glob("*.md"))
    if releases != [f"{version}.md"]:
        errors.append("Каталог аннотаций должен содержать только текущую версию")
    for name in ["docs/AI_HANDOFF.md", ".gitignore"]:
        path = ROOT / name
        if not path.is_file() or f"NagramiX {version}" not in path.read_text():
            errors.append(f"Нет заголовка текущей версии: {name}")
    # Текст GPL-2.0 не содержит номера приложения и не меняется при выпуске новой версии.
    license_path = ROOT / "LICENSE"
    if not license_path.is_file() or hashlib.sha256(license_path.read_bytes()).hexdigest() != "edaef632cbb643e4e7a221717a6c441a4c1a7c918e6e4d56debc3d8739b233f6":
        errors.append("LICENSE должен содержать полный неизменённый текст GNU GPL-2.0")
    annotation = ROOT / f"product/releases/{version}.md"
    expected_annotation = "NagramiX — неофициальный Telegram-клиент для iPhone с дополнительными настройками общения, приватности и медия."
    if not annotation.is_file() or annotation.read_text().strip() != expected_annotation:
        errors.append("Аннотация релиза должна содержать только утверждённую фразу о неофициальном клиенте")
    # README закреплён отдельно от версии и аннотации; менять только по прямой команде пользователя.
    readme = ROOT / "README.md"
    expected_readme = expected_annotation
    if not readme.is_file() or readme.read_text().strip() != expected_readme:
        errors.append("README должен сохранять утверждённый пользователем текст без автоматических правок")
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT).decode().split("\0")
    for name in tracked:
        if not name.endswith(".md") and name not in ("LICENSE", ".gitignore"):
            continue
        path = ROOT / name
        if not path.is_file():
            continue
        text = path.read_text()
        # Номера внешних компонентов проверяются отдельно, в upstream-аудите.
        for old in re.findall(r"\bNagramiX\s+(\d+\.\d+\.\d+)\b", text):
            if old != version:
                errors.append(f"Иная версия NagramiX {old}: {name}")
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if "://" in link or link.startswith("#"):
                continue
            target = link.split("#", 1)[0]
            if target and not ((ROOT / name).parent / target).exists():
                errors.append(f"Не существует цель ссылки {target}: {name}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Документация и метаданные NagramiX {version} согласованы")


if __name__ == "__main__":
    main()
