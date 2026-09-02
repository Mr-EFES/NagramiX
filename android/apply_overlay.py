#!/usr/bin/env python3
"""Apply NagramiX Android sources to pinned official Telegram Android."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
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


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    env = load_env(ROOT / "android" / "upstream.env")
    actual_ref = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual_ref != env["TELEGRAM_ANDROID_REF"]:
        raise RuntimeError(
            f"Android source is {actual_ref}, expected official Telegram pin "
            f"{env['TELEGRAM_ANDROID_REF']}"
        )

    properties = source / "gradle.properties"
    replace_exact(properties, "APP_VERSION_CODE=7038", f"APP_VERSION_CODE={env['NAGRAMIX_ANDROID_VERSION_CODE']}")
    replace_exact(properties, "APP_VERSION_NAME=12.10.1", f"APP_VERSION_NAME={env['NAGRAMIX_ANDROID_VERSION']}")
    replace_exact(properties, "APP_PACKAGE=org.telegram.messenger", f"APP_PACKAGE={env['NAGRAMIX_ANDROID_PACKAGE']}")

    core_gradle = source / "TMessagesProj" / "build.gradle"
    replace_exact(
        core_gradle,
        "apply plugin: 'com.android.library'",
        "apply plugin: 'com.android.library'\napply plugin: 'kotlin-android'",
    )
    replace_exact(
        core_gradle,
        "    implementation 'androidx.core:core:1.16.0'",
        "    implementation 'androidx.core:core:1.16.0'\n    implementation 'org.jetbrains.kotlin:kotlin-stdlib:2.1.0'",
    )
    replace_exact(
        core_gradle,
        "        targetSdkVersion 36\n\n        vectorDrawables.generatedDensities",
        "        targetSdkVersion 36\n\n"
        "        buildConfigField \"int\", \"NAGRAMIX_APP_ID\", getProps(\"TELEGRAM_APP_ID\")\n"
        "        buildConfigField \"String\", \"NAGRAMIX_APP_HASH\", \"\\\"\" + getProps(\"TELEGRAM_APP_HASH\") + \"\\\"\"\n\n"
        "        vectorDrawables.generatedDensities",
    )

    build_vars = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "BuildVars.java"
    replace_exact(build_vars, "    public static int APP_ID = 4;", "    public static int APP_ID = BuildConfig.NAGRAMIX_APP_ID;")
    replace_exact(build_vars, '    public static String APP_HASH = "014b35b6184100b085b0d0572f9b5103";', "    public static String APP_HASH = BuildConfig.NAGRAMIX_APP_HASH;")
    replace_exact(build_vars, "    public static boolean CHECK_UPDATES = true;", "    public static boolean CHECK_UPDATES = false;")
    replace_exact(build_vars, "    public static boolean SUPPORTS_PASSKEYS = true;", "    public static boolean SUPPORTS_PASSKEYS = false;")

    app_gradle = source / "TMessagesProj_App" / "build.gradle"
    replace_exact(app_gradle, "\n\napply plugin: 'com.google.gms.google-services'", "")
    replace_exact(
        app_gradle,
        '        debug {\n            storeFile file("../TMessagesProj/config/release.keystore")\n            storePassword RELEASE_STORE_PASSWORD\n            keyAlias RELEASE_KEY_ALIAS\n            keyPassword RELEASE_KEY_PASSWORD\n        }',
        '        debug {\n            storeFile file(System.getProperty("user.home") + "/.android/debug.keystore")\n            storePassword "android"\n            keyAlias "androiddebugkey"\n            keyPassword "android"\n        }',
    )
    replace_exact(app_gradle, "            signingConfig signingConfigs.debug\n            applicationIdSuffix \".beta\"", "            signingConfig signingConfigs.debug\n            // No suffix: NagramiX owns a separate package id.")
    replace_exact(
        app_gradle,
        '        afat {\n            ndk {\n                abiFilters "armeabi-v7a", "arm64-v8a", "x86", "x86_64"',
        '        afat {\n            ndk {\n                abiFilters "arm64-v8a"',
    )

    resource_root = source / "TMessagesProj" / "src" / "main" / "res"
    copy(ROOT / "android" / "Sources" / "strings_nagramix.xml", resource_root / "values" / "strings_nagramix.xml")
    copy(ROOT / "android" / "Sources" / "strings_nagramix_ru.xml", resource_root / "values-ru" / "strings_nagramix.xml")
    copy(
        ROOT / "android" / "Sources" / "NagramiXSettings.kt",
        source / "TMessagesProj" / "src" / "main" / "java" / "com" / "mr_efes" / "nagramix" / "NagramiXSettings.kt",
    )
    copy(
        ROOT / "android" / "Sources" / "NagramiXSettingsActivity.java",
        source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "NagramiXSettingsActivity.java",
    )

    settings_activity = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "SettingsActivity.java"
    replace_exact(
        settings_activity,
        "        items.add(SettingCell.Factory.of(10, IconBackgroundColors.PURPLE.top, IconBackgroundColors.PURPLE.bottom, R.drawable.settings_language, getString(R.string.SettingsLanguage), LocaleController.getCurrentLanguageName()));",
        "        items.add(SettingCell.Factory.of(10, IconBackgroundColors.PURPLE.top, IconBackgroundColors.PURPLE.bottom, R.drawable.settings_language, getString(R.string.SettingsLanguage), LocaleController.getCurrentLanguageName()));\n"
        "        items.add(SettingCell.Factory.of(24, IconBackgroundColors.BLUE_ALT.top, IconBackgroundColors.BLUE_ALT.bottom, R.drawable.settings_features, getString(R.string.NagramiXSettingsTitle)));",
    )
    replace_exact(
        settings_activity,
        "            case 10:\n                presentSettingFragment(new LanguageSelectActivity());\n                break;",
        "            case 10:\n                presentSettingFragment(new LanguageSelectActivity());\n                break;\n"
        "            case 24:\n                presentSettingFragment(new NagramiXSettingsActivity());\n                break;",
    )
    copy(ROOT / "android" / "branding" / "AppIcons" / "1.png", resource_root / "drawable-nodpi" / "nagramix_app_icon.png")

    manifests = [
        source / "TMessagesProj" / "config" / "debug" / "AndroidManifest.xml",
        source / "TMessagesProj" / "config" / "debug" / "AndroidManifest_SDK23.xml",
        source / "TMessagesProj" / "config" / "release" / "AndroidManifest.xml",
        source / "TMessagesProj" / "config" / "release" / "AndroidManifest_SDK23.xml",
        source / "TMessagesProj" / "config" / "release" / "AndroidManifest_standalone.xml",
    ]
    for manifest in manifests:
        content = manifest.read_text(encoding="utf-8")
        label_count = content.count('android:label="@string/AppName"') + content.count('android:label="@string/AppNameBeta"')
        if label_count != 1:
            raise RuntimeError(f"Expected one application label in {manifest}; found {label_count}")
        content = content.replace('android:label="@string/AppNameBeta"', 'android:label="@string/NagramiXAppName"')
        content = content.replace('android:label="@string/AppName"', 'android:label="@string/NagramiXAppName"')
        content = content.replace('android:icon="@mipmap/ic_launcher"', 'android:icon="@drawable/nagramix_app_icon"')
        content = content.replace('android:roundIcon="@mipmap/ic_launcher_round"', 'android:roundIcon="@drawable/nagramix_app_icon"')
        manifest.write_text(content, encoding="utf-8")

    print(
        "Applied NagramiX Android foundation "
        f"{env['NAGRAMIX_ANDROID_VERSION']} to official Telegram Android "
        f"{env['TELEGRAM_ANDROID_VERSION']} ({actual_ref})"
    )


if __name__ == "__main__":
    main()
