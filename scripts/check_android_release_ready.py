#!/usr/bin/env python3
"""Block Android packaging until every release feature has been ported."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "product" / "features" / "registry.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True)
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if registry.get("release") != args.release:
        raise SystemExit(
            f"Feature registry release is {registry.get('release')!r}, "
            f"expected {args.release!r}"
        )

    incomplete = [
        feature
        for feature in registry.get("features", [])
        if feature.get("android", {}).get("implementation") != "implemented"
    ]
    if incomplete:
        print(f"Android {args.release} build is disabled: functional parity is incomplete.")
        for feature in incomplete:
            status = feature.get("android", {}).get("implementation", "missing")
            print(f"- {feature.get('id', '<missing id>')}: {status}")
        raise SystemExit(1)

    print(f"Android {args.release} implementation parity gate passed.")


if __name__ == "__main__":
    main()
