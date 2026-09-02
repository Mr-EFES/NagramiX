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

    main_tabs_activity = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "MainTabsActivity.java"
    replace_exact(
        main_tabs_activity,
        "import org.telegram.ui.Components.chat.ViewPositionWatcher;",
        "import org.telegram.ui.Components.chat.ViewPositionWatcher;\n\n"
        "import com.mr_efes.nagramix.NagramiXSettings;",
    )

    dialogs_activity = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "DialogsActivity.java"
    replace_exact(
        dialogs_activity,
        "import org.telegram.ui.Components.chat.ViewPositionWatcher;",
        "import org.telegram.ui.Components.chat.ViewPositionWatcher;\n\n"
        "import com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        dialogs_activity,
        "        searchItem.setVisibility(View.GONE);\n\n"
        "        if (!onlySelect && searchString == null && folderId == 0 && communityId == 0) {",
        "        checkUi_nagramixSearchButton();\n\n"
        "        if (!onlySelect && searchString == null && folderId == 0 && communityId == 0) {",
    )
    replace_exact(
        dialogs_activity,
        "            updateStatus(UserConfig.getInstance(account).getCurrentUser(), true);\n"
        "        } else if (id == NotificationCenter.appDidLogout) {",
        "            updateStatus(UserConfig.getInstance(account).getCurrentUser(), true);\n"
        "            checkUi_nagramixSearchButton();\n"
        "            updateStoriesVisibility(true);\n"
        "        } else if (id == NotificationCenter.appDidLogout) {",
    )
    replace_exact(
        dialogs_activity,
        "        if (!show) {\n"
        "            initialSearchType = -1;\n"
        "        }",
        "        if (!show) {\n"
        "            initialSearchType = -1;\n"
        "            checkUi_nagramixSearchButton();\n"
        "        }",
    )
    replace_exact(
        dialogs_activity,
        "    private void checkSuggestClearDatabase() {",
        "    private void checkUi_nagramixSearchButton() {\n"
        "        if (searchItem == null) {\n"
        "            return;\n"
        "        }\n"
        "        boolean eligible = initialDialogsType == DIALOGS_TYPE_DEFAULT && !isArchive() && !onlySelect && searchString == null && folderId == 0 && communityId == 0;\n"
        "        boolean visible = NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.SHOW_SEARCH_TAB, false);\n"
        "        searchItem.setVisibility(eligible && visible ? View.VISIBLE : View.GONE);\n"
        "    }\n\n"
        "    private void checkSuggestClearDatabase() {",
    )
    replace_exact(
        dialogs_activity,
        "        hasOnlySlefStories = onlySelfStories;\n\n"
        "        boolean oldStoriesCellVisibility = dialogStoriesCellVisible;",
        "        if (NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.HIDE_STORIES, false)) {\n"
        "            onlySelfStories = false;\n"
        "            newVisibility = false;\n"
        "        }\n\n"
        "        hasOnlySlefStories = onlySelfStories;\n\n"
        "        boolean oldStoriesCellVisibility = dialogStoriesCellVisible;",
    )

    voip_service = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "voip" / "VoIPService.java"
    replace_exact(
        voip_service,
        "import android.app.NotificationChannel;",
        "import android.app.NotificationChannel;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        voip_service,
        "\t\t\tfinal Instance.Config config = new Instance.Config(initializationTimeout, receiveTimeout, voipDataSaving, privateCall.p2p_allowed, enableAec, enableNs, true, false, serverConfig.enableStunMarking, logFilePath, statsLogFilePath, privateCall.protocol.max_layer, privateCall.custom_parameters == null ? \"\" : privateCall.custom_parameters.data);",
        "\t\t\tfinal boolean forceTcp = NagramiXSettings.INSTANCE.preferences(this).getBoolean(NagramiXSettings.FORCE_TCP_CALLS, false);\n"
        "\t\t\tfinal Instance.Config config = new Instance.Config(initializationTimeout, receiveTimeout, voipDataSaving, forceTcp ? false : privateCall.p2p_allowed, enableAec, enableNs, true, false, serverConfig.enableStunMarking, logFilePath, statsLogFilePath, privateCall.protocol.max_layer, privateCall.custom_parameters == null ? \"\" : privateCall.custom_parameters.data);",
    )
    replace_exact(
        voip_service,
        "\t\t\tfinal boolean forceTcp = preferences.getBoolean(\"dbg_force_tcp_in_calls\", false);\n",
        "",
    )

    instant_camera = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Components" / "InstantCameraView.java"
    replace_exact(
        instant_camera,
        "import com.google.android.exoplayer2.ExoPlayer;",
        "import com.google.android.exoplayer2.ExoPlayer;\n\n"
        "import com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        instant_camera,
        "        if (!fromPaused) {\n"
        "            if (!useCamera2) {\n"
        "                isFrontface = true;\n"
        "            }\n"
        "            updateFlash();",
        "        if (!fromPaused) {\n"
        "            isFrontface = !NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.REAR_VIDEO_MESSAGES, false);\n"
        "            updateFlash();",
    )

    dialog_stories = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Stories" / "DialogStoriesCell.java"
    replace_exact(
        dialog_stories,
        "import org.telegram.ui.ActionBar.AlertDialog;",
        "import org.telegram.ui.ActionBar.AlertDialog;\n\n"
        "import com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(dialog_stories, "            openStoryForCell(cell, false);", "            openStoryForCell(cell, false, false);")
    replace_exact(
        dialog_stories,
        "    public void openStoryForCell(StoryCell cell) {\n"
        "        openStoryForCell(cell, false);\n"
        "    }\n\n"
        "    private void openStoryForCell(StoryCell cell, boolean overscroll) {",
        "    public void openStoryForCell(StoryCell cell) {\n"
        "        openStoryForCell(cell, false, false);\n"
        "    }\n\n"
        "    private void openStoryForCell(StoryCell cell, boolean overscroll, boolean confirmed) {",
    )
    replace_exact(
        dialog_stories,
        "        try {\n"
        "            performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);",
        "        if (!confirmed && !cell.isSelf && storiesController.hasUnreadStories(cell.dialogId)\n"
        "                && NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.CONFIRM_STORY_VIEWING, false)) {\n"
        "            new AlertDialog.Builder(getContext(), fragment != null ? fragment.getResourceProvider() : null)\n"
        "                    .setTitle(getString(R.string.NagramiXStoryViewConfirmTitle))\n"
        "                    .setMessage(getString(R.string.NagramiXStoryViewConfirmText))\n"
        "                    .setNegativeButton(getString(R.string.Cancel), null)\n"
        "                    .setPositiveButton(getString(R.string.NagramiXStoryViewConfirmAction), (dialog, which) -> openStoryForCell(cell, overscroll, true))\n"
        "                    .show();\n"
        "            return;\n"
        "        }\n"
        "        try {\n"
        "            performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);",
    )
    replace_exact(dialog_stories, "        openStoryForCell(overscrollSelectedView, true);", "        openStoryForCell(overscrollSelectedView, true, false);")

    peer_stories = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Stories" / "PeerStoriesView.java"
    replace_exact(
        peer_stories,
        "import org.telegram.messenger.AccountInstance;",
        "import org.telegram.messenger.AccountInstance;\n\n"
        "import com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        peer_stories,
        "                allowRepost = allowShare;",
        "                allowRepost = allowShare && NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.ENABLE_STORY_REPOST, false);",
    )
    replace_exact(
        voip_service,
        "\t\t\tif (forceTcp) {\n"
        "\t\t\t\tAndroidUtilities.runOnUIThread(() -> Toast.makeText(VoIPService.this, \"This call uses TCP which will degrade its quality.\", Toast.LENGTH_SHORT).show());\n"
        "\t\t\t}\n\n",
        "",
    )
    replace_exact(
        main_tabs_activity,
        "        checkUi_callTabVisible(getUserConfig().showCallsTab, false);",
        "        checkUi_callTabVisible(getUserConfig().showCallsTab, false);\n"
        "        checkUi_nagramixTabs(false);",
    )
    replace_exact(
        main_tabs_activity,
        "        if (id == NotificationCenter.notificationsCountUpdated || id == NotificationCenter.updateInterfaces) {\n"
        "            checkUnreadCount(fragmentView != null && fragmentView.isAttachedToWindow());",
        "        if (id == NotificationCenter.notificationsCountUpdated || id == NotificationCenter.updateInterfaces) {\n"
        "            checkUnreadCount(fragmentView != null && fragmentView.isAttachedToWindow());\n"
        "            checkUi_nagramixTabs(true);",
    )
    replace_exact(
        main_tabs_activity,
        "    private void checkUi_callTabVisible(boolean callTabsVisible, boolean animated) {\n"
        "        if (tabsView != null) {",
        "    private void checkUi_nagramixTabs(boolean animated) {\n"
        "        if (tabsView == null || tabs == null) {\n"
        "            return;\n"
        "        }\n"
        "        boolean hideContacts = NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.HIDE_CONTACTS_TAB, true);\n"
        "        boolean showTitles = NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.SHOW_TAB_TITLES, true);\n"
        "        tabsView.setViewVisible(tabs[INDEX_CONTACTS], !hideContacts, animated);\n"
        "        tabs[INDEX_CHATS].setText(showTitles ? getString(R.string.MainTabsChats) : \"\");\n"
        "        tabs[INDEX_CONTACTS].setText(showTitles ? getString(R.string.MainTabsContacts) : \"\");\n"
        "        tabs[INDEX_SETTINGS].setText(showTitles ? getString(R.string.Settings) : \"\");\n"
        "        tabs[INDEX_CALLS].setText(showTitles ? getString(R.string.MainTabsCalls) : \"\");\n"
        "        tabs[INDEX_PROFILE].setText(showTitles ? getString(R.string.MainTabsProfile) : \"\");\n"
        "        checkUi_callTabVisible(getUserConfig().showCallsTab, animated);\n"
        "    }\n\n"
        "    private void checkUi_callTabVisible(boolean callTabsVisible, boolean animated) {\n"
        "        callTabsVisible = callTabsVisible && !NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.HIDE_CALLS_TAB, true);\n"
        "        if (tabsView != null) {",
    )
    replace_exact(
        main_tabs_activity,
        "        } else if (position == POSITION_CALLS_OR_SETTINGS) {\n"
        "            if (getUserConfig().showCallsTab) {",
        "        } else if (position == POSITION_CALLS_OR_SETTINGS) {\n"
        "            if (getUserConfig().showCallsTab && !NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.HIDE_CALLS_TAB, true)) {",
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
