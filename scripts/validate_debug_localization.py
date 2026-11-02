#!/usr/bin/env python3
"""Check rendered debug labels against bundled RU/EN strings on the pinned base."""
import argparse
import json
from pathlib import Path
import re


# Reviewed diagnostic identifiers, paths, payload literals and enum keys.
# New UI strings must use localization rather than expand this list.
REVIEWED_RAW = json.loads(r'''
{
  "DebugController.swift": [
    "",
    "------ Additional Info ------\\n",
    "------ File: \\(name) ------\\n",
    "/",
    "/Documents/importcompleted",
    "/group-calls",
    "/logs/\\(type)",
    "/logs/notification-logs",
    "/logs/profile-logs",
    "/logs/share-logs",
    "/postbox",
    "/postbox/db",
    "1234",
    "123456",
    "All Logs",
    "CFBundleShortVersionString",
    "Chat/Context Menu/Back",
    "Chat/Context Menu/Telegram",
    "Critical Logs",
    "Group Call Logs",
    "HD · Bilinear",
    "HD · Lanczos",
    "Item List/Icons/Email",
    "Latest Logs",
    "Legacy",
    "Log-\\(type).txt",
    "Log-iOS-All.txt.zip",
    "Log-iOS-Full.txt.zip",
    "Log-iOS-Short.txt",
    "Log.txt",
    "Logs",
    "Notification Logs",
    "Profiles-iOS.txt.zip",
    "Profiles.txt",
    "Share Logs",
    "Storage Stats",
    "StorageReport.txt",
    "VGA (640×480)",
    "\\(additionalInfo)",
    "\\n",
    "app-logs",
    "application/text",
    "application/zip",
    "broadcast-logs",
    "destination.zip",
    "dev",
    "group.\\(Bundle.main.bundleIdentifier!)",
    "importstickers",
    "ios_display_pwa",
    "ios_killswitch_disable_neo_round_camera_v2",
    "json",
    "lock",
    "log-",
    "log-cpu-profile-\\(dateFormatter.string(from: Date())).txt",
    "notification-logs",
    "notificationcontent-logs",
    "org.telegram.third-party.stickerset",
    "qwerty",
    "siri-logs",
    "title",
    "widget-logs",
    "yyyy-MM-dd_HH-mm-ss"
  ],
  "DebugAccountsController.swift": [],
  "CrashReportsController.swift": [
    "",
    " (@\\(username))",
    " (Simulator)",
    "CFBundleShortVersionString",
    "CFBundleVersion",
    "Chat/Context Menu/Delete",
    "Chat/Context Menu/File",
    "Chat/Context Menu/Forward",
    "CrashReport-\\(report.id.prefix(12)).zip",
    "SIMULATOR_MODEL_IDENTIFIER",
    "Unknown",
    "\\(report.metadata.applicationVersion) (\\(report.metadata.buildVersion))",
    "alertsInfo",
    "application/zip",
    "arm64",
    "crash.json",
    "NagramiX_bot",
    "information",
    "init(coder:) has not been implemented",
    "metadata.json",
    "org.telegram.crash-report-ui",
    "report.txt",
    "report.zip",
    "reportsHeader",
    "showAlerts",
    "unknown",
    "x86_64"
  ]
}
''')

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
    for name in ("DebugController.swift", "DebugAccountsController.swift", "CrashReportsController.swift"):
        text = (args.source / "submodules/DebugSettingsUI/Sources" / name).read_text()
        stripped = re.sub(r'nagramiXDebugLocalized\("((?:[^"\\]|\\.)*)"\)', 'LOCALIZED', text)
        raw_literals = set(re.findall(r'"((?:[^"\\]|\\.)*)"', stripped))
        assert raw_literals <= set(REVIEWED_RAW[name]), f"Unreviewed/untranslated UI in {name}: {raw_literals - set(REVIEWED_RAW[name])}"
        literals = re.findall(r'nagramiXDebugLocalized\("((?:[^"\\]|\\.)*)"\)', text)
        if name == "DebugController.swift":
            # Enum values remain stable; every display site localizes them.
            literals += re.findall(r'return "([^"\n]+)"', text[:text.index("    func perform(arguments:")])
            assert "nagramiXDebugLocalized(option.title)" in text
            assert "nagramiXDebugLocalized(value.debugTitle)" in text
            assert "nagramiXDebugLocalized(mode.debugTitle)" in text
        for literal in literals:
            # Account IDs are numeric runtime values, not translatable text.
            if literal.startswith(r"\("):
                continue
            english = json.loads('"' + literal + '"')
            key = "NagramiX.Debug." + english
            assert key in ru and ru[key].strip(), f"Missing Russian debug label: {english}"
            placeholders = lambda value: re.findall(r'%(?:[0-9]+\$)?[@dfius]', value)
            assert placeholders(english) == placeholders(ru[key]), key
            assert re.search('[А-Яа-яЁё]', ru[key]) or english in {"JPEG X", "VGA (640×480)"}, key
            if "%@" in english:
                assert en.get(key) == english
            keys.add(key)
        assert '.genericSuccess("' not in text, "Untranslated status message"
        assert 'text: "Preparation failed.' not in text
    assert "NagramiX.Debug.Use Modern Video Message Pipeline" in keys
    assert "NagramiX.Debug.Send Profile Logs" in keys
    controller = (args.source / "submodules/DebugSettingsUI/Sources/DebugController.swift").read_text()
    assert "Telegram for iOS" not in controller
    assert 'nagramiXDebugLocalized("NagramiX for iOS %@ (%@)\\n%@")' in controller
    assert 'import NagramiXCore' in (args.source / "submodules/DebugSettingsUI/Sources/CrashReportsController.swift").read_text()
    print(f"PASS: {len(keys)} debug UI labels/templates including dynamic menus and crash reports have Russian translations; branding/format arguments preserved")


if __name__ == "__main__":
    main()
