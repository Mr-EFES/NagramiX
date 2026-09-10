#!/usr/bin/env python3
"""Apply NagramiX Android sources to pinned official Telegram Android."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
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


def replace_exact_count(path: Path, old: str, new: str, expected: int) -> None:
    content = path.read_text(encoding="utf-8")
    count = content.count(old)
    if count != expected:
        raise RuntimeError(
            f"Expected {expected} anchors in {path}: {old!r}; found {count}"
        )
    path.write_text(content.replace(old, new), encoding="utf-8")


def replace_exact_count_in_range(
    path: Path, start: str, end: str, old: str, new: str, expected: int
) -> None:
    content = path.read_text(encoding="utf-8")
    start_index = content.find(start)
    end_index = content.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        raise RuntimeError(f"Expected unique range anchors in {path}")
    segment = content[start_index:end_index]
    count = segment.count(old)
    if count != expected:
        raise RuntimeError(
            f"Expected {expected} ranged anchors in {path}: {old!r}; found {count}"
        )
    content = content[:start_index] + segment.replace(old, new) + content[end_index:]
    path.write_text(content, encoding="utf-8")


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
        """    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8

        coreLibraryDesugaringEnabled true
    }
""",
        """    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8

        coreLibraryDesugaringEnabled true
    }

    kotlinOptions {
        jvmTarget = '1.8'
    }
