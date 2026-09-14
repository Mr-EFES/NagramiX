#!/usr/bin/env python3
"""Fail a build when the bundled Russian welcome localization is incomplete."""

from __future__ import annotations

import argparse
import plistlib
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

    raw_data = args.strings_file.read_bytes()
    compiled_values: dict[str, str] | None = None
    if raw_data.startswith(b"bplist"):
        parsed = plistlib.loads(raw_data)
        if not isinstance(parsed, dict):
            raise SystemExit(f"Compiled Russian localization is not a dictionary: {args.strings_file}")
        compiled_values = parsed
        text = ""
    else:
        try:
            text = raw_data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise SystemExit(f"Russian localization has an unsupported encoding: {error}") from error

    for key in REQUIRED_KEYS:
        if compiled_values is not None:
            raw_value = compiled_values.get(key)
            if not isinstance(raw_value, str):
                raise SystemExit(f"Compiled Russian welcome localization is missing key: {key}")
            value = raw_value.strip()
        else:
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
