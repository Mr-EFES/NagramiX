package com.mr_efes.nagramix

import android.content.Context
import android.content.SharedPreferences

/**
 * NagramiX-owned Android settings namespace.
 *
 * Product features depend on these canonical keys. Each feature is implemented
 * against official Telegram Android in the tracked overlay and keeps
 * platform-appropriate Kotlin/Java integration.
 */
object NagramiXSettings {
    private const val PREFERENCES = "nagramix.settings"

    const val HIDE_CONTACTS_TAB = "interface.hideContactsTab"
    const val HIDE_CALLS_TAB = "interface.hideCallsTab"
    const val SHOW_TAB_TITLES = "interface.showTabTitles"
    const val SHOW_SEARCH_TAB = "interface.showSearchTab"
    const val HIDE_STORIES = "interface.hideStories"
    const val WIDE_CHANNEL_POSTS = "interface.wideChannelPosts"
    const val REAR_VIDEO_MESSAGES = "videoMessages.useRearCamera"
    const val DISABLE_STORY_CAMERA_SWIPE = "stories.disableCameraSwipe"
    const val CONFIRM_STORY_VIEWING = "stories.confirmViewing"
    const val ENABLE_STORY_REPOST = "stories.enableRepost"
    const val CONFIRM_OUTGOING_CALLS = "calls.confirmOutgoing"
    const val SHOW_DELETED_MESSAGES = "messages.showDeletedMessages"
    const val EDIT_HISTORY = "messages.editHistory"
    const val FORCE_TCP_CALLS = "calls.forceTcp"
    const val SHOW_PROFILE_ID = "profiles.showId"
    const val SHOW_REGISTRATION_DATE = "profiles.showRegistrationDate"
    const val SHOW_MUTUAL_CONTACT_ICON = "profiles.showMutualContactIcon"
    const val DNS_PROVIDER = "network.dnsProvider"
    const val CUSTOM_DOH_URL = "network.customDohUrl"
    const val PROXY_AUTO_SWITCH = "network.proxyAutoSwitchEnabled"
    const val PROXY_AUTO_SWITCH_TIMEOUT = "network.proxyAutoSwitchTimeout"
    const val SHOW_PROXY_BUTTON = "network.showProxyButton"
    const val HIDE_PROXY_SPONSOR_CHANNEL = "network.hideProxySponsorChannel"

    fun preferences(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    fun initializeDefaults(context: Context) {
        val preferences = preferences(context)
        if (preferences.getBoolean("defaults.initialized", false)) {
            return
        }
        preferences.edit()
            .putBoolean(HIDE_CONTACTS_TAB, true)
            .putBoolean(HIDE_CALLS_TAB, true)
            .putBoolean(SHOW_TAB_TITLES, true)
            .putBoolean(SHOW_SEARCH_TAB, false)
            .putBoolean(HIDE_STORIES, false)
            .putBoolean(WIDE_CHANNEL_POSTS, false)
            .putBoolean(REAR_VIDEO_MESSAGES, false)
            .putBoolean(DISABLE_STORY_CAMERA_SWIPE, false)
            .putBoolean(CONFIRM_STORY_VIEWING, false)
            .putBoolean(ENABLE_STORY_REPOST, false)
            .putBoolean(CONFIRM_OUTGOING_CALLS, true)
            .putBoolean(SHOW_DELETED_MESSAGES, false)
            .putBoolean(EDIT_HISTORY, false)
            .putBoolean(FORCE_TCP_CALLS, false)
            .putBoolean(SHOW_PROFILE_ID, true)
            .putBoolean(SHOW_REGISTRATION_DATE, true)
            .putBoolean(SHOW_MUTUAL_CONTACT_ICON, false)
            .putString(DNS_PROVIDER, "system")
            .putBoolean(PROXY_AUTO_SWITCH, false)
            .putInt(PROXY_AUTO_SWITCH_TIMEOUT, 15)
            .putBoolean(SHOW_PROXY_BUTTON, true)
            .putBoolean(HIDE_PROXY_SPONSOR_CHANNEL, true)
            .putBoolean("defaults.initialized", true)
            .apply()
    }

    @JvmStatic
    fun booleanDefault(key: String): Boolean = when (key) {
        HIDE_CONTACTS_TAB,
        HIDE_CALLS_TAB,
        SHOW_TAB_TITLES,
        CONFIRM_OUTGOING_CALLS,
        SHOW_PROFILE_ID,
        SHOW_REGISTRATION_DATE,
        SHOW_PROXY_BUTTON,
        HIDE_PROXY_SPONSOR_CHANNEL -> true
        else -> false
    }
}
