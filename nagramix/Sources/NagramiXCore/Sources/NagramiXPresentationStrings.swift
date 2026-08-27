import Foundation
import TelegramPresentationData

private final class NagramiXLocalizationMarker {
}

private extension PresentationStrings {
    var nagramiXUsesRussian: Bool {
        return self.primaryComponent.languageCode.lowercased().hasPrefix("ru")
    }

    func nagramiXLocalized(_ key: String) -> String {
        let containingBundle = Bundle(for: NagramiXLocalizationMarker.self)
        guard let resourcePath = containingBundle.path(forResource: "NagramiXLocalization", ofType: "bundle"), let resourceBundle = Bundle(path: resourcePath) else {
            return key
        }
        let languageCode = self.nagramiXUsesRussian ? "ru" : "en"
        guard let languagePath = resourceBundle.path(forResource: languageCode, ofType: "lproj"), let languageBundle = Bundle(path: languagePath) else {
            return resourceBundle.localizedString(forKey: key, value: key, table: nil)
        }
        return languageBundle.localizedString(forKey: key, value: key, table: nil)
    }
}

public extension PresentationStrings {
    func nagramiXDebugLocalized(_ english: String) -> String {
        let key = "NagramiX.Debug." + english
        let value = self.nagramiXLocalized(key)
        return value == key ? english : value
    }
    var nagramiXSettingsTitle: String { self.nagramiXLocalized("NagramiX.Settings.Title") }
    var nagramiXSettingsInterface: String { self.nagramiXLocalized("NagramiX.Settings.Page.Interface") }
    var nagramiXSettingsFeatures: String { self.nagramiXLocalized("NagramiX.Settings.Page.Features") }
    var nagramiXSettingsOther: String { self.nagramiXLocalized("NagramiX.Settings.Page.Other") }
    var nagramiXProxySettings: String { self.nagramiXLocalized("NagramiX.Settings.Proxy") }
    var nagramiXTabsHeader: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.Header") }
    var nagramiXHideContactsTab: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.HideContacts") }
    var nagramiXHideCallsTab: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.HideCalls") }
    var nagramiXHideTabTitles: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.HideTitles") }
    var nagramiXShowSearchButton: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.ShowSearch") }
    var nagramiXVideoMessagesHeader: String { self.nagramiXLocalized("NagramiX.Settings.VideoMessages.Header") }
    var nagramiXUseRearCamera: String { self.nagramiXLocalized("NagramiX.Settings.VideoMessages.UseRearCamera") }
    var nagramiXStoriesHeader: String { self.nagramiXLocalized("NagramiX.Settings.Stories.Header") }
    var nagramiXHideStories: String { self.nagramiXLocalized("NagramiX.Settings.Stories.Hide") }
    var nagramiXDisableStoryCameraSwipe: String { self.nagramiXLocalized("NagramiX.Settings.Stories.DisableSwipe") }
    var nagramiXConfirmStoryViewing: String { self.nagramiXLocalized("NagramiX.Settings.Stories.ConfirmViewing") }
    var nagramiXEnableStoryRepost: String { self.nagramiXLocalized("NagramiX.Settings.Stories.Repost") }
    var nagramiXRestartRequiredTitle: String { self.nagramiXLocalized("NagramiX.Restart.Title") }
    var nagramiXRestartRequiredText: String { self.nagramiXLocalized("NagramiX.Restart.Text") }
    var nagramiXRestartAction: String { self.nagramiXLocalized("NagramiX.Restart.Action") }
    var nagramiXStoryConfirmationTitle: String { self.nagramiXLocalized("NagramiX.StoryConfirmation.Title") }
    var nagramiXStoryConfirmationText: String { self.nagramiXLocalized("NagramiX.StoryConfirmation.Text") }
    func nagramiXStoryConfirmationText(owner: String) -> String {
        return String(format: self.nagramiXStoryConfirmationText, owner)
    }
    var nagramiXViewStoryAction: String { self.nagramiXLocalized("NagramiX.StoryConfirmation.Action") }
    var nagramiXIconMain: String { self.nagramiXLocalized("NagramiX.Icon.Main") }
    var nagramiXIconSunset: String { self.nagramiXLocalized("NagramiX.Icon.Sunset") }
    var nagramiXIconAurora: String { self.nagramiXLocalized("NagramiX.Icon.Aurora") }
    var nagramiXIconGraphite: String { self.nagramiXLocalized("NagramiX.Icon.Graphite") }
    var nagramiXIconAmber: String { self.nagramiXLocalized("NagramiX.Icon.Amber") }
    var nagramiXIconNeon: String { self.nagramiXLocalized("NagramiX.Icon.Neon") }
    var nagramiXIconLime: String { self.nagramiXLocalized("NagramiX.Icon.Lime") }
    var nagramiXIconRuby: String { self.nagramiXLocalized("NagramiX.Icon.Ruby") }
    var nagramiXDns: String { self.nagramiXLocalized("NagramiX.Network.DNS") }
    var nagramiXDnsSystem: String { self.nagramiXLocalized("NagramiX.Network.DNS.System") }
    var nagramiXDnsGoogle: String { self.nagramiXLocalized("NagramiX.Network.DNS.Google") }
    var nagramiXDnsQuad9: String { self.nagramiXLocalized("NagramiX.Network.DNS.Quad9") }
    var nagramiXDnsAdGuard: String { self.nagramiXLocalized("NagramiX.Network.DNS.AdGuard") }
    var nagramiXDnsMullvad: String { self.nagramiXLocalized("NagramiX.Network.DNS.Mullvad") }
    var nagramiXDnsCloudflare: String { self.nagramiXLocalized("NagramiX.Network.DNS.Cloudflare") }
    var nagramiXDnsCustom: String { self.nagramiXLocalized("NagramiX.Network.DNS.Custom") }
    var nagramiXCustomDohUrl: String { self.nagramiXLocalized("NagramiX.Network.DNS.CustomURL") }
    var nagramiXCustomDohPlaceholder: String { self.nagramiXLocalized("NagramiX.Network.DNS.CustomPlaceholder") }
    var nagramiXCustomDohInvalid: String { self.nagramiXLocalized("NagramiX.Network.DNS.CustomInvalid") }
    var nagramiXCustomDohUnavailable: String { self.nagramiXLocalized("NagramiX.Network.DNS.CustomUnavailable") }
    var nagramiXProxyAutoSwitch: String { self.nagramiXLocalized("NagramiX.Network.Proxy.AutoSwitch") }
    var nagramiXProxySwitchAfter: String { self.nagramiXLocalized("NagramiX.Network.Proxy.SwitchAfter") }
    var nagramiXProxyCheckAll: String { self.nagramiXLocalized("NagramiX.Network.Proxy.CheckAll") }
    var nagramiXProxyChecking: String { self.nagramiXLocalized("NagramiX.Network.Proxy.Checking") }
    var nagramiXProxyNoneToCheck: String { self.nagramiXLocalized("NagramiX.Network.Proxy.NoneToCheck") }
    func nagramiXProxyCheckSummary(total: Int, available: Int, unavailable: Int) -> String {
        return String(format: self.nagramiXLocalized("NagramiX.Network.Proxy.CheckSummary"), total, available, unavailable)
    }
    var nagramiXSeconds15: String { self.nagramiXLocalized("NagramiX.Time.15Seconds") }
    var nagramiXSeconds30: String { self.nagramiXLocalized("NagramiX.Time.30Seconds") }
    var nagramiXSeconds60: String { self.nagramiXLocalized("NagramiX.Time.60Seconds") }
    var nagramiXShowProxyButton: String { self.nagramiXLocalized("NagramiX.Interface.ShowProxyButton") }
    var nagramiXHideProxySponsorChannel: String { self.nagramiXLocalized("NagramiX.Interface.HideProxySponsorChannel") }
    var nagramiXEdit: String { self.nagramiXLocalized("NagramiX.Common.Edit") }
    var nagramiXSave: String { self.nagramiXLocalized("NagramiX.Common.Save") }
    var nagramiXFeatures: String { self.nagramiXLocalized("NagramiX.Info.Features") }
    var nagramiXUpdates: String { self.nagramiXLocalized("NagramiX.Info.Updates") }
    var nagramiXHelp: String { self.nagramiXLocalized("NagramiX.Info.Help") }
    var nagramiXProfilesHeader: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.Header") }
    var nagramiXShowProfileIds: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.ShowIds") }
    var nagramiXShowRegistrationDate: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.ShowRegistrationDate") }
    var nagramiXShowChatCreationDate: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.ShowChatCreationDate") }
    var nagramiXCallsHeader: String { self.nagramiXLocalized("NagramiX.Settings.Calls.Header") }
    var nagramiXConfirmOutgoingCalls: String { self.nagramiXLocalized("NagramiX.Settings.Calls.ConfirmOutgoing") }
    var nagramiXForceTcpCalls: String { self.nagramiXLocalized("NagramiX.Settings.Calls.ForceTcp") }
    var nagramiXForceTcpCallsInfo: String { self.nagramiXLocalized("NagramiX.Settings.Calls.ForceTcpInfo") }
    var nagramiXMessagesHeader: String { self.nagramiXLocalized("NagramiX.Settings.Messages.Header") }
    var nagramiXDeletedMessages: String { self.nagramiXLocalized("NagramiX.Settings.Messages.Deleted") }
    var nagramiXDeletedMessagesInfo: String { self.nagramiXLocalized("NagramiX.Settings.Messages.DeletedInfo") }
    var nagramiXMessageEditHistory: String { self.nagramiXLocalized("NagramiX.Settings.Messages.EditHistory") }
    var nagramiXMessageEditHistoryInfo: String { self.nagramiXLocalized("NagramiX.Settings.Messages.EditHistoryInfo") }
    var nagramiXDeleted: String { self.nagramiXLocalized("NagramiX.Messages.Deleted") }
    var nagramiXEditHistory: String { self.nagramiXLocalized("NagramiX.Messages.EditHistory") }
    var nagramiXOriginalVersion: String { self.nagramiXLocalized("NagramiX.Messages.OriginalVersion") }
    var nagramiXCurrentVersion: String { self.nagramiXLocalized("NagramiX.Messages.CurrentVersion") }
    var nagramiXNoPreviousVersions: String { self.nagramiXLocalized("NagramiX.Messages.NoPreviousVersions") }
    var nagramiXClearMessageArchive: String { self.nagramiXLocalized("NagramiX.Messages.ClearArchive") }
    var nagramiXClearMessageArchiveConfirm: String { self.nagramiXLocalized("NagramiX.Messages.ClearArchiveConfirm") }
    var nagramiXClear: String { self.nagramiXLocalized("NagramiX.Common.Clear") }
    var nagramiXCancel: String { self.nagramiXLocalized("NagramiX.Common.Cancel") }
    var nagramiXLocalArchiveInfo: String { self.nagramiXLocalized("NagramiX.Messages.ArchiveInfo") }
    var nagramiXCallConfirmationTitle: String { self.nagramiXLocalized("NagramiX.CallConfirmation.Title") }
    var nagramiXCallConfirmationText: String { self.nagramiXLocalized("NagramiX.CallConfirmation.Text") }
    var nagramiXCallAction: String { self.nagramiXLocalized("NagramiX.CallConfirmation.Action") }
    var nagramiXForwardWithAuthor: String { self.nagramiXLocalized("NagramiX.Context.ForwardWithAuthor") }
    var nagramiXForwardWithoutAuthor: String { self.nagramiXLocalized("NagramiX.Context.ForwardWithoutAuthor") }
    var nagramiXSelectFromAuthor: String { self.nagramiXLocalized("NagramiX.Context.SelectFromAuthor") }
    var nagramiXDataCenters: String { self.nagramiXLocalized("NagramiX.Network.DataCenters") }
    var nagramiXProfileId: String { self.nagramiXLocalized("NagramiX.Profile.Id") }
    var nagramiXRegistrationDate: String { self.nagramiXLocalized("NagramiX.Profile.RegistrationDate") }
    func nagramiXApproximateRegistration(_ year: Int) -> String {
        return self.nagramiXLocalized("NagramiX.Profile.RegistrationApproximate").replacingOccurrences(of: "%@", with: "\(year)")
    }
    var nagramiXChatCreationDate: String { self.nagramiXLocalized("NagramiX.Profile.ChatCreationDate") }
    var nagramiXUnknown: String { self.nagramiXLocalized("NagramiX.Common.Unknown") }
}
