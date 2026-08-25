private final class ProxySettingsControllerArguments {
    let toggleEnabled: (Bool) -> Void
    let selectDns: () -> Void
    let editCustomDoh: () -> Void
    let toggleAutoSwitch: (Bool) -> Void
    let selectAutoSwitchTimeout: () -> Void
    let addNewServer: () -> Void
    let activateServer: (ProxyServerSettings) -> Void
    let editServer: (ProxyServerSettings) -> Void
    let removeServer: (ProxyServerSettings) -> Void
    let setServerWithRevealedOptions: (ProxyServerSettings?, ProxyServerSettings?) -> Void
    let toggleUseForCalls: (Bool) -> Void
    let shareProxyList: () -> Void

    init(toggleEnabled: @escaping (Bool) -> Void, selectDns: @escaping () -> Void, editCustomDoh: @escaping () -> Void, toggleAutoSwitch: @escaping (Bool) -> Void, selectAutoSwitchTimeout: @escaping () -> Void, addNewServer: @escaping () -> Void, activateServer: @escaping (ProxyServerSettings) -> Void, editServer: @escaping (ProxyServerSettings) -> Void, removeServer: @escaping (ProxyServerSettings) -> Void, setServerWithRevealedOptions: @escaping (ProxyServerSettings?, ProxyServerSettings?) -> Void, toggleUseForCalls: @escaping (Bool) -> Void, shareProxyList: @escaping () -> Void) {
        self.toggleEnabled = toggleEnabled
        self.selectDns = selectDns
        self.editCustomDoh = editCustomDoh
        self.toggleAutoSwitch = toggleAutoSwitch
        self.selectAutoSwitchTimeout = selectAutoSwitchTimeout
        self.addNewServer = addNewServer
        self.activateServer = activateServer
        self.editServer = editServer
        self.removeServer = removeServer
        self.setServerWithRevealedOptions = setServerWithRevealedOptions
        self.toggleUseForCalls = toggleUseForCalls
        self.shareProxyList = shareProxyList
    }
}

private enum ProxySettingsControllerSection: Int32 {
    case enabled
    case servers
    case calls
    case share
}

private struct DisplayProxyServerStatus: Equatable {
    let activity: Bool
    let text: String
    let textActive: Bool
}

private enum ProxySettingsControllerEntryId: Equatable, Hashable {
    case index(Int)
    case server(String, Int32, ProxyServerConnection)
}

public enum ProxySettingsEntryTag: ItemListItemTag, Equatable {
    case edit
    case useProxy
    case shareList
    case useForCalls

    public func isEqual(to other: ItemListItemTag) -> Bool {
        return (other as? ProxySettingsEntryTag) == self
    }
}

private enum ProxySettingsControllerEntry: ItemListNodeEntry {
    case enabled(PresentationTheme, String, Bool, Bool)
    case dns(PresentationTheme, String, String)
    case customDoh(PresentationTheme, String, String)
    case autoSwitch(PresentationTheme, String, Bool)
    case autoSwitchTimeout(PresentationTheme, String, String)
    case serversHeader(PresentationTheme, String)
    case addServer(PresentationTheme, String, Bool)
    case server(Int, PresentationTheme, PresentationStrings, ProxyServerSettings, Bool, DisplayProxyServerStatus, ProxySettingsServerItemEditing, Bool)
    case shareProxyList(PresentationTheme, String)
    case useForCalls(PresentationTheme, String, Bool)
    case useForCallsInfo(PresentationTheme, String)

    var section: ItemListSectionId {
        switch self {
        case .enabled, .dns, .customDoh, .autoSwitch, .autoSwitchTimeout:
            return ProxySettingsControllerSection.enabled.rawValue
        case .serversHeader, .addServer, .server:
            return ProxySettingsControllerSection.servers.rawValue
        case .useForCalls, .useForCallsInfo:
            return ProxySettingsControllerSection.calls.rawValue
        case .shareProxyList:
            return ProxySettingsControllerSection.share.rawValue
        }
    }

    private var sortIndex: Int {
        switch self {
        case .enabled: return 0
        case .dns: return 1
        case .customDoh: return 2
        case .autoSwitch: return 3
        case .autoSwitchTimeout: return 4
        case .serversHeader: return 10
        case .addServer: return 11
        case let .server(index, _, _, _, _, _, _, _): return 20 + index
        case .useForCalls: return 9_990
        case .useForCallsInfo: return 9_991
        case .shareProxyList: return 10_000
        }
    }

    var stableId: ProxySettingsControllerEntryId {
        switch self {
        case .enabled: return .index(0)
        case .dns: return .index(1)
        case .customDoh: return .index(2)
        case .autoSwitch: return .index(3)
        case .autoSwitchTimeout: return .index(4)
        case .serversHeader: return .index(10)
        case .addServer: return .index(11)
        case let .server(_, _, _, settings, _, _, _, _): return .server(settings.host, settings.port, settings.connection)
        case .shareProxyList: return .index(12)
        case .useForCalls: return .index(13)
        case .useForCallsInfo: return .index(14)
        }
    }

