import Foundation

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
    public static let dnsChangedNotification = Notification.Name("NagramiXDnsSettingsChanged")
    public static let softRestartRequestedNotification = Notification.Name("NagramiXTabInterfaceSoftRestartRequested")

    private enum Key {
        static let hideContacts = "nagramix.tabs.hideContacts"
        static let hideCalls = "nagramix.tabs.hideCalls"
        static let showSearchButton = "nagramix.tabs.showSearchButton"
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
        static let showChatCreationDate = "nagramix.profiles.showChatCreationDate"
        static let confirmOutgoingCalls = "nagramix.calls.confirmOutgoing"
    }

    public var hideContacts: Bool
    public var hideCalls: Bool
    public var showSearchButton: Bool
    public var useRearCameraForVideoMessages: Bool
    public var hideStories: Bool
    public var disableStoryCameraSwipe: Bool
    public var confirmStoryViewing: Bool
    public var enableStoryRepost: Bool
    public var dnsProvider: NagramiXDnsProvider
    public var customDohUrl: String
    public var proxyAutoSwitchEnabled: Bool
    public var proxyAutoSwitchTimeout: Int
    public var showProxyButton: Bool
    public var hideProxySponsorChannel: Bool
    public var showProfileIds: Bool
    public var showRegistrationDate: Bool
    public var showChatCreationDate: Bool
    public var confirmOutgoingCalls: Bool

    public init(
        hideContacts: Bool,
        hideCalls: Bool,
        showSearchButton: Bool,
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
        showChatCreationDate: Bool,
        confirmOutgoingCalls: Bool
    ) {
        self.hideContacts = hideContacts
        self.hideCalls = hideCalls
        self.showSearchButton = showSearchButton
        self.useRearCameraForVideoMessages = useRearCameraForVideoMessages
        self.hideStories = hideStories
        self.disableStoryCameraSwipe = disableStoryCameraSwipe
        self.confirmStoryViewing = confirmStoryViewing
        self.enableStoryRepost = enableStoryRepost
        self.dnsProvider = dnsProvider
        self.customDohUrl = customDohUrl
        self.proxyAutoSwitchEnabled = proxyAutoSwitchEnabled
        self.proxyAutoSwitchTimeout = proxyAutoSwitchTimeout
        self.showProxyButton = showProxyButton
        self.hideProxySponsorChannel = hideProxySponsorChannel
        self.showProfileIds = showProfileIds
        self.showRegistrationDate = showRegistrationDate
        self.showChatCreationDate = showChatCreationDate
        self.confirmOutgoingCalls = confirmOutgoingCalls
    }

    public static var current: NagramiXTabSettings {
        let defaults = UserDefaults.standard
        let hideProxySponsorChannel: Bool
        if let value = defaults.object(forKey: Key.hideProxySponsorChannel) as? Bool {
            hideProxySponsorChannel = value
        } else if let legacyShowValue = defaults.object(forKey: Key.legacyShowProxySponsorChannel) as? Bool {
            // 0.2.0 stored the opposite semantic. Preserve the user's visible
            // result while migrating to the new "hide" setting.
            hideProxySponsorChannel = !legacyShowValue
        } else {
            hideProxySponsorChannel = true
        }
        return NagramiXTabSettings(
            hideContacts: defaults.object(forKey: Key.hideContacts) as? Bool ?? true,
            hideCalls: defaults.object(forKey: Key.hideCalls) as? Bool ?? true,
            showSearchButton: defaults.object(forKey: Key.showSearchButton) as? Bool ?? false,
            useRearCameraForVideoMessages: defaults.object(forKey: Key.useRearCameraForVideoMessages) as? Bool ?? true,
            hideStories: defaults.object(forKey: Key.hideStories) as? Bool ?? false,
            disableStoryCameraSwipe: defaults.object(forKey: Key.disableStoryCameraSwipe) as? Bool ?? false,
            confirmStoryViewing: defaults.object(forKey: Key.confirmStoryViewing) as? Bool ?? false,
            enableStoryRepost: defaults.object(forKey: Key.enableStoryRepost) as? Bool ?? false,
            dnsProvider: NagramiXDnsProvider(rawValue: defaults.integer(forKey: Key.dnsProvider)) ?? .system,
            customDohUrl: defaults.string(forKey: Key.customDohUrl) ?? "",
            proxyAutoSwitchEnabled: defaults.object(forKey: Key.proxyAutoSwitchEnabled) as? Bool ?? false,
            proxyAutoSwitchTimeout: [15, 30, 60].contains(defaults.integer(forKey: Key.proxyAutoSwitchTimeout)) ? defaults.integer(forKey: Key.proxyAutoSwitchTimeout) : 15,
            showProxyButton: defaults.object(forKey: Key.showProxyButton) as? Bool ?? true,
            hideProxySponsorChannel: hideProxySponsorChannel,
            showProfileIds: defaults.object(forKey: Key.showProfileIds) as? Bool ?? false,
            showRegistrationDate: defaults.object(forKey: Key.showRegistrationDate) as? Bool ?? false,
            showChatCreationDate: defaults.object(forKey: Key.showChatCreationDate) as? Bool ?? true,
            confirmOutgoingCalls: defaults.object(forKey: Key.confirmOutgoingCalls) as? Bool ?? true
        )
    }

    public static func update(_ transform: (inout NagramiXTabSettings) -> Void) {
        var value = self.current
        let previousDnsProvider = value.dnsProvider
        let previousCustomDohUrl = value.customDohUrl
        transform(&value)

        let defaults = UserDefaults.standard
        defaults.set(value.hideContacts, forKey: Key.hideContacts)
        defaults.set(value.hideCalls, forKey: Key.hideCalls)
        defaults.set(value.showSearchButton, forKey: Key.showSearchButton)
        defaults.set(value.useRearCameraForVideoMessages, forKey: Key.useRearCameraForVideoMessages)
        defaults.set(value.hideStories, forKey: Key.hideStories)
        defaults.set(value.disableStoryCameraSwipe, forKey: Key.disableStoryCameraSwipe)
        defaults.set(value.confirmStoryViewing, forKey: Key.confirmStoryViewing)
        defaults.set(value.enableStoryRepost, forKey: Key.enableStoryRepost)
        defaults.set(value.dnsProvider.rawValue, forKey: Key.dnsProvider)
        defaults.set(value.customDohUrl, forKey: Key.customDohUrl)
        defaults.set(value.proxyAutoSwitchEnabled, forKey: Key.proxyAutoSwitchEnabled)
        defaults.set([15, 30, 60].contains(value.proxyAutoSwitchTimeout) ? value.proxyAutoSwitchTimeout : 15, forKey: Key.proxyAutoSwitchTimeout)
        defaults.set(value.showProxyButton, forKey: Key.showProxyButton)
        defaults.set(value.hideProxySponsorChannel, forKey: Key.hideProxySponsorChannel)
        defaults.set(value.showProfileIds, forKey: Key.showProfileIds)
        defaults.set(value.showRegistrationDate, forKey: Key.showRegistrationDate)
        defaults.set(value.showChatCreationDate, forKey: Key.showChatCreationDate)
        defaults.set(value.confirmOutgoingCalls, forKey: Key.confirmOutgoingCalls)
        defaults.removeObject(forKey: Key.legacyShowProxySponsorChannel)

        NotificationCenter.default.post(name: self.changedNotification, object: nil)
        if previousDnsProvider != value.dnsProvider || previousCustomDohUrl != value.customDohUrl {
            NotificationCenter.default.post(name: self.dnsChangedNotification, object: nil)
        }
    }

    public static func requestTabInterfaceSoftRestart() {
        NotificationCenter.default.post(name: self.softRestartRequestedNotification, object: nil)
    }
}
