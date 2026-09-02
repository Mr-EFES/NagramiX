#!/usr/bin/env python3
"""Audit pinned NagramiX bases against official Telegram default branches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "NagramiX-upstream-audit"


def env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise RuntimeError(f"Invalid entry in {path}: {raw!r}")
        result[key] = value
    return result


def remote_head(repository: str) -> str:
    output = subprocess.check_output(
        ["git", "ls-remote", repository, "refs/heads/master"], text=True
    ).strip()
    if not output:
        raise RuntimeError(f"Official master was not found: {repository}")
    return output.split()[0]


def download_text(repository: str, commit: str, path: str) -> str:
    slug = repository.removesuffix(".git").removeprefix("https://github.com/")
    url = f"https://raw.githubusercontent.com/{slug}/{commit}/{path}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def ios_status() -> dict[str, object]:
    pin = env_file(ROOT / "ios" / "upstream.env")
    repository = "https://github.com/TelegramMessenger/Telegram-iOS.git"
    head = remote_head(repository)
    metadata = json.loads(download_text(repository, head, "versions.json"))
    return {
        "platform": "ios",
        "repository": repository,
        "pinnedCommit": pin["TELEGRAM_IOS_REF"],
        "pinnedVersion": pin["TELEGRAM_IOS_VERSION"],
        "officialCommit": head,
        "officialVersion": metadata["app"],
        "minimumOS": "13.0",
        "current": head == pin["TELEGRAM_IOS_REF"] and metadata["app"] == pin["TELEGRAM_IOS_VERSION"],
    }


def android_status() -> dict[str, object]:
    pin = env_file(ROOT / "android" / "upstream.env")
    repository = pin["TELEGRAM_ANDROID_REPOSITORY"]
    head = remote_head(repository)
    properties = {}
    for line in download_text(repository, head, "gradle.properties").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key] = value
    return {
        "platform": "android",
        "repository": repository,
        "pinnedCommit": pin["TELEGRAM_ANDROID_REF"],
        "pinnedVersion": pin["TELEGRAM_ANDROID_VERSION"],
        "officialCommit": head,
        "officialVersion": properties["APP_VERSION_NAME"],
        "officialVersionCode": properties["APP_VERSION_CODE"],
        "minimumOS": "API 21",
        "current": head == pin["TELEGRAM_ANDROID_REF"] and properties["APP_VERSION_NAME"] == pin["TELEGRAM_ANDROID_VERSION"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("all", "ios", "android"), default="all")
    parser.add_argument("--require-current", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = []
    if args.platform in ("all", "ios"):
        results.append(ios_status())
    if args.platform in ("all", "android"):
        results.append(android_status())

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for item in results:
            marker = "CURRENT" if item["current"] else "STALE"
            print(
                f"{item['platform']}: {marker}; pin {item['pinnedVersion']} "
                f"{item['pinnedCommit']}; official {item['officialVersion']} "
                f"{item['officialCommit']}; minimum {item['minimumOS']}"
            )

    if args.require_current and any(not item["current"] for item in results):
        raise SystemExit("A pinned official Telegram base is stale; audit and migrate before building")


if __name__ == "__main__":
    main()