    static func == (lhs: ProxySettingsControllerEntry, rhs: ProxySettingsControllerEntry) -> Bool {
        switch (lhs, rhs) {
        case let (.enabled(lt, ls, lv, lc), .enabled(rt, rs, rv, rc)):
            return lt === rt && ls == rs && lv == rv && lc == rc
        case let (.dns(lt, ls, lv), .dns(rt, rs, rv)), let (.customDoh(lt, ls, lv), .customDoh(rt, rs, rv)), let (.autoSwitchTimeout(lt, ls, lv), .autoSwitchTimeout(rt, rs, rv)):
            return lt === rt && ls == rs && lv == rv
        case let (.autoSwitch(lt, ls, lv), .autoSwitch(rt, rs, rv)):
            return lt === rt && ls == rs && lv == rv
        case let (.serversHeader(lt, ls), .serversHeader(rt, rs)), let (.shareProxyList(lt, ls), .shareProxyList(rt, rs)), let (.useForCallsInfo(lt, ls), .useForCallsInfo(rt, rs)):
            return lt === rt && ls == rs
        case let (.addServer(lt, ls, lv), .addServer(rt, rs, rv)):
            return lt === rt && ls == rs && lv == rv
        case let (.server(li, lt, ls, lset, la, lst, le, len), .server(ri, rt, rs, rset, ra, rst, re, ren)):
            return li == ri && lt === rt && ls === rs && lset == rset && la == ra && lst == rst && le == re && len == ren
        case let (.useForCalls(lt, ls, lv), .useForCalls(rt, rs, rv)):
            return lt === rt && ls == rs && lv == rv
        default:
            return false
        }
    }

    static func < (lhs: ProxySettingsControllerEntry, rhs: ProxySettingsControllerEntry) -> Bool {
        return lhs.sortIndex < rhs.sortIndex
    }

    func item(presentationData: ItemListPresentationData, arguments: Any) -> ListViewItem {
        let arguments = arguments as! ProxySettingsControllerArguments
        switch self {
        case let .enabled(_, text, value, createsNew):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: text, value: value, enableInteractiveChanges: !createsNew, enabled: true, sectionId: self.section, style: .blocks, updated: { value in
                if createsNew {
                    arguments.addNewServer()
                } else {
                    arguments.toggleEnabled(value)
                }
            }, tag: ProxySettingsEntryTag.useProxy)
        case let .dns(_, title, value):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: title, label: value, sectionId: self.section, style: .blocks, action: arguments.selectDns)
        case let .customDoh(_, title, value):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: title, label: value, sectionId: self.section, style: .blocks, action: arguments.editCustomDoh)
        case let .autoSwitch(_, title, value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: title, value: value, sectionId: self.section, style: .blocks, updated: arguments.toggleAutoSwitch)
        case let .autoSwitchTimeout(_, title, value):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: title, label: value, sectionId: self.section, style: .blocks, action: arguments.selectAutoSwitchTimeout)
        case let .serversHeader(_, text):
            return ItemListSectionHeaderItem(presentationData: presentationData, text: text, sectionId: self.section)
        case let .addServer(_, text, _):
            return ProxySettingsActionItem(presentationData: presentationData, systemStyle: .glass, title: text, icon: .add, sectionId: self.section, editing: false, action: arguments.addNewServer)
        case let .server(_, theme, strings, settings, active, status, editing, enabled):
            return ProxySettingsServerItem(theme: theme, strings: strings, systemStyle: .glass, server: settings, activity: status.activity, active: active, color: enabled ? .accent : .secondary, label: status.text, labelAccent: status.textActive, editing: editing, sectionId: self.section, action: { arguments.activateServer(settings) }, infoAction: { arguments.editServer(settings) }, setServerWithRevealedOptions: arguments.setServerWithRevealedOptions, removeServer: { _ in arguments.removeServer(settings) })
        case let .shareProxyList(_, text):
            return ProxySettingsActionItem(presentationData: presentationData, systemStyle: .glass, title: text, sectionId: self.section, editing: false, action: arguments.shareProxyList, tag: ProxySettingsEntryTag.shareList)
        case let .useForCalls(_, text, value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: text, value: value, enableInteractiveChanges: true, enabled: true, sectionId: self.section, style: .blocks, updated: arguments.toggleUseForCalls, tag: ProxySettingsEntryTag.useForCalls)
        case let .useForCallsInfo(_, text):
            return ItemListTextItem(presentationData: presentationData, text: .plain(text), sectionId: self.section)
        }
    }
}

