#!/usr/bin/env python3
"""Check rendered debug labels against bundled RU/EN strings on the pinned base."""
import argparse
import json
from pathlib import Path
import re


def strings(path):
    pairs = re.findall(r'^"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)";', path.read_text(), re.M)
    decoded = [(json.loads('"' + k + '"'), json.loads('"' + v + '"')) for k, v in pairs]
    assert len(dict(decoded)) == len(decoded), f"Duplicate key: {path}"
    return dict(decoded)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    resources = args.source / "submodules/NagramiXCore/Resources"
    ru = strings(resources / "ru.lproj/Localizable.strings")
    en = strings(resources / "en.lproj/Localizable.strings")
    keys = set()
    for name in ("DebugController.swift", "DebugAccountsController.swift"):
        text = (args.source / "submodules/DebugSettingsUI/Sources" / name).read_text()
        for literal in re.findall(r'nagramiXDebugLocalized\("((?:[^"\\]|\\.)*)"\)', text):
            # Account IDs are numeric runtime values, not translatable text.
            if literal.startswith(r"\("):
                continue
            english = json.loads('"' + literal + '"')
            key = "NagramiX.Debug." + english
            assert key in ru and ru[key].strip(), f"Missing Russian debug label: {english}"
            assert english.count("%@") == ru[key].count("%@"), key
            if "%@" in english:
                assert en.get(key) == english
            keys.add(key)
        assert '.genericSuccess("' not in text, "Untranslated status message"
        assert 'text: "Preparation failed.' not in text
    assert "NagramiX.Debug.Use Modern Video Message Pipeline" in keys
    assert "NagramiX.Debug.Send Profile Logs" in keys
    print(f"PASS: {len(keys)} static debug labels/status templates have Russian translations; format arguments preserved")


if __name__ == "__main__":
    main()
