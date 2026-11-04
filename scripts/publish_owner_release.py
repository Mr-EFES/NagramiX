#!/usr/bin/env python3
"""Опубликовать проверенный CI-артефакт через личный аккаунт владельца."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OWNER = "Mr-EFES"
REPO = f"{OWNER}/NagramiX"
API = f"repos/{REPO}"
COLD_GATE = "Подтвердить холодную основу релизной сборки"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def api(path, method="GET", data=None, optional=False):
    command = ["gh", "api", "--method", method, path]
    if data is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
                            text=True, capture_output=True)
    if result.returncode:
        if optional and method == "GET" and "HTTP 404" in result.stderr:
            return None
        raise RuntimeError(f"GitHub: {method} {path}: {result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return "sha256:" + value.hexdigest()


def validate_package(folder, version, build, source):
    subprocess.run([
        sys.executable, str(ROOT / "scripts/validate_unsigned_ipa.py"),
        "--ipa", str(folder / f"NagramiX-{version}-unsigned.ipa"),
        "--version", version, "--build-number", str(build), "--source-commit", source,
        "--provenance", str(folder / "BUILD-PROVENANCE.txt"),
        "--checksums", str(folder / "SHA256SUMS"),
    ], check=True)


def upload(tag, paths):
    subprocess.run(["gh", "release", "upload", tag, "--repo", REPO,
                    *map(str, paths)], check=True)


def check_remote_assets(release, paths):
    require(release["author"]["login"] == OWNER, "Автор релиза отличается от владельца")
    remote = release["assets"]
    require(len(remote) == len(paths), "Неверное количество файлов релиза")
    by_name = {item["name"]: item for item in remote}
    require(set(by_name) == {p.name for p in paths}, "Неверный состав файлов релиза")
    for path in paths:
        item = by_name[path.name]
        require(item["uploader"]["login"] == OWNER, "Файл загружен другим аккаунтом")
        require(item["size"] == path.stat().st_size and item.get("digest") == digest(path),
                f"Размер или SHA256 опубликованного файла не совпадает: {path.name}")


def find_release(tag):
    release = api(f"{API}/releases/tags/{tag}", optional=True)
    if release is not None:
        return release
    # GitHub не возвращает собственный неопубликованный черновик по тегу.
    matches, page = [], 1
    while True:
        releases = api(f"{API}/releases?per_page=100&page={page}")
        matches.extend(item for item in releases if item["tag_name"] == tag)
        if len(releases) < 100:
            break
        page += 1
    require(len(matches) <= 1, "Найдено несколько релизов с выбранным тегом")
    return matches[0] if matches else None


def publish(source_run_id, artifact_zip, prerelease=False, finalize_uploaded=False):
    # Эта проверка выполняется до создания тегов, черновиков или загрузки файлов.
    require(api("user")["login"] == OWNER, f"Нужна авторизация gh как {OWNER}")
    version = json.loads((ROOT / "product/features/registry.json").read_text())["release"]
    require(re.fullmatch(r"\d+\.\d+\.\d+", version), "Неверная версия")
    annotation = (ROOT / f"product/releases/{version}.md").read_text()
    tag = f"v{version}"
    run = api(f"{API}/actions/runs/{source_run_id}")
    workflow = api(f"{API}/actions/workflows/build-unsigned-ipa.yml")
    require(run["id"] == source_run_id and run["workflow_id"] == workflow["id"]
            and run["head_repository"]["full_name"] == REPO
            and run["head_branch"] == "main" and run["event"] == "workflow_dispatch"
            and run["status"] == "completed", "Неверный источник CI-артефакта")
    require(run["actor"]["login"] == OWNER and run["triggering_actor"]["login"] == OWNER,
            "Сборку должен запускать и перезапускать владелец")
    source, build = run["head_sha"], run["run_number"]
    require(re.fullmatch(r"[0-9a-f]{40}", source) and isinstance(build, int) and build > 0,
            "Неверный commit или номер сборки")
    jobs = api(f"{API}/actions/runs/{source_run_id}/jobs?per_page=100")["jobs"]
    builds = [job for job in jobs if job["name"] == "build" and job["conclusion"] == "success"]
    require(len(builds) == 1 and any(step["name"] == COLD_GATE and step["conclusion"] == "success"
                                  for step in builds[0]["steps"]),
            "Нет успешной чистой SDK-сборки")
    name = f"NagramiX-{version}-unsigned-arm64"
    artifacts = api(f"{API}/actions/runs/{source_run_id}/artifacts?per_page=100")["artifacts"]
    selected = [item for item in artifacts if item["name"] == name and not item["expired"]]
    require(len(selected) == 1 and selected[0].get("digest") == digest(artifact_zip),
            "ZIP не совпадает с SHA256 исходного Actions-артефакта")

    with tempfile.TemporaryDirectory(prefix="nagramix-owner-release-") as temp:
        folder = Path(temp)
        names = {f"NagramiX-{version}-unsigned.ipa", "BUILD-PROVENANCE.txt", "SHA256SUMS"}
        with zipfile.ZipFile(artifact_zip) as archive:
            entries = archive.infolist()
            require(len(entries) == 3 and {entry.filename for entry in entries} == names
                    and all(not entry.is_dir() and ((entry.external_attr >> 16) & 0o170000) != 0o120000
                            for entry in entries), "Неверный состав ZIP-артефакта")
            require(archive.testzip() is None, "Повреждён ZIP-артефакт")
            archive.extractall(folder)
        provenance = (folder / "BUILD-PROVENANCE.txt").read_text().splitlines()
        require(f"Workflow run: https://github.com/{REPO}/actions/runs/{source_run_id}" in provenance,
                "Provenance указывает другой запуск")
        validate_package(folder, version, build, source)

        paths = [folder / name for name in sorted(names)]
        existing = find_release(tag)
        if existing is not None:
            require(existing["draft"] and existing["author"]["login"] == OWNER
                    and existing["target_commitish"] == source,
                    "Замена опубликованного релиза или чужого черновика запрещена")
            require(finalize_uploaded or not existing["assets"],
                    "Перезапись непустого черновика запрещена; для готовых файлов нужен --finalize-uploaded")
        if finalize_uploaded:
            require(existing is not None, "Нет собственного черновика для завершения публикации")
            check_remote_assets(existing, paths)
        ref = api(f"{API}/git/ref/tags/{tag}", optional=True)
        require(ref is None or (ref["object"]["type"] == "commit" and ref["object"]["sha"] == source),
                "Существующий тег указывает другой исходник")
        if existing is None:
            existing = api(f"{API}/releases", "POST", {
                "tag_name": tag, "target_commitish": source, "name": f"Релиз {version}",
                "body": annotation, "draft": True, "prerelease": prerelease,
            })
        require(existing["author"]["login"] == OWNER and existing["draft"],
                "Черновик создан не от имени владельца")
        release_path = f"{API}/releases/{existing['id']}"
        if not finalize_uploaded:
            try:
                upload(tag, paths)
            except subprocess.CalledProcessError as error:
                raise RuntimeError(
                    "Загрузка файлов не завершена. Собственный черновик сохранён: "
                    + existing["html_url"]
                    + ". После загрузки трёх исходных файлов через браузер использовать --finalize-uploaded."
                ) from error
        check_remote_assets(api(release_path), paths)
        result = api(release_path, "PATCH", {
            "name": f"Релиз {version}", "body": annotation, "draft": False,
            "prerelease": prerelease, "make_latest": "false" if prerelease else "true",
        })
        check_remote_assets(result, paths)
        require(not result["draft"] and result["prerelease"] == prerelease,
                "Публикация не подтверждена GitHub")
        return result["html_url"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-id", required=True, type=int)
    parser.add_argument("--artifact-zip", required=True, type=Path)
    parser.add_argument("--prerelease", action="store_true")
    parser.add_argument("--finalize-uploaded", action="store_true",
                        help="Опубликовать собственный черновик с тремя уже загруженными проверенными файлами, без их перезаписи")
    args = parser.parse_args()
    try:
        print(publish(args.source_run_id, args.artifact_zip, args.prerelease,
                      finalize_uploaded=args.finalize_uploaded))
    except (RuntimeError, subprocess.CalledProcessError, OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Публикация не выполнена: {error}\n")


if __name__ == "__main__":
    main()