private func nagramiXDnsTitle(_ provider: NagramiXDnsProvider, strings: PresentationStrings) -> String {
    switch provider {
    case .system: return strings.nagramiXDnsSystem
    case .google: return strings.nagramiXDnsGoogle
    case .quad9: return strings.nagramiXDnsQuad9
    case .adGuard: return strings.nagramiXDnsAdGuard
    case .mullvad: return strings.nagramiXDnsMullvad
    case .cloudflare: return strings.nagramiXDnsCloudflare
    case .customDoh: return strings.nagramiXDnsCustom
    }
}

private func nagramiXTimeoutTitle(_ timeout: Int, strings: PresentationStrings) -> String {
    switch timeout {
    case 30: return strings.nagramiXSeconds30
    case 60: return strings.nagramiXSeconds60
    default: return strings.nagramiXSeconds15
    }
}

private func proxySettingsControllerEntries(theme: PresentationTheme, strings: PresentationStrings, state: ProxySettingsControllerState, proxySettings: ProxySettings, nagramiXSettings: NagramiXTabSettings, statuses: [ProxyServerSettings: ProxyServerStatus], connectionStatus: ConnectionStatus) -> [ProxySettingsControllerEntry] {
    var entries: [ProxySettingsControllerEntry] = []
    entries.append(.enabled(theme, strings.ChatSettings_ConnectionType_UseProxy, proxySettings.enabled, proxySettings.servers.isEmpty))
    entries.append(.dns(theme, strings.nagramiXDns, nagramiXDnsTitle(nagramiXSettings.dnsProvider, strings: strings)))
    if nagramiXSettings.dnsProvider == .customDoh {
        entries.append(.customDoh(theme, strings.nagramiXCustomDohUrl, nagramiXSettings.customDohUrl.isEmpty ? strings.nagramiXCustomDohPlaceholder : nagramiXSettings.customDohUrl))
    }
    entries.append(.autoSwitch(theme, strings.nagramiXProxyAutoSwitch, nagramiXSettings.proxyAutoSwitchEnabled))
    if nagramiXSettings.proxyAutoSwitchEnabled {
        entries.append(.autoSwitchTimeout(theme, strings.nagramiXProxySwitchAfter, nagramiXTimeoutTitle(nagramiXSettings.proxyAutoSwitchTimeout, strings: strings)))
    }
    entries.append(.serversHeader(theme, strings.SocksProxySetup_SavedProxies))
    entries.append(.addServer(theme, strings.SocksProxySetup_AddProxy, state.editing))
    var index = 0
    var existingServers = Set<ProxyServerSettings>()
    for server in proxySettings.servers where existingServers.insert(server).inserted {
        let status = statuses[server] ?? .checking
        let displayStatus: DisplayProxyServerStatus
        if proxySettings.enabled && server == proxySettings.activeServer {
            switch connectionStatus {
            case .waitingForNetwork:
                displayStatus = DisplayProxyServerStatus(activity: true, text: strings.State_WaitingForNetwork.lowercased(), textActive: false)
            case .connecting, .updating:
                displayStatus = DisplayProxyServerStatus(activity: true, text: strings.SocksProxySetup_ProxyStatusConnecting, textActive: false)
            case .online:
                var text = strings.SocksProxySetup_ProxyStatusConnected
                if case let .available(rtt) = status {
                    text += ", \(strings.SocksProxySetup_ProxyStatusPing("\(Int(rtt * 1000.0))").string)"
                }
                displayStatus = DisplayProxyServerStatus(activity: false, text: text, textActive: true)
            }
        } else {
            var text: String = server.connection.isMtp ? strings.SocksProxySetup_ProxyTelegram : strings.ChatSettings_ConnectionType_UseSocks5
            switch status {
            case .notAvailable:
                text += ", " + strings.SocksProxySetup_ProxyStatusUnavailable
                displayStatus = DisplayProxyServerStatus(activity: false, text: text, textActive: false)
            case .checking:
                text += ", " + strings.SocksProxySetup_ProxyStatusChecking
                displayStatus = DisplayProxyServerStatus(activity: false, text: text, textActive: false)
            case let .available(rtt):
                text += ", \(strings.SocksProxySetup_ProxyStatusPing("\(Int(rtt * 1000.0))").string)"
                displayStatus = DisplayProxyServerStatus(activity: false, text: text, textActive: false)
            }
        }
        entries.append(.server(index, theme, strings, server, server == proxySettings.activeServer, displayStatus, ProxySettingsServerItemEditing(editable: true, editing: state.editing, revealed: state.revealedServer == server), proxySettings.enabled))
        index += 1
    }
    if let activeServer = proxySettings.activeServer, case .socks5 = activeServer.connection {
        entries.append(.useForCalls(theme, strings.SocksProxySetup_UseForCalls, proxySettings.useForCalls))
        entries.append(.useForCallsInfo(theme, strings.SocksProxySetup_UseForCallsHelp))
    }
    entries.append(.shareProxyList(theme, strings.SocksProxySetup_ShareProxyList))
    return entries
}

private extension ProxyServerConnection {
    var isMtp: Bool {
        if case .mtp = self { return true }
        return false
    }
}
