import Foundation
import NagramiXMediaSettings

public enum NagramiXDnsProvider: Int, CaseIterable, Equatable {
    case system = 0
    case google = 1
    case quad9 = 2
    case adGuard = 3
    case mullvad = 4
    case cloudflare = 5
    case customDoh = 6

    public var dohEndpoint: String? {
        switch self {
        case .system:
            return nil
        case .google:
            return "https://dns.google/dns-query"
        case .quad9:
            return "https://dns.quad9.net/dns-query"
        case .adGuard:
            return "https://dns.adguard-dns.com/dns-query"
        case .mullvad:
            return "https://dns.mullvad.net/dns-query"
        case .cloudflare:
            return "https://cloudflare-dns.com/dns-query"
        case .customDoh:
            return nil
        }
    }
}

public struct NagramiXTabSettings: Equatable {
    public static let changedNotification = Notification.Name("NagramiXSettingsChanged")
    public static let wideChannelPostsChangedNotification = Notification.Name("NagramiXWideChannelPostsChanged")
    public static let deletedMessageLabelChangedNotification = Notification.Name("NagramiXDeletedMessageLabelChanged")
    public static let dnsChangedNotification = Notification.Name("NagramiXDnsSettingsChanged")
    public static let softRestartRequestedNotification = Notification.Name("NagramiXTabInterfaceSoftRestartRequested")

    public static let compactChatListChangedNotification = Notification.Name("NagramiXCompactChatListChanged")
    public static let channelBottomPanelChangedNotification = Notification.Name("NagramiXChannelBottomPanelChanged")
    public static let hideReactionsChangedNotification = Notification.Name("NagramiXHideReactionsChanged")

    private enum Key {
        static let hideContacts = "nagramix.tabs.hideContacts"
        static let hideCalls = "nagramix.tabs.hideCalls"
        static let showSearchButton = "nagramix.tabs.showSearchButton"
        static let wideChannelPosts = "nagramix.interface.wideChannelPosts"
        static let videoPiPSwipe = "nagramix.video.pipSwipe"
        static let backgroundVideoPlayback = "nagramix.video.backgroundPlayback"
        static let compactChatList = "nagramix.interface.compactChatList"
        static let showChannelBottomPanel = "nagramix.interface.showChannelBottomPanel"
        static let doubleTapEdit = "nagramix.features.doubleTapEdit"
        static let hideReactions = "nagramix.interface.hideReactions"
        static let chatActionsOnHold = "nagramix.interface.chatActionsOnHold"
        static let showForwardWithoutAuthor = "nagramix.contextMenu.showForwardWithoutAuthor"
        static let showBroadcastMessages = "nagramix.contextMenu.showBroadcastMessages"
        static let showSelectByAuthor = "nagramix.contextMenu.showSelectByAuthor"
        static let useRearCameraForVideoMessages = "nagramix.videoMessages.useRearCamera"
        static let hideStories = "nagramix.stories.hide"
        static let disableStoryCameraSwipe = "nagramix.stories.disableCameraSwipe"
        static let confirmStoryViewing = "nagramix.stories.confirmViewing"
        static let enableStoryRepost = "nagramix.stories.enableRepost"
        static let dnsProvider = "nagramix.network.dnsProvider"
        static let customDohUrl = "nagramix.network.customDohUrl"
        static let proxyAutoSwitchEnabled = "nagramix.network.proxyAutoSwitchEnabled"
        static let proxyAutoSwitchTimeout = "nagramix.network.proxyAutoSwitchTimeout"
        static let showProxyButton = "nagramix.interface.showProxyButton"
        static let hideProxySponsorChannel = "nagramix.interface.hideProxySponsorChannel"
        static let legacyShowProxySponsorChannel = "nagramix.interface.showProxySponsorChannel"
        static let showProfileIds = "nagramix.profiles.showIds"
        static let showRegistrationDate = "nagramix.profiles.showRegistrationDate"
        static let showMutualContactIcon = "nagramix.profiles.showMutualContactIcon"
        static let confirmOutgoingCalls = "nagramix.calls.confirmOutgoing"
        static let forceTcpCalls = "nagramix.calls.forceTcp"
        static let showDeletedMessages = "nagramix.messages.showDeletedMessages"
        static let saveTemporaryMessages = "nagramix.messages.saveTemporaryMessages"
        static let deletedMessageLabel = "nagramix.messages.deletedMessageLabel"
        static let messageEditHistory = "nagramix.messages.editHistory"
    }

