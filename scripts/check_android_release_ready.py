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

    features = registry.get("features")
    if not isinstance(features, list) or not features:
        raise SystemExit("Feature registry must contain a non-empty 'features' list.")
    if any(not isinstance(feature, dict) or not feature.get("id") for feature in features):
        raise SystemExit("Every feature registry entry must be an object with a non-empty id.")
    ids = [feature["id"] for feature in features]
    if len(ids) != len(set(ids)):
        raise SystemExit("Feature registry contains duplicate feature ids.")

    incomplete = [
        feature
        for feature in features
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
