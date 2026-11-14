import Foundation
import UIKit
import Display
import SwiftSignalKit
import TelegramCore
import TelegramPresentationData
import MtProtoKit
import ItemListUI
import PresentationDataUtils
import AccountContext
import ShareController
import UrlEscaping
import UndoUI
import NagramiXCore
import NagramiXMediaSettings

private final class ProxySettingsControllerArguments {
    let toggleEnabled: (Bool) -> Void
    let selectDns: () -> Void
    let togglePreferIPv6: (Bool) -> Void
    let editCustomDoh: () -> Void
    let toggleAutoSwitch: (Bool) -> Void
    let toggleAvoidProxyWithVPN: (Bool) -> Void
    let selectAutoSwitchTimeout: () -> Void
    let checkAllProxies: () -> Void
    let addNewServer: () -> Void
    let activateServer: (ProxyServerSettings) -> Void
    let editServer: (ProxyServerSettings) -> Void
    let removeServer: (ProxyServerSettings) -> Void
    let setServerWithRevealedOptions: (ProxyServerSettings?, ProxyServerSettings?) -> Void
    let toggleUseForCalls: (Bool) -> Void
    let shareProxyList: () -> Void

    init(toggleEnabled: @escaping (Bool) -> Void, selectDns: @escaping () -> Void, togglePreferIPv6: @escaping (Bool) -> Void, editCustomDoh: @escaping () -> Void, toggleAutoSwitch: @escaping (Bool) -> Void, toggleAvoidProxyWithVPN: @escaping (Bool) -> Void, selectAutoSwitchTimeout: @escaping () -> Void, checkAllProxies: @escaping () -> Void, addNewServer: @escaping () -> Void, activateServer: @escaping (ProxyServerSettings) -> Void, editServer: @escaping (ProxyServerSettings) -> Void, removeServer: @escaping (ProxyServerSettings) -> Void, setServerWithRevealedOptions: @escaping (ProxyServerSettings?, ProxyServerSettings?) -> Void, toggleUseForCalls: @escaping (Bool) -> Void, shareProxyList: @escaping () -> Void) {
        self.toggleEnabled = toggleEnabled
        self.selectDns = selectDns
        self.togglePreferIPv6 = togglePreferIPv6
        self.editCustomDoh = editCustomDoh
        self.toggleAutoSwitch = toggleAutoSwitch
        self.toggleAvoidProxyWithVPN = toggleAvoidProxyWithVPN
        self.selectAutoSwitchTimeout = selectAutoSwitchTimeout
        self.checkAllProxies = checkAllProxies
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
    case check
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
    case preferIPv6(PresentationTheme, String, Bool)
    case customDoh(PresentationTheme, String, String)
    case autoSwitch(PresentationTheme, String, Bool)
    case autoSwitchTimeout(PresentationTheme, String, String)
    case checkAllProxies(PresentationTheme, String, Bool)
    case avoidProxyWithVPN(PresentationTheme, String, Bool)
    case avoidProxyWithVPNInfo(PresentationTheme, String)
    case serversHeader(PresentationTheme, String)
    case addServer(PresentationTheme, String, Bool)
    case server(Int, PresentationTheme, PresentationStrings, ProxyServerSettings, Bool, DisplayProxyServerStatus, ProxySettingsServerItemEditing, Bool)
    case shareProxyList(PresentationTheme, String)
    case useForCalls(PresentationTheme, String, Bool)
    case useForCallsInfo(PresentationTheme, String)

    var section: ItemListSectionId {
        switch self {
        case .enabled, .dns, .preferIPv6, .customDoh, .autoSwitch, .autoSwitchTimeout, .avoidProxyWithVPN, .avoidProxyWithVPNInfo:
            return ProxySettingsControllerSection.enabled.rawValue
        case .serversHeader, .addServer, .server:
            return ProxySettingsControllerSection.servers.rawValue
        case .useForCalls, .useForCallsInfo:
            return ProxySettingsControllerSection.calls.rawValue
        case .shareProxyList:
            return ProxySettingsControllerSection.share.rawValue
        case .checkAllProxies:
            return ProxySettingsControllerSection.check.rawValue
        }
    }

    private var sortIndex: Int {
        switch self {
        case .enabled: return 0
        case .dns: return 1
        case .customDoh: return 2
        case .preferIPv6: return 3
        case .autoSwitch: return 4
        case .autoSwitchTimeout: return 5
        case .avoidProxyWithVPN: return 6
        case .avoidProxyWithVPNInfo: return 7
        case .checkAllProxies: return 8
        case .serversHeader: return 10
        case .addServer: return 11
        case let .server(index, _, _, _, _, _, _, _): return 20 + index
        case .useForCalls: return 9_990
        case .useForCallsInfo: return 9_991
        case .shareProxyList: return 9
        }
    }

    var stableId: ProxySettingsControllerEntryId {
        switch self {
        case .enabled: return .index(0)
        case .dns: return .index(1)
        case .preferIPv6: return .index(17)
        case .customDoh: return .index(2)
        case .autoSwitch: return .index(3)
        case .autoSwitchTimeout: return .index(4)
        case .checkAllProxies: return .index(5)
        case .avoidProxyWithVPN: return .index(15)
        case .avoidProxyWithVPNInfo: return .index(16)
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
        case let (.preferIPv6(lt, ls, lv), .preferIPv6(rt, rs, rv)), let (.autoSwitch(lt, ls, lv), .autoSwitch(rt, rs, rv)), let (.avoidProxyWithVPN(lt, ls, lv), .avoidProxyWithVPN(rt, rs, rv)):
            return lt === rt && ls == rs && lv == rv
        case let (.checkAllProxies(lt, ls, lv), .checkAllProxies(rt, rs, rv)):
            return lt === rt && ls == rs && lv == rv
        case let (.avoidProxyWithVPNInfo(lt, ls), .avoidProxyWithVPNInfo(rt, rs)), let (.serversHeader(lt, ls), .serversHeader(rt, rs)), let (.shareProxyList(lt, ls), .shareProxyList(rt, rs)), let (.useForCallsInfo(lt, ls), .useForCallsInfo(rt, rs)):
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
        case let .preferIPv6(_, title, value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: title, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.togglePreferIPv6)
        case let .customDoh(_, title, value):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: title, label: value, sectionId: self.section, style: .blocks, action: arguments.editCustomDoh)
        case let .autoSwitch(_, title, value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: title, value: value, sectionId: self.section, style: .blocks, updated: arguments.toggleAutoSwitch)
        case let .avoidProxyWithVPN(_, title, value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: title, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.toggleAvoidProxyWithVPN)
        case let .avoidProxyWithVPNInfo(_, text):
            return ItemListTextItem(presentationData: presentationData, text: .plain(text), sectionId: self.section)
        case let .autoSwitchTimeout(_, title, value):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: title, label: value, sectionId: self.section, style: .blocks, action: arguments.selectAutoSwitchTimeout)
        case let .checkAllProxies(_, title, checking):
            return ProxySettingsActionItem(presentationData: presentationData, systemStyle: .glass, title: title, sectionId: self.section, editing: false, action: {
                if !checking {
                    arguments.checkAllProxies()
                }
            })
        case let .serversHeader(_, text):
            return ItemListSectionHeaderItem(presentationData: presentationData, text: text, sectionId: self.section)
        case let .addServer(_, text, _):
            return ProxySettingsActionItem(presentationData: presentationData, systemStyle: .glass, title: text, icon: .add, sectionId: self.section, editing: false, action: arguments.addNewServer)
        case let .server(_, theme, strings, settings, active, status, editing, enabled):
            return ProxySettingsServerItem(theme: theme, strings: strings, systemStyle: .glass, server: settings, activity: status.activity, active: active, color: enabled ? .accent : .secondary, label: status.text, labelAccent: status.textActive, editing: editing, sectionId: self.section, action: { arguments.activateServer(settings) }, infoAction: { arguments.editServer(settings) }, setServerWithRevealedOptions: arguments.setServerWithRevealedOptions, removeServer: { _ in arguments.removeServer(settings) })
        case let .shareProxyList(_, text):
            return ProxySettingsActionItem(presentationData: presentationData, systemStyle: .glass, title: text, sectionId: self.section, editing: false, action: arguments.shareProxyList, tag: ProxySettingsEntryTag.shareList)
        case let .useForCalls(_, text, value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: text, value: value, enableInteractiveChanges: true, enabled: true, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.toggleUseForCalls, tag: ProxySettingsEntryTag.useForCalls)
        case let .useForCallsInfo(_, text):
            return ItemListTextItem(presentationData: presentationData, text: .plain(text), sectionId: self.section)
        }
    }
}