    public var hideContacts: Bool
    public var hideCalls: Bool
    public var showSearchButton: Bool
    public var wideChannelPosts: Bool
    public var videoPiPSwipe: Bool
    public var backgroundVideoPlayback: Bool
    public var compactChatList: Bool
    public var showChannelBottomPanel: Bool
    public var doubleTapEdit: Bool
    public var hideReactions: Bool
    public var downloads: NagramiXDownloadSettings
    public var chatActionsOnHold: Bool
    public var showForwardWithoutAuthor: Bool
    public var showBroadcastMessages: Bool
    public var showSelectByAuthor: Bool
    public var useRearCameraForVideoMessages: Bool
    public var hideStories: Bool
    public var disableStoryCameraSwipe: Bool
    public var confirmStoryViewing: Bool
    public var enableStoryRepost: Bool
    public var anonymousStoryViewing: Bool
    public var dnsProvider: NagramiXDnsProvider
    public var customDohUrl: String
    public var proxyAutoSwitchEnabled: Bool
    public var proxyAutoSwitchTimeout: Int
    public var showProxyButton: Bool
    public var hideProxySponsorChannel: Bool
    public var showProfileIds: Bool
    public var showRegistrationDate: Bool
    public var showMutualContactIcon: Bool
    public var confirmOutgoingCalls: Bool
    public var forceTcpCalls: Bool
    public var showDeletedMessages: Bool
    public var saveTemporaryMessages: Bool
    public var deletedMessageLabel: String
    public var messageEditHistory: Bool
    public var media: NagramiXMediaSettings

    public init(
        hideContacts: Bool,
        hideCalls: Bool,
        showSearchButton: Bool,
        wideChannelPosts: Bool,
        useRearCameraForVideoMessages: Bool,
        hideStories: Bool,
        disableStoryCameraSwipe: Bool,
        confirmStoryViewing: Bool,
        enableStoryRepost: Bool,
        dnsProvider: NagramiXDnsProvider,
        customDohUrl: String,
        proxyAutoSwitchEnabled: Bool,
        proxyAutoSwitchTimeout: Int,
        showProxyButton: Bool,
        hideProxySponsorChannel: Bool,
        showProfileIds: Bool,
        showRegistrationDate: Bool,
        showMutualContactIcon: Bool,
        confirmOutgoingCalls: Bool,
        forceTcpCalls: Bool,
        showDeletedMessages: Bool,
        deletedMessageLabel: String,
        messageEditHistory: Bool,
        showForwardWithoutAuthor: Bool = true,
        showSelectByAuthor: Bool = true,
        chatActionsOnHold: Bool = true,
        media: NagramiXMediaSettings = .default,
        compactChatList: Bool = false,
        saveTemporaryMessages: Bool = false,
        videoPiPSwipe: Bool = true,
        backgroundVideoPlayback: Bool = true,
        showChannelBottomPanel: Bool = false,
        doubleTapEdit: Bool = false,
        hideReactions: Bool = false,
        downloads: NagramiXDownloadSettings = .default,
        showBroadcastMessages: Bool = true,
        anonymousStoryViewing: Bool = false
    ) {
        self.hideContacts = hideContacts
        self.hideCalls = hideCalls
        self.showSearchButton = showSearchButton
        self.wideChannelPosts = wideChannelPosts
        self.videoPiPSwipe = videoPiPSwipe
        self.backgroundVideoPlayback = backgroundVideoPlayback
        self.compactChatList = compactChatList
        self.showChannelBottomPanel = showChannelBottomPanel
        self.doubleTapEdit = doubleTapEdit
        self.hideReactions = hideReactions
        self.downloads = downloads
        self.chatActionsOnHold = chatActionsOnHold
        self.media = media
        self.useRearCameraForVideoMessages = useRearCameraForVideoMessages
        self.hideStories = hideStories
        self.disableStoryCameraSwipe = disableStoryCameraSwipe
        self.confirmStoryViewing = confirmStoryViewing
        self.enableStoryRepost = enableStoryRepost
        self.anonymousStoryViewing = anonymousStoryViewing
        self.dnsProvider = dnsProvider
        self.customDohUrl = customDohUrl
        self.proxyAutoSwitchEnabled = proxyAutoSwitchEnabled
        self.proxyAutoSwitchTimeout = proxyAutoSwitchTimeout
        self.showProxyButton = showProxyButton
        self.hideProxySponsorChannel = hideProxySponsorChannel
        self.showProfileIds = showProfileIds
        self.showRegistrationDate = showRegistrationDate
        self.showMutualContactIcon = showMutualContactIcon
        self.confirmOutgoingCalls = confirmOutgoingCalls
        self.forceTcpCalls = forceTcpCalls
        self.showDeletedMessages = showDeletedMessages
        self.saveTemporaryMessages = saveTemporaryMessages
        self.deletedMessageLabel = deletedMessageLabel
        self.messageEditHistory = messageEditHistory
        self.showForwardWithoutAuthor = showForwardWithoutAuthor
        self.showBroadcastMessages = showBroadcastMessages
        self.showSelectByAuthor = showSelectByAuthor
    }

