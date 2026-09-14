#!/usr/bin/env python3
"""Fail a build when the bundled Russian welcome localization is incomplete."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_KEYS = tuple(
    [f"Tour.Title{index}" for index in range(1, 7)]
    + [f"Tour.Text{index}" for index in range(1, 7)]
    + ["Tour.StartButton"]
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("strings_file", type=Path)
    args = parser.parse_args()

    if not args.strings_file.is_file():
        raise SystemExit(f"Russian localization is missing: {args.strings_file}")

    text = args.strings_file.read_text(encoding="utf-8")
    for key in REQUIRED_KEYS:
        match = re.search(
            rf'^"{re.escape(key)}"\s*=\s*"((?:\\.|[^"\\])*)";\s*$',
            text,
            flags=re.MULTILINE,
        )
        if match is None:
            raise SystemExit(f"Russian welcome localization is missing key: {key}")
        value = match.group(1).strip()
        if not value or value == key or value.startswith("Tour."):
            raise SystemExit(f"Russian welcome localization has invalid value for {key}: {value!r}")
        if key != "Tour.Title1" and not re.search("[А-Яа-яЁё]", value):
            raise SystemExit(f"Russian welcome localization has no Cyrillic text for {key}: {value!r}")

    print(f"Validated {len(REQUIRED_KEYS)} Russian welcome strings: {args.strings_file}")


if __name__ == "__main__":
    main()
