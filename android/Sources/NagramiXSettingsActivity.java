package org.telegram.ui;

import android.content.Context;
import android.content.SharedPreferences;
import android.text.InputType;
import android.text.TextUtils;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.FrameLayout;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.mr_efes.nagramix.NagramiXSettings;

import org.telegram.messenger.LocaleController;
import org.telegram.messenger.NotificationCenter;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.AlertDialog;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Cells.HeaderCell;
import org.telegram.ui.Cells.TextCheckCell;
import org.telegram.ui.Cells.TextInfoPrivacyCell;
import org.telegram.ui.Cells.TextSettingsCell;
import org.telegram.ui.Components.LayoutHelper;
import org.telegram.ui.Components.ListView.AdapterWithDiffUtils;
import org.telegram.ui.Components.RecyclerListView;

import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** NagramiX-owned settings surface backed only by the canonical preference contract. */
public class NagramiXSettingsActivity extends BaseFragment {
    private static final int HEADER = 0;
    private static final int CHECK = 1;
    private static final int INFO = 2;
    private static final int ACTION = 3;
    private static final int DNS = 4;

    private final ArrayList<Item> items = new ArrayList<>();
    private SharedPreferences preferences;
    private RecyclerListView listView;
    private final ExecutorService dnsValidationExecutor = Executors.newSingleThreadExecutor();
    private int dnsValidationGeneration;

    @Override
    public void onFragmentDestroy() {
        dnsValidationGeneration++;
        dnsValidationExecutor.shutdownNow();
        super.onFragmentDestroy();
    }