    public static var videoPiPSwipeEnabled: Bool {
        return UserDefaults.standard.object(forKey: Key.videoPiPSwipe) as? Bool ?? true
    }

    public static var backgroundVideoPlaybackEnabled: Bool {
        return UserDefaults.standard.object(forKey: Key.backgroundVideoPlayback) as? Bool ?? true
    }

    public static var compactChatListEnabled: Bool {
        return UserDefaults.standard.object(forKey: Key.compactChatList) as? Bool ?? false
    }

    public static var doubleTapEditEnabled: Bool {
        return UserDefaults.standard.object(forKey: Key.doubleTapEdit) as? Bool ?? false
    }

    public static var hideReactionsEnabled: Bool {
        return UserDefaults.standard.object(forKey: Key.hideReactions) as? Bool ?? false
    }

    public static var channelBottomPanelEnabled: Bool {
        return UserDefaults.standard.object(forKey: Key.showChannelBottomPanel) as? Bool ?? false
    }

    public static var anonymousStoryViewingEnabled: Bool {
        return NagramiXStorySettings.anonymousViewingEnabled
    }

    public static var current: NagramiXTabSettings {
        let defaults = UserDefaults.standard
        let hideProxySponsorChannel: Bool
        if let value = defaults.object(forKey: Key.hideProxySponsorChannel) as? Bool {
            hideProxySponsorChannel = value
        } else if let legacyShowValue = defaults.object(forKey: Key.legacyShowProxySponsorChannel) as? Bool {
            // Legacy builds stored the opposite semantic. Preserve the user's visible
            // result while migrating to the new "hide" setting.
            hideProxySponsorChannel = !legacyShowValue
        } else {
            hideProxySponsorChannel = true
        }
        return NagramiXTabSettings(
            hideContacts: defaults.object(forKey: Key.hideContacts) as? Bool ?? true,
            hideCalls: defaults.object(forKey: Key.hideCalls) as? Bool ?? true,
            showSearchButton: defaults.object(forKey: Key.showSearchButton) as? Bool ?? false,
            wideChannelPosts: defaults.object(forKey: Key.wideChannelPosts) as? Bool ?? true,
            useRearCameraForVideoMessages: defaults.object(forKey: Key.useRearCameraForVideoMessages) as? Bool ?? true,
            hideStories: defaults.object(forKey: Key.hideStories) as? Bool ?? true,
            disableStoryCameraSwipe: defaults.object(forKey: Key.disableStoryCameraSwipe) as? Bool ?? true,
            confirmStoryViewing: defaults.object(forKey: Key.confirmStoryViewing) as? Bool ?? true,
            enableStoryRepost: defaults.object(forKey: Key.enableStoryRepost) as? Bool ?? true,
            dnsProvider: NagramiXDnsProvider(rawValue: defaults.integer(forKey: Key.dnsProvider)) ?? .system,
            customDohUrl: defaults.string(forKey: Key.customDohUrl) ?? "",
            proxyAutoSwitchEnabled: defaults.object(forKey: Key.proxyAutoSwitchEnabled) as? Bool ?? false,
            proxyAutoSwitchTimeout: [15, 30, 60].contains(defaults.integer(forKey: Key.proxyAutoSwitchTimeout)) ? defaults.integer(forKey: Key.proxyAutoSwitchTimeout) : 15,
            showProxyButton: defaults.object(forKey: Key.showProxyButton) as? Bool ?? true,
            hideProxySponsorChannel: hideProxySponsorChannel,
            showProfileIds: defaults.object(forKey: Key.showProfileIds) as? Bool ?? true,
            showRegistrationDate: defaults.object(forKey: Key.showRegistrationDate) as? Bool ?? true,
            showMutualContactIcon: defaults.object(forKey: Key.showMutualContactIcon) as? Bool ?? true,
            confirmOutgoingCalls: defaults.object(forKey: Key.confirmOutgoingCalls) as? Bool ?? true,
            forceTcpCalls: defaults.object(forKey: Key.forceTcpCalls) as? Bool ?? false,
            showDeletedMessages: defaults.object(forKey: Key.showDeletedMessages) as? Bool ?? false,
            deletedMessageLabel: self.normalizedDeletedMessageLabel(defaults.string(forKey: Key.deletedMessageLabel) ?? ""),
            messageEditHistory: defaults.object(forKey: Key.messageEditHistory) as? Bool ?? false,
            showForwardWithoutAuthor: defaults.object(forKey: Key.showForwardWithoutAuthor) as? Bool ?? true,
            showSelectByAuthor: defaults.object(forKey: Key.showSelectByAuthor) as? Bool ?? true,
            chatActionsOnHold: defaults.object(forKey: Key.chatActionsOnHold) as? Bool ?? true,
            media: .current,
            compactChatList: self.compactChatListEnabled,
            saveTemporaryMessages: defaults.object(forKey: Key.saveTemporaryMessages) as? Bool ?? false,
            videoPiPSwipe: self.videoPiPSwipeEnabled,
            backgroundVideoPlayback: self.backgroundVideoPlaybackEnabled,
            showChannelBottomPanel: self.channelBottomPanelEnabled,
            doubleTapEdit: self.doubleTapEditEnabled,
            hideReactions: self.hideReactionsEnabled,
            downloads: .current,
            // Preserve the previous copy-action visibility until explicitly changed.
            showBroadcastMessages: defaults.object(forKey: Key.showBroadcastMessages) as? Bool ?? (defaults.object(forKey: Key.showForwardWithoutAuthor) as? Bool ?? true),
            anonymousStoryViewing: self.anonymousStoryViewingEnabled
        )
    }