""",
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

    application_loader = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "ApplicationLoader.java"
    replace_exact(
        application_loader,
        "import androidx.annotation.NonNull;",
        "import androidx.annotation.NonNull;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        application_loader,
        '''        NativeLoader.initNativeLibs(ApplicationLoader.applicationContext);

        try {
            LocaleController.getInstance(); //TODO improve''',
        '''        NativeLoader.initNativeLibs(ApplicationLoader.applicationContext);

        // Classify the installation before LocaleController or Theme can write
        // global settings. Existing installs retain system/user choices; Clear
        // Data has empty stores and is intentionally a clean first run again.
        android.content.SharedPreferences nagramiXPreferences = NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext);
        if (!nagramiXPreferences.contains("installation.cleanDefaults")) {
            boolean cleanInstall = MessagesController.getGlobalMainSettings().getAll().isEmpty();
            nagramiXPreferences.edit().putBoolean("installation.cleanDefaults", cleanInstall).commit();
        }

        try {
            LocaleController.getInstance(); //TODO improve''',
    )

    locale_controller = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "LocaleController.java"
    replace_exact(
        locale_controller,
        "import androidx.annotation.RequiresApi;",
        "import androidx.annotation.RequiresApi;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        locale_controller,
        '''            String lang = preferences.getString("language", null);
            if (lang != null) {''',
        '''            String lang = preferences.getString("language", null);
            // NagramiX clean-install default. Telegram writes this preference
            // only after an explicit language choice, so a saved selection is
            // never replaced and logout does not reset it.
            if (lang == null && NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean("installation.cleanDefaults", false)) {
                lang = "ru";
            }
            if (lang != null) {''',
    )

    theme = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "ActionBar" / "Theme.java"
    replace_exact(
        theme,
        "import androidx.annotation.NonNull;",
        "import androidx.annotation.NonNull;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )

    connections_manager = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "tgnet" / "ConnectionsManager.java"
    replace_exact(
        connections_manager,
        "import androidx.annotation.Keep;",
        "import androidx.annotation.Keep;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        connections_manager,
        '''    private static class ResolveHostByNameTask extends AsyncTask<Void, Void, ResolvedDomain> {''',
        '''    private static byte[] nagramiXBuildDnsQuery(String host) throws Exception {
        java.io.ByteArrayOutputStream bytes = new java.io.ByteArrayOutputStream();
        java.io.DataOutputStream output = new java.io.DataOutputStream(bytes);
        output.writeShort(Utilities.random.nextInt(0x10000));
        output.writeShort(0x0100);
        output.writeShort(1);
        output.writeShort(0);
        output.writeShort(0);
        output.writeShort(0);
        for (String label : host.split("\\\\.")) {
            byte[] encoded = label.getBytes("UTF-8");
            if (encoded.length == 0 || encoded.length > 63) throw new IllegalArgumentException("Invalid DNS label");
            output.writeByte(encoded.length);
            output.write(encoded);
        }
        output.writeByte(0);
        output.writeShort(1);
        output.writeShort(1);
        output.flush();
        return bytes.toByteArray();
    }

    private static int nagramiXSkipDnsName(byte[] data, int offset) throws Exception {
        while (offset < data.length) {
            int length = data[offset++] & 0xff;
            if (length == 0) return offset;
            if ((length & 0xc0) == 0xc0) {
                if (offset >= data.length) throw new java.io.EOFException();
                return offset + 1;
            }
            offset += length;
            if (offset > data.length) throw new java.io.EOFException();
        }
        throw new java.io.EOFException();
    }

    private static ResolvedDomain nagramiXParseDnsResponse(byte[] data) throws Exception {
        if (data.length < 12) throw new java.io.EOFException();
        java.io.DataInputStream header = new java.io.DataInputStream(new java.io.ByteArrayInputStream(data));
        header.readUnsignedShort();
        int flags = header.readUnsignedShort();
        int questions = header.readUnsignedShort();
        int answers = header.readUnsignedShort();
        header.readUnsignedShort();
        header.readUnsignedShort();
        if ((flags & 0x8000) == 0 || (flags & 0x000f) != 0) return null;
        int offset = 12;
        for (int i = 0; i < questions; i++) {
            offset = nagramiXSkipDnsName(data, offset) + 4;
            if (offset > data.length) throw new java.io.EOFException();
        }
        ArrayList<String> addresses = new ArrayList<>();
        for (int i = 0; i < answers; i++) {
            offset = nagramiXSkipDnsName(data, offset);
            if (offset + 10 > data.length) throw new java.io.EOFException();
            int type = ((data[offset] & 0xff) << 8) | (data[offset + 1] & 0xff);
            int clazz = ((data[offset + 2] & 0xff) << 8) | (data[offset + 3] & 0xff);
            int length = ((data[offset + 8] & 0xff) << 8) | (data[offset + 9] & 0xff);
            offset += 10;
            if (offset + length > data.length) throw new java.io.EOFException();
            if (type == 1 && clazz == 1 && length == 4) {
                addresses.add(InetAddress.getByAddress(java.util.Arrays.copyOfRange(data, offset, offset + length)).getHostAddress());
            }
            offset += length;
        }
        return addresses.isEmpty() ? null : new ResolvedDomain(addresses, SystemClock.elapsedRealtime());
    }

    private static String nagramiXDohEndpoint() {
        SharedPreferences preferences = NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext);
        switch (preferences.getString(NagramiXSettings.DNS_PROVIDER, "system")) {
            case "google": return "https://dns.google/dns-query";
            case "quad9": return "https://dns.quad9.net/dns-query";
            case "adguard": return "https://dns.adguard-dns.com/dns-query";
            case "mullvad": return "https://dns.mullvad.net/dns-query";
            case "cloudflare": return "https://cloudflare-dns.com/dns-query";
            case "custom":
                String custom = preferences.getString(NagramiXSettings.CUSTOM_DOH_URL, "");
                return custom != null && custom.regionMatches(true, 0, "https://", 0, 8) ? custom : null;
            default: return null;
        }
    }

    public static void invalidateNagramiXDnsCache() {
        for (ResolveHostByNameTask task : resolvingHostnameTasks.values()) {
            task.cancel(true);
        }
        resolvingHostnameTasks.clear();
        dnsCache.clear();
    }

    private static class ResolveHostByNameTask extends AsyncTask<Void, Void, ResolvedDomain> {''',
    )
    replace_exact(
        connections_manager,
        '''            try {
                URL downloadUrl = new URL("https://www.google.com/resolve?name=" + currentHostName + "&type=A");
                URLConnection httpConnection = downloadUrl.openConnection();
                httpConnection.addRequestProperty("User-Agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 10_0 like Mac OS X) AppleWebKit/602.1.38 (KHTML, like Gecko) Version/10.0 Mobile/14A5297c Safari/602.1");
                httpConnection.addRequestProperty("Host", "dns.google.com");''',
        '''            try {
                String endpoint = nagramiXDohEndpoint();
                if (endpoint == null) {
                    InetAddress address = InetAddress.getByName(currentHostName);
                    ArrayList<String> systemAddresses = new ArrayList<>(1);
                    systemAddresses.add(address.getHostAddress());
                    return new ResolvedDomain(systemAddresses, SystemClock.elapsedRealtime());
                }
                String separator = endpoint.contains("?") ? "&" : "?";
                URL downloadUrl = new URL(endpoint + separator + "name=" + java.net.URLEncoder.encode(currentHostName, "UTF-8") + "&type=A");
                URLConnection httpConnection = downloadUrl.openConnection();
                httpConnection.addRequestProperty("User-Agent", "NagramiX/0.2.6");
                httpConnection.addRequestProperty("Accept", "application/dns-json");''',
    )
    replace_exact(
        connections_manager,
        '''                String separator = endpoint.contains("?") ? "&" : "?";
                URL downloadUrl = new URL(endpoint + separator + "name=" + java.net.URLEncoder.encode(currentHostName, "UTF-8") + "&type=A");
                URLConnection httpConnection = downloadUrl.openConnection();
                httpConnection.addRequestProperty("User-Agent", "NagramiX/0.2.6");
                httpConnection.addRequestProperty("Accept", "application/dns-json");
                httpConnection.setConnectTimeout(1000);
                httpConnection.setReadTimeout(2000);
                httpConnection.connect();
                httpConnectionStream = httpConnection.getInputStream();

                outbuf = new ByteArrayOutputStream();

                byte[] data = new byte[1024 * 32];
                while (true) {
                    int read = httpConnectionStream.read(data);
                    if (read > 0) {
                        outbuf.write(data, 0, read);
                    } else if (read == -1) {
                        break;
                    } else {
                        break;
                    }
                }

                JSONObject jsonObject = new JSONObject(new String(outbuf.toByteArray()));
                if (jsonObject.has("Answer")) {
                    JSONArray array = jsonObject.getJSONArray("Answer");
                    int len = array.length();
                    if (len > 0) {
                        ArrayList<String> addresses = new ArrayList<>(len);
                        for (int a = 0; a < len; a++) {
                            addresses.add(array.getJSONObject(a).getString("data"));
                        }
                        return new ResolvedDomain(addresses, SystemClock.elapsedRealtime());
                    }
                }
                done = true;''',
        '''                byte[] query = nagramiXBuildDnsQuery(currentHostName);
                java.net.HttpURLConnection httpConnection = (java.net.HttpURLConnection) new URL(endpoint).openConnection();
                httpConnection.setRequestMethod("POST");
                httpConnection.setDoOutput(true);
                httpConnection.addRequestProperty("User-Agent", "NagramiX/0.2.6");
                httpConnection.addRequestProperty("Content-Type", "application/dns-message");
                httpConnection.addRequestProperty("Accept", "application/dns-message");
                httpConnection.setFixedLengthStreamingMode(query.length);
                httpConnection.setConnectTimeout(1000);
                httpConnection.setReadTimeout(2000);
                try (java.io.OutputStream output = httpConnection.getOutputStream()) {
                    output.write(query);
                }
                httpConnectionStream = httpConnection.getInputStream();
                outbuf = new ByteArrayOutputStream();
                byte[] data = new byte[4096];
                int read;
                while ((read = httpConnectionStream.read(data)) != -1) {
                    outbuf.write(data, 0, read);
                }
                ResolvedDomain resolved = nagramiXParseDnsResponse(outbuf.toByteArray());
                if (resolved != null) return resolved;''',
    )
    replace_exact(
        theme,
        '''            String theme = preferences.getString("theme", null);
            if ("Default".equals(theme)) {''',
        '''            String theme = preferences.getString("theme", null);
            // Use Telegram's built-in dark-blue ThemeInfo before the first UI
            // render. Any existing explicit theme remains authoritative.
            if (theme == null && NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean("installation.cleanDefaults", false)) {
                applyingTheme = themeDarkBlue;
                applyingTheme.currentAccentId = 9;
            } else if ("Default".equals(theme)) {''',
    )

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
    copy(ROOT / "android" / "Sources" / "values-ru" / "strings_nagramix.xml", resource_root / "values-ru" / "strings_nagramix.xml")
    copy(
        ROOT / "android" / "Sources" / "NagramiXSettings.kt",
        source / "TMessagesProj" / "src" / "main" / "java" / "com" / "mr_efes" / "nagramix" / "NagramiXSettings.kt",
    )
    copy(
        ROOT / "android" / "Sources" / "NagramiXPeerMetadata.java",
        source / "TMessagesProj" / "src" / "main" / "java" / "com" / "mr_efes" / "nagramix" / "NagramiXPeerMetadata.java",
    )
    copy(
        ROOT / "android" / "Sources" / "NagramiXMessageArchive.java",
        source / "TMessagesProj" / "src" / "main" / "java" / "com" / "mr_efes" / "nagramix" / "NagramiXMessageArchive.java",
    )
    copy(
        ROOT / "android" / "Sources" / "NagramiXSettingsActivity.java",
        source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "NagramiXSettingsActivity.java",
    )
    copy(
        ROOT / "android" / "Sources" / "NagramiXStoryConfirmationView.java",
        source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Stories" / "NagramiXStoryConfirmationView.java",
    )
    for icon_index in range(1, 9):
        copy(
            ROOT / "android" / "branding" / "AppIcons" / f"{icon_index}.png",
            resource_root / "drawable-nodpi" / f"nagramix_app_icon_{icon_index}.png",
        )

    settings_activity = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "SettingsActivity.java"
    replace_exact(
        settings_activity,
        '''        items.add(SettingCell.Factory.of(10, IconBackgroundColors.PURPLE.top, IconBackgroundColors.PURPLE.bottom, R.drawable.settings_language, getString(R.string.SettingsLanguage), LocaleController.getCurrentLanguageName()));

        items.add(UItem.asShadow(null));''',
        '''        items.add(SettingCell.Factory.of(10, IconBackgroundColors.PURPLE.top, IconBackgroundColors.PURPLE.bottom, R.drawable.settings_language, getString(R.string.SettingsLanguage), LocaleController.getCurrentLanguageName()));
        items.add(SettingCell.Factory.of(100, IconBackgroundColors.BLUE_DEEP.top, IconBackgroundColors.BLUE_DEEP.bottom, R.drawable.settings_chat, getString(R.string.NagramiXSettings)));

        items.add(UItem.asShadow(null));''',
    )

    profile_activity = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "ProfileActivity.java"
    replace_exact(
        profile_activity,
        "import androidx.annotation.Keep;",
        "import androidx.annotation.Keep;\n\nimport com.mr_efes.nagramix.NagramiXPeerMetadata;\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        profile_activity,
        "    private int phoneRow;\n    private int noteRow;",
        "    private int phoneRow;\n    private int nagramiXProfileIdRow;\n    private int nagramiXRegistrationRow;\n    private int noteRow;",
    )
    replace_exact(
        profile_activity,
        "        phoneRow = -1;\n        noteRow = -1;",
        "        phoneRow = -1;\n        nagramiXProfileIdRow = -1;\n        nagramiXRegistrationRow = -1;\n        noteRow = -1;",
    )
    replace_exact(
        profile_activity,
        """                infoStartRow = rowCount;
                if (!isBot && (hasPhone || !hasInfo)) {""",
        """                infoStartRow = rowCount;
                android.content.SharedPreferences nagramiXProfilePreferences = NagramiXSettings.INSTANCE.preferences(getContext());
                if (nagramiXProfilePreferences.getBoolean(NagramiXSettings.SHOW_PROFILE_IDS, true)) {
                    nagramiXProfileIdRow = rowCount++;
                }
                if (!isBot && nagramiXProfilePreferences.getBoolean(NagramiXSettings.SHOW_REGISTRATION_DATE, true)) {
                    nagramiXRegistrationRow = rowCount++;
                }
                if (!isBot && (hasPhone || !hasInfo)) {""",
    )
    replace_exact(
        profile_activity,
        """            if (actionsView == null) {
                if (infoHeaderRow != -1) {""",
        """            if (NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.SHOW_PROFILE_IDS, true)) {
                nagramiXProfileIdRow = rowCount++;
            }
            if (actionsView == null) {
                if (infoHeaderRow != -1) {""",
    )
    replace_exact(
        profile_activity,
        """                    } else if (position == phoneRow) {
                        String text;""",
        """                    } else if (position == nagramiXProfileIdRow) {
                        long peerId = userId != 0 ? userId : chatId;
                        detailCell.setTextAndValue(Long.toString(peerId), LocaleController.getString(R.string.NagramiXProfileId), nagramiXRegistrationRow != -1);
                    } else if (position == nagramiXRegistrationRow) {
                        int year = NagramiXPeerMetadata.approximateRegistrationYear(userId);
                        detailCell.setTextAndValue(LocaleController.formatString(R.string.NagramiXApproximateYear, year), LocaleController.getString(R.string.NagramiXRegistrationYear), false);
                    } else if (position == phoneRow) {
                        String text;""",
    )
    replace_exact(
        profile_activity,
        """            } else if (position == settingsKeyRow) {
                Bundle args = new Bundle();""",
        """            } else if (position == nagramiXProfileIdRow) {
                long peerId = userId != 0 ? userId : chatId;
                AndroidUtilities.addToClipboard(Long.toString(peerId));
                BulletinFactory.of(ProfileActivity.this).createCopyBulletin(LocaleController.getString(R.string.NagramiXProfileIdCopied)).show();
            } else if (position == settingsKeyRow) {
                Bundle args = new Bundle();""",
    )
    replace_exact(
        profile_activity,
        """            } else if (position == phoneRow || position == locationRow || position == numberRow || position == birthdayRow) {
                return VIEW_TYPE_TEXT_DETAIL;""",
        """            } else if (position == phoneRow || position == locationRow || position == numberRow || position == birthdayRow || position == nagramiXProfileIdRow || position == nagramiXRegistrationRow) {
                return VIEW_TYPE_TEXT_DETAIL;""",
    )

    user_cell = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Cells" / "UserCell.java"
    replace_exact(
        user_cell,
        "import androidx.annotation.NonNull;",
        "import androidx.annotation.NonNull;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        user_cell,
        """        } else {
            nameTextView.setRightDrawable(null);
            nameTextView.setRightDrawableTopPadding(0);
        }
        if (currentStatus != null) {""",
        """        } else if (currentUser != null && currentUser.mutual_contact && !currentUser.self && !currentUser.bot
                && NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.SHOW_MUTUAL_CONTACT_ICON, false)) {
            Drawable mutualContact = getContext().getResources().getDrawable(R.drawable.msg_contacts).mutate();
            mutualContact.setColorFilter(new PorterDuffColorFilter(Theme.getColor(Theme.key_windowBackgroundWhiteBlueText, resourcesProvider), PorterDuff.Mode.MULTIPLY));
            nameTextView.setRightDrawable(new AnimatedEmojiDrawable.WrapSizeDrawable(mutualContact, dp(14), dp(14)));
            nameTextView.setRightDrawableTopPadding(0);
        } else {
            nameTextView.setRightDrawable(null);
            nameTextView.setRightDrawableTopPadding(0);
        }
        if (currentStatus != null) {""",
    )

    story_viewer = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Stories" / "StoryViewer.java"
    replace_exact(
        story_viewer,
        "import org.telegram.ui.Stories.recorder.LivePlayerView;",
        "import org.telegram.ui.Stories.recorder.LivePlayerView;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        story_viewer,
        '''    HwFrameLayout containerView;
    SelfStoryViewsView selfStoryViewsView;''',
        '''    HwFrameLayout containerView;
    SelfStoryViewsView selfStoryViewsView;
    private NagramiXStoryConfirmationView nagramiXStoryConfirmation;
    private long nagramiXApprovedStoryDialogId;
    private int nagramiXApprovedStoryId;''',
    )
    replace_exact(
        story_viewer,
        '''    @Override
    public boolean onAttachedBackPressed() {
        if (selfStoriesViewsOffset != 0) {''',
        '''    @Override
    public boolean onAttachedBackPressed() {
        if (nagramiXStoryConfirmation != null) {
            NagramiXStoryConfirmationView confirmation = nagramiXStoryConfirmation;
            nagramiXStoryConfirmation = null;
            return confirmation.cancel();
        }
        if (selfStoriesViewsOffset != 0) {''',
    )
    replace_exact(
        story_viewer,
        '''    public void switchByTap(boolean forward) {
        PeerStoriesView peerView = storiesViewPager.getCurrentPeerView();''',
        '''    boolean requestNagramiXStoryConfirmation(long dialogId, TL_stories.StoryItem storyItem, Runnable confirmed, Runnable cancelled) {
        if (storyItem == null || dialogId == UserConfig.getInstance(currentAccount).getClientUserId() || !NagramiXSettings.INSTANCE.preferences(containerView.getContext()).getBoolean(NagramiXSettings.CONFIRM_STORY_VIEWING, false)) {
            return false;
        }
        if (nagramiXApprovedStoryDialogId == dialogId && nagramiXApprovedStoryId == storyItem.id) {
            nagramiXApprovedStoryDialogId = 0;
            nagramiXApprovedStoryId = 0;
            return false;
        }
        if (nagramiXStoryConfirmation != null) {
            return true;
        }
        nagramiXStoryConfirmation = new NagramiXStoryConfirmationView(containerView.getContext(), currentAccount, dialogId, storyItem, () -> {
            nagramiXApprovedStoryDialogId = dialogId;
            nagramiXApprovedStoryId = storyItem.id;
            nagramiXStoryConfirmation = null;
            confirmed.run();
        }, () -> {
            nagramiXStoryConfirmation = null;
            cancelled.run();
        });
        containerView.addView(nagramiXStoryConfirmation, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT));
        return true;
    }

    public void switchByTap(boolean forward) {
        PeerStoriesView peerView = storiesViewPager.getCurrentPeerView();''',
    )

    peer_stories_view = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Stories" / "PeerStoriesView.java"
    replace_exact(
        peer_stories_view,
        "    private int selectedPosition;",
        "    private int selectedPosition;\n    private int nagramiXCommittedPosition = -1;",
    )

    voip_service = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "voip" / "VoIPService.java"
    replace_exact(
        voip_service,
        "import androidx.annotation.Nullable;",
        "import androidx.annotation.Nullable;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        voip_service,
        '\t\t\tfinal boolean forceTcp = preferences.getBoolean("dbg_force_tcp_in_calls", false);',
        '\t\t\tfinal boolean forceTcp = preferences.getBoolean("dbg_force_tcp_in_calls", false)\n\t\t\t\t\t|| NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.FORCE_TCP_CALLS, false);',
    )
    replace_exact(
        peer_stories_view,
        "import androidx.annotation.Nullable;",
        "import androidx.annotation.Nullable;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        peer_stories_view,
        """                allowRepost = allowShare;
                if (allowRepost && isChannel) {""",
        """                allowRepost = allowShare && NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.ENABLE_STORY_REPOST, false);
                if (allowRepost && isChannel) {""",
    )
    replace_exact(
        peer_stories_view,
        '''        currentStory.editingSourceItem = null;
        if (uploadingStory != null) {''',
        '''        if (isActive && storyItem != null && storyViewer.requestNagramiXStoryConfirmation(dialogId, storyItem, () -> {
            selectedPosition = position;
            updatePosition();
        }, () -> {
            if (nagramiXCommittedPosition < 0) {
                storyViewer.close(true);
            } else {
                selectedPosition = nagramiXCommittedPosition;
            }
        })) {
            selectedPosition = nagramiXCommittedPosition < 0 ? position : nagramiXCommittedPosition;
            return;
        }
        nagramiXCommittedPosition = position;

        currentStory.editingSourceItem = null;
        if (uploadingStory != null) {''',
    )

    dialogs_activity = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "DialogsActivity.java"
    replace_exact(
        dialogs_activity,
        "import androidx.annotation.Nullable;",
        "import androidx.annotation.Nullable;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        dialogs_activity,
        "        searchItem.setVisibility(View.GONE);\n\n        if (!onlySelect",
        "        searchItem.setVisibility(NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.SHOW_SEARCH_TAB, false) ? View.VISIBLE : View.GONE);\n\n        if (!onlySelect",
    )
    replace_exact(
        dialogs_activity,
        '''            final boolean proxyVisible = proxyEnabled && !TextUtils.isEmpty(proxyAddress)
                    || getMessagesController().blockedCountry && !SharedConfig.proxyList.isEmpty();''',
        '''            final boolean proxyVisible = NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.SHOW_PROXY_BUTTON, true) && (
                    proxyEnabled && !TextUtils.isEmpty(proxyAddress)
                    || getMessagesController().blockedCountry && !SharedConfig.proxyList.isEmpty()
            );''',
    )

    main_tabs = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "MainTabsActivity.java"
    replace_exact(
        main_tabs,
        "import androidx.annotation.NonNull;",
        "import androidx.annotation.NonNull;\n\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        main_tabs,
        '''    private static int indexToPosition(int index) {
        return index > 2 ? index - 1 : index;
    }''',
        '''    private boolean nagramiXHideContacts() {
        return NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.HIDE_CONTACTS_TAB, true);
    }

    private int nagramiXPositionCallsOrSettings() {
        return nagramiXHideContacts() ? 1 : POSITION_CALLS_OR_SETTINGS;
    }

    private int nagramiXPositionProfile() {
        return nagramiXHideContacts() ? 2 : POSITION_PROFILE;
    }

    private int indexToPosition(int index) {
        if (index == INDEX_CONTACTS) return nagramiXHideContacts() ? -1 : POSITION_CONTACTS;
        if (index == INDEX_SETTINGS || index == INDEX_CALLS) return nagramiXPositionCallsOrSettings();
        if (index == INDEX_PROFILE) return nagramiXPositionProfile();
        return POSITION_CHATS;
    }''',
    )
    replace_exact(
        main_tabs,
        "            tabsView.setViewVisible(view, true, false);",
        "            tabsView.setViewVisible(view, index != INDEX_CONTACTS || !nagramiXHideContacts(), false);",
    )
    replace_exact(
        main_tabs,
        "        checkUi_callTabVisible(getUserConfig().showCallsTab, false);",
        "        if (!NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.SHOW_TAB_TITLES, true)) {\n"
        "            tabs[INDEX_CHATS].setContentDescription(getString(R.string.MainTabsChats));\n"
        "            tabs[INDEX_CONTACTS].setContentDescription(getString(R.string.MainTabsContacts));\n"
        "            tabs[INDEX_SETTINGS].setContentDescription(getString(R.string.Settings));\n"
        "            tabs[INDEX_CALLS].setContentDescription(getString(R.string.MainTabsCalls));\n"
        "            tabs[INDEX_PROFILE].setContentDescription(getString(R.string.MainTabsProfile));\n"
        "            for (GlassTabView tab : tabs) tab.setText(\"\");\n"
        "        }\n"
        "        checkUi_callTabVisible(getUserConfig().showCallsTab, false);",
    )
    replace_exact(
        main_tabs,
        "        return TABS_COUNT;",
        "        return nagramiXHideContacts() ? TABS_COUNT - 1 : TABS_COUNT;",
    )
    replace_exact(
        main_tabs,
        "        if (position == POSITION_CONTACTS) {",
        "        if (!nagramiXHideContacts() && position == POSITION_CONTACTS) {",
    )
    replace_exact(
        main_tabs,
        "        } else if (position == POSITION_CALLS_OR_SETTINGS) {",
        "        } else if (position == nagramiXPositionCallsOrSettings()) {",
    )
    replace_exact(
        main_tabs,
        "            if (getUserConfig().showCallsTab) {",
        "            if (getUserConfig().showCallsTab && !NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.HIDE_CALLS_TAB, true)) {",
    )
    replace_exact(
        main_tabs,
        "        } else if (position == POSITION_PROFILE) {",
        "        } else if (position == nagramiXPositionProfile()) {",
    )
    replace_exact_count(main_tabs, "currentPosition != POSITION_CALLS_OR_SETTINGS", "currentPosition != nagramiXPositionCallsOrSettings()", 1)
    replace_exact_count(main_tabs, "dropFragmentAtPosition(POSITION_CALLS_OR_SETTINGS)", "dropFragmentAtPosition(nagramiXPositionCallsOrSettings())", 2)
    replace_exact(main_tabs, "viewPager.getCurrentPosition() == POSITION_CALLS_OR_SETTINGS", "viewPager.getCurrentPosition() == nagramiXPositionCallsOrSettings()")
    replace_exact(main_tabs, "currentPosition != POSITION_PROFILE", "currentPosition != nagramiXPositionProfile()")
    replace_exact(main_tabs, "dropFragmentAtPosition(POSITION_PROFILE)", "dropFragmentAtPosition(nagramiXPositionProfile())")
    replace_exact(main_tabs, "Math.abs(POSITION_PROFILE - animatedPosition)", "Math.abs(nagramiXPositionProfile() - animatedPosition)")
    replace_exact(
        main_tabs,
        '''    private void checkUi_callTabVisible(boolean callTabsVisible, boolean animated) {
        if (tabsView != null) {''',
        '''    private void checkUi_callTabVisible(boolean callTabsVisible, boolean animated) {
        callTabsVisible = callTabsVisible && !NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.HIDE_CALLS_TAB, true);
        if (tabsView != null) {''',
    )

    messages_controller = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "MessagesController.java"
    replace_exact(
        messages_controller,
        "import androidx.annotation.NonNull;",
        "import androidx.annotation.NonNull;\n\nimport com.mr_efes.nagramix.NagramiXMessageArchive;\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        messages_controller,
        '''            } else if (baseUpdate instanceof TL_update.TL_updateDeleteMessages) {
                TL_update.TL_updateDeleteMessages update = (TL_update.TL_updateDeleteMessages) baseUpdate;''',
        '''            } else if (baseUpdate instanceof TL_update.TL_updateDeleteMessages) {
                TL_update.TL_updateDeleteMessages update = (TL_update.TL_updateDeleteMessages) baseUpdate;
                NagramiXMessageArchive.getInstance(currentAccount).markDeleted(0, update.messages);''',
    )
    replace_exact(
        messages_controller,
        '''            } else if (baseUpdate instanceof TL_update.TL_updateDeleteChannelMessages) {
                TL_update.TL_updateDeleteChannelMessages update = (TL_update.TL_updateDeleteChannelMessages) baseUpdate;''',
        '''            } else if (baseUpdate instanceof TL_update.TL_updateDeleteChannelMessages) {
                TL_update.TL_updateDeleteChannelMessages update = (TL_update.TL_updateDeleteChannelMessages) baseUpdate;
                NagramiXMessageArchive.getInstance(currentAccount).markDeleted(-update.channel_id, update.messages);''',
    )

    messages_storage = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "MessagesStorage.java"
    replace_exact(
        messages_storage,
        "import androidx.annotation.UiThread;",
        "import androidx.annotation.UiThread;\n\nimport com.mr_efes.nagramix.NagramiXMessageArchive;",
    )
    replace_exact(
        messages_storage,
        '''    private void putMessagesInternal(ArrayList<TLRPC.Message> messages, boolean withTransaction, boolean doNotUpdateDialogDate, int downloadMask, boolean ifNoLastMessage, int mode, long threadMessageId) {
        if (messages != null) {''',
        '''    private void putMessagesInternal(ArrayList<TLRPC.Message> messages, boolean withTransaction, boolean doNotUpdateDialogDate, int downloadMask, boolean ifNoLastMessage, int mode, long threadMessageId) {
        // Snapshot on Telegram's storage path, then persist asynchronously on
        // the archive's private serial queue. Native message insertion never
        // waits for NagramiX disk I/O.
        NagramiXMessageArchive.getInstance(currentAccount).capture(messages);
        if (messages != null) {''',
    )

    proxy_rotation = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "ProxyRotationController.java"
    replace_exact(
        proxy_rotation,
        '''    private boolean isCurrentlyChecking;
    private Runnable checkProxyAndSwitchRunnable = () -> {
        isCurrentlyChecking = true;''',
        '''    private boolean isCurrentlyChecking;
    private int nagramiXCheckGeneration;
    private SharedConfig.ProxyInfo nagramiXCheckOrigin;
    private Runnable checkProxyAndSwitchRunnable = () -> {
        isCurrentlyChecking = true;
        final int checkGeneration = ++nagramiXCheckGeneration;
        nagramiXCheckOrigin = SharedConfig.currentProxy;''',
    )
    replace_exact(
        proxy_rotation,
        '''            proxyInfo.proxyCheckPingId = ConnectionsManager.getInstance(currentAccount).checkProxy(proxyInfo.address, proxyInfo.port, proxyInfo.username, proxyInfo.password, proxyInfo.secret, time -> AndroidUtilities.runOnUIThread(() -> {
                proxyInfo.availableCheckTime = SystemClock.elapsedRealtime();''',
        '''            proxyInfo.proxyCheckPingId = ConnectionsManager.getInstance(currentAccount).checkProxy(proxyInfo.address, proxyInfo.port, proxyInfo.username, proxyInfo.password, proxyInfo.secret, time -> AndroidUtilities.runOnUIThread(() -> {
                if (checkGeneration != nagramiXCheckGeneration || SharedConfig.currentProxy != nagramiXCheckOrigin) {
                    proxyInfo.checking = false;
                    return;
                }
                proxyInfo.availableCheckTime = SystemClock.elapsedRealtime();''',
    )
    replace_exact(
        proxy_rotation,
        '''        if (!SharedConfig.proxyRotationEnabled) {
            return;
        }

        List<SharedConfig.ProxyInfo> sortedList''',
        '''        if (!SharedConfig.proxyRotationEnabled || SharedConfig.currentProxy != nagramiXCheckOrigin) {
            return;
        }

        List<SharedConfig.ProxyInfo> sortedList''',
    )
    replace_exact(
        proxy_rotation,
        '''        } else if (id == NotificationCenter.proxySettingsChanged) {
            AndroidUtilities.cancelRunOnUIThread(checkProxyAndSwitchRunnable);''',
        '''        } else if (id == NotificationCenter.proxySettingsChanged) {
            nagramiXCheckGeneration++;
            nagramiXCheckOrigin = null;
            isCurrentlyChecking = false;
            AndroidUtilities.cancelRunOnUIThread(checkProxyAndSwitchRunnable);''',
    )
    replace_exact(
        proxy_rotation,
        '''            } else {
                AndroidUtilities.cancelRunOnUIThread(checkProxyAndSwitchRunnable);
            }
        }
    }
}''',
        '''            } else {
                // Connected, updating and waiting-for-network are not evidence
                // that the selected proxy failed. Invalidate delayed/native
                // callbacks so an offline transition cannot switch a proxy.
                nagramiXCheckGeneration++;
                nagramiXCheckOrigin = null;
                isCurrentlyChecking = false;
                AndroidUtilities.cancelRunOnUIThread(checkProxyAndSwitchRunnable);
            }
        }
    }
}''',
    )
    replace_exact(
        messages_controller,
        '''                if (res.proxy) {
                    promoDialogType = PROMO_TYPE_PROXY;''',
        '''                if (res.proxy) {
                    promoDialogType = PROMO_TYPE_PROXY;
                    if (NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext).getBoolean(NagramiXSettings.HIDE_PROXY_SPONSOR_CHANNEL, true)) {
                        noDialog = true;
                    }''',
    )
    replace_exact(
        dialogs_activity,
        '''        hasOnlySlefStories = onlySelfStories;

        boolean oldStoriesCellVisibility = dialogStoriesCellVisible;''',
        '''        if (NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.HIDE_STORIES, false)) {
            onlySelfStories = false;
            newVisibility = false;
        }
        hasOnlySlefStories = onlySelfStories;

        boolean oldStoriesCellVisibility = dialogStoriesCellVisible;''',
    )

    dialog_stories_cell = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Stories" / "DialogStoriesCell.java"
    replace_exact(
        dialog_stories_cell,
        "import org.telegram.messenger.AndroidUtilities;",
        "import com.mr_efes.nagramix.NagramiXSettings;\n\nimport org.telegram.messenger.AndroidUtilities;",
    )

    chat_activity = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "ChatActivity.java"
    replace_exact(
        chat_activity,
        "import androidx.annotation.DrawableRes;",
        "import androidx.annotation.DrawableRes;\n\nimport com.mr_efes.nagramix.NagramiXMessageArchive;\nimport com.mr_efes.nagramix.NagramiXSettings;",
    )
    replace_exact(
        chat_activity,
        "import android.util.SparseArray;",
        "import android.util.SparseArray;\nimport android.util.SparseBooleanArray;",
    )
    replace_exact(
        chat_activity,
        "import android.widget.TextView;",
        "import android.widget.TextView;\nimport android.widget.Toast;",
    )
    replace_exact(
        chat_activity,
        "    public final static int OPTION_FORWARD = 2;",
        "    public final static int OPTION_FORWARD = 2;\n"
        "    private static final int OPTION_NAGRAMIX_COPY_AS_NEW = 10002;\n"
        "    private static final int OPTION_NAGRAMIX_SELECT_FROM_AUTHOR = 10003;\n"
        "    private static final int OPTION_NAGRAMIX_EDIT_HISTORY = 10004;\n"
        "    private static final int OPTION_NAGRAMIX_DELETE_LOCAL = 10005;",
    )

    instant_camera = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Components" / "InstantCameraView.java"
    replace_exact(
        instant_camera,
        "import org.telegram.messenger.AndroidUtilities;",
        "import com.mr_efes.nagramix.NagramiXSettings;\n\n"
        "import org.telegram.messenger.AndroidUtilities;",
    )
    replace_exact(
        instant_camera,
        '''        if (!fromPaused) {
            if (!useCamera2) {
                isFrontface = true;
            }
            updateFlash();''',
        '''        if (!fromPaused) {
            // Select only the initial camera. Telegram's native Camera1/Camera2,
            // dual-camera, switch, zoom, flash and recorder paths remain intact.
            isFrontface = !NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.REAR_VIDEO_MESSAGES, false);
            updateFlash();''',
    )

    chat_message_cell = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "Cells" / "ChatMessageCell.java"
    replace_exact(
        chat_message_cell,
        "import org.telegram.messenger.AndroidUtilities;",
        "import com.mr_efes.nagramix.NagramiXSettings;\n\n"
        "import org.telegram.messenger.AndroidUtilities;",
    )
    replace_exact(
        chat_message_cell,
        '''        } else {
            currentTimeString = timeString;
        }
        if (currentMessageObject.isStakedDice()) {''',
        '''        } else {
            currentTimeString = timeString;
        }
        if (currentMessageObject.nagramiXArchivedDeleted) {
            currentTimeString = TextUtils.concat(LocaleController.getString(R.string.NagramiXDeletedLabel), " · ", currentTimeString);
        }
        if (currentMessageObject.isStakedDice()) {''',
    )

    message_object = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "messenger" / "MessageObject.java"
    replace_exact(
        message_object,
        "    public boolean deleted;\n    public boolean deletedByThanos;",
        "    public boolean deleted;\n    public boolean deletedByThanos;\n    public boolean nagramiXArchivedDeleted;",
    )
    replace_exact(
        chat_activity,
        '''            MessageObject obj = chatAdapter != null && chatAdapter.isFiltered ? filteredMessagesDict.get(mid) :  messagesDict[loadIndex].get(mid);
            if (selectedObject != null && obj == selectedObject''',
        '''            MessageObject obj = chatAdapter != null && chatAdapter.isFiltered ? filteredMessagesDict.get(mid) :  messagesDict[loadIndex].get(mid);
            if (sent && obj != null) {
                NagramiXMessageArchive.getInstance(currentAccount).removeLocal(obj.getDialogId(), obj.getId());
            }
            if (!sent && obj != null && NagramiXMessageArchive.getInstance(currentAccount).canDisplayDeleted(obj.messageOwner)) {
                obj.nagramiXArchivedDeleted = true;
                obj.deleted = false;
                int retainedIndex = chatAdapter != null && chatAdapter.isFiltered ? chatAdapter.filteredMessages.indexOf(obj) : messages.indexOf(obj);
                if (chatAdapter != null && retainedIndex >= 0) {
                    chatAdapter.notifyItemChanged(chatAdapter.messagesStartRow + retainedIndex);
                }
                updated = true;
                continue;
            }
            if (selectedObject != null && obj == selectedObject''',
    )
    replace_exact(
        chat_activity,
        '''                } else {
                    clearHistory((Boolean) args[1], (TLRPC.TL_updates_channelDifferenceTooLong) args[2]);
                }
            }
        } else if (id == NotificationCenter.screenshotTook) {''',
        '''                } else {
                    NagramiXMessageArchive.getInstance(currentAccount).clear(dialog_id);
                    clearHistory((Boolean) args[1], (TLRPC.TL_updates_channelDifferenceTooLong) args[2]);
                }
            }
        } else if (id == NotificationCenter.screenshotTook) {''',
    )
    replace_exact(
        chat_message_cell,
        '''    public int getParentWidth() {
        MessageObject object = currentMessageObject == null ? messageObjectToSet : currentMessageObject;''',
        '''    private boolean nagramiXUsesWideBroadcastLayout() {
        MessageObject object = currentMessageObject == null ? messageObjectToSet : currentMessageObject;
        if (object == null || object.messageOwner == null || object.messageOwner.action != null || object.isSponsored()) {
            return false;
        }
        long did = object.getDialogId();
        if (did >= 0 || !NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.WIDE_CHANNEL_POSTS, false)) {
            return false;
        }
        TLRPC.Chat dialogChat = MessagesController.getInstance(currentAccount).getChat(-did);
        return ChatObject.isChannelAndNotMegaGroup(dialogChat);
    }

    private int nagramiXWideContentWidth(int defaultWidth) {
        if (!nagramiXUsesWideBroadcastLayout()) {
            return defaultWidth;
        }
        int parent = AndroidUtilities.isTablet()
                ? AndroidUtilities.getMinTabletSide()
                : Math.min(getParentWidth(), AndroidUtilities.displaySize.y);
        int sideMenu = isSideMenued || isSideMenuEnabled ? ChatActivity.SIDE_MENU_WIDTH : 0;
        return Math.max(defaultWidth, parent - dp(50 + sideMenu));
    }

    public int getParentWidth() {
        MessageObject object = currentMessageObject == null ? messageObjectToSet : currentMessageObject;''',
    )
    wide_range_start = "            } else if (messageObject.isExpiredStory()) {"
    wide_range_end = "        updateWaveform();"
    replace_exact_count_in_range(
        chat_message_cell,
        wide_range_start,
        wide_range_end,
        "dp(270)",
        "nagramiXWideContentWidth(dp(270))",
        10,
    )
    replace_exact_count_in_range(
        chat_message_cell,
        wide_range_start,
        wide_range_end,
        "dp(300)",
        "nagramiXWideContentWidth(dp(300))",
        3,
    )
    replace_exact_count_in_range(
        chat_message_cell,
        wide_range_start,
        wide_range_end,
        "dp(252 + 37)",
        "nagramiXWideContentWidth(dp(252 + 37))",
        6,
    )
    replace_exact(
        chat_message_cell,
        '''                drawName = drawAvatar || isPinnedChat || isSavedChat''',
        '''                maxWidth = nagramiXWideContentWidth(maxWidth);
                drawName = drawAvatar || isPinnedChat || isSavedChat''',
    )
    replace_exact(
        chat_message_cell,
        '''        updateWaveform();
        updateButtonState(false, !messageIdChanged && !messageObject.cancelEditing, true);''',
        '''        if (nagramiXUsesWideBroadcastLayout() && drawBackground) {
            backgroundWidth = nagramiXWideContentWidth(backgroundWidth);
            availableTimeWidth = Math.max(availableTimeWidth, backgroundWidth - dp(31));
        }
        updateWaveform();
        updateButtonState(false, !messageIdChanged && !messageObject.cancelEditing, true);''',
    )
    replace_exact(
        chat_message_cell,
        "                groupMedia.setOverrideWidth(-1);",
        "                groupMedia.setOverrideWidth(nagramiXUsesWideBroadcastLayout() ? nagramiXWideContentWidth(0) - dp(17) : -1);",
    )
    replace_exact(
        chat_message_cell,
        "        int maxWidth = Math.min(dp(500), messageObject.getMaxMessageTextWidth());",
        "        int maxWidth = Math.min(nagramiXWideContentWidth(dp(500)), messageObject.getMaxMessageTextWidth());",
    )
    replace_exact(
        chat_activity,
        "    private MessageObject forwardingMessage;\n    private MessageObject.GroupedMessages forwardingMessageGroup;",
        "    private MessageObject forwardingMessage;\n"
        "    private MessageObject.GroupedMessages forwardingMessageGroup;\n"
        "    private boolean nagramiXCopyAsNew;\n"
        "    private int nagramiXAuthorSearchGeneration;\n"
        "    private int nagramiXAuthorSearchRequestId;\n"
        "    private AlertDialog nagramiXAuthorSearchProgress;\n"
        "    private final SparseBooleanArray nagramiXArchiveLoads = new SparseBooleanArray();",
    )
    replace_exact(
        chat_activity,
        '''        ArrayList<MessageObject> messArr = (ArrayList<MessageObject>) args[2];

        boolean universalNotify = false;''',
        '''        ArrayList<MessageObject> messArr = (ArrayList<MessageObject>) args[2];

        if ((mode == MODE_DEFAULT || mode == MODE_SUGGESTIONS) && currentEncryptedChat == null
                && NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.SHOW_DELETED_MESSAGES, false)
                && !nagramiXArchiveLoads.get(queryLoadIndex)) {
            nagramiXArchiveLoads.put(queryLoadIndex, true);
            int archiveMinDate = 0;
            int archiveMaxDate = 0;
            for (MessageObject item : messArr) {
                int date = item.messageOwner.date;
                archiveMinDate = archiveMinDate == 0 ? date : Math.min(archiveMinDate, date);
                archiveMaxDate = Math.max(archiveMaxDate, date);
            }
            final long expectedDialogId = dialog_id;
            final ArrayList<MessageObject> archiveMessages = messArr;
            NagramiXMessageArchive.getInstance(currentAccount).loadDeleted(dialog_id, archiveMinDate, archiveMaxDate, archived -> {
                if (dialog_id != expectedDialogId || getParentActivity() == null) return;
                java.util.HashSet<Integer> existingIds = new java.util.HashSet<>();
                for (MessageObject item : archiveMessages) existingIds.add(item.getId());
                for (TLRPC.Message message : archived) {
                    if (existingIds.add(message.id)) {
                        MessageObject item = new MessageObject(currentAccount, message, false, true);
                        item.nagramiXArchivedDeleted = true;
                        archiveMessages.add(item);
                    }
                }
                boolean descending = archiveMessages.size() > 1 && archiveMessages.get(0).messageOwner.date > archiveMessages.get(archiveMessages.size() - 1).messageOwner.date;
                java.util.Collections.sort(archiveMessages, (left, right) -> descending
                        ? Integer.compare(right.messageOwner.date, left.messageOwner.date)
                        : Integer.compare(left.messageOwner.date, right.messageOwner.date));
                didReceivedNotification_messagesDidLoad(id, account, args);
            });
            return;
        }

        boolean universalNotify = false;''',
    )
    replace_exact(
        chat_activity,
        "    private final static int forward = 11;",
        "    private final static int forward = 11;\n"
        "    private final static int nagramix_copy_as_new = 102;",
    )
    replace_exact(
        chat_activity,
        '''                } else if (id == forward) {
                    openForward(true);
                } else if (id == share) {''',
        '''                } else if (id == forward) {
                    nagramiXCopyAsNew = false;
                    openForward(true);
                } else if (id == nagramix_copy_as_new) {
                    nagramiXCopyAsNew = true;
                    openForward(true);
                } else if (id == share) {''',
    )
    replace_exact(
        chat_activity,
        '''            if (!isSavedMessages && getDialogId() != UserObject.VERIFY) {
                actionModeViews.add(actionMode.addItemWithWidth(forward, R.drawable.msg_forward, dp(48), LocaleController.getString(R.string.Forward)));
            }''',
        '''            if (!isSavedMessages && getDialogId() != UserObject.VERIFY) {
                actionModeViews.add(actionMode.addItemWithWidth(forward, R.drawable.msg_forward, dp(48), LocaleController.getString(R.string.Forward)));
                actionModeViews.add(actionMode.addItemWithWidth(nagramix_copy_as_new, R.drawable.msg_copy, dp(48), LocaleController.getString(R.string.NagramiXCopyAsNew)));
            }''',
    )
    replace_exact(
        chat_activity,
        '''                if (canForward) {
                    items.add(LocaleController.getString(R.string.Forward));
                    options.add(OPTION_FORWARD);
                    icons.add(R.drawable.msg_forward);
                }''',
        '''                if (canForward) {
                    items.add(LocaleController.getString(R.string.Forward));
                    options.add(OPTION_FORWARD);
                    icons.add(R.drawable.msg_forward);
                    items.add(LocaleController.getString(R.string.NagramiXCopyAsNew));
                    options.add(OPTION_NAGRAMIX_COPY_AS_NEW);
                    icons.add(R.drawable.msg_copy);
                }
                if (selectedObject.getFromChatId() != 0 && selectedObject.getId() > 0 && !DialogObject.isEncryptedDialog(dialog_id)) {
                    items.add(LocaleController.getString(R.string.NagramiXSelectFromAuthor));
                    options.add(OPTION_NAGRAMIX_SELECT_FROM_AUTHOR);
                    icons.add(R.drawable.msg_select);
                }
                if (selectedObject.getId() > 0 && !DialogObject.isEncryptedDialog(dialog_id)
                        && NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.EDIT_HISTORY, false)) {
                    items.add(LocaleController.getString(R.string.NagramiXEditHistory));
                    options.add(OPTION_NAGRAMIX_EDIT_HISTORY);
                    icons.add(R.drawable.msg_edit);
                }''',
    )
    replace_exact(
        chat_activity,
        '''            case OPTION_FORWARD: {
                if (getMessagesController().isFrozen()) {''',
        '''            case OPTION_FORWARD:
            case OPTION_NAGRAMIX_COPY_AS_NEW: {
                nagramiXCopyAsNew = option == OPTION_NAGRAMIX_COPY_AS_NEW;
                if (getMessagesController().isFrozen()) {''',
    )
    replace_exact(
        chat_activity,
        '''            if (selectedObject != null && selectedObject.isHiddenSensitive() && !selectedObject.isMediaSpoilersRevealed) {''',
        '''            if (selectedObject != null && selectedObject.nagramiXArchivedDeleted) {
                items.clear();
                options.clear();
                icons.clear();
                if (!TextUtils.isEmpty(selectedObject.messageOwner.message)) {
                    items.add(LocaleController.getString(R.string.Copy));
                    options.add(OPTION_COPY);
                    icons.add(R.drawable.msg_copy);
                }
                items.add(LocaleController.getString(R.string.NagramiXEditHistory));
                options.add(OPTION_NAGRAMIX_EDIT_HISTORY);
                icons.add(R.drawable.msg_edit);
                items.add(LocaleController.getString(R.string.Delete));
                options.add(OPTION_NAGRAMIX_DELETE_LOCAL);
                icons.add(R.drawable.msg_delete);
            }

            if (selectedObject != null && selectedObject.isHiddenSensitive() && !selectedObject.isMediaSpoilersRevealed) {''',
    )
    replace_exact(
        chat_activity,
        '''            case OPTION_COPY: {
                final TL_iv.RichMessage copyRichMessage''',
        '''            case OPTION_NAGRAMIX_DELETE_LOCAL: {
                ArrayList<Integer> ids = new ArrayList<>();
                ids.add(selectedObject.getId());
                processDeletedMessages(ids, ChatObject.isChannel(currentChat) ? -dialog_id : 0, true, false);
                break;
            }
            case OPTION_NAGRAMIX_EDIT_HISTORY: {
                showNagramiXEditHistory(selectedObject);
                break;
            }
            case OPTION_NAGRAMIX_SELECT_FROM_AUTHOR: {
                startNagramiXSelectFromAuthor(selectedObject);
                break;
            }
            case OPTION_COPY: {
                final TL_iv.RichMessage copyRichMessage''',
    )
    replace_exact(
        chat_activity,
        '''                if (selectedMessagesIds[0].size() + selectedMessagesIds[1].size() >= 100) {
                    AndroidUtilities.shakeView(selectedMessagesCountTextView);
                    Vibrator vibrator = (Vibrator) ApplicationLoader.applicationContext.getSystemService(Context.VIBRATOR_SERVICE);
                    if (vibrator != null) {
                        vibrator.vibrate(200);
                    }
                    return;
                }
                selectedMessagesIds[index].put(messageObject.getId(), messageObject);''',
        '''                selectedMessagesIds[index].put(messageObject.getId(), messageObject);''',
    )
    replace_exact(
        chat_activity,
        '''    private void addToSelectedMessages(MessageObject messageObject, boolean outside) {
        addToSelectedMessages(messageObject, outside, true);
    }''',
        '''    private void showNagramiXEditHistory(MessageObject source) {
        if (source == null) return;
        final long expectedDialogId = dialog_id;
        final int expectedMessageId = source.getId();
        NagramiXMessageArchive.getInstance(currentAccount).loadRevisions(expectedDialogId, expectedMessageId, revisions -> {
            if (dialog_id != expectedDialogId || getParentActivity() == null) return;
            if (revisions.isEmpty()) {
                Toast.makeText(getParentActivity(), LocaleController.getString(R.string.NagramiXNoEditHistory), Toast.LENGTH_SHORT).show();
                return;
            }
            StringBuilder body = new StringBuilder();
            for (int i = 0; i < revisions.size(); i++) {
                TLRPC.Message revision = revisions.get(i);
                if (body.length() > 0) body.append("\\n\\n");
                body.append(i == 0 ? LocaleController.getString(R.string.NagramiXOriginalVersion) : LocaleController.formatDateTime(revision.date, true));
                body.append("\\n").append(revision.message == null ? "" : revision.message);
            }
            body.append("\\n\\n").append(LocaleController.getString(R.string.NagramiXCurrentVersion));
            body.append("\\n").append(source.messageOwner.message == null ? "" : source.messageOwner.message);
            new AlertDialog.Builder(getParentActivity())
                    .setTitle(LocaleController.getString(R.string.NagramiXEditHistory))
                    .setMessage(body.toString())
                    .setPositiveButton(LocaleController.getString(R.string.OK), null)
                    .show();
        });
    }

    private void cancelNagramiXAuthorSearch() {
        nagramiXAuthorSearchGeneration++;
        if (nagramiXAuthorSearchRequestId != 0) {
            getConnectionsManager().cancelRequest(nagramiXAuthorSearchRequestId, true);
            nagramiXAuthorSearchRequestId = 0;
        }
        if (nagramiXAuthorSearchProgress != null) {
            nagramiXAuthorSearchProgress.setOnCancelListener(null);
            nagramiXAuthorSearchProgress.dismiss();
            nagramiXAuthorSearchProgress = null;
        }
    }

    private void startNagramiXSelectFromAuthor(MessageObject sourceMessage) {
        if (sourceMessage == null || sourceMessage.getId() <= 0 || sourceMessage.getFromChatId() == 0 || nagramiXAuthorSearchRequestId != 0) {
            return;
        }
        cancelNagramiXAuthorSearch();
        clearSelectionMode();
        createActionMode();
        actionBar.showActionMode(true, null, null, null, new boolean[]{true}, null, 0);
        bottomViewsVisibilityController.setViewVisible(MESSAGE_ACTION_CONTAINER, true, true);
        if (chatActivityEnterView != null) {
            chatActivityEnterView.preventInput = true;
        }
        addToSelectedMessages(sourceMessage, false);
        updateVisibleRows();

        final int generation = ++nagramiXAuthorSearchGeneration;
        final long expectedDialogId = dialog_id;
        final long expectedTopicId = getTopicId();
        final long fromId = sourceMessage.getFromChatId();
        nagramiXAuthorSearchProgress = new AlertDialog(getParentActivity(), 3);
        nagramiXAuthorSearchProgress.setMessage(LocaleController.formatString(R.string.NagramiXSelectingMessages, 1));
        nagramiXAuthorSearchProgress.setOnCancelListener(dialog -> {
            cancelNagramiXAuthorSearch();
            clearSelectionMode();
        });
        showDialog(nagramiXAuthorSearchProgress);
        loadNagramiXAuthorSearchPage(generation, expectedDialogId, expectedTopicId, fromId, 0);
    }

    private void loadNagramiXAuthorSearchPage(int generation, long expectedDialogId, long expectedTopicId, long fromId, int offsetId) {
        if (generation != nagramiXAuthorSearchGeneration || dialog_id != expectedDialogId || getTopicId() != expectedTopicId) {
            return;
        }
        TLRPC.TL_messages_search request = new TLRPC.TL_messages_search();
        request.peer = getMessagesController().getInputPeer(expectedDialogId);
        request.from_id = getMessagesController().getInputPeer(fromId);
        request.q = "";
        request.filter = new TLRPC.TL_inputMessagesFilterEmpty();
        request.offset_id = offsetId;
        request.limit = 100;
        if (expectedTopicId != 0) {
            request.flags |= 2;
            request.top_msg_id = (int) expectedTopicId;
        }
        nagramiXAuthorSearchRequestId = getConnectionsManager().sendRequest(request, (response, error) -> AndroidUtilities.runOnUIThread(() -> {
            if (generation != nagramiXAuthorSearchGeneration || dialog_id != expectedDialogId || getTopicId() != expectedTopicId) {
                return;
            }
            nagramiXAuthorSearchRequestId = 0;
            if (!(response instanceof TLRPC.messages_Messages)) {
                cancelNagramiXAuthorSearch();
                return;
            }
            TLRPC.messages_Messages result = (TLRPC.messages_Messages) response;
            int nextOffset = offsetId;
            for (TLRPC.Message message : result.messages) {
                nextOffset = nextOffset == 0 ? message.id : Math.min(nextOffset, message.id);
                int index = MessageObject.getDialogId(message) == dialog_id ? 0 : 1;
                if (selectedMessagesIds[index].indexOfKey(message.id) < 0) {
                    addToSelectedMessages(new MessageObject(currentAccount, message, false, true), false, false);
                }
            }
            addToSelectedMessages(null, false, true);
            if (selectedMessagesCountTextView != null) {
                int count = selectedMessagesIds[0].size() + selectedMessagesIds[1].size();
                selectedMessagesCountTextView.setText(LocaleController.formatPluralString("MessagesSelected", count), false);
                if (nagramiXAuthorSearchProgress != null) {
                    nagramiXAuthorSearchProgress.setMessage(LocaleController.formatString(R.string.NagramiXSelectingMessages, count));
                }
            }
            updateVisibleRows();
            if (!result.messages.isEmpty() && result.messages.size() >= request.limit && nextOffset != offsetId) {
                loadNagramiXAuthorSearchPage(generation, expectedDialogId, expectedTopicId, fromId, nextOffset);
            } else {
                cancelNagramiXAuthorSearch();
            }
        }));
        getConnectionsManager().bindRequestToGuid(nagramiXAuthorSearchRequestId, classGuid);
    }

    private void addToSelectedMessages(MessageObject messageObject, boolean outside) {
        addToSelectedMessages(messageObject, outside, true);
    }''',
    )
    replace_exact(
        chat_activity,
        '''    public void clearSelectionMode(boolean suppressUpdateMessageObject) {
        for (int a = 1; a >= 0; a--) {''',
        '''    public void clearSelectionMode(boolean suppressUpdateMessageObject) {
        cancelNagramiXAuthorSearch();
        for (int a = 1; a >= 0; a--) {''',
    )
    replace_exact(
        chat_activity,
        '''    @Override
    public boolean didSelectDialogs(DialogsActivity fragment, ArrayList<MessagesStorage.TopicKey> dids, CharSequence message, boolean param, boolean notify, int scheduleDate, int scheduleRepeatPeriod, TopicsFragment topicsFragment) {
        if ((messagePreviewParams == null''',
        '''    @Override
    public boolean didSelectDialogs(DialogsActivity fragment, ArrayList<MessagesStorage.TopicKey> dids, CharSequence message, boolean param, boolean notify, int scheduleDate, int scheduleRepeatPeriod, TopicsFragment topicsFragment) {
        final boolean copyAsNew = nagramiXCopyAsNew;
        nagramiXCopyAsNew = false;
        if ((messagePreviewParams == null''',
    )
    replace_exact(
        chat_activity,
        '''                    getSendMessagesHelper().sendMessage(fmessages, did, false, false, notify, scheduleDate, scheduleRepeatPeriod, null, -1, price == null ? 0 : price, getSendMonoForumPeerId(), getSendMessageSuggestionParams());''',
        '''                    // Telegram's fromMyName path copies supported content into new
                    // outgoing messages. The picker-provided notify/scheduleDate values keep
                    // native silent and scheduled delivery semantics.
                    getSendMessagesHelper().sendMessage(fmessages, did, copyAsNew, false, notify, scheduleDate, scheduleRepeatPeriod, null, -1, price == null ? 0 : price, getSendMonoForumPeerId(), getSendMessageSuggestionParams());''',
    )
    replace_exact(
        chat_activity,
        '''                    } else {
                        chatActivity.showFieldPanelForForward(true, fmessages);
                    }''',
        '''                    } else {
                        chatActivity.showFieldPanelForForward(true, fmessages);
                        if (copyAsNew && chatActivity.messagePreviewParams != null && chatActivity.messagePreviewParams.forwardMessages != null) {
                            chatActivity.messagePreviewParams.hideForwardSendersName = true;
                        }
                    }''',
    )
    replace_exact(
        chat_activity,
        '''                } else {
                    showFieldPanelForForward(true, fmessages);
                }
                if (AndroidUtilities.isTablet()) {''',
        '''                } else {
                    showFieldPanelForForward(true, fmessages);
                    if (copyAsNew && messagePreviewParams != null && messagePreviewParams.forwardMessages != null) {
                        messagePreviewParams.hideForwardSendersName = true;
                    }
                }
                if (AndroidUtilities.isTablet()) {''',
    )
    replace_exact(
        dialog_stories_cell,
        '''        if (cell.isSelf && !storiesController.hasSelfStories()) {
            if (!MessagesController.getInstance(currentAccount).storiesEnabled()) {''',
        '''        if (cell.isSelf && !storiesController.hasSelfStories()) {
            if (overscroll && NagramiXSettings.INSTANCE.preferences(getContext()).getBoolean(NagramiXSettings.DISABLE_STORY_CAMERA_SWIPE, false)) {
                return;
            }
            if (!MessagesController.getInstance(currentAccount).storiesEnabled()) {''',
    )
    replace_exact(
        peer_stories_view,
        '''    public void setActive(long t, boolean active) {
        if (isActive != active) {''',
        '''    public void setActive(long t, boolean active) {
        if (active && !isActive && currentStory.storyItem != null && storyViewer.requestNagramiXStoryConfirmation(dialogId, currentStory.storyItem, () -> setActive(t, true), () -> {})) {
            return;
        }
        if (isActive != active) {''',
    )
    replace_exact(
        settings_activity,
        '''            case 10:
                presentSettingFragment(new LanguageSelectActivity());
                break;

            case 11:''',
        '''            case 10:
                presentSettingFragment(new LanguageSelectActivity());
                break;
            case 100:
                presentSettingFragment(new NagramiXSettingsActivity());
                break;

            case 11:''',
    )

    launcher_icons = source / "TMessagesProj" / "src" / "main" / "java" / "org" / "telegram" / "ui" / "LauncherIconController.java"
    replace_exact(
        launcher_icons,
        '''        DEFAULT("DefaultIcon", R.drawable.icon_background_sa, R.mipmap.icon_foreground_sa, R.string.AppIconDefault),
        VINTAGE("VintageIcon", R.drawable.icon_6_background_sa, R.mipmap.icon_6_foreground_sa, R.string.AppIconVintage),
        AQUA("AquaIcon", R.drawable.icon_4_background_sa, R.mipmap.icon_foreground_sa, R.string.AppIconAqua),
        PREMIUM("PremiumIcon", R.drawable.icon_3_background_sa, R.mipmap.icon_3_foreground_sa, R.string.AppIconPremium, true),
        TURBO("TurboIcon", R.drawable.icon_5_background_sa, R.mipmap.icon_5_foreground_sa, R.string.AppIconTurbo, true),
        NOX("NoxIcon", R.mipmap.icon_2_background_sa, R.mipmap.icon_foreground_sa, R.string.AppIconNox, true);''',
        '''        DEFAULT("DefaultIcon", R.drawable.nagramix_app_icon_1, android.R.color.transparent, R.string.NagramiXIcon1),
        VINTAGE("VintageIcon", R.drawable.nagramix_app_icon_2, android.R.color.transparent, R.string.NagramiXIcon2),
        AQUA("AquaIcon", R.drawable.nagramix_app_icon_3, android.R.color.transparent, R.string.NagramiXIcon3),
        PREMIUM("PremiumIcon", R.drawable.nagramix_app_icon_4, android.R.color.transparent, R.string.NagramiXIcon4),
        TURBO("TurboIcon", R.drawable.nagramix_app_icon_5, android.R.color.transparent, R.string.NagramiXIcon5),
        NOX("NoxIcon", R.drawable.nagramix_app_icon_6, android.R.color.transparent, R.string.NagramiXIcon6),
        NAGRAMIX_7("NagramiX7Icon", R.drawable.nagramix_app_icon_7, android.R.color.transparent, R.string.NagramiXIcon7),
        NAGRAMIX_8("NagramiX8Icon", R.drawable.nagramix_app_icon_8, android.R.color.transparent, R.string.NagramiXIcon8);''',
    )

    manifests = [
        source / "TMessagesProj" / "config" / "debug" / "AndroidManifest.xml",
        source / "TMessagesProj" / "config" / "debug" / "AndroidManifest_SDK23.xml",
        source / "TMessagesProj" / "config" / "release" / "AndroidManifest.xml",
        source / "TMessagesProj" / "config" / "release" / "AndroidManifest_SDK23.xml",
        source / "TMessagesProj" / "config" / "release" / "AndroidManifest_standalone.xml",
    ]

    icon_components = {
        "DefaultIcon": 1,
        "VintageIcon": 2,
        "AquaIcon": 3,
        "PremiumIcon": 4,
        "TurboIcon": 5,
        "NoxIcon": 6,
    }

    def replace_alias_icon(content: str, component: str, icon_index: int) -> str:
        pattern = rf'(<activity-alias\b(?:(?!</activity-alias>).)*android:name="org\.telegram\.messenger\.{component}"(?:(?!</activity-alias>).)*</activity-alias>)'
        match = re.search(pattern, content, flags=re.DOTALL)
        if match is None:
            return content
        block = match.group(1)
        icon = f"@drawable/nagramix_app_icon_{icon_index}"
        if 'android:icon=' in block:
            block = re.sub(r'android:icon="[^"]+"', f'android:icon="{icon}"', block, count=1)
        else:
            block = block.replace('android:targetActivity="org.telegram.ui.LaunchActivity"', f'android:targetActivity="org.telegram.ui.LaunchActivity"\n            android:icon="{icon}"', 1)
        if 'android:roundIcon=' in block:
            block = re.sub(r'android:roundIcon="[^"]+"', f'android:roundIcon="{icon}"', block, count=1)
        else:
            block = block.replace(f'android:icon="{icon}"', f'android:icon="{icon}"\n            android:roundIcon="{icon}"', 1)
        return content[:match.start(1)] + block + content[match.end(1):]

    base_manifest = source / "TMessagesProj" / "src" / "main" / "AndroidManifest.xml"
    base_content = base_manifest.read_text(encoding="utf-8")
    for component, icon_index in icon_components.items():
        updated = replace_alias_icon(base_content, component, icon_index)
        if updated == base_content:
            raise RuntimeError(f"Missing launcher alias {component} in {base_manifest}")
        base_content = updated
    extra_aliases = """
        <activity-alias
            android:enabled="false"
            android:name="org.telegram.messenger.NagramiX7Icon"
            android:targetActivity="org.telegram.ui.LaunchActivity"
            android:icon="@drawable/nagramix_app_icon_7"
            android:roundIcon="@drawable/nagramix_app_icon_7"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
                <category android:name="android.intent.category.MULTIWINDOW_LAUNCHER" />
            </intent-filter>
            <meta-data android:name="android.app.shortcuts" android:resource="@xml/shortcuts" />
        </activity-alias>
        <activity-alias
            android:enabled="false"
            android:name="org.telegram.messenger.NagramiX8Icon"
            android:targetActivity="org.telegram.ui.LaunchActivity"
            android:icon="@drawable/nagramix_app_icon_8"
            android:roundIcon="@drawable/nagramix_app_icon_8"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
                <category android:name="android.intent.category.MULTIWINDOW_LAUNCHER" />
            </intent-filter>
            <meta-data android:name="android.app.shortcuts" android:resource="@xml/shortcuts" />
        </activity-alias>
"""
    replace_anchor = '''        <activity
            android:name="org.telegram.ui.LaunchActivity"'''
    if base_content.count(replace_anchor) != 1:
        raise RuntimeError("Missing stable launcher-alias insertion anchor")
    base_manifest.write_text(base_content.replace(replace_anchor, extra_aliases + "\n" + replace_anchor), encoding="utf-8")

    for manifest in manifests:
        content = manifest.read_text(encoding="utf-8")
        label_count = content.count('android:label="@string/AppName"') + content.count('android:label="@string/AppNameBeta"')
        if label_count != 1:
            raise RuntimeError(f"Expected one application label in {manifest}; found {label_count}")
        content = content.replace('android:label="@string/AppNameBeta"', 'android:label="@string/NagramiXAppName"')
        content = content.replace('android:label="@string/AppName"', 'android:label="@string/NagramiXAppName"')
        content = re.sub(r'android:icon="@mipmap/ic_launcher(?:_sa)?"', 'android:icon="@drawable/nagramix_app_icon_1"', content)
        content = re.sub(r'android:roundIcon="@mipmap/ic_launcher(?:_round|_sa)?"', 'android:roundIcon="@drawable/nagramix_app_icon_1"', content)
        for component, icon_index in icon_components.items():
            content = replace_alias_icon(content, component, icon_index)
        manifest.write_text(content, encoding="utf-8")

    print(
        "Applied NagramiX Android foundation "
        f"{env['NAGRAMIX_ANDROID_VERSION']} to official Telegram Android "
        f"{env['TELEGRAM_ANDROID_VERSION']} ({actual_ref})"
    )


if __name__ == "__main__":
    main()
