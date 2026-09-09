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
    const val HIDE_CALLS_TAB = "interface.hideCallsTab"
    const val SHOW_TAB_TITLES = "interface.showTabTitles"
    const val SHOW_SEARCH_TAB = "interface.showSearchTab"
    const val HIDE_STORIES = "interface.hideStories"
    const val DISABLE_STORY_CAMERA_SWIPE = "stories.disableCameraSwipe"
    const val CONFIRM_STORY_VIEWING = "stories.confirmViewing"
    const val ENABLE_STORY_REPOST = "stories.enableRepost"
    const val WIDE_CHANNEL_POSTS = "interface.wideChannelPosts"
    const val REAR_VIDEO_MESSAGES = "videoMessages.useRearCamera"
    const val SHOW_DELETED_MESSAGES = "messages.showDeletedMessages"
    const val EDIT_HISTORY = "messages.editHistory"
    const val FORCE_TCP_CALLS = "calls.forceTcp"
    const val DNS_PROVIDER = "network.dnsProvider"
    const val CUSTOM_DOH_URL = "network.customDohUrl"
    const val PROXY_AUTO_SWITCH = "network.proxyAutoSwitchEnabled"
    const val PROXY_AUTO_SWITCH_TIMEOUT = "network.proxyAutoSwitchTimeout"
    const val SHOW_PROXY_BUTTON = "network.showProxyButton"
    const val HIDE_PROXY_SPONSOR_CHANNEL = "network.hideProxySponsorChannel"
    const val SHOW_PROFILE_IDS = "profiles.showId"
    const val SHOW_REGISTRATION_DATE = "profiles.showRegistrationDate"
    const val SHOW_MUTUAL_CONTACT_ICON = "profiles.showMutualContactIcon"

    fun preferences(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    fun initializeDefaults(context: Context) {
        val preferences = preferences(context)
        if (preferences.getBoolean("defaults.initialized", false)) {
            return
        }
        // Older NagramiX builds wrote feature keys before this initialization
        // marker existed. Seed only absent values so an update can never reset
        // an already selected language-independent product preference.
        val editor = preferences.edit()
        fun booleanDefault(key: String, value: Boolean) {
            if (!preferences.contains(key)) {
                editor.putBoolean(key, value)
            }
        }
        booleanDefault(HIDE_CONTACTS_TAB, true)
        booleanDefault(HIDE_CALLS_TAB, true)
        booleanDefault(SHOW_TAB_TITLES, true)
        booleanDefault(SHOW_SEARCH_TAB, false)
        booleanDefault(HIDE_STORIES, false)
        booleanDefault(DISABLE_STORY_CAMERA_SWIPE, false)
        booleanDefault(CONFIRM_STORY_VIEWING, false)
        booleanDefault(ENABLE_STORY_REPOST, false)
        booleanDefault(WIDE_CHANNEL_POSTS, false)
        booleanDefault(REAR_VIDEO_MESSAGES, false)
        booleanDefault(SHOW_DELETED_MESSAGES, false)
        booleanDefault(EDIT_HISTORY, false)
        booleanDefault(FORCE_TCP_CALLS, false)
        booleanDefault(PROXY_AUTO_SWITCH, false)
        booleanDefault(SHOW_PROXY_BUTTON, true)
        booleanDefault(HIDE_PROXY_SPONSOR_CHANNEL, true)
        booleanDefault(SHOW_PROFILE_IDS, true)
        booleanDefault(SHOW_REGISTRATION_DATE, true)
        booleanDefault(SHOW_MUTUAL_CONTACT_ICON, false)
        if (!preferences.contains(DNS_PROVIDER)) {
            editor.putString(DNS_PROVIDER, "system")
        }
        if (!preferences.contains(PROXY_AUTO_SWITCH_TIMEOUT)) {
            editor.putInt(PROXY_AUTO_SWITCH_TIMEOUT, 15)
        }
        editor.putBoolean("defaults.initialized", true).apply()
    }
}