    public static func update(_ transform: (inout NagramiXTabSettings) -> Void) {
        var value = self.current
        let previousCompactChatList = value.compactChatList
        let previousChannelBottomPanel = value.showChannelBottomPanel
        let previousHideReactions = value.hideReactions
        let previousWideChannelPosts = value.wideChannelPosts
        let previousDeletedMessageLabel = value.deletedMessageLabel
        let previousDnsProvider = value.dnsProvider
        let previousCustomDohUrl = value.customDohUrl
        transform(&value)

        let defaults = UserDefaults.standard
        defaults.set(value.hideContacts, forKey: Key.hideContacts)
        defaults.set(value.hideCalls, forKey: Key.hideCalls)
        defaults.set(value.showSearchButton, forKey: Key.showSearchButton)
        defaults.set(value.wideChannelPosts, forKey: Key.wideChannelPosts)
        defaults.set(value.videoPiPSwipe, forKey: Key.videoPiPSwipe)
        defaults.set(value.backgroundVideoPlayback, forKey: Key.backgroundVideoPlayback)
        defaults.set(value.compactChatList, forKey: Key.compactChatList)
        defaults.set(value.showChannelBottomPanel, forKey: Key.showChannelBottomPanel)
        defaults.set(value.doubleTapEdit, forKey: Key.doubleTapEdit)
        defaults.set(value.hideReactions, forKey: Key.hideReactions)
        defaults.set(value.chatActionsOnHold, forKey: Key.chatActionsOnHold)
        defaults.set(value.useRearCameraForVideoMessages, forKey: Key.useRearCameraForVideoMessages)
        defaults.set(value.hideStories, forKey: Key.hideStories)
        defaults.set(value.disableStoryCameraSwipe, forKey: Key.disableStoryCameraSwipe)
        defaults.set(value.confirmStoryViewing, forKey: Key.confirmStoryViewing)
        defaults.set(value.enableStoryRepost, forKey: Key.enableStoryRepost)
        NagramiXStorySettings.update(anonymousViewing: value.anonymousStoryViewing)
        defaults.set(value.dnsProvider.rawValue, forKey: Key.dnsProvider)
        defaults.set(value.customDohUrl, forKey: Key.customDohUrl)
        defaults.set(value.proxyAutoSwitchEnabled, forKey: Key.proxyAutoSwitchEnabled)
        defaults.set([15, 30, 60].contains(value.proxyAutoSwitchTimeout) ? value.proxyAutoSwitchTimeout : 15, forKey: Key.proxyAutoSwitchTimeout)
        defaults.set(value.showProxyButton, forKey: Key.showProxyButton)
        defaults.set(value.hideProxySponsorChannel, forKey: Key.hideProxySponsorChannel)
        defaults.set(value.showProfileIds, forKey: Key.showProfileIds)
        defaults.set(value.showRegistrationDate, forKey: Key.showRegistrationDate)
        defaults.set(value.showMutualContactIcon, forKey: Key.showMutualContactIcon)
        defaults.set(value.confirmOutgoingCalls, forKey: Key.confirmOutgoingCalls)
        defaults.set(value.forceTcpCalls, forKey: Key.forceTcpCalls)
        defaults.set(value.showDeletedMessages, forKey: Key.showDeletedMessages)
        defaults.set(value.saveTemporaryMessages, forKey: Key.saveTemporaryMessages)
        value.deletedMessageLabel = self.normalizedDeletedMessageLabel(value.deletedMessageLabel)
        defaults.set(value.deletedMessageLabel, forKey: Key.deletedMessageLabel)
        defaults.set(value.messageEditHistory, forKey: Key.messageEditHistory)
        defaults.set(value.showForwardWithoutAuthor, forKey: Key.showForwardWithoutAuthor)
        defaults.set(value.showBroadcastMessages, forKey: Key.showBroadcastMessages)
        defaults.set(value.showSelectByAuthor, forKey: Key.showSelectByAuthor)
        defaults.removeObject(forKey: Key.legacyShowProxySponsorChannel)

        NagramiXMediaSettings.update(value.media)
        NagramiXDownloadSettings.update(value.downloads)

        NotificationCenter.default.post(name: self.changedNotification, object: nil)
        if previousHideReactions != value.hideReactions {
            NotificationCenter.default.post(name: self.hideReactionsChangedNotification, object: nil)
        }
        if previousChannelBottomPanel != value.showChannelBottomPanel {
            NotificationCenter.default.post(name: self.channelBottomPanelChangedNotification, object: nil)
        }
        if previousCompactChatList != value.compactChatList {
            NotificationCenter.default.post(name: self.compactChatListChangedNotification, object: nil)
        }
        if previousWideChannelPosts != value.wideChannelPosts {
            NotificationCenter.default.post(name: self.wideChannelPostsChangedNotification, object: nil)
        }
        if previousDeletedMessageLabel != value.deletedMessageLabel {
            NotificationCenter.default.post(name: self.deletedMessageLabelChangedNotification, object: nil)
        }
        if previousDnsProvider != value.dnsProvider || previousCustomDohUrl != value.customDohUrl {
            NotificationCenter.default.post(name: self.dnsChangedNotification, object: nil)
        }
    }

    public static func requestTabInterfaceSoftRestart() {
        NotificationCenter.default.post(name: self.softRestartRequestedNotification, object: nil)
    }

    public static func normalizedDeletedMessageLabel(_ value: String) -> String {
        let singleLine = value.replacingOccurrences(of: "\r\n", with: " ")
            .replacingOccurrences(of: "\n", with: " ")
            .replacingOccurrences(of: "\r", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return String(singleLine.prefix(64))
    }
}