private func nagramiXDnsTitle(_ provider: NagramiXDnsProvider, strings: PresentationStrings) -> String {
    switch provider {
    case .system: return strings.nagramiXDnsSystem
    case .telegram: return strings.nagramiXDnsTelegram
    case .google: return strings.nagramiXDnsGoogle
    case .adGuard: return strings.nagramiXDnsAdGuard
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

private func proxySettingsControllerEntries(theme: PresentationTheme, strings: PresentationStrings, state: ProxySettingsControllerState, proxySettings: ProxySettings, nagramiXSettings: NagramiXTabSettings, statuses: [ProxyServerSettings: ProxyServerStatus], connectionStatus: ConnectionStatus, vpnBypassed: Bool) -> [ProxySettingsControllerEntry] {
    var entries: [ProxySettingsControllerEntry] = []
    entries.append(.enabled(theme, strings.ChatSettings_ConnectionType_UseProxy, proxySettings.enabled, proxySettings.servers.isEmpty))
    entries.append(.dns(theme, strings.nagramiXDns, nagramiXDnsTitle(nagramiXSettings.dnsProvider, strings: strings)))
    if nagramiXSettings.dnsProvider == .customDoh {
        entries.append(.customDoh(theme, strings.nagramiXCustomDohUrl, nagramiXSettings.customDohUrl.isEmpty ? strings.nagramiXCustomDohPlaceholder : nagramiXSettings.customDohUrl))
    }
    entries.append(.preferIPv6(theme, strings.nagramiXPreferIPv6, NagramiXProxyPreferences.preferIPv6))
    entries.append(.autoSwitch(theme, strings.nagramiXProxyAutoSwitch, nagramiXSettings.proxyAutoSwitchEnabled))
    if nagramiXSettings.proxyAutoSwitchEnabled {
        entries.append(.autoSwitchTimeout(theme, strings.nagramiXProxySwitchAfter, nagramiXTimeoutTitle(nagramiXSettings.proxyAutoSwitchTimeout, strings: strings)))
    }
    entries.append(.avoidProxyWithVPN(theme, strings.nagramiXAvoidProxyWithVPN, nagramiXSettings.avoidProxyWithVPN))
    entries.append(.checkAllProxies(theme, state.checkingAllProxies ? strings.nagramiXProxyChecking : strings.nagramiXProxyCheckAll, state.checkingAllProxies))
    entries.append(.shareProxyList(theme, strings.SocksProxySetup_ShareProxyList))
    entries.append(.serversHeader(theme, strings.SocksProxySetup_SavedProxies))
    entries.append(.addServer(theme, strings.SocksProxySetup_AddProxy, state.editing))
    var index = 0
    var existingServers = Set<ProxyServerSettings>()
    for server in proxySettings.servers where existingServers.insert(server).inserted {
        let status = statuses[server] ?? .checking
        let displayStatus: DisplayProxyServerStatus
        if proxySettings.enabled && !vpnBypassed && server == proxySettings.activeServer {
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
        entries.append(.server(index, theme, strings, server, server == proxySettings.activeServer, displayStatus, ProxySettingsServerItemEditing(editable: true, editing: state.editing, revealed: state.revealedServer == server), proxySettings.enabled && !vpnBypassed))
        index += 1
    }
    if let activeServer = proxySettings.activeServer, case .socks5 = activeServer.connection {
        entries.append(.useForCalls(theme, strings.SocksProxySetup_UseForCalls, proxySettings.useForCalls))
    }
    return entries
}

private extension ProxyServerConnection {
    var isMtp: Bool {
        if case .mtp = self { return true }
        return false
    }
}
private struct ProxySettingsControllerState: Equatable {
    var editing: Bool = false
    var revealedServer: ProxyServerSettings? = nil
    var checkingAllProxies: Bool = false
}

public enum ProxySettingsControllerMode {
    case `default`
    case modal
}

public func proxySettingsController(context: AccountContext, mode: ProxySettingsControllerMode = .default, focusOnItemTag: ProxySettingsEntryTag? = nil) -> ViewController {
    let presentationData = context.sharedContext.currentPresentationData.with { $0 }
    return proxySettingsController(accountManager: context.sharedContext.accountManager, sharedContext: context.sharedContext, context: context, network: context.account.network, mode: mode, presentationData: presentationData, updatedPresentationData: context.sharedContext.presentationData, focusOnItemTag: focusOnItemTag)
}

public func proxySettingsController(accountManager: AccountManager<TelegramAccountManagerTypes>, sharedContext: SharedAccountContext, context: AccountContext? = nil, network: Network, mode: ProxySettingsControllerMode, presentationData: PresentationData, updatedPresentationData: Signal<PresentationData, NoError>, focusOnItemTag: ProxySettingsEntryTag? = nil) -> ViewController {
    var pushControllerImpl: ((ViewController) -> Void)?
    var presentControllerImpl: ((ViewController) -> Void)?
    var dismissImpl: (() -> Void)?
    let stateValue = Atomic(value: ProxySettingsControllerState())
    let statePromise = ValuePromise<ProxySettingsControllerState>(stateValue.with { $0 })
    let updateState: ((ProxySettingsControllerState) -> ProxySettingsControllerState) -> Void = { f in
        var changed = false
        let value = stateValue.modify { current in
            let updated = f(current)
            if updated != current {
                changed = true
            }
            return updated
        }
        if changed {
            statePromise.set(value)
        }
    }
    
    if focusOnItemTag == ProxySettingsEntryTag.edit {
        updateState { state in
            var state = state
            state.editing = true
            return state
        }
    }
    
    var shareProxyListImpl: (() -> Void)?
    let nagramiXSettingsPromise = ValuePromise(NagramiXTabSettings.current, ignoreRepeated: false)
    let updateNagramiXSettings: ((inout NagramiXTabSettings) -> Void) -> Void = { transform in
        NagramiXTabSettings.update(transform)
        nagramiXSettingsPromise.set(NagramiXTabSettings.current)
    }
    // Observe external changes only while the controller's state is
    // subscribed. An unpresented controller never installs an observer.
    let nagramiXSettingsSignal = Signal<NagramiXTabSettings, NoError> { subscriber in
        let observer = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { _ in
            nagramiXSettingsPromise.set(NagramiXTabSettings.current)
        })
        let disposable = nagramiXSettingsPromise.get().start(next: { value in
            subscriber.putNext(value)
        })
        nagramiXSettingsPromise.set(NagramiXTabSettings.current)
        return ActionDisposable {
            disposable.dispose()
            NotificationCenter.default.removeObserver(observer)
        }
    }
    var selectDnsImpl: (() -> Void)?
    var editCustomDohImpl: (() -> Void)?
    var selectTimeoutImpl: (() -> Void)?
    var checkAllProxiesImpl: (() -> Void)?
    let checkAllProxiesSettingsDisposable = MetaDisposable()
    let checkAllProxiesStatusesDisposable = MetaDisposable()

    let arguments = ProxySettingsControllerArguments(toggleEnabled: { value in
        let _ = updateProxySettingsInteractively(accountManager: accountManager, { current in
            var current = current
            current.enabled = value
            if value && current.activeServer == nil {
                current.activeServer = current.servers.first
            }
            NagramiXProxyPreferences.initializeIfNeeded(proxyEnabled: current.enabled && current.activeServer != nil, serverCount: Set(current.servers).count)
            return current
        }).start()
    }, selectDns: {
        selectDnsImpl?()
    }, togglePreferIPv6: { value in
        NagramiXProxyPreferences.setPreferIPv6(value)
    }, editCustomDoh: {
        editCustomDohImpl?()
    }, toggleAutoSwitch: { value in
        // Persist even an explicit false matching the absent default.
        NagramiXProxyPreferences.setAutoSwitch(value)
        updateNagramiXSettings { $0.proxyAutoSwitchEnabled = value }
    }, toggleAvoidProxyWithVPN: { value in
        NagramiXProxyPreferences.setAvoidVPN(value)
        updateNagramiXSettings { $0.avoidProxyWithVPN = value }
    }, selectAutoSwitchTimeout: {
        selectTimeoutImpl?()
    }, checkAllProxies: {
        checkAllProxiesImpl?()
    }, addNewServer: {
        pushControllerImpl?(proxyServerSettingsController(sharedContext: sharedContext, presentationData: presentationData, updatedPresentationData: updatedPresentationData, accountManager: accountManager, network: network, currentSettings: nil))
    }, activateServer: { server in
        NotificationCenter.default.post(name: Notification.Name("NagramiXProxySelectionRequested"), object: nil)
        let _ = (accountManager.sharedData(keys: [SharedDataKeys.proxySettings])
        |> take(1)
        |> deliverOnMainQueue).start(next: { data in
            let settings = data.entries[SharedDataKeys.proxySettings]?.get(ProxySettings.self) ?? .defaultSettings
            guard settings.servers.contains(server) else { return }
            let _ = updateProxySettingsInteractively(accountManager: accountManager, { current in
                var current = current
                if current.servers.contains(server) {
                    current.activeServer = server
                    current.enabled = true
                    NagramiXProxyPreferences.initializeIfNeeded(proxyEnabled: true, serverCount: Set(current.servers).count)
                }
                return current
            }).start()
        })
    }, editServer: { server in
        pushControllerImpl?(proxyServerSettingsController(sharedContext: sharedContext, presentationData: presentationData, updatedPresentationData: updatedPresentationData, accountManager: accountManager, network: network, currentSettings: server))
    }, removeServer: { server in
        let _ = updateProxySettingsInteractively(accountManager: accountManager, { current in
            var current = current
            if let index = current.servers.firstIndex(of: server) {
                current.servers.remove(at: index)
                if current.activeServer == server {
                    current.activeServer = nil
                    current.enabled = false
                }
            }
            return current
        }).start()
    }, setServerWithRevealedOptions: { server, fromServer in
        updateState { state in
            var state = state
            if (server == nil && fromServer == state.revealedServer) || (server != nil && fromServer == nil) {
                state.revealedServer = server
            }
            return state
        }
    }, toggleUseForCalls: { value in
        let _ = updateProxySettingsInteractively(accountManager: accountManager, { current in
            var current = current
            current.useForCalls = value
            return current
        }).start()
    }, shareProxyList: {
       shareProxyListImpl?()
    })
    
    editCustomDohImpl = {
        guard let context else {
            return
        }
        let current = NagramiXTabSettings.current
        presentControllerImpl?(nagramiXCustomDohController(context: context, initialValue: current.customDohUrl, apply: { value in
            updateNagramiXSettings {
                $0.customDohUrl = value
                $0.dnsProvider = .customDoh
            }
        }, clear: {
            updateNagramiXSettings {
                let previous = NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current: $0.dnsProvider)
                $0.customDohUrl = ""
                $0.dnsProvider = previous
            }
        }))
    }
    selectDnsImpl = {
        let presentationData = sharedContext.currentPresentationData.with { $0 }
        let actionSheet = ActionSheetController(presentationData: presentationData)
        let current = NagramiXTabSettings.current
        let providers = NagramiXDnsProvider.allCases
        let items: [ActionSheetItem] = providers.map { provider in
            ActionSheetButtonItem(title: (current.dnsProvider == provider ? "✓ " : "") + nagramiXDnsTitle(provider, strings: presentationData.strings), color: .accent, action: { [weak actionSheet] in
                actionSheet?.dismissAnimated()
                if provider == .customDoh && current.customDohUrl.isEmpty {
                    editCustomDohImpl?()
                } else {
                    updateNagramiXSettings { $0.dnsProvider = provider }
                }
            })
        }
        var providerItems: [ActionSheetItem] = [ActionSheetTextItem(title: presentationData.strings.nagramiXDns)]
        providerItems.append(contentsOf: items)
        actionSheet.setItemGroups([
            ActionSheetItemGroup(items: providerItems),
            ActionSheetItemGroup(items: [ActionSheetButtonItem(title: presentationData.strings.Common_Cancel, color: .accent, font: .bold, action: { [weak actionSheet] in actionSheet?.dismissAnimated() })])
        ])
        presentControllerImpl?(actionSheet)
    }
    selectTimeoutImpl = {
        let presentationData = sharedContext.currentPresentationData.with { $0 }
        let currentTimeout = NagramiXTabSettings.current.proxyAutoSwitchTimeout
        let values = [15, 30, 60]
        let options = values.map { value in
            NagramiXOptionSheetOption(id: value, title: nagramiXTimeoutTitle(value, strings: presentationData.strings), subtitle: "")
        }
        let actionSheet = nagramiXOptionSheet(presentationData: presentationData, title: presentationData.strings.nagramiXProxySwitchAfter, options: options, selectedId: currentTimeout, footnote: presentationData.strings.nagramiXProxyTimeoutInfo, selected: { value in
            guard values.contains(value) else { return }
            updateNagramiXSettings { $0.proxyAutoSwitchTimeout = value }
        })
        presentControllerImpl?(actionSheet)
    }

    let proxySettings = Promise<ProxySettings>()
    proxySettings.set(accountManager.sharedData(keys: [SharedDataKeys.proxySettings])
    |> map { sharedData -> ProxySettings in
        if let value = sharedData.entries[SharedDataKeys.proxySettings]?.get(ProxySettings.self) {
            return value
        } else {
            return ProxySettings.defaultSettings
        }
    })
    
    let statusesContext = network.nagramiXProxyStatuses.with { $0 } ?? ProxyServersStatuses(network: network, servers: proxySettings.get()
    |> map { proxySettings -> [ProxyServerSettings] in
        return proxySettings.servers
    })
    
    checkAllProxiesImpl = { [checkAllProxiesStatusesDisposable] in
        if stateValue.with({ $0.checkingAllProxies }) {
            return
        }
        checkAllProxiesSettingsDisposable.set((proxySettings.get()
        |> take(1)
        |> deliverOnMainQueue).start(next: { settings in
            var uniqueServers: [ProxyServerSettings] = []
            var seenServers = Set<ProxyServerSettings>()
            for server in settings.servers where seenServers.insert(server).inserted {
                uniqueServers.append(server)
            }
            guard !uniqueServers.isEmpty else {
                let presentationData = sharedContext.currentPresentationData.with { $0 }
                presentControllerImpl?(UndoOverlayController(presentationData: presentationData, content: .info(title: nil, text: presentationData.strings.nagramiXProxyNoneToCheck, timeout: nil, customUndoText: nil), elevatedLayout: false, action: { _ in return false }))
                return
            }
            updateState { state in
                var state = state
                state.checkingAllProxies = true
                return state
            }
            Logger.shared.log("NagramiX", "Proxy batch check started: count=\(uniqueServers.count)")
            let targetServers = Set(uniqueServers)
            var observedCheckingState = false
            checkAllProxiesStatusesDisposable.set((combineLatest(statusesContext.statuses(), proxySettings.get())
            |> deliverOnMainQueue).start(next: { [weak checkAllProxiesStatusesDisposable] statuses, currentSettings in
                let currentServers = targetServers.intersection(Set(currentSettings.servers))
                var resultStatuses: [ProxyServerStatus] = []
                resultStatuses.reserveCapacity(currentServers.count)
                for server in currentServers {
                    guard let status = statuses[server] else {
                        return
                    }
                    resultStatuses.append(status)
                }
                if resultStatuses.contains(where: { status in
                    if case .checking = status {
                        return true
                    }
                    return false
                }) {
                    observedCheckingState = true
                    return
                }
                if currentServers.isEmpty {
                    observedCheckingState = true
                }
                guard observedCheckingState else {
                    return
                }
                var availableCount = 0
                for status in resultStatuses {
                    if case .available = status {
                        availableCount += 1
                    }
                }
                let totalCount = resultStatuses.count
                let unavailableCount = totalCount - availableCount
                checkAllProxiesStatusesDisposable?.set(nil)
                updateState { state in
                    var state = state
                    state.checkingAllProxies = false
                    return state
                }
                Logger.shared.log("NagramiX", "Proxy batch check completed: available=\(availableCount) unavailable=\(unavailableCount)")
                let presentationData = sharedContext.currentPresentationData.with { $0 }
                let text = presentationData.strings.nagramiXProxyCheckSummary(total: totalCount, available: availableCount, unavailable: unavailableCount)
                presentControllerImpl?(UndoOverlayController(presentationData: presentationData, content: .succeed(text: text, timeout: nil, customUndoText: nil), elevatedLayout: false, action: { _ in return false }))
            }))
            statusesContext.recheckAll(servers: uniqueServers)
        }))
    }

    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus, nagramiXSettingsSignal, NagramiXProxyVPNPolicy.bypassedSignal())
    |> map { presentationData, state, proxySettings, statuses, connectionStatus, nagramiXSettings, vpnBypassed -> (ItemListControllerState, (ItemListNodeState, Any)) in
        var presentationData = presentationData
        let updatedTheme = presentationData.theme.withModalBlocksBackground()
        presentationData = presentationData.withUpdated(theme: updatedTheme)
        
        var leftNavigationButton: ItemListNavigationButton?
        if case .modal = mode {
            leftNavigationButton = ItemListNavigationButton(content: .icon(.close), style: .regular, enabled: true, action: {
                dismissImpl?()
            })
        }
        
        let rightNavigationButton: ItemListNavigationButton?
        if proxySettings.servers.isEmpty {
            rightNavigationButton = nil
        } else if state.editing {
            rightNavigationButton = ItemListNavigationButton(content: .icon(.done), style: .bold, enabled: true, staysInRow: true, action: {
                updateState { state in
                    var state = state
                    state.editing = false
                    return state
                }
            })
        } else {
            rightNavigationButton = ItemListNavigationButton(content: .text(presentationData.strings.Common_Edit), style: .regular, enabled: true, action: {
                updateState { state in
                    var state = state
                    state.editing = true
                    return state
                }
            })
        }
        
        let controllerState = ItemListControllerState(presentationData: ItemListPresentationData(presentationData), title: .text(presentationData.strings.SocksProxySetup_Title), leftNavigationButton: leftNavigationButton, rightNavigationButton: rightNavigationButton, backNavigationButton: ItemListBackButton(title: presentationData.strings.Common_Back))
        let listState = ItemListNodeState(presentationData: ItemListPresentationData(presentationData), entries: proxySettingsControllerEntries(theme: presentationData.theme, strings: presentationData.strings, state: state, proxySettings: proxySettings, nagramiXSettings: nagramiXSettings, statuses: statuses, connectionStatus: connectionStatus, vpnBypassed: vpnBypassed), style: .blocks, ensureVisibleItemTag: focusOnItemTag)
        
        return (controllerState, (listState, arguments))
    }
    
    let controller = ItemListController(presentationData: ItemListPresentationData(presentationData), updatedPresentationData: updatedPresentationData |> map(ItemListPresentationData.init(_:)), state: signal, tabBarItem: nil)
    controller.navigationPresentation = .modal
    pushControllerImpl = { [weak controller] c in
        (controller?.navigationController as? NavigationController)?.pushViewController(c)
    }
    presentControllerImpl = { [weak controller] c in
        controller?.present(c, in: .window(.root))
    }
    dismissImpl = { [weak controller] in
        controller?.dismiss()
    }
    controller.setReorderEntry({ (fromIndex: Int, toIndex: Int, entries: [ProxySettingsControllerEntry]) -> Signal<Bool, NoError> in
        let fromEntry = entries[fromIndex]
        guard case let .server(_, _, _, fromServer, _, _, _, _) = fromEntry else {
            return .single(false)
        }
        var referenceServer: ProxyServerSettings?
        var beforeAll = false
        var afterAll = false
        if toIndex < entries.count {
            switch entries[toIndex] {
                case let .server(_, _, _, toServer, _, _, _, _):
                    referenceServer = toServer
                default:
                    if entries[toIndex] < fromEntry {
                        beforeAll = true
                    } else {
                        afterAll = true
                    }
            }
        } else {
            afterAll = true
        }

        return updateProxySettingsInteractively(accountManager: accountManager, { current in
            var current = current
            if let index = current.servers.firstIndex(of: fromServer) {
                current.servers.remove(at: index)
            }
            if let referenceServer = referenceServer {
                var inserted = false
                for i in 0 ..< current.servers.count {
                    if current.servers[i] == referenceServer {
                        if fromIndex < toIndex {
                            current.servers.insert(fromServer, at: i + 1)
                        } else {
                            current.servers.insert(fromServer, at: i)
                        }
                        inserted = true
                        break
                    }
                }
                if !inserted {
                    current.servers.append(fromServer)
                }
            } else if beforeAll {
                current.servers.insert(fromServer, at: 0)
            } else if afterAll {
                current.servers.append(fromServer)
            }
            return current
        })
    })
    
    shareProxyListImpl = { [weak controller] in
        guard let context = context, let strongController = controller else {
            return
        }
        let _ = (proxySettings.get()
            |> take(1)
            |> deliverOnMainQueue).start(next: { settings in
                var result = ""
                for server in settings.servers {
                    var string: String
                    switch server.connection {
                    case let .mtp(secret):
                        let secret = MTProxySecret.parseData(secret)?.serializeToString() ?? ""
                        string = "https://t.me/proxy?server=\(server.host)&port=\(server.port)"
                        string += "&secret=\((secret as NSString).addingPercentEncoding(withAllowedCharacters: CharacterSet.urlQueryValueAllowed) ?? "")"
                    case let .socks5(username, password):
                        string = "https://t.me/socks?server=\(server.host)&port=\(server.port)"
                        if let username = username, let password = password {
                            string += "&user=\((username as NSString).addingPercentEncoding(withAllowedCharacters: CharacterSet.urlQueryValueAllowed) ?? "")&pass=\((password as NSString).addingPercentEncoding(withAllowedCharacters: CharacterSet.urlQueryValueAllowed) ?? "")"
                        }
                    case .web:
                        // nil when a stored server no longer canonicalizes. Skip it rather
                        // than contributing an empty entry and a stray blank line.
                        guard let link = webProxySettingsLink(server) else {
                            continue
                        }
                        string = link
                    }
                    
                    if !result.isEmpty {
                        result += "\n\n"
                    }
                    result += string
                }
                
                presentExternalShare(context: context, text: result, parentController: strongController)
            })
    }
    
    if let focusOnItemTag {
        var didFocusOnItem = false
        controller.afterTransactionCompleted = { [weak controller] in
            if !didFocusOnItem, let controller {
                controller.forEachItemNode { itemNode in
                    if let itemNode = itemNode as? ItemListItemNode, let tag = itemNode.tag, tag.isEqual(to: focusOnItemTag) {
                        didFocusOnItem = true
                        itemNode.displayHighlight()
                    }
                }
            }
        }
    }
    
    return controller
}
