#!/usr/bin/env python3
"""Проверить интеграцию PiP-жестов, обратимость и отказ без частичной записи."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "submodules/GalleryUI/Sources/"
NAMES = [PREFIX + name for name in (
    "GalleryControllerNode.swift", "GalleryPagerNode.swift", "GalleryItemNode.swift",
    "Items/UniversalVideoGalleryItem.swift",
)]


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def validate(before: Path, after: Path) -> dict:
    previous, current = hashes(before), hashes(after)
    assert previous.keys() == current.keys()
    changed = sorted(name for name in previous if previous[name] != current[name])
    locales = [f"submodules/NagramiXCore/Resources/{language}.lproj/Localizable.strings" for language in ("ru", "en")]
    assert changed == sorted(NAMES + locales), changed
    copy_line = re.compile(r'^"NagramiX\.Settings\.Video\.PiPSwipe\.Info"\s*=\s*"(?:[^"\\]|\\.)*";\s*$', re.M)
    for name in locales:
        old, new = (before / name).read_text(), (after / name).read_text()
        assert len(copy_line.findall(old)) == len(copy_line.findall(new)) == 1
        assert copy_line.sub("PI_P_SWIPE_DESCRIPTION", old) == copy_line.sub("PI_P_SWIPE_DESCRIPTION", new)
        assert new == (ROOT / "ios/Sources/NagramiXCore/Resources" / Path(name).relative_to("submodules/NagramiXCore/Resources")).read_text()
    module_text = (ROOT / "ios/apply_features.py").read_text()
    tree = ast.parse(module_text)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "apply_directional_swipe_picture_in_picture")
    values = {n.targets[0].id: ast.literal_eval(n.value) for n in function.body
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
              and n.targets[0].id in ("guards", "patches")}
    assert values["guards"] == {name: previous[name] for name in NAMES}
    templates = {
        "__CONTROLLER_METHODS__": ROOT / "ios/Sources/GalleryUI/NagramiXDirectionalPiPGesture.swift.inc",
        "__REQUEST_METHODS__": ROOT / "ios/Sources/GalleryUI/NagramiXDirectionalPiPRequest.swift.inc",
    }
    restored = {name: (after / name).read_text() for name in NAMES}
    for name, old, new in reversed(values["patches"]):
        for marker, path in templates.items():
            new = new.replace(marker, path.read_text().rstrip("\n") + "\n\n")
        assert restored[name].count(new) == 1, (name, new[:90])
        restored[name] = restored[name].replace(new, old, 1)
    assert all(restored[name].encode() == (before / name).read_bytes() for name in NAMES)

    entry = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_features")
    calls = [n.func.id for n in ast.walk(entry) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert calls.count("apply_directional_swipe_picture_in_picture") == 1
    assert calls.index("apply_background_transaction_lifetime") < calls.index("apply_directional_swipe_picture_in_picture")

    spec = importlib.util.spec_from_file_location("directional_pip_overlay", ROOT / "ios/apply_features.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = 0
    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory) / "native"
        overlay = Path(directory) / "ios"
        for path in templates.values():
            target = overlay / path.relative_to(ROOT / "ios")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        def seed():
            for name in NAMES:
                path = fixture / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((before / name).read_bytes())
        seed()
        module.apply_directional_swipe_picture_in_picture(fixture, overlay)
        assert all((fixture / name).read_bytes() == (after / name).read_bytes() for name in NAMES)
        def reject():
            nonlocal rejected
            initial = hashes(fixture)
            try:
                module.apply_directional_swipe_picture_in_picture(fixture, overlay)
            except (SystemExit, FileNotFoundError):
                assert hashes(fixture) == initial
                rejected += 1
            else:
                raise AssertionError("Повреждённый/повторный вход принят")
        reject()
        for name in NAMES:
            seed()
            with (fixture / name).open("ab") as file:
                file.write(b"\n// drift\n")
            reject()
        for template in templates.values():
            seed()
            target = overlay / template.relative_to(ROOT / "ios")
            target.unlink()
            reject()
            shutil.copyfile(template, target)
    return {"outputs": len(previous), "changed": changed,
            "byte_identical": len(previous) - len(changed), "exact_reverse_patches": len(values["patches"]),
            "rejected_without_partial_writes": rejected, "patch_integration": "PASS",
            "native_compile": "pending", "physical_device": "pending"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = json.dumps(validate(args.before, args.after), ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(result)
    print(result, end="")
