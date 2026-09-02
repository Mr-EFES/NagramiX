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
    copy(
        ROOT / "android" / "Sources" / "NagramiXMessageArchive.java",
        source / "TMessagesProj" / "src" / "main" / "java" / "com" / "mr_efes" / "nagramix" / "NagramiXMessageArchive.java",
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
        "public class DialogsActivity extends BaseFragment implements NotificationCenter.NotificationCenterDelegate, FloatingDebugProvider, FactorAnimator.Target, MainTabsActivity.TabFragmentDelegate {",
        "public class DialogsActivity extends BaseFragment implements NotificationCenter.NotificationCenterDelegate, FloatingDebugProvider, FactorAnimator.Target, MainTabsActivity.TabFragmentDelegate {\n\n"
        "    public boolean nagramixCopyAsNew;",
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

    send_messages_helper = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "SendMessagesHelper.java"
    replace_exact(
        send_messages_helper,
        "    public void processForwardFromMyName(MessageObject messageObject, long did, long payStars, long monoForumPeerId, MessageSuggestionParams suggestionParams) {",
        "    public int sendMessagesAsNagramiXCopy(ArrayList<MessageObject> messages, long did, boolean notify, int scheduleDate, int scheduleRepeatPeriod, long payStars, long monoForumPeerId, MessageSuggestionParams suggestionParams) {\n"
        "        if (messages == null || messages.isEmpty()) {\n"
        "            return 0;\n"
        "        }\n"
        "        for (MessageObject message : messages) {\n"
        "            boolean text = message != null && message.messageOwner.message != null\n"
        "                    && (message.messageOwner.media == null || message.messageOwner.media instanceof TLRPC.TL_messageMediaEmpty\n"
        "                    || message.messageOwner.media instanceof TLRPC.TL_messageMediaWebPage);\n"
        "            boolean media = message != null && message.messageOwner.media != null\n"
        "                    && (message.messageOwner.media.photo instanceof TLRPC.TL_photo\n"
        "                    || message.messageOwner.media.document instanceof TLRPC.TL_document\n"
        "                    || message.messageOwner.media instanceof TLRPC.TL_messageMediaVenue\n"
        "                    || message.messageOwner.media instanceof TLRPC.TL_messageMediaGeo\n"
        "                    || message.messageOwner.media.phone_number != null);\n"
        "            if (message == null || !text && !media || message.isEphemeral() || message.messageOwner.noforwards\n"
        "                    || message.messageOwner.media instanceof TLRPC.TL_messageMediaPaidMedia) {\n"
        "                return 1;\n"
        "            }\n"
        "        }\n"
        "        HashMap<Long, Long> groupIds = new HashMap<>();\n"
        "        for (int i = 0; i < messages.size(); i++) {\n"
        "            MessageObject message = messages.get(i);\n"
        "            HashMap<String, String> copyParams = null;\n"
        "            if (message.getGroupId() != 0) {\n"
        "                long groupId = groupIds.computeIfAbsent(message.getGroupId(), ignored -> Utilities.random.nextLong());\n"
        "                copyParams = new HashMap<>();\n"
        "                copyParams.put(\"groupId\", Long.toString(groupId));\n"
        "                if (i + 1 == messages.size() || messages.get(i + 1).getGroupId() != message.getGroupId()) {\n"
        "                    copyParams.put(\"final\", \"1\");\n"
        "                }\n"
        "            }\n"
        "            processForwardFromMyName(message, did, payStars, monoForumPeerId, suggestionParams, notify, scheduleDate, scheduleRepeatPeriod, true, copyParams);\n"
        "        }\n"
        "        return 0;\n"
        "    }\n\n"
        "    public void processForwardFromMyName(MessageObject messageObject, long did, long payStars, long monoForumPeerId, MessageSuggestionParams suggestionParams) {\n"
        "        processForwardFromMyName(messageObject, did, payStars, monoForumPeerId, suggestionParams, true, 0, 0, false, null);\n"
        "    }\n\n"
        "    private void processForwardFromMyName(MessageObject messageObject, long did, long payStars, long monoForumPeerId, MessageSuggestionParams suggestionParams, boolean notify, int scheduleDate, int scheduleRepeatPeriod, boolean copyAsNew, HashMap<String, String> copyParams) {",
    )
    replace_exact(
        send_messages_helper,
        "        if (messageObject == null) {\n"
        "            return;\n"
        "        }\n"
        "        if (messageObject.messageOwner.media != null",
        "        if (messageObject == null) {\n"
        "            return;\n"
        "        }\n"
        "        MessageObject copyReply = copyAsNew ? null : messageObject.replyMessageObject;\n"
        "        int copyTtl = copyAsNew ? 0 : messageObject.messageOwner.media != null ? messageObject.messageOwner.media.ttl_seconds : 0;\n"
        "        if (messageObject.messageOwner.media != null",
    )
    replace_exact(
        send_messages_helper,
        "SendMessagesHelper.SendMessageParams.of((TLRPC.TL_photo) messageObject.messageOwner.media.photo, null, did, messageObject.replyMessageObject, null, messageObject.messageOwner.message, messageObject.messageOwner.entities, null, params, true, 0, 0, messageObject.messageOwner.media.ttl_seconds, messageObject, false)",
        "SendMessagesHelper.SendMessageParams.of((TLRPC.TL_photo) messageObject.messageOwner.media.photo, null, did, copyReply, null, messageObject.messageOwner.message, messageObject.messageOwner.entities, null, params, notify, scheduleDate, scheduleRepeatPeriod, copyTtl, messageObject, false, messageObject.hasMediaSpoilers())",
    )
    replace_exact(
        send_messages_helper,
        "SendMessagesHelper.SendMessageParams.of((TLRPC.TL_document) messageObject.messageOwner.media.document, null, messageObject.messageOwner.attachPath, did, messageObject.replyMessageObject, null, messageObject.messageOwner.message, messageObject.messageOwner.entities, null, params, true, 0, 0, messageObject.messageOwner.media.ttl_seconds, messageObject, null, false)",
        "SendMessagesHelper.SendMessageParams.of((TLRPC.TL_document) messageObject.messageOwner.media.document, null, messageObject.messageOwner.attachPath, did, copyReply, null, messageObject.messageOwner.message, messageObject.messageOwner.entities, null, params, notify, scheduleDate, scheduleRepeatPeriod, copyTtl, messageObject, null, false, messageObject.hasMediaSpoilers())",
    )
    replace_exact(
        send_messages_helper,
        "SendMessagesHelper.SendMessageParams.of(messageObject.messageOwner.media, did, messageObject.replyMessageObject, null, null, null, true, 0, 0)",
        "SendMessagesHelper.SendMessageParams.of(messageObject.messageOwner.media, did, copyReply, null, null, null, notify, scheduleDate, scheduleRepeatPeriod)",
    )
    replace_exact(
        send_messages_helper,
        "SendMessagesHelper.SendMessageParams.of(user, did, messageObject.replyMessageObject, null, null, null, true, 0, 0)",
        "SendMessagesHelper.SendMessageParams.of(user, did, copyReply, null, null, null, notify, scheduleDate, scheduleRepeatPeriod)",
    )
    replace_exact(
        send_messages_helper,
        "SendMessagesHelper.SendMessageParams.of(messageObject.messageOwner.message, did, messageObject.replyMessageObject, null, webPage, true, entities, null, null, true, 0, 0, null, false)",
        "SendMessagesHelper.SendMessageParams.of(messageObject.messageOwner.message, did, copyReply, null, webPage, true, entities, null, copyParams, notify, scheduleDate, scheduleRepeatPeriod, null, false)",
    )
    replace_exact(
        send_messages_helper,
        "            HashMap<String, String> params = null;\n"
        "            if (DialogObject.isEncryptedDialog(did) && messageObject.messageOwner.peer_id != null && (messageObject.messageOwner.media.photo instanceof TLRPC.TL_photo || messageObject.messageOwner.media.document instanceof TLRPC.TL_document)) {\n"
        "                params = new HashMap<>();",
        "            HashMap<String, String> params = copyParams == null ? null : new HashMap<>(copyParams);\n"
        "            if (DialogObject.isEncryptedDialog(did) && messageObject.messageOwner.peer_id != null && (messageObject.messageOwner.media.photo instanceof TLRPC.TL_photo || messageObject.messageOwner.media.document instanceof TLRPC.TL_document)) {\n"
        "                if (params == null) {\n"
        "                    params = new HashMap<>();\n"
        "                }",
    )
    entity_filter = """            ArrayList<TLRPC.MessageEntity> entities;
            if (messageObject.messageOwner.entities != null && !messageObject.messageOwner.entities.isEmpty()) {
                entities = new ArrayList<>();
                for (int a = 0; a < messageObject.messageOwner.entities.size(); a++) {
                    TLRPC.MessageEntity entity = messageObject.messageOwner.entities.get(a);
                    if (entity instanceof TLRPC.TL_messageEntityBold ||
                            entity instanceof TLRPC.TL_messageEntityItalic ||
                            entity instanceof TLRPC.TL_messageEntityPre ||
                            entity instanceof TLRPC.TL_messageEntityCode ||
                            entity instanceof TLRPC.TL_messageEntityTextUrl ||
                            entity instanceof TLRPC.TL_messageEntitySpoiler ||
                            entity instanceof TLRPC.TL_messageEntityCustomEmoji) {
                        entities.add(entity);
                    }
                }
            } else {
                entities = null;
            }
"""
    replace_exact(
        send_messages_helper,
        entity_filter,
        "            ArrayList<TLRPC.MessageEntity> entities = messageObject.messageOwner.entities == null\n"
        "                    ? null : new ArrayList<>(messageObject.messageOwner.entities);\n",
    )

    chat_activity = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "ChatActivity.java"
    replace_exact(
        chat_activity,
        "    public final static int OPTION_ADD_TO_TODO = 110;",
        "    public final static int OPTION_ADD_TO_TODO = 110;\n"
        "    public final static int OPTION_NAGRAMIX_FORWARD_COPY = 111;\n"
        "    public final static int OPTION_NAGRAMIX_EDIT_HISTORY = 112;",
    )
    replace_exact(
        chat_activity,
        "    public MessagePreviewParams messagePreviewParams;",
        "    public MessagePreviewParams messagePreviewParams;\n"
        "    private boolean nagramixForwardPanelAsCopy;",
    )
    replace_exact(
        chat_activity,
        "                final boolean canForward = !selectedObject.isSponsored()",
        "                if (!com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).revisions(dialog_id, selectedObject.getId()).isEmpty()) {\n"
        "                    items.add(LocaleController.getString(R.string.NagramiXEditHistoryTitle));\n"
        "                    options.add(OPTION_NAGRAMIX_EDIT_HISTORY);\n"
        "                    icons.add(R.drawable.msg_edit);\n"
        "                }\n\n"
        "                final boolean canForward = !selectedObject.isSponsored()",
    )
    replace_exact(
        chat_activity,
        "                if (canForward) {\n"
        "                    items.add(LocaleController.getString(R.string.Forward));\n"
        "                    options.add(OPTION_FORWARD);\n"
        "                    icons.add(R.drawable.msg_forward);\n"
        "                }",
        "                if (canForward) {\n"
        "                    items.add(LocaleController.getString(R.string.Forward));\n"
        "                    options.add(OPTION_FORWARD);\n"
        "                    icons.add(R.drawable.msg_forward);\n"
        "                    items.add(LocaleController.getString(R.string.NagramiXForwardAsCopy));\n"
        "                    options.add(OPTION_NAGRAMIX_FORWARD_COPY);\n"
        "                    icons.add(R.drawable.msg_copy);\n"
        "                }",
    )
    forward_case = """            case OPTION_FORWARD: {
                if (getMessagesController().isFrozen()) {
                    AccountFrozenAlert.show(currentAccount);
                    selectedObject = null;
                    selectedObjectToEditCaption = null;
                    selectedObjectGroup = null;
                    return;
                }
                forwardingMessage = selectedObject;
                forwardingMessageGroup = selectedObjectGroup;
                Bundle args = new Bundle();
                args.putBoolean("onlySelect", true);
                args.putInt("dialogsType", DialogsActivity.DIALOGS_TYPE_FORWARD);
                args.putInt("messagesCount", 1);
                args.putInt("hasPoll", forwardingMessage.isTodo() ? 3 : forwardingMessage.isPoll() ? (forwardingMessage.isPublicPoll() ? 2 : 1) : 0);
                if (ChatObject.isMonoForum(currentChat) && ChatObject.canManageMonoForum(currentAccount, currentChat) && currentChat.linked_monoforum_id != 0) {
                    args.putLong("forward_into_channel", -currentChat.linked_monoforum_id);
                }
                args.putBoolean("hasInvoice", forwardingMessage.isInvoice());
                args.putBoolean("canSelectTopics", true);
                DialogsActivity fragment = new DialogsActivity(args);
                fragment.setDelegate(this);
                presentFragment(fragment);
                break;
            }
"""
    copy_case = forward_case.replace("OPTION_FORWARD", "OPTION_NAGRAMIX_FORWARD_COPY", 1).replace(
        "                fragment.setDelegate(this);",
        "                fragment.nagramixCopyAsNew = true;\n                fragment.setDelegate(this);",
    )
    history_case = """            case OPTION_NAGRAMIX_EDIT_HISTORY: {
                ArrayList<TLRPC.Message> revisions = com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).revisions(dialog_id, selectedObject.getId());
                CharSequence[] entries = new CharSequence[revisions.size()];
                for (int i = 0; i < revisions.size(); i++) {
                    TLRPC.Message revision = revisions.get(i);
                    int timestamp = revision.edit_date != 0 ? revision.edit_date : revision.date;
                    entries[i] = LocaleController.formatDateTime(timestamp, false) + "\\n" + revision.message;
                }
                AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity(), themeDelegate);
                builder.setTitle(LocaleController.getString(R.string.NagramiXEditHistoryTitle));
                builder.setItems(entries, (dialog, which) -> AndroidUtilities.addToClipboard(revisions.get(which).message));
                showDialog(builder.create());
                break;
            }
"""
    replace_exact(chat_activity, forward_case, forward_case + history_case + copy_case)
    replace_exact(
        chat_activity,
        "            case OPTION_DELETE: {\n                if (getParentActivity() == null) {",
        "            case OPTION_DELETE: {\n"
        "                if (selectedObject != null && com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).isDeleted(dialog_id, selectedObject.getId())) {\n"
        "                    int localId = selectedObject.getId();\n"
        "                    com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).remove(dialog_id, localId);\n"
        "                    ArrayList<Integer> localIds = new ArrayList<>();\n"
        "                    localIds.add(localId);\n"
        "                    processDeletedMessages(localIds, 0, false);\n"
        "                    break;\n"
        "                }\n"
        "                if (getParentActivity() == null) {",
    )
    replace_exact(
        chat_activity,
        "                    getSendMessagesHelper().sendMessage(fmessages, did, false, false, notify, scheduleDate, scheduleRepeatPeriod, null, -1, price == null ? 0 : price, getSendMonoForumPeerId(), getSendMessageSuggestionParams());",
        "                    if (fragment.nagramixCopyAsNew) {\n"
        "                        getSendMessagesHelper().sendMessagesAsNagramiXCopy(fmessages, did, notify, scheduleDate, scheduleRepeatPeriod, price == null ? 0 : price, getSendMonoForumPeerId(), getSendMessageSuggestionParams());\n"
        "                    } else {\n"
        "                        getSendMessagesHelper().sendMessage(fmessages, did, false, false, notify, scheduleDate, scheduleRepeatPeriod, null, -1, price == null ? 0 : price, getSendMonoForumPeerId(), getSendMessageSuggestionParams());\n"
        "                    }",
    )
    replace_exact(
        chat_activity,
        "                        chatActivity.showFieldPanelForForward(true, fmessages);",
        "                        if (fragment.nagramixCopyAsNew) {\n"
        "                            chatActivity.showFieldPanelForForwardAsCopy(fmessages);\n"
        "                        } else {\n"
        "                            chatActivity.showFieldPanelForForward(true, fmessages);\n"
        "                        }",
    )
    replace_exact(
        chat_activity,
        "                    showFieldPanelForForward(true, fmessages);",
        "                    if (fragment.nagramixCopyAsNew) {\n"
        "                        showFieldPanelForForwardAsCopy(fmessages);\n"
        "                    } else {\n"
        "                        showFieldPanelForForward(true, fmessages);\n"
        "                    }",
    )
    replace_exact(
        chat_activity,
        "    public void showFieldPanelForForward(boolean show, ArrayList<MessageObject> messageObjectsToForward) {",
        "    public void showFieldPanelForForwardAsCopy(ArrayList<MessageObject> messageObjectsToForward) {\n"
        "        showFieldPanelForForward(true, messageObjectsToForward);\n"
        "        nagramixForwardPanelAsCopy = true;\n"
        "        if (messagePreviewParams != null) {\n"
        "            messagePreviewParams.hideForwardSendersName = true;\n"
        "        }\n"
        "    }\n\n"
        "    public void showFieldPanelForForward(boolean show, ArrayList<MessageObject> messageObjectsToForward) {\n"
        "        nagramixForwardPanelAsCopy = false;",
    )
    replace_exact(
        chat_activity,
        "        int result = getSendMessagesHelper().sendMessage(arrayList, dialog_id, fromMyName, hideCaption, notify, scheduleDate, 0, getThreadMessage(), -1, payStars, getSendMonoForumPeerId(), getSendMessageSuggestionParams());",
        "        int result;\n"
        "        if (nagramixForwardPanelAsCopy) {\n"
        "            result = getSendMessagesHelper().sendMessagesAsNagramiXCopy(arrayList, dialog_id, notify, scheduleDate, 0, payStars, getSendMonoForumPeerId(), getSendMessageSuggestionParams());\n"
        "            nagramixForwardPanelAsCopy = false;\n"
        "        } else {\n"
        "            result = getSendMessagesHelper().sendMessage(arrayList, dialog_id, fromMyName, hideCaption, notify, scheduleDate, 0, getThreadMessage(), -1, payStars, getSendMonoForumPeerId(), getSendMessageSuggestionParams());\n"
        "        }",
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
    replace_exact(
        chat_activity,
        "        ArrayList<MessageObject> messArr = (ArrayList<MessageObject>) args[2];",
        "        ArrayList<MessageObject> messArr = (ArrayList<MessageObject>) args[2];\n"
        "        com.mr_efes.nagramix.NagramiXMessageArchive archive = com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount);\n"
        "        archive.captureLoaded(dialog_id, messArr);\n"
        "        archive.mergeDeleted(dialog_id, messArr);",
    )
    replace_exact(
        chat_activity,
        "            ArrayList<Integer> markAsDeletedMessages = (ArrayList<Integer>) args[0];\n"
        "            long channelId = (Long) args[1];",
        "            ArrayList<Integer> markAsDeletedMessages = (ArrayList<Integer>) args[0];\n"
        "            long channelId = (Long) args[1];\n"
        "            markAsDeletedMessages = com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).archiveDeletion(dialog_id, markAsDeletedMessages, messagesDict[0]);",
    )
    replace_exact(
        chat_activity,
        "            int loadIndex = did == dialog_id ? 0 : 1;\n"
        "            doOnIdle(() -> {\n"
        "                replaceMessageObjects(messageObjects, loadIndex, false);",
        "            int loadIndex = did == dialog_id ? 0 : 1;\n"
        "            com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).recordEdits(did, messageObjects, messagesDict[loadIndex]);\n"
        "            doOnIdle(() -> {\n"
        "                replaceMessageObjects(messageObjects, loadIndex, false);",
    )
    messages_storage = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "MessagesStorage.java"
    replace_exact(
        messages_storage,
        "    private void putMessagesInternal(ArrayList<TLRPC.Message> messages, boolean withTransaction, boolean doNotUpdateDialogDate, int downloadMask, boolean ifNoLastMessage, int mode, long threadMessageId) {\n"
        "        if (messages != null) {",
        "    private void putMessagesInternal(ArrayList<TLRPC.Message> messages, boolean withTransaction, boolean doNotUpdateDialogDate, int downloadMask, boolean ifNoLastMessage, int mode, long threadMessageId) {\n"
        "        if (messages != null && mode == ChatActivity.MODE_DEFAULT) {\n"
        "            com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).captureIncoming(messages);\n"
        "        }\n"
        "        if (messages != null) {",
    )
    replace_exact(
        messages_storage,
        "    private ArrayList<Long> markMessagesAsDeletedInternal(long dialogId, ArrayList<Integer> messages, boolean deleteFiles, int mode, int threadMessageId) {\n"
        "        SQLiteCursor cursor = null;",
        "    private ArrayList<Long> markMessagesAsDeletedInternal(long dialogId, ArrayList<Integer> messages, boolean deleteFiles, int mode, int threadMessageId) {\n"
        "        if (mode == ChatActivity.MODE_DEFAULT) {\n"
        "            com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).markDeleted(dialogId, messages);\n"
        "        }\n"
        "        SQLiteCursor cursor = null;",
    )
    user_config = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "UserConfig.java"
    replace_exact(
        user_config,
        "    public void clearConfig() {\n        getPreferences().edit().clear().apply();",
        "    public void clearConfig() {\n"
        "        com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).clearAll();\n"
        "        getPreferences().edit().clear().apply();",
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
