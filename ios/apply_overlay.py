#!/usr/bin/env python3
"""Apply the smallest possible NagramiX branding layer to Telegram-iOS."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from apply_features import apply_features


ALTERNATE_ICON_SIZES = {
    "@2x.png": 120,
    "@3x.png": 180,
    "-76.png": 76,
    "-76@2x.png": 152,
    "-83.5@2x.png": 167,
    "_29x29.png": 29,
    "_58x58.png": 58,
    "_80x80.png": 80,
    "_87x87.png": 87,
    "_notification.png": 20,
    "_notification@2x.png": 40,
    "_notification@3x.png": 60,
}

PRIMARY_ICON_IMAGES = [
    ("iphone", "20x20", "2x", "NagramiX1-40.png", 40),
    ("iphone", "20x20", "3x", "NagramiX1-60.png", 60),
    ("iphone", "29x29", "2x", "NagramiX1-58.png", 58),
    ("iphone", "29x29", "3x", "NagramiX1-87.png", 87),
    ("iphone", "40x40", "2x", "NagramiX1-80.png", 80),
    ("iphone", "40x40", "3x", "NagramiX1-120.png", 120),
    ("iphone", "60x60", "2x", "NagramiX1-120-home.png", 120),
    ("iphone", "60x60", "3x", "NagramiX1-180.png", 180),
    ("ipad", "20x20", "1x", "NagramiX1-20.png", 20),
    ("ipad", "20x20", "2x", "NagramiX1-40-ipad.png", 40),
    ("ipad", "29x29", "1x", "NagramiX1-29.png", 29),
    ("ipad", "29x29", "2x", "NagramiX1-58-ipad.png", 58),
    ("ipad", "40x40", "1x", "NagramiX1-40-settings.png", 40),
    ("ipad", "40x40", "2x", "NagramiX1-80-ipad.png", 80),
    ("ipad", "76x76", "2x", "NagramiX1-152.png", 152),
    ("ipad", "83.5x83.5", "2x", "NagramiX1-167.png", 167),
    ("ios-marketing", "1024x1024", "1x", "NagramiX1-1024.png", 1024),
]

PRIMARY_ICON_PREVIEW_IMAGES = [
    ("1x", "NagramiX1Preview.png", 60),
    ("2x", "NagramiX1Preview@2x.png", 120),
    ("3x", "NagramiX1Preview@3x.png", 180),
]


def resize_icon(source: Path, destination: Path, size: int) -> None:
    try:
        from PIL import Image
    except ImportError:
        subprocess.run(
            ["sips", "-z", str(size), str(size), str(source), "--out", str(destination)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    else:
        with Image.open(source) as image:
            resized = image.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            opaque = Image.new("RGB", resized.size, (0, 0, 0))
            opaque.paste(resized, mask=resized.getchannel("A"))
            opaque.save(destination, format="PNG")


def replace_text(path: Path, old: str, new: str) -> bool:
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    if old not in content:
        return False
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    return True


def create_primary_icon_set(source_icon: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    images = []
    for idiom, size_name, scale, filename, pixels in PRIMARY_ICON_IMAGES:
        resize_icon(source_icon, destination / filename, pixels)
        images.append({
            "size": size_name,
            "idiom": idiom,
            "filename": filename,
            "scale": scale,
        })
    contents = {
        "images": images,
        "info": {"version": 1, "author": "xcode"},
    }
    (destination / "Contents.json").write_text(
        json.dumps(contents, indent=2) + "\n",
        encoding="utf-8",
    )


def create_primary_icon_preview_set(source_icon: Path, destination: Path) -> None:
    """Create a normal image asset used by the in-app icon picker.

    An AppIcon asset is available to iOS as the primary application icon, but
    it cannot be loaded reliably through UIImage(named:). Keeping the picker
    preview separate lets the default icon remain a true primary icon while
    still providing a tappable image in Telegram's icon grid.
    """
    destination.mkdir(parents=True, exist_ok=True)
    images = []
    for scale, filename, pixels in PRIMARY_ICON_PREVIEW_IMAGES:
        resize_icon(source_icon, destination / filename, pixels)
        images.append({
            "idiom": "universal",
            "filename": filename,
            "scale": scale,
        })
    contents = {
        "images": images,
        "info": {"version": 1, "author": "xcode"},
    }
    (destination / "Contents.json").write_text(
        json.dumps(contents, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    if not (source / "Telegram" / "BUILD").exists() and not (source / "Telegram" / "BUILD.bazel").exists():
        raise SystemExit(f"Not a Telegram-iOS source tree: {source}")

    api_id = os.environ.get("TELEGRAM_API_ID", "")
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    if not api_id.isdigit() or not api_hash:
        raise SystemExit("TELEGRAM_API_ID and TELEGRAM_API_HASH must be configured")

    template = Path(__file__).with_name("configuration.template.json")
    configuration = json.loads(template.read_text(encoding="utf-8"))
    configuration["api_id"] = api_id
    configuration["api_hash"] = api_hash
    args.configuration.parent.mkdir(parents=True, exist_ok=True)
    args.configuration.write_text(json.dumps(configuration, indent=2) + "\n", encoding="utf-8")

    # This exact fragment is pinned to the audited Telegram-iOS commit. Failing
    # instead of guessing prevents a silent loss of branding after an update.
    build_file = source / "Telegram" / "BUILD"
    old_fragment = "<key>CFBundleDisplayName</key>\n    <string>Telegram</string>"
    new_fragment = "<key>CFBundleDisplayName</key>\n    <string>NagramiX</string>"
    if not replace_text(build_file, old_fragment, new_fragment):
        raise SystemExit("Pinned CFBundleDisplayName fragment was not found")

    # Build the device app with its real identifier and generated build-only
    # profiles. Extensions stay out of the first login checkpoint.
    make_file = source / "build-system" / "Make" / "Make.py"
    anchor = "    bazel_command_line.set_configuration(arguments.configuration)"
    replacement = """    bazel_command_line.common_build_args += ['--//Telegram:disableExtensions']
    bazel_command_line.set_configuration(arguments.configuration)"""
    if not replace_text(make_file, anchor, replacement):
        raise SystemExit("Pinned unsigned-build anchor was not found in Make.py")

    icon_sources = Path(__file__).with_name("branding") / "AppIcons"
    icon_source = icon_sources / "1.png"
    # The primary icon must be an .appiconset for rules_apple. It is generated
    # from the same prepared source as the seven conventional alternate icons,
    # so all eight retain the same visual scale without using Icon Composer.
    create_primary_icon_set(
        icon_source,
        source / "Telegram" / "Telegram-iOS" / "AppIcons.xcassets" / "NagramiX1.appiconset",
    )
    create_primary_icon_preview_set(
        icon_source,
        source / "Telegram" / "Telegram-iOS" / "Icons.xcassets" / "NagramiX1Preview.imageset",
    )
    for index in range(2, 9):
        source_icon = icon_sources / f"{index}.png"
        if not source_icon.exists():
            raise SystemExit(f"Missing NagramiX icon source: {source_icon}")
        icon_name = f"NagramiX{index}"
        destination = source / "Telegram" / "Telegram-iOS" / f"{icon_name}.alticon"
        destination.mkdir(parents=True, exist_ok=True)
        for suffix, size in ALTERNATE_ICON_SIZES.items():
            resize_icon(source_icon, destination / f"{icon_name}{suffix}", size)

    apply_features(source)

    print(f"Generated configuration: {args.configuration}")
    print(f"Applied NagramiX primary icon and picker preview from: {icon_source}")
    print("Applied 8 consistently prepared NagramiX system app icons")


if __name__ == "__main__":
    main()
