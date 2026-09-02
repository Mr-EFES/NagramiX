package com.mr_efes.nagramix

import android.content.Context
import android.content.SharedPreferences

/**
 * NagramiX-owned Android settings namespace.
 *
 * Product features must depend on these keys rather than NagramX classes. Each
 * feature is implemented against official Telegram Android in the tracked
 * overlay and keeps platform-appropriate Kotlin/Java integration.
 */
object NagramiXSettings {
    private const val PREFERENCES = "nagramix.settings"

    const val HIDE_CONTACTS_TAB = "interface.hideContactsTab"
    const val SHOW_TAB_TITLES = "interface.showTabTitles"
    const val HIDE_STORIES = "interface.hideStories"
    const val REAR_VIDEO_MESSAGES = "videoMessages.useRearCamera"
    const val SHOW_DELETED_MESSAGES = "messages.showDeletedMessages"
    const val EDIT_HISTORY = "messages.editHistory"
    const val FORCE_TCP_CALLS = "calls.forceTcp"
    const val DNS_PROVIDER = "network.dnsProvider"
    const val CUSTOM_DOH_URL = "network.customDohUrl"
    const val PROXY_AUTO_SWITCH = "network.proxyAutoSwitchEnabled"
    const val PROXY_AUTO_SWITCH_TIMEOUT = "network.proxyAutoSwitchTimeout"

    fun preferences(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    fun initializeDefaults(context: Context) {
        val preferences = preferences(context)
        if (preferences.getBoolean("defaults.initialized", false)) {
            return
        }
        preferences.edit()
            .putBoolean(HIDE_CONTACTS_TAB, true)
            .putBoolean(SHOW_TAB_TITLES, true)
            .putBoolean(HIDE_STORIES, false)
            .putBoolean(REAR_VIDEO_MESSAGES, false)
            .putBoolean(SHOW_DELETED_MESSAGES, false)
            .putBoolean(EDIT_HISTORY, false)
            .putBoolean(FORCE_TCP_CALLS, false)
            .putString(DNS_PROVIDER, "system")
            .putBoolean(PROXY_AUTO_SWITCH, false)
            .putInt(PROXY_AUTO_SWITCH_TIMEOUT, 15)
            .putBoolean("defaults.initialized", true)
            .apply()
    }
}