    @Override
    public View createView(Context context) {
        NagramiXSettings.INSTANCE.initializeDefaults(context);
        preferences = NagramiXSettings.INSTANCE.preferences(context);
        items.clear();

        actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        actionBar.setAllowOverlayTitle(true);
        actionBar.setTitle(LocaleController.getString(R.string.NagramiXSettingsTitle));
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) finishFragment();
            }
        });

        addHeader(R.string.NagramiXCategoryInterface);
        addCheck(NagramiXSettings.HIDE_CONTACTS_TAB, R.string.NagramiXHideContactsTab);
        addCheck(NagramiXSettings.HIDE_CALLS_TAB, R.string.NagramiXHideCallsTab);
        addCheck(NagramiXSettings.SHOW_TAB_TITLES, R.string.NagramiXShowTabTitles);
        addCheck(NagramiXSettings.SHOW_SEARCH_TAB, R.string.NagramiXShowSearchTab);
        addCheck(NagramiXSettings.HIDE_STORIES, R.string.NagramiXHideStories);
        addCheck(NagramiXSettings.WIDE_CHANNEL_POSTS, R.string.NagramiXWideChannelPosts);
        addCheck(NagramiXSettings.SHOW_PROFILE_ID, R.string.NagramiXShowProfileId);
        addCheck(NagramiXSettings.SHOW_REGISTRATION_DATE, R.string.NagramiXShowRegistrationDate);
        addCheck(NagramiXSettings.SHOW_MUTUAL_CONTACT_ICON, R.string.NagramiXShowMutualContactIcon);
        addInfo(R.string.NagramiXInterfaceInfo);

        addHeader(R.string.NagramiXCategoryFeatures);
        addCheck(NagramiXSettings.REAR_VIDEO_MESSAGES, R.string.NagramiXRearVideoMessages);
        addCheck(NagramiXSettings.DISABLE_STORY_CAMERA_SWIPE, R.string.NagramiXDisableStoryCameraSwipe);
        addCheck(NagramiXSettings.CONFIRM_STORY_VIEWING, R.string.NagramiXConfirmStoryViewing);
        addCheck(NagramiXSettings.ENABLE_STORY_REPOST, R.string.NagramiXEnableStoryRepost);
        addCheck(NagramiXSettings.CONFIRM_OUTGOING_CALLS, R.string.NagramiXConfirmOutgoingCalls);
        addCheck(NagramiXSettings.SHOW_DELETED_MESSAGES, R.string.NagramiXShowDeletedMessages);
        addCheck(NagramiXSettings.EDIT_HISTORY, R.string.NagramiXEditHistory);
        addCheck(NagramiXSettings.FORCE_TCP_CALLS, R.string.NagramiXForceTcpCalls);
        addAction(R.string.NagramiXClearArchive);
        addInfo(R.string.NagramiXFeaturesInfo);

        addHeader(R.string.NagramiXCategoryOther);
        addDns();
        addCheck(NagramiXSettings.PROXY_AUTO_SWITCH, R.string.NagramiXProxyAutoSwitch);
        addCheck(NagramiXSettings.SHOW_PROXY_BUTTON, R.string.NagramiXShowProxyButton);
        addCheck(NagramiXSettings.HIDE_PROXY_SPONSOR_CHANNEL, R.string.NagramiXHideProxySponsorChannel);
        addInfo(R.string.NagramiXOtherInfo);

        fragmentView = new FrameLayout(context);
        fragmentView.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray));
        listView = new RecyclerListView(context);
        listView.setLayoutManager(new LinearLayoutManager(context));
        listView.setVerticalScrollBarEnabled(false);
        listView.setAdapter(new ListAdapter());
        listView.setOnItemClickListener((view, position) -> {
            if (position < 0 || position >= items.size()) return;
            Item item = items.get(position);
            if (item.viewType == ACTION) {
                AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity(), resourceProvider);
                builder.setTitle(LocaleController.getString(R.string.NagramiXClearArchive));
                builder.setMessage(LocaleController.getString(R.string.NagramiXClearArchiveConfirm));
                builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);
                builder.setPositiveButton(LocaleController.getString(R.string.Delete), (dialog, which) ->
                        com.mr_efes.nagramix.NagramiXMessageArchive.getInstance(currentAccount).clearAll());
                showDialog(builder.create());
                return;
            }
            if (item.viewType == DNS) {
                showDnsProviders();
                return;
            }
            if (item.key == null) return;
            boolean value = !preferences.getBoolean(item.key, NagramiXSettings.booleanDefault(item.key));
            preferences.edit().putBoolean(item.key, value).apply();
            ((TextCheckCell) view).setChecked(value);
            NotificationCenter.getInstance(currentAccount).postNotificationName(NotificationCenter.updateInterfaces, org.telegram.messenger.MessagesController.UPDATE_MASK_ALL);
        });
        ((FrameLayout) fragmentView).addView(listView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT));
        return fragmentView;
    }

    private void addHeader(int text) { items.add(new Item(HEADER, null, text)); }
    private void addCheck(String key, int text) { items.add(new Item(CHECK, key, text)); }
    private void addInfo(int text) { items.add(new Item(INFO, null, text)); }
    private void addAction(int text) { items.add(new Item(ACTION, null, text)); }
    private void addDns() { items.add(new Item(DNS, NagramiXSettings.DNS_PROVIDER, R.string.NagramiXDns)); }

    private void showDnsProviders() {
        CharSequence[] labels = new CharSequence[] {
                LocaleController.getString(R.string.NagramiXDnsSystem),
                "Google DNS", "Quad9", "AdGuard DNS", "Mullvad DNS", "Cloudflare DNS",
                LocaleController.getString(R.string.NagramiXDnsCustom)
        };
        String[] values = new String[] {"system", "google", "quad9", "adguard", "mullvad", "cloudflare", "custom"};
        AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity(), resourceProvider);
        builder.setTitle(LocaleController.getString(R.string.NagramiXDns));
        builder.setItems(labels, (dialog, which) -> {
            if (which == values.length - 1) {
                showCustomDohEditor();
            } else {
                dnsValidationGeneration++;
                preferences.edit().putString(NagramiXSettings.DNS_PROVIDER, values[which]).apply();
                clearDnsCache();
                notifyListChanged();
            }
        });
        showDialog(builder.create());
    }

    private void showCustomDohEditor() {
        EditText input = new EditText(getParentActivity());
        input.setSingleLine(true);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setHint("https://example.com/dns-query");
        input.setText(preferences.getString(NagramiXSettings.CUSTOM_DOH_URL, ""));
        int padding = org.telegram.messenger.AndroidUtilities.dp(24);
        FrameLayout container = new FrameLayout(getParentActivity());
        container.setPadding(padding, 0, padding, 0);
        container.addView(input, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, 50));
        AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity(), resourceProvider);
        builder.setTitle(LocaleController.getString(R.string.NagramiXCustomDohUrl));
        builder.setView(container);
        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);
        builder.setPositiveButton(LocaleController.getString(R.string.Save), null);
        AlertDialog dialog = builder.create();
        final int generation = ++dnsValidationGeneration;
        dialog.setOnDismissListener(ignored -> {
            if (dnsValidationGeneration == generation) dnsValidationGeneration++;
        });
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view -> {
            String value = input.getText().toString().trim();
            if (!com.mr_efes.nagramix.NagramiXDnsResolver.isValidEndpoint(value)) {
                input.setError(LocaleController.getString(R.string.NagramiXDnsInvalid));
                return;
            }
            input.setEnabled(false);
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setEnabled(false);
            dnsValidationExecutor.execute(() -> {
                boolean available = com.mr_efes.nagramix.NagramiXDnsResolver.testEndpoint(value);
                org.telegram.messenger.AndroidUtilities.runOnUIThread(() -> {
                    if (dnsValidationGeneration != generation || !dialog.isShowing()) return;
                    if (!available) {
                        input.setEnabled(true);
                        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setEnabled(true);
                        input.setError(LocaleController.getString(R.string.NagramiXDnsUnavailable));
                        return;
                    }
                    preferences.edit().putString(NagramiXSettings.CUSTOM_DOH_URL, value)
                            .putString(NagramiXSettings.DNS_PROVIDER, "custom").apply();
                    clearDnsCache();
                    dialog.dismiss();
                    notifyListChanged();
                });
            });
        }));
        showDialog(dialog);
    }

    private void clearDnsCache() {
        org.telegram.tgnet.ConnectionsManager.nagramixClearDnsCache();
    }

    private void notifyListChanged() {
        if (listView != null && listView.getAdapter() != null) listView.getAdapter().notifyDataSetChanged();
    }

    private static final class Item extends AdapterWithDiffUtils.Item {
        final String key;
        final int text;
        Item(int type, String key, int text) { super(type, false); this.key = key; this.text = text; }
    }

    private final class ListAdapter extends RecyclerListView.SelectionAdapter {
        @Override
        public boolean isEnabled(RecyclerView.ViewHolder holder) { return holder.getItemViewType() == CHECK || holder.getItemViewType() == ACTION || holder.getItemViewType() == DNS; }
        @Override
        public int getItemCount() { return items.size(); }
        @Override
        public int getItemViewType(int position) { return items.get(position).viewType; }

        @NonNull
        @Override
        public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int type) {
            View view = type == HEADER ? new HeaderCell(getContext()) : type == CHECK ? new TextCheckCell(getContext()) : type == ACTION || type == DNS ? new TextSettingsCell(getContext()) : new TextInfoPrivacyCell(getContext());
            return new RecyclerListView.Holder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
            Item item = items.get(position);
            CharSequence text = LocaleController.getString(item.text);
            if (item.viewType == HEADER) {
                ((HeaderCell) holder.itemView).setText(text);
            } else if (item.viewType == CHECK) {
                boolean divider = position + 1 < items.size() && items.get(position + 1).viewType == CHECK;
                ((TextCheckCell) holder.itemView).setTextAndCheck(text, preferences.getBoolean(item.key, NagramiXSettings.booleanDefault(item.key)), divider);
            } else if (item.viewType == ACTION) {
                TextSettingsCell cell = (TextSettingsCell) holder.itemView;
                cell.setTextColor(Theme.getColor(Theme.key_text_RedRegular));
                cell.setText(text, false);
            } else if (item.viewType == DNS) {
                String provider = preferences.getString(NagramiXSettings.DNS_PROVIDER, "system");
                ((TextSettingsCell) holder.itemView).setTextAndValue(text, dnsProviderTitle(provider), false);
            } else {
                TextInfoPrivacyCell cell = (TextInfoPrivacyCell) holder.itemView;
                cell.setText(TextUtils.isEmpty(text) ? null : text);
            }
        }
    }

    private String dnsProviderTitle(String provider) {
        if ("google".equals(provider)) return "Google DNS";
        if ("quad9".equals(provider)) return "Quad9";
        if ("adguard".equals(provider)) return "AdGuard DNS";
        if ("mullvad".equals(provider)) return "Mullvad DNS";
        if ("cloudflare".equals(provider)) return "Cloudflare DNS";
        if ("custom".equals(provider)) return LocaleController.getString(R.string.NagramiXDnsCustom);
        return LocaleController.getString(R.string.NagramiXDnsSystem);
    }
}
