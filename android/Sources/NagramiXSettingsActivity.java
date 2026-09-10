package org.telegram.ui;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.net.Uri;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.mr_efes.nagramix.NagramiXSettings;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.MessagesController;
import org.telegram.messenger.NotificationCenter;
import org.telegram.messenger.ProxyRotationController;
import org.telegram.messenger.SharedConfig;
import org.telegram.tgnet.ConnectionsManager;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.AlertDialog;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Cells.HeaderCell;
import org.telegram.ui.Cells.AppIconsSelectorCell;
import org.telegram.ui.Cells.TextCheckCell;
import org.telegram.ui.Cells.TextInfoPrivacyCell;
import org.telegram.ui.Cells.TextSettingsCell;
import org.telegram.ui.Components.LayoutHelper;

/** NagramiX-owned settings UI; product keys remain independent of row placement. */
public class NagramiXSettingsActivity extends BaseFragment {
    private enum Category { INTERFACE, FEATURES, OTHER }

    private LinearLayout content;
    private Category category = Category.INTERFACE;
    private SharedPreferences preferences;

    @Override
    public View createView(Context context) {
        actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        actionBar.setTitle(LocaleController.getString(R.string.NagramiXSettings));
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                }
            }
        });
        preferences = NagramiXSettings.INSTANCE.preferences(context);
        NagramiXSettings.INSTANCE.initializeDefaults(context);

        LinearLayout root = new LinearLayout(context);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray));
        root.addView(createTabs(context), LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, 48));
        ScrollView scrollView = new ScrollView(context);
        content = new LinearLayout(context);
        content.setOrientation(LinearLayout.VERTICAL);
        scrollView.addView(content, LayoutHelper.createScroll(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.TOP));
        root.addView(scrollView, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, 0, 1f));
        fragmentView = root;
        rebuild(context);
        return fragmentView;
    }

    private View createTabs(Context context) {
        LinearLayout tabs = new LinearLayout(context);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        addTab(tabs, context, R.string.NagramiXCategoryInterface, Category.INTERFACE);
        addTab(tabs, context, R.string.NagramiXCategoryFeatures, Category.FEATURES);
        addTab(tabs, context, R.string.NagramiXCategoryOther, Category.OTHER);
        return tabs;
    }

    private void addTab(LinearLayout tabs, Context context, int title, Category value) {
        TextView tab = new TextView(context);
        tab.setGravity(Gravity.CENTER);
        tab.setText(LocaleController.getString(title));
        tab.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlueText));
        tab.setTypeface(Typeface.DEFAULT_BOLD);
        tab.setOnClickListener(v -> { category = value; rebuild(context); });
        tabs.addView(tab, new LinearLayout.LayoutParams(0, AndroidUtilities.dp(48), 1f));
    }

    private void rebuild(Context context) {
        content.removeAllViews();
        if (category == Category.INTERFACE) {
            addHeader(context, R.string.NagramiXSectionInterface);
            addHeader(context, R.string.NagramiXSectionAppIcon);
            content.addView(new AppIconsSelectorCell(context, this, currentAccount), LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
            addCheck(context, R.string.NagramiXHideContacts, NagramiXSettings.HIDE_CONTACTS_TAB, true);
            addCheck(context, R.string.NagramiXHideCalls, NagramiXSettings.HIDE_CALLS_TAB, true);
            addCheck(context, R.string.NagramiXShowTabTitles, NagramiXSettings.SHOW_TAB_TITLES, true);
            addCheck(context, R.string.NagramiXShowSearch, NagramiXSettings.SHOW_SEARCH_TAB, false);
            addCheck(context, R.string.NagramiXShowProxyButton, NagramiXSettings.SHOW_PROXY_BUTTON, true);
            addCheck(context, R.string.NagramiXHideProxySponsor, NagramiXSettings.HIDE_PROXY_SPONSOR_CHANNEL, true);
            addCheck(context, R.string.NagramiXWideChannelPosts, NagramiXSettings.WIDE_CHANNEL_POSTS, false);
        } else if (category == Category.FEATURES) {
            addHeader(context, R.string.NagramiXSectionStories);
            addCheck(context, R.string.NagramiXDisableStorySwipe, NagramiXSettings.DISABLE_STORY_CAMERA_SWIPE, false);
            addCheck(context, R.string.NagramiXConfirmStory, NagramiXSettings.CONFIRM_STORY_VIEWING, false);
            addCheck(context, R.string.NagramiXStoryRepost, NagramiXSettings.ENABLE_STORY_REPOST, false);
            addCheck(context, R.string.NagramiXHideStories, NagramiXSettings.HIDE_STORIES, false);
            addHeader(context, R.string.NagramiXSectionMessages);
            addCheck(context, R.string.NagramiXRearVideoMessages, NagramiXSettings.REAR_VIDEO_MESSAGES, false);
            addCheck(context, R.string.NagramiXDeletedMessages, NagramiXSettings.SHOW_DELETED_MESSAGES, false);
            addInfo(context, R.string.NagramiXDeletedMessagesInfo);
            addCheck(context, R.string.NagramiXEditHistory, NagramiXSettings.EDIT_HISTORY, false);
            addInfo(context, R.string.NagramiXEditHistoryInfo);
        } else {
            addHeader(context, R.string.NagramiXSectionProfiles);
            addCheck(context, R.string.NagramiXShowProfileIds, NagramiXSettings.SHOW_PROFILE_IDS, true);
            addCheck(context, R.string.NagramiXShowRegistrationDate, NagramiXSettings.SHOW_REGISTRATION_DATE, true);
            addCheck(context, R.string.NagramiXShowMutualContactIcon, NagramiXSettings.SHOW_MUTUAL_CONTACT_ICON, false);
            addHeader(context, R.string.NagramiXSectionNetwork);
            addDnsProvider(context);
            addProxySettings(context);
            addHeader(context, R.string.NagramiXSectionCalls);
            addCheck(context, R.string.NagramiXForceTcp, NagramiXSettings.FORCE_TCP_CALLS, false);
            addInfo(context, R.string.NagramiXForceTcpInfo);
        }
    }

    private static final String[] DNS_PROVIDERS = {"system", "google", "quad9", "adguard", "mullvad", "cloudflare", "custom"};

    private void addProxySettings(Context context) {
        TextSettingsCell proxies = new TextSettingsCell(context);
        proxies.setText(LocaleController.getString(R.string.NagramiXProxySettings), false);
        proxies.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
        proxies.setOnClickListener(v -> presentFragment(new ProxyListActivity()));
        content.addView(proxies, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));

        addCheck(context, R.string.NagramiXProxyAutoSwitch, NagramiXSettings.PROXY_AUTO_SWITCH, false);
        if (preferences.getBoolean(NagramiXSettings.PROXY_AUTO_SWITCH, false)) {
            int seconds = preferences.getInt(NagramiXSettings.PROXY_AUTO_SWITCH_TIMEOUT, 15);
            TextSettingsCell timeout = new TextSettingsCell(context);
            timeout.setTextAndValue(LocaleController.getString(R.string.NagramiXProxySwitchAfter), LocaleController.formatString(R.string.NagramiXSeconds, seconds), false);
            timeout.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
            timeout.setOnClickListener(v -> {
                int next = seconds == 15 ? 30 : seconds == 30 ? 60 : 15;
                preferences.edit().putInt(NagramiXSettings.PROXY_AUTO_SWITCH_TIMEOUT, next).apply();
                applyNativeProxyRotation(true, next);
                rebuild(context);
            });
            content.addView(timeout, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        }
    }

    private void applyNativeProxyRotation(boolean enabled, int seconds) {
        int timeoutIndex = ProxyRotationController.ROTATION_TIMEOUTS.indexOf(seconds);
        if (timeoutIndex < 0) {
            timeoutIndex = ProxyRotationController.ROTATION_TIMEOUTS.indexOf(15);
        }
        SharedConfig.proxyRotationEnabled = enabled;
        SharedConfig.proxyRotationTimeout = timeoutIndex;
        MessagesController.getGlobalMainSettings().edit()
                .putBoolean("proxyRotationEnabled", enabled)
                .putInt("proxyRotationTimeout", timeoutIndex)
                .apply();
        NotificationCenter.getGlobalInstance().postNotificationName(NotificationCenter.proxySettingsChanged);
    }

    private int dnsProviderName(String value) {
        switch (value) {
            case "google": return R.string.NagramiXDnsGoogle;
            case "quad9": return R.string.NagramiXDnsQuad9;
            case "adguard": return R.string.NagramiXDnsAdGuard;
            case "mullvad": return R.string.NagramiXDnsMullvad;
            case "cloudflare": return R.string.NagramiXDnsCloudflare;
            case "custom": return R.string.NagramiXDnsCustom;
            default: return R.string.NagramiXDnsSystem;
        }
    }

    private void addDnsProvider(Context context) {
        String provider = preferences.getString(NagramiXSettings.DNS_PROVIDER, "system");
        TextSettingsCell cell = new TextSettingsCell(context);
        cell.setTextAndValue(LocaleController.getString(R.string.NagramiXDnsProvider), LocaleController.getString(dnsProviderName(provider)), false);
        cell.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
        cell.setOnClickListener(v -> {
            int index = java.util.Arrays.asList(DNS_PROVIDERS).indexOf(provider);
            String next = DNS_PROVIDERS[(Math.max(index, 0) + 1) % DNS_PROVIDERS.length];
            if ("custom".equals(next)) {
                editCustomDoh(context);
            } else {
                preferences.edit().putString(NagramiXSettings.DNS_PROVIDER, next).apply();
                ConnectionsManager.invalidateNagramiXDnsCache();
                rebuild(context);
            }
        });
        content.addView(cell, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        if ("custom".equals(provider)) {
            TextSettingsCell custom = new TextSettingsCell(context);
            custom.setTextAndValue(LocaleController.getString(R.string.NagramiXCustomDohUrl), preferences.getString(NagramiXSettings.CUSTOM_DOH_URL, ""), false);
            custom.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
            custom.setOnClickListener(v -> editCustomDoh(context));
            content.addView(custom, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
        }
    }

    private void editCustomDoh(Context context) {
        EditText input = new EditText(context);
        input.setSingleLine(true);
        input.setHint(LocaleController.getString(R.string.NagramiXCustomDohHint));
        input.setText(preferences.getString(NagramiXSettings.CUSTOM_DOH_URL, ""));
        input.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
        input.setHintTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteHintText));
        int padding = AndroidUtilities.dp(24);
        input.setPadding(padding, 0, padding, 0);
        new AlertDialog.Builder(context, getResourceProvider())
                .setTitle(LocaleController.getString(R.string.NagramiXCustomDohUrl))
                .setView(input)
                .setNegativeButton(LocaleController.getString(R.string.Cancel), null)
                .setPositiveButton(LocaleController.getString(R.string.Save), (dialog, which) -> {
                    String value = input.getText().toString().trim();
                    Uri uri = Uri.parse(value);
                    if ("https".equalsIgnoreCase(uri.getScheme()) && uri.getHost() != null) {
                        preferences.edit().putString(NagramiXSettings.CUSTOM_DOH_URL, value).putString(NagramiXSettings.DNS_PROVIDER, "custom").apply();
                        ConnectionsManager.invalidateNagramiXDnsCache();
                        rebuild(context);
                    } else {
                        Toast.makeText(getParentActivity(), LocaleController.getString(R.string.NagramiXInvalidDoh), Toast.LENGTH_SHORT).show();
                    }
                }).show();
    }

    private void addHeader(Context context, int text) {
        HeaderCell cell = new HeaderCell(context);
        cell.setText(LocaleController.getString(text));
        content.addView(cell, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
    }

    private void addCheck(Context context, int text, String key, boolean fallback) {
        TextCheckCell cell = new TextCheckCell(context);
        cell.setTextAndCheck(LocaleController.getString(text), preferences.getBoolean(key, fallback), false);
        cell.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
        cell.setOnClickListener(v -> {
            boolean value = !preferences.getBoolean(key, fallback);
            preferences.edit().putBoolean(key, value).apply();
            cell.setChecked(value);
            if (NagramiXSettings.WIDE_CHANNEL_POSTS.equals(key)) {
                NotificationCenter.getInstance(currentAccount).postNotificationName(
                        NotificationCenter.updateInterfaces,
                        MessagesController.UPDATE_MASK_ALL
                );
            } else if (NagramiXSettings.PROXY_AUTO_SWITCH.equals(key)) {
                applyNativeProxyRotation(value, preferences.getInt(NagramiXSettings.PROXY_AUTO_SWITCH_TIMEOUT, 15));
                rebuild(context);
            } else if (NagramiXSettings.HIDE_PROXY_SPONSOR_CHANNEL.equals(key)) {
                MessagesController.getInstance(currentAccount).checkPromoInfo(true);
            }
        });
        content.addView(cell, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
    }

    private void addInfo(Context context, int text) {
        TextInfoPrivacyCell cell = new TextInfoPrivacyCell(context);
        cell.setText(LocaleController.getString(text));
        content.addView(cell, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT));
    }
}
