#!/usr/bin/env python3
"""Apply the tracked NagramiX Android overlay to pinned NagramX sources."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key or not value:
            raise RuntimeError(f"Invalid environment entry in {path}: {raw_line!r}")
        values[key] = value
    return values


def replace_exact(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one anchor in {path}: {old!r}; found {count}")
    path.write_text(content.replace(old, new), encoding="utf-8")


def require_text(path: Path, value: str) -> None:
    if value not in path.read_text(encoding="utf-8"):
        raise RuntimeError(f"Required Android parity anchor is missing from {path}: {value!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    env = load_env(ROOT / "android" / "upstream.env")
    actual_ref = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual_ref != env["NAGRAMX_REF"]:
        raise RuntimeError(
            f"Android source is {actual_ref}, expected pinned {env['NAGRAMX_REF']}"
        )

    properties = source / "gradle.properties"
    replace_exact(properties, "APP_VERSION_CODE=6991", f"APP_VERSION_CODE={env['NAGRAMIX_ANDROID_VERSION_CODE']}")
    replace_exact(properties, "APP_VERSION_NAME=12.9.2", f"APP_VERSION_NAME={env['NAGRAMIX_ANDROID_VERSION']}")
    replace_exact(properties, "APP_PACKAGE=nu.gpu.nagram", f"APP_PACKAGE={env['NAGRAMIX_ANDROID_PACKAGE']}")

    settings = source / "settings.gradle"
    replace_exact(settings, 'rootProject.name = "NagramX"', 'rootProject.name = "NagramiX-Android"')

    daemon_jvm = source / "gradle" / "gradle-daemon-jvm.properties"
    require_text(daemon_jvm, "toolchainVendor=JETBRAINS")
    require_text(daemon_jvm, "toolchainVersion=21")
    daemon_jvm.unlink()

    app_gradle = source / "TMessagesProj" / "build.gradle"
    replace_exact(app_gradle, "    id 'com.google.gms.google-services'\n", "")
    replace_exact(app_gradle, "    id 'com.google.firebase.crashlytics'\n", "")
    replace_exact(app_gradle, "def verCode = 1258", f"def verCode = {env['NAGRAMIX_ANDROID_VERSION_CODE']}")
    replace_exact(app_gradle, "            String gramName = 'NagramX'", "            String gramName = 'NagramiX'")
    replace_exact(
        app_gradle,
        "        debug {\n            isDefault = true\n            debuggable = true\n            jniDebuggable = true\n            multiDexEnabled = true\n            signingConfig = signingConfigs.release\n        }",
        "        debug {\n            isDefault = true\n            debuggable = true\n            jniDebuggable = true\n            multiDexEnabled = true\n        }",
    )

    strings = source / "TMessagesProj" / "src" / "main" / "res" / "values" / "strings.xml"
    replace_exact(strings, '<string name="AppName">Nagram X</string>', '<string name="AppName">NagramiX</string>')
    nax_strings = source / "TMessagesProj" / "src" / "main" / "res" / "values" / "strings_nax.xml"
    replace_exact(nax_strings, '<string name="NagramX" translatable="false">Nagram X</string>', '<string name="NagramX" translatable="false">NagramiX</string>')

    config = source / "TMessagesProj" / "src" / "main" / "kotlin" / "xyz" / "nextalone" / "nagram" / "NaConfig.kt"
    replace_exact(config, '            "Nagram X"\n        )', '            "NagramiX"\n        )')
    replace_exact(
        config,
        '    val showNoQuoteForward =\n        addConfig(\n            "NoQuoteForward",\n            ConfigItem.configTypeBool,\n            false\n        )',
        '    val showNoQuoteForward =\n        addConfig(\n            "NoQuoteForward",\n            ConfigItem.configTypeBool,\n            true\n        )',
    )
    replace_exact(
        config,
        '    val showRepeatAsCopy =\n        addConfig(\n            "RepeatAsCopy",\n            ConfigItem.configTypeBool,\n            false\n        )',
        '    val showRepeatAsCopy =\n        addConfig(\n            "RepeatAsCopy",\n            ConfigItem.configTypeBool,\n            true\n        )',
    )
    replace_exact(
        config,
        '    val hideStoriesFromHeader =\n        addConfig(\n            "HideStoriesFromHeader",\n            ConfigItem.configTypeBool,\n            true\n        )',
        '    val hideStoriesFromHeader =\n        addConfig(\n            "HideStoriesFromHeader",\n            ConfigItem.configTypeBool,\n            false\n        )',
    )
    replace_exact(
        config,
        '    val cameraInVideoMessages =\n        addConfig(\n            "CameraInVideoMessages",\n            ConfigItem.configTypeInt,\n            1 // 0: front; 1: rear; 2: ask\n        )',
        '    val cameraInVideoMessages =\n        addConfig(\n            "CameraInVideoMessages",\n            ConfigItem.configTypeInt,\n            0 // 0: front; 1: rear; 2: ask\n        )',
    )
    replace_exact(
        config,
        '    val mainTabsHideContacts =\n        addConfig(\n            "MainTabsHideContacts",\n            ConfigItem.configTypeBool,\n            false\n        )',
        '    val mainTabsHideContacts =\n        addConfig(\n            "MainTabsHideContacts",\n            ConfigItem.configTypeBool,\n            true\n        )',
    )

    feature_anchors = {
        config: [
            "EnableSaveDeletedMessages",
            "EnableSaveEditsHistory",
            "HideStoriesFromHeader",
            "CameraInVideoMessages",
            "MainTabsHideContacts",
            "NoQuoteForward",
            "RepeatAsCopy",
        ],
        source / "TMessagesProj" / "src" / "main" / "java" / "tw" / "nekomimi" / "nekogram" / "utils" / "DnsFactory.kt": [
            "DNS_TYPE_CUSTOM_DOH",
            "application/dns-message",
        ],
        source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "voip" / "VoIPService.java": [
            'preferences.getBoolean("dbg_force_tcp_in_calls", false)',
        ],
    }
    for path, anchors in feature_anchors.items():
        for anchor in anchors:
            require_text(path, anchor)

    print(
        "Applied NagramiX Android overlay "
        f"{env['NAGRAMIX_ANDROID_VERSION']} to NagramX {env['NAGRAMX_TAG']} ({actual_ref})"
    )


if __name__ == "__main__":
    main()
