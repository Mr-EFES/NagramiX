#!/usr/bin/env python3
"""Apply the isolated NagramiX next-version feature overlay."""

from __future__ import annotations

import shutil
import re
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Pinned patch anchor was not found ({label}): {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_unique(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    occurrence_count = text.count(old)
    if occurrence_count != 1:
        raise SystemExit(f"Pinned patch anchor must occur exactly once, found {occurrence_count} ({label}): {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_between(path: Path, start: str, end: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    start_index = text.find(start)
    end_index = text.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        raise SystemExit(f"Pinned 0.2.0 patch range was not found ({label}): {path}")
    path.write_text(text[:start_index] + new + text[end_index:], encoding="utf-8")


def localize_debug_titles(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'title: "([^"\\]*(?:\\.[^"\\]*)*)"', lambda match: f'title: presentationData.strings.nagramiXDebugLocalized("{match.group(1)}")', text)
    text = re.sub(r'title: \.text\("([^"\\]*(?:\\.[^"\\]*)*)"\)', lambda match: f'title: .text(presentationData.strings.nagramiXDebugLocalized("{match.group(1)}"))', text)
    text = text.replace('text: "Now restart the app"', 'text: presentationData.strings.nagramiXDebugLocalized("Now restart the app")')
    text = text.replace('text = "Done"', 'text = presentationData.strings.nagramiXDebugLocalized("Done")')
    text = text.replace('text = "Failed"', 'text = presentationData.strings.nagramiXDebugLocalized("Failed")')
    path.write_text(text, encoding="utf-8")


def apply_features(source: Path) -> None:
    overlay = Path(__file__).resolve().parent

    settings_icons_source = overlay / "Assets" / "SettingsIcons"
    settings_icons_target = source / "submodules" / "TelegramUI" / "Images.xcassets" / "Item List" / "Icons"
    for icon_source in settings_icons_source.iterdir():
        if icon_source.is_dir():
            shutil.copytree(icon_source, settings_icons_target / icon_source.name, dirs_exist_ok=True)

    presentation_resources_settings = source / "submodules" / "TelegramPresentationData" / "Sources" / "Resources" / "PresentationResourcesSettings.swift"
    replace_once(
        presentation_resources_settings,
        """    public static let support = renderSettingsIcon(name: "Item List/Icons/Support", backgroundColors: [colorOrange])
    public static let faq = renderSettingsIcon(name: "Item List/Icons/Faq", backgroundColors: [colorLightBlue])
    public static let tips = renderSettingsIcon(name: "Item List/Icons/Tips", backgroundColors: [UIColor(rgb: 0xffcc02)])
""",
        """    public static let support = renderSettingsIcon(name: "Item List/Icons/Support", backgroundColors: [colorOrange])
    public static let faq = renderSettingsIcon(name: "Item List/Icons/Faq", backgroundColors: [colorLightBlue])
    public static let tips = renderSettingsIcon(name: "Item List/Icons/Tips", backgroundColors: [UIColor(rgb: 0xffcc02)])
    public static let nagramiXFeatures = renderSettingsIcon(name: "Item List/Icons/NagramiXFeatures", backgroundColors: [colorPurple])
    public static let nagramiXUpdates = renderSettingsIcon(name: "Item List/Icons/NagramiXUpdates", backgroundColors: [colorOrange])
""",
        "NagramiX information block icons",
    )

    default_strings = source / "submodules" / "TelegramPresentationData" / "Sources" / "DefaultPresentationStrings.swift"
    replace_once(
        default_strings,
        'PresentationStrings.Component(languageCode: "en", localizedName: "English", pluralizationRulesCode: nil, dict: NSDictionary(contentsOf: URL(fileURLWithPath: getAppBundle().path(forResource: "Localizable", ofType: "strings", inDirectory: nil, forLocalization: "en")!))',
        'PresentationStrings.Component(languageCode: "ru", localizedName: "Русский", pluralizationRulesCode: nil, dict: NSDictionary(contentsOf: URL(fileURLWithPath: getAppBundle().path(forResource: "Localizable", ofType: "strings", inDirectory: nil, forLocalization: "ru")!))',
        "Use Russian as the clean-install primary localization",
    )
    replace_once(
        default_strings,
        """public let defaultPresentationStrings = PresentationStrings(primaryComponent:""",
        """private func nagramiXDefaultRussianDictionary() -> [String: String] {
    var dictionary = NSDictionary(contentsOf: URL(fileURLWithPath: getAppBundle().path(forResource: "Localizable", ofType: "strings", inDirectory: nil, forLocalization: "ru")!)) as! [String: String]
    dictionary["Common.Edit"] = "Изменить"
    return dictionary
}

public let defaultPresentationStrings = PresentationStrings(primaryComponent:""",
        "Override the abbreviated Russian Edit label in the default locale",
    )
    replace_once(
        default_strings,
        'dict: NSDictionary(contentsOf: URL(fileURLWithPath: getAppBundle().path(forResource: "Localizable", ofType: "strings", inDirectory: nil, forLocalization: "ru")!)) as! [String : String]), secondaryComponent:',
        'dict: nagramiXDefaultRussianDictionary()), secondaryComponent:',
        "Use the corrected Russian dictionary on clean install",
    )

    presentation_theme_settings = source / "submodules" / "TelegramUIPreferences" / "Sources" / "PresentationThemeSettings.swift"
    replace_once(
        presentation_theme_settings,
        "PresentationThemeSettings(theme: .builtin(.dayClassic), themePreferredBaseTheme:",
        "PresentationThemeSettings(theme: .builtin(.nightAccent), themePreferredBaseTheme:",
        "Use Telegram's standard dark-blue theme on a clean install",
    )

    presentation_data = source / "submodules" / "TelegramPresentationData" / "Sources" / "PresentationData.swift"
    replace_once(
        presentation_data,
        "public func dictFromLocalization(_ value: Localization) -> [String: String] {",
        "public func dictFromLocalization(_ value: Localization, languageCode: String? = nil) -> [String: String] {",
        "Pass locale identity into downloaded localization conversion",
    )
    replace_once(
        presentation_data,
        """    return dict
}

private func currentDateTimeFormat()""",
        """    if languageCode?.lowercased().hasPrefix("ru") == true {
        dict["Common.Edit"] = "Изменить"
    }
    return dict
}

private func currentDateTimeFormat()""",
        "Correct every user-facing Edit action in the Russian locale",
    )
    presentation_data_text = presentation_data.read_text(encoding="utf-8")
    presentation_data_text = presentation_data_text.replace(
        "dictFromLocalization(localizationSettings.primaryComponent.localization)",
        "dictFromLocalization(localizationSettings.primaryComponent.localization, languageCode: localizationSettings.primaryComponent.languageCode)",
    ).replace(
        "dictFromLocalization($0.localization)",
        "dictFromLocalization($0.localization, languageCode: $0.languageCode)",
    )
    presentation_data.write_text(presentation_data_text, encoding="utf-8")
    replace_once(
        presentation_data,
        """    return PresentationData(strings: defaultPresentationStrings, theme: defaultPresentationTheme, autoNightModeTriggered: false, chatWallpaper: defaultPresentationTheme.chat.defaultWallpaper,""",
        """    return PresentationData(strings: defaultPresentationStrings, theme: defaultDarkTintedPresentationTheme, autoNightModeTriggered: false, chatWallpaper: defaultDarkTintedPresentationTheme.chat.defaultWallpaper,""",
        "Use Telegram's dark-blue presentation before account settings load",
    )

    core_source = overlay / "Sources" / "NagramiXCore"
    core_target = source / "submodules" / "NagramiXCore"
    if core_target.exists():
        raise SystemExit(f"NagramiXCore already exists in the source tree: {core_target}")
    shutil.copytree(core_source, core_target)

    mtproto_source = overlay / "Sources" / "MtProtoKit"
    mtproto_target = source / "submodules" / "MtProtoKit" / "Sources"
    shutil.copy2(mtproto_source / "NagramiXDNSResolver.h", mtproto_target / "NagramiXDNSResolver.h")
    shutil.copy2(mtproto_source / "NagramiXDNSResolver.m", mtproto_target / "NagramiXDNSResolver.m")
    mtproto_public = source / "submodules" / "MtProtoKit" / "PublicHeaders" / "MtProtoKit"
    shutil.copy2(mtproto_source / "NagramiXDNSResolver.h", mtproto_public / "NagramiXDNSResolver.h")
    replace_once(
        mtproto_public / "MtProtoKit.h",
        "#import <MtProtoKit/MTProxyConnectivity.h>\n",
        "#import <MtProtoKit/MTProxyConnectivity.h>\n#import <MtProtoKit/NagramiXDNSResolver.h>\n",
        "Expose NagramiX DoH endpoint validation to SettingsUI",
    )

    mt_dns = mtproto_target / "MTDNS.m"
    replace_once(
        mt_dns,
        '#import "MTDNS.h"\n',
        '#import "MTDNS.h"\n#import "NagramiXDNSResolver.h"\n',
        "NagramiX real DoH resolver import",
    )
    replace_once(
        mt_dns,
        """+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port {
    return [[self resolveHostname:hostname] timeout:10.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[self resolveHostnameNative:hostname port:port]];
}
""",
        """+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port {
    if ([NagramiXDNSResolver usesSystemResolver]) {
        return [self resolveHostnameNative:hostname port:port];
    }
    return [[NagramiXDNSResolver resolveHostname:hostname] timeout:12.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[MTSignal fail:[NSError errorWithDomain:@"org.nagramix.dns" code:5 userInfo:nil]]];
}

+ (MTSignal *)testDohEndpoint:(NSString *)endpoint hostname:(NSString *)hostname {
    return [[NagramiXDNSResolver testEndpoint:endpoint hostname:hostname] timeout:12.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[MTSignal fail:[NSError errorWithDomain:@"org.nagramix.dns" code:6 userInfo:nil]]];
}
""",
        "Use selected System or DoH resolver in the real MTProto proxy DNS path",
    )

    mt_dns_header = mtproto_target / "MTDNS.h"
    replace_once(
        mt_dns_header,
        "+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port;\n",
        "+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port;\n+ (MTSignal *)testDohEndpoint:(NSString *)endpoint hostname:(NSString *)hostname;\n",
        "Expose Custom DoH validation through the actual resolver",
    )

    mt_tcp_connection = mtproto_target / "MTTcpConnection.m"
    replace_once(
        mt_tcp_connection,
        """                }];
            } file:__FILE_NAME__ line:__LINE__]];
""",
        """                }];
            } error:^(id error) {
                (void)error;
                [[MTTcpConnection tcpQueue] dispatchOnQueue:^{
                    __strong MTTcpConnection *strongSelf = weakSelf;
                    if (strongSelf != nil) {
                        [strongSelf closeAndNotifyWithError:true];
                    }
                }];
            } completed:nil file:__FILE_NAME__ line:__LINE__]];
""",
        "Close MTProto connection when the selected DoH resolver fails",
    )

    network_source = source / "submodules" / "TelegramCore" / "Sources" / "Network" / "Network.swift"
    replace_once(
        network_source,
        """    public func dropConnectionStatus() {
        _connectionStatus.set(.single(.waitingForNetwork))
    }
""",
        """    public func dropConnectionStatus() {
        _connectionStatus.set(.single(.waitingForNetwork))
    }

    public func reconnectForNagramiXDnsChange() {
        self.mtProto.simulateDisconnection()
        self.dropConnectionStatus()
    }
""",
        "Reconnect MTProto after a runtime DNS resolver change",
    )

    account_source = source / "submodules" / "TelegramCore" / "Sources" / "Account" / "Account.swift"
    replace_once(
        account_source,
        """        }))

        if !supplementary {
            let mediaBox = postbox.mediaBox
""",
        """        }))

        let nagramiXDnsObserver = NotificationCenter.default.addObserver(forName: Notification.Name("NagramiXDnsSettingsChanged"), object: nil, queue: nil, using: { _ in
            network.reconnectForNagramiXDnsChange()
        })
        self.managedOperationsDisposable.add(ActionDisposable {
            NotificationCenter.default.removeObserver(nagramiXDnsObserver)
        })

        if !supplementary {
            let mediaBox = postbox.mediaBox
""",
        "Reconnect every account network when the selected resolver changes",
    )
    replace_once(
        account_source,
        """        self.managedOperationsDisposable.add(ActionDisposable {
            NotificationCenter.default.removeObserver(nagramiXDnsObserver)
        })

        if !supplementary {
""",
        """        self.managedOperationsDisposable.add(ActionDisposable {
            NotificationCenter.default.removeObserver(nagramiXDnsObserver)
        })

        if !supplementary {
            let nagramiXProxyFailoverController = NagramiXProxyFailoverController()
            nagramiXProxyFailoverController.start(accountManager: accountManager, network: network)
            self.managedOperationsDisposable.add(ActionDisposable {
                nagramiXProxyFailoverController.stop()
            })
        }

        if !supplementary {
""",
        "Start the process-wide proxy failover controller outside UI lifecycle",
    )

    settings_controller_source = overlay / "Sources" / "SettingsUI" / "NagramiXSettingsController.swift"
    settings_controller_target = source / "submodules" / "SettingsUI" / "Sources" / settings_controller_source.name
    shutil.copy2(settings_controller_source, settings_controller_target)
    shutil.copy2(overlay / "Sources" / "SettingsUI" / "NagramiXCustomDohController.swift", settings_controller_target.parent / "NagramiXCustomDohController.swift")

    item_list_controller = source / "submodules" / "ItemListUI" / "Sources" / "ItemListController.swift"
    replace_once(
        item_list_controller,
        "    case sectionControl([String], Int)\n",
        "    case sectionControl([String], Int)\n    case equalSectionControl([String], Int)\n",
        "Equal-width NagramiX settings title mode",
    )
    replace_once(
        item_list_controller,
        "                            case let .sectionControl(sections, index):\n",
        "                            case let .sectionControl(sections, index), let .equalSectionControl(sections, index):\n",
        "Handle equal-width NagramiX settings title mode",
    )
    replace_once(
        item_list_controller,
        "                                let segmentedTitleView = ItemListControllerSegmentedTitleView(theme: controllerState.presentationData.theme, segments: sections, selectedIndex: index)\n",
        "                                let segmentedTitleView = ItemListControllerSegmentedTitleView(theme: controllerState.presentationData.theme, segments: sections, selectedIndex: index, fillsAvailableWidth: controllerState.title.isEqualSectionControl)\n",
        "Configure equal-width NagramiX settings title mode",
    )
    replace_once(
        item_list_controller,
        "public final class ItemListControllerTabBarItem: Equatable {\n",
        """public extension ItemListControllerTitle {
    var isEqualSectionControl: Bool {
        if case .equalSectionControl = self {
            return true
        }
        return false
    }
}

public final class ItemListControllerTabBarItem: Equatable {
""",
        "Expose equal-width title layout selection",
    )

    segmented_title_view = source / "submodules" / "ItemListUI" / "Sources" / "ItemListControllerSegmentedTitleView.swift"
    replace_once(
        segmented_title_view,
        "    private let tabSelector = ComponentView<Empty>()\n",
        "    private let tabSelector = ComponentView<Empty>()\n    private let fillsAvailableWidth: Bool\n    private var expandedContentFrame: CGRect?\n",
        "Store full-width NagramiX segmented title layout",
    )
    replace_once(
        segmented_title_view,
        "    public init(theme: PresentationTheme, segments: [String], selectedIndex: Int) {\n",
        "    public init(theme: PresentationTheme, segments: [String], selectedIndex: Int, fillsAvailableWidth: Bool = false) {\n",
        "Add equal-width segmented title initializer",
    )
    replace_once(
        segmented_title_view,
        "        self.index = selectedIndex\n        \n        self.backgroundContainer = GlassBackgroundContainerView()\n",
        "        self.index = selectedIndex\n        self.fillsAvailableWidth = fillsAvailableWidth\n        \n        self.backgroundContainer = GlassBackgroundContainerView()\n",
        "Initialize equal-width segmented title layout",
    )
    replace_once(
        segmented_title_view,
        "                content: .title(HorizontalTabsComponent.Tab.Title(text: segment, entities: [], enableAnimations: false)),\n",
        "                content: .title(HorizontalTabsComponent.Tab.Title(text: segment, entities: [], enableAnimations: false, isBold: self.fillsAvailableWidth)),\n",
        "Use bold NagramiX settings category titles",
    )
    replace_once(
        segmented_title_view,
        "                layout: .fit\n",
        "                layout: self.fillsAvailableWidth ? .equal : .fit\n",
        "Use equal-width NagramiX settings category sections",
    )
    replace_once(
        segmented_title_view,
        """        self.addSubview(self.backgroundContainer)
        self.backgroundContainer.contentView.addSubview(self.backgroundView)
""",
        """        self.clipsToBounds = !self.fillsAvailableWidth
        self.addSubview(self.backgroundContainer)
        self.backgroundContainer.contentView.addSubview(self.backgroundView)

        if self.fillsAvailableWidth {
            self.setContentHuggingPriority(.defaultLow, for: .horizontal)
            self.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        }
""",
        "Allow the NagramiX category panel to use the trailing navigation space",
    )
    replace_once(
        segmented_title_view,
        """    override public func layoutSubviews() {
""",
        """    override public var intrinsicContentSize: CGSize {
        if self.fillsAvailableWidth {
            return CGSize(width: UIView.noIntrinsicMetric, height: 44.0)
        }
        return super.intrinsicContentSize
    }

    override public func sizeThatFits(_ size: CGSize) -> CGSize {
        if self.fillsAvailableWidth {
            return CGSize(width: size.width, height: 44.0)
        }
        return super.sizeThatFits(size)
    }

    override public func layoutSubviews() {
""",
        "Make the category title adaptive instead of sizing it from localized text",
    )
    replace_once(
        segmented_title_view,
        "    private func update(transition: ComponentTransition) {\n        guard let size = self.validLayout else {\n            return\n        }\n",
        """    override public func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        if let expandedContentFrame = self.expandedContentFrame, expandedContentFrame.contains(point) {
            return true
        }
        return super.point(inside: point, with: event)
    }

    private func update(transition: ComponentTransition) {
        guard let size = self.validLayout else {
            return
        }

        var contentWidth = size.width
        if self.fillsAvailableWidth, let window = self.window {
            let windowFrame = self.convert(self.bounds, to: window)
            let trailingInset = max(16.0, window.safeAreaInsets.right)
            contentWidth = max(contentWidth, floor(window.bounds.width - windowFrame.minX - trailingInset))
        }
""",
        "Extend the category panel from its post-back-button origin to the content trailing inset",
    )
    replace_once(
        segmented_title_view,
        "            containerSize: CGSize(width: size.width, height: 44.0)\n",
        "            containerSize: CGSize(width: contentWidth, height: 44.0)\n",
        "Give equal category tabs the complete trailing navigation width",
    )
    replace_once(
        segmented_title_view,
        "        let tabSelectorFrame = CGRect(origin: CGPoint(x: floor((size.width - tabSelectorSize.width) / 2.0), y: floor((size.height - tabSelectorSize.height) / 2.0)), size: tabSelectorSize)\n",
        "        let tabSelectorFrame = CGRect(origin: CGPoint(x: self.fillsAvailableWidth ? 0.0 : floor((size.width - tabSelectorSize.width) / 2.0), y: floor((size.height - tabSelectorSize.height) / 2.0)), size: tabSelectorSize)\n        self.expandedContentFrame = tabSelectorFrame\n",
        "Anchor the full-width category panel after the back button instead of centering a compressed control",
    )

    horizontal_tabs = source / "submodules" / "TelegramUI" / "Components" / "HorizontalTabsComponent" / "Sources" / "HorizontalTabsComponent.swift"
    replace_once(
        horizontal_tabs,
        """    public enum Layout {
        case fit
        case fill
    }
""",
        """    public enum Layout {
        case fit
        case fill
        case equal
    }
""",
        "Add unconditional equal-width horizontal tab layout",
    )
    replace_once(
        horizontal_tabs,
        """            public let enableAnimations: Bool
""" + "            \n" + """            public init(text: String, entities: [MessageTextEntity], enableAnimations: Bool) {
                self.text = text
                self.entities = entities
                self.enableAnimations = enableAnimations
            }
""",
        """            public let enableAnimations: Bool
            public let isBold: Bool
""" + "            \n" + """            public init(text: String, entities: [MessageTextEntity], enableAnimations: Bool, isBold: Bool = false) {
                self.text = text
                self.entities = entities
                self.enableAnimations = enableAnimations
                self.isBold = isBold
            }
""",
        "Support explicitly bold horizontal tab titles",
    )
    replace_once(
        horizontal_tabs,
        "                let font = Font.medium(15.0)\n",
        "                let font = title.isBold ? Font.bold(15.0) : Font.medium(15.0)\n",
        "Render NagramiX settings category titles in bold",
    )
    replace_once(
        horizontal_tabs,
        """            let scrollContentWidth: CGFloat
            if case .fill = component.layout, totalContentWidth < availableSize.width {
""",
        """            let scrollContentWidth: CGFloat
            let usesEqualItemWidths: Bool
            switch component.layout {
            case .fit:
                usesEqualItemWidths = false
            case .fill:
                usesEqualItemWidths = totalContentWidth < availableSize.width
            case .equal:
                usesEqualItemWidths = true
            }
            if usesEqualItemWidths {
""",
        "Always divide NagramiX settings categories equally",
    )
    replace_once(
        horizontal_tabs,
        """            switch component.layout {
            case .fill:
                sizeWidth = availableSize.width
            case .fit:
""",
        """            switch component.layout {
            case .fill, .equal:
                sizeWidth = availableSize.width
            case .fit:
""",
        "Size equal-width NagramiX settings categories to the full panel",
    )

    telegram_voip_build = source / "submodules" / "TelegramVoip" / "BUILD"
    replace_once(
        telegram_voip_build,
        '        "//submodules/TelegramCore:TelegramCore",\n',
        '        "//submodules/TelegramCore:TelegramCore",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "TelegramVoip NagramiX settings dependency",
    )
    ongoing_call_context = source / "submodules" / "TelegramVoip" / "Sources" / "OngoingCallContext.swift"
    replace_once(
        ongoing_call_context,
        "import CoreMedia\n",
        "import CoreMedia\nimport NagramiXCore\n",
        "VoIP Force TCP settings import",
    )
    replace_once(
        ongoing_call_context,
        "                var allowP2P = allowP2P\n",
        "                var allowP2P = allowP2P\n                let forceTcpCalls = NagramiXTabSettings.current.forceTcpCalls\n",
        "Snapshot Force TCP for the newly created call",
    )
    replace_once(
        ongoing_call_context,
        """                #if DEBUG && true
                var customParameters = customParameters
""",
        """                var customParameters = customParameters

                #if DEBUG && true
""",
        "Make VoIP custom parameters mutable in release builds",
    )
    replace_once(
        ongoing_call_context,
        """                #endif
""" + "                \n" + """                /*#if DEBUG
""",
        """                #endif
""" + "                \n" + """                if forceTcpCalls {
                    var customParametersValue = (try? JSONSerialization.jsonObject(with: (customParameters ?? "{}").data(using: .utf8)!) as? [String: Any]) ?? [:]
                    customParametersValue["network_use_tcponly"] = true as NSNumber
                    customParameters = String(data: try! JSONSerialization.data(withJSONObject: customParametersValue), encoding: .utf8)!
                    filteredConnections = filteredConnections.filter { $0.hasTcp }
                    allowP2P = false
                }

                /*#if DEBUG
""",
        "Force one-to-one calls onto Telegram TCP relay endpoints",
    )
    replace_once(
        ongoing_call_context,
        "                    allowTCP: enableTCP,\n",
        "                    allowTCP: enableTCP || forceTcpCalls,\n",
        "Enable Telegram TCP transport when Force TCP is active",
    )

    telegram_core_overlay = overlay / "Sources" / "TelegramCore" / "NagramiXProxyFailoverController.swift"
    telegram_core_target = source / "submodules" / "TelegramCore" / "Sources" / "Network" / telegram_core_overlay.name
    shutil.copy2(telegram_core_overlay, telegram_core_target)

    proxy_statuses = source / "submodules" / "TelegramCore" / "Sources" / "Network" / "ProxyServersStatuses.swift"
    replace_once(
        proxy_statuses,
        """            let disposable = MTProxyConnectivity.pingProxy(with: context, datacenterId: datacenterId, settings: server.mtProxySettings).start(next: { next in
                if let next = next as? MTProxyConnectivityStatus {
                    if !next.reachable {
                        subscriber.putNext(.notAvailable)
                    } else {
                        subscriber.putNext(.available(next.roundTripTime))
                    }
                }
            })
""",
        """            let disposable = MTProxyConnectivity.pingProxy(with: context, datacenterId: datacenterId, settings: server.mtProxySettings).start(next: { next in
                if let next = next as? MTProxyConnectivityStatus {
                    if !next.reachable {
                        subscriber.putNext(.notAvailable)
                    } else {
                        subscriber.putNext(.available(next.roundTripTime))
                    }
                }
            }, error: { _ in
                subscriber.putNext(.notAvailable)
            }, completed: {
            })
""",
        "Treat offline and DNS proxy-check failures as unavailable results",
    )
    replace_once(
        proxy_statuses,
        """final class ProxyServersStatusesImpl {
    private let queue: Queue
\x20\x20\x20\x20
    private var contexts: [ProxyServerSettings: ProxyServerItemContext] = [:]
""",
        """final class ProxyServersStatusesImpl {
    private let queue: Queue
    private let context: MTContext
    private let datacenterId: Int

    private var contexts: [ProxyServerSettings: ProxyServerItemContext] = [:]
    private var contextIds: [ProxyServerSettings: Int64] = [:]
    private var nextContextId: Int64 = 0
""",
        "Retain native proxy checker inputs for manual refresh",
    )
    replace_once(
        proxy_statuses,
        """    init(queue: Queue, network: Network, servers: Signal<[ProxyServerSettings], NoError>) {
        self.queue = queue
\x20\x20\x20\x20\x20\x20\x20\x20
""",
        """    init(queue: Queue, network: Network, servers: Signal<[ProxyServerSettings], NoError>) {
        self.queue = queue
        self.context = network.context
        self.datacenterId = network.datacenterId

""",
        "Capture native proxy checker context",
    )
    replace_once(
        proxy_statuses,
        """                        if strongSelf.contexts[key] == nil {
                            let context = ProxyServerItemContext(queue: strongSelf.queue, context: network.context, datacenterId: network.datacenterId, server: key, updated: { value in
                                queue.async {
                                    if let strongSelf = self {
                                        strongSelf.contexts[key]?.value = value
                                        strongSelf.updateValues()
                                    }
                                }
                            })
                            strongSelf.contexts[key] = context
                        }
""",
        """                        if strongSelf.contexts[key] == nil {
                            strongSelf.addContext(for: key)
                        }
""",
        "Create proxy checks through a reusable native context helper",
    )
    replace_once(
        proxy_statuses,
        """                    for key in removeKeys {
                        let _ = strongSelf.contexts.removeValue(forKey: key)
                    }
""",
        """                    for key in removeKeys {
                        let _ = strongSelf.contexts.removeValue(forKey: key)
                        strongSelf.contextIds.removeValue(forKey: key)
                    }
""",
        "Invalidate deleted proxy check callbacks",
    )
    replace_once(
        proxy_statuses,
        """    deinit {
        self.serversDisposable?.dispose()
    }
\x20\x20\x20\x20
    private func updateValues() {
""",
        """    deinit {
        self.serversDisposable?.dispose()
    }

    private func addContext(for server: ProxyServerSettings) {
        assert(self.queue.isCurrent())
        self.nextContextId &+= 1
        let contextId = self.nextContextId
        self.contextIds[server] = contextId
        let queue = self.queue
        let context = ProxyServerItemContext(queue: queue, context: self.context, datacenterId: self.datacenterId, server: server, updated: { [weak self] value in
            queue.async {
                if let strongSelf = self, strongSelf.contextIds[server] == contextId {
                    strongSelf.contexts[server]?.value = value
                    strongSelf.updateValues()
                }
            }
        })
        self.contexts[server] = context
    }

    func recheckAll(servers: [ProxyServerSettings]) {
        assert(self.queue.isCurrent())
        let servers = Array(Set(servers))
        self.contexts.removeAll()
        self.contextIds.removeAll()
        self.currentValues = Dictionary(uniqueKeysWithValues: servers.map { ($0, ProxyServerStatus.checking) })
        for server in servers {
            self.addContext(for: server)
        }
    }

    private func updateValues() {
""",
        "Add native batch proxy recheck implementation",
    )
    replace_once(
        proxy_statuses,
        """    public func statuses() -> Signal<[ProxyServerSettings: ProxyServerStatus], NoError> {
""",
        """    public func recheckAll(servers: [ProxyServerSettings]) {
        self.impl.with { impl in
            impl.recheckAll(servers: servers)
        }
    }

    public func statuses() -> Signal<[ProxyServerSettings: ProxyServerStatus], NoError> {
""",
        "Expose native proxy batch recheck trigger",
    )

    settings_build = source / "submodules" / "SettingsUI" / "BUILD"
    replace_once(
        settings_build,
        '        "//submodules/AccountContext:AccountContext",\n',
        '        "//submodules/AccountContext:AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "SettingsUI NagramiXCore dependency",
    )

    proxy_list = source / "submodules" / "SettingsUI" / "Sources" / "Data and Storage" / "ProxyListSettingsController.swift"
    replace_once(
        proxy_list,
        "import UrlEscaping\n",
        "import UrlEscaping\nimport UndoUI\nimport NagramiXCore\n",
        "Proxy settings NagramiXCore import",
    )
    replace_between(
        proxy_list,
        "private final class ProxySettingsControllerArguments {",
        "private struct ProxySettingsControllerState: Equatable {",
        (overlay / "Sources" / "SettingsUI" / "ProxyListNagramiXBlock.swift.inc").read_text(encoding="utf-8"),
        "Proxy screen DNS and automatic failover controls",
    )
    replace_once(
        proxy_list,
        """private struct ProxySettingsControllerState: Equatable {
    var editing: Bool = false
    var revealedServer: ProxyServerSettings? = nil
}
""",
        """private struct ProxySettingsControllerState: Equatable {
    var editing: Bool = false
    var revealedServer: ProxyServerSettings? = nil
    var checkingAllProxies: Bool = false
}
""",
        "Track the manual proxy batch check state",
    )
    replace_once(
        proxy_list,
        """    var pushControllerImpl: ((ViewController) -> Void)?
    var dismissImpl: (() -> Void)?
""",
        """    var pushControllerImpl: ((ViewController) -> Void)?
    var presentControllerImpl: ((ViewController) -> Void)?
    var dismissImpl: (() -> Void)?
""",
        "Proxy settings presentation callback",
    )
    replace_once(
        proxy_list,
        "    var shareProxyListImpl: (() -> Void)?\n    \n    let arguments = ProxySettingsControllerArguments(toggleEnabled: { value in\n",
        """    var shareProxyListImpl: (() -> Void)?
    let nagramiXSettingsPromise = ValuePromise(NagramiXTabSettings.current, ignoreRepeated: false)
    let updateNagramiXSettings: ((inout NagramiXTabSettings) -> Void) -> Void = { transform in
        NagramiXTabSettings.update(transform)
        nagramiXSettingsPromise.set(NagramiXTabSettings.current)
    }
    var selectDnsImpl: (() -> Void)?
    var editCustomDohImpl: (() -> Void)?
    var selectTimeoutImpl: (() -> Void)?
    var checkAllProxiesImpl: (() -> Void)?
    let checkAllProxiesSettingsDisposable = MetaDisposable()
    let checkAllProxiesStatusesDisposable = MetaDisposable()

    let arguments = ProxySettingsControllerArguments(toggleEnabled: { value in
""",
        "Proxy settings persistent NagramiX state",
    )
    replace_once(
        proxy_list,
        """        }).start()
    }, addNewServer: {
""",
        """        }).start()
    }, selectDns: {
        selectDnsImpl?()
    }, editCustomDoh: {
        editCustomDohImpl?()
    }, toggleAutoSwitch: { value in
        updateNagramiXSettings { $0.proxyAutoSwitchEnabled = value }
    }, selectAutoSwitchTimeout: {
        selectTimeoutImpl?()
    }, checkAllProxies: {
        checkAllProxiesImpl?()
    }, addNewServer: {
""",
        "Proxy settings DNS and Auto-Switch actions",
    )
    replace_once(
        proxy_list,
        """    let proxySettings = Promise<ProxySettings>()
""",
        """    editCustomDohImpl = {
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
                $0.customDohUrl = ""
                $0.dnsProvider = .system
            }
        }))
    }
    selectDnsImpl = {
        let presentationData = sharedContext.currentPresentationData.with { $0 }
        let actionSheet = ActionSheetController(presentationData: presentationData)
        let current = NagramiXTabSettings.current
        let providers: [NagramiXDnsProvider] = [.system, .google, .quad9, .adGuard, .mullvad, .cloudflare, .customDoh]
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
        let actionSheet = ActionSheetController(presentationData: presentationData)
        let currentTimeout = NagramiXTabSettings.current.proxyAutoSwitchTimeout
        let values = [15, 30, 60]
        let items: [ActionSheetItem] = values.map { value in
            ActionSheetButtonItem(title: (currentTimeout == value ? "✓ " : "") + nagramiXTimeoutTitle(value, strings: presentationData.strings), color: .accent, action: { [weak actionSheet] in
                actionSheet?.dismissAnimated()
                updateNagramiXSettings { $0.proxyAutoSwitchTimeout = value }
            })
        }
        var timeoutItems: [ActionSheetItem] = [ActionSheetTextItem(title: presentationData.strings.nagramiXProxySwitchAfter)]
        timeoutItems.append(contentsOf: items)
        actionSheet.setItemGroups([
            ActionSheetItemGroup(items: timeoutItems),
            ActionSheetItemGroup(items: [ActionSheetButtonItem(title: presentationData.strings.Common_Cancel, color: .accent, font: .bold, action: { [weak actionSheet] in actionSheet?.dismissAnimated() })])
        ])
        presentControllerImpl?(actionSheet)
    }

    let proxySettings = Promise<ProxySettings>()
""",
        "Native DNS and Auto-Switch selectors plus Custom DoH editor",
    )
    replace_once(
        proxy_list,
        """    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus)
""",
        """    checkAllProxiesImpl = {
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
            Logger.shared.log("NagramiX", "Proxy batch check started: count=\\(uniqueServers.count)")
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
                Logger.shared.log("NagramiX", "Proxy batch check completed: available=\\(availableCount) unavailable=\\(unavailableCount)")
                let presentationData = sharedContext.currentPresentationData.with { $0 }
                let text = presentationData.strings.nagramiXProxyCheckSummary(total: totalCount, available: availableCount, unavailable: unavailableCount)
                presentControllerImpl?(UndoOverlayController(presentationData: presentationData, content: .succeed(text: text, timeout: nil, customUndoText: nil), elevatedLayout: false, action: { _ in return false }))
            }))
            statusesContext.recheckAll(servers: uniqueServers)
        }))
    }

    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus)
""",
        "Run all saved proxies through Telegram's native checker",
    )
    replace_once(
        proxy_list,
        """    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus)
    |> map { presentationData, state, proxySettings, statuses, connectionStatus -> (ItemListControllerState, (ItemListNodeState, Any)) in
""",
        """    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus, nagramiXSettingsPromise.get())
    |> map { presentationData, state, proxySettings, statuses, connectionStatus, nagramiXSettings -> (ItemListControllerState, (ItemListNodeState, Any)) in
""",
        "Observe NagramiX networking settings in Proxy screen",
    )
    replace_once(
        proxy_list,
        "entries: proxySettingsControllerEntries(theme: presentationData.theme, strings: presentationData.strings, state: state, proxySettings: proxySettings, statuses: statuses, connectionStatus: connectionStatus)",
        "entries: proxySettingsControllerEntries(theme: presentationData.theme, strings: presentationData.strings, state: state, proxySettings: proxySettings, nagramiXSettings: nagramiXSettings, statuses: statuses, connectionStatus: connectionStatus)",
        "Render NagramiX networking settings",
    )
    replace_once(
        proxy_list,
        """    pushControllerImpl = { [weak controller] c in
        (controller?.navigationController as? NavigationController)?.pushViewController(c)
    }
""",
        """    pushControllerImpl = { [weak controller] c in
        (controller?.navigationController as? NavigationController)?.pushViewController(c)
    }
    presentControllerImpl = { [weak controller] c in
        controller?.present(c, in: .window(.root))
    }
""",
        "Present Proxy selectors and Custom DoH editor",
    )

    proxy_action_item = source / "submodules" / "SettingsUI" / "Sources" / "Data and Storage" / "ProxySettingsActionItem.swift"
    replace_once(
        proxy_action_item,
        "import PresentationDataUtils\n",
        "import PresentationDataUtils\nimport AppBundle\n",
        "Proxy batch action refresh icon dependency",
    )
    replace_once(
        proxy_action_item,
        """enum ProxySettingsActionIcon {
    case none
    case add
}
""",
        """enum ProxySettingsActionIcon {
    case none
    case add
    case refresh
}
""",
        "Add the proxy batch refresh action icon",
    )
    replace_once(
        proxy_action_item,
        """            let icon = item.icon == .add ? PresentationResourcesItemList.plusIconImage(item.presentationData.theme) : nil
""",
        """            let icon: UIImage?
            switch item.icon {
            case .none:
                icon = nil
            case .add:
                icon = PresentationResourcesItemList.plusIconImage(item.presentationData.theme)
            case .refresh:
                icon = generateTintedImage(image: UIImage(bundleImageName: "Settings/Refresh"), color: item.presentationData.theme.list.itemAccentColor)
            }
""",
        "Render the themed proxy batch refresh icon",
    )

    telegram_ui_build = source / "submodules" / "TelegramUI" / "BUILD"
    replace_once(
        telegram_ui_build,
        '        "//submodules/SettingsUI:SettingsUI",\n',
        '        "//submodules/SettingsUI:SettingsUI",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "TelegramUI NagramiXCore dependency",
    )

    chat_bubble_build = source / "submodules" / "TelegramUI" / "Components" / "Chat" / "ChatMessageBubbleItemNode" / "BUILD"
    replace_once(
        chat_bubble_build,
        '        "//submodules/AccountContext",\n',
        '        "//submodules/AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "Chat message bubble NagramiX settings dependency",
    )
    chat_bubble_source = source / "submodules" / "TelegramUI" / "Components" / "Chat" / "ChatMessageBubbleItemNode" / "Sources" / "ChatMessageBubbleItemNode.swift"
    replace_once(
        chat_bubble_source,
        "import AccountContext\n",
        "import AccountContext\nimport NagramiXCore\n",
        "Chat message bubble NagramiX settings import",
    )
    replace_once(
        chat_bubble_source,
        "        let chatLocationPeerId: PeerId = item.chatLocation.peerId ?? item.content.firstMessage.id.peerId\n",
        """        let chatLocationPeerId: PeerId = item.chatLocation.peerId ?? item.content.firstMessage.id.peerId
        let nagramiXWideChannelPost: Bool
        if NagramiXTabSettings.current.wideChannelPosts,
           case .peer = item.chatLocation,
           let channel = firstMessage.peers[firstMessage.id.peerId] as? TelegramChannel,
           case .broadcast = channel.info,
           firstMessage.adAttribute == nil,
           !isPreview {
            nagramiXWideChannelPost = true
        } else {
            nagramiXWideChannelPost = false
        }
""",
        "Identify only ordinary main-timeline broadcast posts for wide layout",
    )
    replace_once(
        chat_bubble_source,
        "        /*if isInlinePage {\n            needsShareButton = false\n        }*/\n                        \n        var tmpWidth: CGFloat\n",
        """        /*if isInlinePage {
            needsShareButton = false
        }*/

        if nagramiXWideChannelPost {
            needsShareButton = false
            needsSummarizeButton = false
            allowFullWidth = true
        }

        var tmpWidth: CGFloat
""",
        "Use the floating-control gutter for optional wide channel posts",
    )
    replace_once(
        chat_bubble_source,
        "        maximumContentWidth = max(0.0, maximumContentWidth)\n        \n        var contentPropertiesAndPrepareLayouts:",
        """        if nagramiXWideChannelPost {
            // Content-type branches above retain Telegram's special sizing in
            // every other chat. A broadcast post deliberately receives the
            // common adaptive width so forwarded content, polls, media,
            // instant video and grouped content all start from one geometry.
            maximumContentWidth = floor(tmpWidth - layoutConstants.bubble.edgeInset * 3.0 - layoutConstants.bubble.contentInsets.left - layoutConstants.bubble.contentInsets.right - avatarInset)
        }
        maximumContentWidth = max(0.0, maximumContentWidth)

        var contentPropertiesAndPrepareLayouts:""",
        "Give every ordinary broadcast-post content node the shared adaptive width",
    )

    tab_bar_build = source / "submodules" / "TabBarUI" / "BUILD"
    replace_once(
        tab_bar_build,
        '        "//submodules/Display",\n',
        '        "//submodules/Display",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "TabBarUI NagramiXCore dependency",
    )

    chat_list_build = source / "submodules" / "ChatListUI" / "BUILD"
    replace_once(
        chat_list_build,
        '        "//submodules/AccountContext:AccountContext",\n',
        '        "//submodules/AccountContext:AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "ChatListUI NagramiXCore dependency",
    )

    video_message_build = source / "submodules" / "TelegramUI" / "Components" / "VideoMessageCameraScreen" / "BUILD"
    replace_once(
        video_message_build,
        '        "//submodules/AccountContext",\n',
        '        "//submodules/AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "VideoMessageCameraScreen NagramiXCore dependency",
    )

    story_container_build = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "BUILD"
    replace_once(
        story_container_build,
        '        "//submodules/AccountContext",\n',
        '        "//submodules/AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n        "//submodules/PhotoResources",\n',
        "StoryContainerScreen NagramiXCore dependency",
    )

    debug_settings_build = source / "submodules" / "DebugSettingsUI" / "BUILD"
    replace_once(
        debug_settings_build,
        '        "//submodules/Display:Display",\n',
        '        "//submodules/Display:Display",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "DebugSettingsUI NagramiXCore dependency",
    )
    for debug_source_name in ["DebugController.swift", "DebugAccountsController.swift"]:
        debug_source = source / "submodules" / "DebugSettingsUI" / "Sources" / debug_source_name
        replace_once(
            debug_source,
            "import TelegramPresentationData\n",
            "import TelegramPresentationData\nimport NagramiXCore\n",
            f"{debug_source_name} NagramiXCore import",
        )
        localize_debug_titles(debug_source)

    story_content = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryContent.swift"
    replace_once(
        story_content,
        """    public let itemPeer: EnginePeer?

    public init(
""",
        """    public let itemPeer: EnginePeer?
    public let isSeen: Bool

    public init(
""",
        "Story items carry their server read state",
    )
    replace_once(
        story_content,
        """        entityFiles: [EngineMedia.Id: TelegramMediaFile],
        itemPeer: EnginePeer?
    ) {
""",
        """        entityFiles: [EngineMedia.Id: TelegramMediaFile],
        itemPeer: EnginePeer?,
        isSeen: Bool = false
    ) {
""",
        "Add backward-compatible story read-state parameter",
    )
    replace_once(
        story_content,
        """        self.itemPeer = itemPeer
    }
""",
        """        self.itemPeer = itemPeer
        self.isSeen = isSeen
    }
""",
        "Store story read state",
    )
    replace_once(
        story_content,
        """        if lhs.itemPeer != rhs.itemPeer {
            return false
        }
        return true
""",
        """        if lhs.itemPeer != rhs.itemPeer {
            return false
        }
        if lhs.isSeen != rhs.isSeen {
            return false
        }
        return true
""",
        "Compare story read state",
    )

    story_chat_content = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryChatContent.swift"
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: item, allEntityFiles: allEntityFiles),
                                itemPeer: nil
                            )
                        }
""" + "                        \n" + """                        self.nextItems = nextItems
""",
        """                                entityFiles: extractItemEntityFiles(item: item, allEntityFiles: allEntityFiles),
                                itemPeer: nil,
                                isSeen: item.id <= (state?.maxReadId ?? 0)
                            )
                        }
""" + "                        \n" + """                        self.nextItems = nextItems
""",
        "Carry read state for peer story feed items",
    )
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                                itemPeer: nil
                            ),
                            totalCount: totalCount,
""",
        """                                entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                                itemPeer: nil,
                                isSeen: mappedItem.id <= (state?.maxReadId ?? 0)
                            ),
                            totalCount: totalCount,
""",
        "Carry read state for focused peer story",
    )
    replace_once(
        story_chat_content,
        """        self.storyDisposable = (combineLatest(queue: .mainQueue(),
            listContext.state,
            self.focusedIdUpdated.get(),
            preferHighQualityStories
        )
        |> deliverOnMainQueue).startStrict(next: { [weak self] state, _, preferHighQualityStories in
            guard let self else {
                return
            }
""",
        """        let listStateWithReadIds: Signal<(StoryListContext.State, [PeerId: Int32]), NoError> = listContext.state
        |> mapToSignal { state in
            return context.account.postbox.transaction { transaction -> (StoryListContext.State, [PeerId: Int32]) in
                var maxReadIds: [PeerId: Int32] = [:]
                for item in state.items {
                    if maxReadIds[item.id.peerId] == nil {
                        maxReadIds[item.id.peerId] = transaction.getPeerStoryState(peerId: item.id.peerId)?.entry.get(Stories.PeerState.self)?.maxReadId ?? 0
                    }
                }
                return (state, maxReadIds)
            }
        }

        self.storyDisposable = (combineLatest(queue: .mainQueue(),
            listStateWithReadIds,
            self.focusedIdUpdated.get(),
            preferHighQualityStories
        )
        |> deliverOnMainQueue).startStrict(next: { [weak self] stateAndMaxReadIds, _, preferHighQualityStories in
            guard let self else {
                return
            }
            let state = stateAndMaxReadIds.0
            let maxReadIds = stateAndMaxReadIds.1
""",
        "Load per-peer read state for story-list items",
    )
    replace_once(
        story_chat_content,
        """                            entityFiles: extractItemEntityFiles(item: stateItem.storyItem, allEntityFiles: state.allEntityFiles),
                            itemPeer: stateItem.peer
                        ))
""",
        """                            entityFiles: extractItemEntityFiles(item: stateItem.storyItem, allEntityFiles: state.allEntityFiles),
                            itemPeer: stateItem.peer,
                            isSeen: stateItem.id.id <= (maxReadIds[stateItem.id.peerId] ?? 0)
                        ))
""",
        "Carry read state for story-list items",
    )
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: item.storyItem, allEntityFiles: state.allEntityFiles),
                                itemPeer: item.peer
                            ),
                            totalCount: state.totalCount,
""",
        """                                entityFiles: extractItemEntityFiles(item: item.storyItem, allEntityFiles: state.allEntityFiles),
                                itemPeer: item.peer,
                                isSeen: item.id.id <= (maxReadIds[item.id.peerId] ?? 0)
                            ),
                            totalCount: state.totalCount,
""",
        "Carry read state for focused story-list item",
    )
    replace_once(
        story_chat_content,
        """            item |> mapToSignal { item -> Signal<(Stories.StoredItem?, [PeerId: Peer], [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?]), NoError> in
                return context.account.postbox.transaction { transaction -> (Stories.StoredItem?, [PeerId: Peer], [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?]) in
                    guard let item else {
                        return (nil, [:], [:], [:])
                    }
""",
        """            item |> mapToSignal { item -> Signal<(Stories.StoredItem?, [PeerId: Peer], [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Int32), NoError> in
                return context.account.postbox.transaction { transaction -> (Stories.StoredItem?, [PeerId: Peer], [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Int32) in
                    let maxReadId = transaction.getPeerStoryState(peerId: storyId.peerId)?.entry.get(Stories.PeerState.self)?.maxReadId ?? 0
                    guard let item else {
                        return (nil, [:], [:], [:], maxReadId)
                    }
""",
        "Load read state for a single deep-linked story",
    )
    replace_once(
        story_chat_content,
        """                    return (item, peers, allEntityFiles, stories)
                }
            },
""",
        """                    return (item, peers, allEntityFiles, stories, maxReadId)
                }
            },
""",
        "Return read state for a single deep-linked story",
    )
    replace_once(
        story_chat_content,
        """            let (item, peers, allEntityFiles, forwardInfoStories) = itemAndPeers
""",
        """            let (item, peers, allEntityFiles, forwardInfoStories, maxReadId) = itemAndPeers
""",
        "Unpack single-story read state",
    )
    replace_once(
        story_chat_content,
        """                    entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                    itemPeer: nil
                )
                let stateValue = StoryContentContextState(
""",
        """                    entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                    itemPeer: nil,
                    isSeen: mappedItem.id <= maxReadId
                )
                let stateValue = StoryContentContextState(
""",
        "Do not reconfirm an already-viewed deep-linked story",
    )
    replace_once(
        story_chat_content,
        """            |> mapToSignal { _, views, data, preferHighQualityStories -> Signal<(CombinedView, [PeerId: Peer], (EngineGlobalNotificationSettings, Bool), [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Bool), NoError> in
""",
        """            |> mapToSignal { _, views, data, preferHighQualityStories -> Signal<(CombinedView, [PeerId: Peer], (EngineGlobalNotificationSettings, Bool), [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Bool, Int32), NoError> in
""",
        "Expose repost-chain read state in the signal type",
    )
    replace_once(
        story_chat_content,
        """                return context.account.postbox.transaction { transaction -> (CombinedView, [PeerId: Peer], (EngineGlobalNotificationSettings, Bool), [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Bool) in
""",
        """                return context.account.postbox.transaction { transaction -> (CombinedView, [PeerId: Peer], (EngineGlobalNotificationSettings, Bool), [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Bool, Int32) in
""",
        "Load read state for repost-chain stories",
    )
    replace_once(
        story_chat_content,
        """                    return (views, peers, data, allEntityFiles, forwardInfoStories, preferHighQualityStories)
                }
            }
            |> deliverOnMainQueue).startStrict(next: { [weak self] views, peers, data, allEntityFiles, forwardInfoStories, preferHighQualityStories in
""",
        """                    let maxReadId = transaction.getPeerStoryState(peerId: peerId)?.entry.get(Stories.PeerState.self)?.maxReadId ?? 0
                    return (views, peers, data, allEntityFiles, forwardInfoStories, preferHighQualityStories, maxReadId)
                }
            }
            |> deliverOnMainQueue).startStrict(next: { [weak self] views, peers, data, allEntityFiles, forwardInfoStories, preferHighQualityStories, maxReadId in
""",
        "Return repost-chain story read state",
    )
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: item, allEntityFiles: allEntityFiles),
                                itemPeer: nil
                            )
                        }
""",
        """                                entityFiles: extractItemEntityFiles(item: item, allEntityFiles: allEntityFiles),
                                itemPeer: nil,
                                isSeen: item.id <= maxReadId
                            )
                        }
""",
        "Carry read state for repost-chain items",
    )
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                                itemPeer: nil
                            ),
                            totalCount: totalCount,
""",
        """                                entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                                itemPeer: nil,
                                isSeen: mappedItem.id <= maxReadId
                            ),
                            totalCount: totalCount,
""",
        "Carry read state for the focused repost-chain story",
    )

    settings_items = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoSettingsItems.swift"
    replace_once(
        settings_items,
        "import TelegramPresentationData\n",
        "import TelegramPresentationData\nimport NagramiXCore\n",
        "NagramiX settings localization import",
    )
    replace_once(
        settings_items,
        "    case myProfile\n    case proxy\n",
        "    case nagramix\n    case myProfile\n    case proxy\n",
        "NagramiX settings group order",
    )
    replace_once(
        settings_items,
        """        items[.myProfile]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.Settings_MyProfile, icon: PresentationResourcesSettings.myProfile, action: {
            interaction.openSettings(.profile)
        }))
""" + "        \n" + """        if !settings.proxySettings.servers.isEmpty {
""",
        """        items[.nagramix]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.nagramiXSettingsTitle, icon: PresentationResourcesSettings.appearance, action: {
            interaction.openSettings(.nagramix)
        }))

        items[.myProfile]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.Settings_MyProfile, icon: PresentationResourcesSettings.myProfile, action: {
            interaction.openSettings(.profile)
        }))
""" + "        \n" + """        if !settings.proxySettings.servers.isEmpty {
""",
        "NagramiX settings row",
    )
    replace_once(
        settings_items,
        """    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.Settings_Support, icon: PresentationResourcesSettings.support, action: {
        interaction.openSettings(.support)
    }))
    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 1, text: presentationData.strings.Settings_FAQ, icon: PresentationResourcesSettings.faq, action: {
        interaction.openSettings(.faq)
    }))
    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 2, text: presentationData.strings.Settings_Tips, icon: PresentationResourcesSettings.tips, action: {
        interaction.openSettings(.tips)
    }))
""",
        """    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.nagramiXFeatures, icon: PresentationResourcesSettings.nagramiXFeatures, action: {
        interaction.openSettings(.nagramiXFeatures)
    }))
    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 1, text: presentationData.strings.nagramiXUpdates, icon: PresentationResourcesSettings.nagramiXUpdates, action: {
        interaction.openSettings(.nagramiXUpdates)
    }))
    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 2, text: presentationData.strings.nagramiXHelp, icon: PresentationResourcesSettings.messages, action: {
        interaction.openSettings(.nagramiXHelp)
    }))
""",
        "Replace Telegram support rows with the NagramiX information block",
    )

    peer_info_screen = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoScreen.swift"
    replace_once(
        peer_info_screen,
        "    case profile\n    case premiumManagement\n",
        "    case profile\n    case nagramix\n    case premiumManagement\n",
        "NagramiX settings route",
    )
    replace_once(
        peer_info_screen,
        "    case support\n    case faq\n    case tips\n",
        "    case support\n    case faq\n    case tips\n    case nagramiXFeatures\n    case nagramiXUpdates\n    case nagramiXHelp\n",
        "NagramiX information routes",
    )

    settings_actions = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoScreenSettingsActions.swift"
    replace_once(
        settings_actions,
        """        case .stories:
            push(PeerInfoStoryGridScreen(context: self.context, peerId: self.context.account.peerId, scope: .saved))
""",
        """        case .nagramix:
            push(nagramiXSettingsController(context: self.context))
        case .stories:
            push(PeerInfoStoryGridScreen(context: self.context, peerId: self.context.account.peerId, scope: .saved))
""",
        "NagramiX settings navigation",
    )
    replace_once(
        settings_actions,
        """        case .watch:
            push(watchSettingsController(context: self.context))
        case .support:
""",
        """        case .watch:
            push(watchSettingsController(context: self.context))
        case .nagramiXFeatures:
            self.context.sharedContext.openExternalUrl(context: self.context, urlContext: .generic, url: "https://NagramiX.ru", forceExternal: true, presentationData: self.presentationData, navigationController: self.controller?.navigationController as? NavigationController, dismissInput: {})
        case .nagramiXUpdates:
            self.context.sharedContext.openExternalUrl(context: self.context, urlContext: .generic, url: "https://t.me/NagramiX", forceExternal: false, presentationData: self.presentationData, navigationController: self.controller?.navigationController as? NavigationController, dismissInput: {})
        case .nagramiXHelp:
            self.context.sharedContext.openExternalUrl(context: self.context, urlContext: .generic, url: "https://t.me/NagramiX_bot", forceExternal: false, presentationData: self.presentationData, navigationController: self.controller?.navigationController as? NavigationController, dismissInput: {})
        case .support:
""",
        "NagramiX information navigation",
    )

    root_controller = source / "submodules" / "TelegramUI" / "Sources" / "TelegramRootController.swift"
    replace_once(
        root_controller,
        "import SettingsUI\n",
        "import SettingsUI\nimport NagramiXCore\n",
        "Telegram root NagramiXCore import",
    )
    replace_once(
        root_controller,
        """    private var applicationInFocusDisposable: Disposable?
    private var storyUploadEventsDisposable: Disposable?
""",
        """    private var applicationInFocusDisposable: Disposable?
    private var storyUploadEventsDisposable: Disposable?
    private var nagramiXTabSettingsObserver: NSObjectProtocol?
    private var nagramiXTabInterfaceSoftRestartObserver: NSObjectProtocol?
    private var nagramiXOriginalTabTitles: [ObjectIdentifier: String] = [:]
""",
        "Telegram root tab settings state",
    )
    replace_once(
        root_controller,
        """        super.init(mode: .automaticMasterDetail, theme: NavigationControllerTheme(presentationTheme: self.presentationData.theme))
""" + "        \n" + """        self.presentationDataDisposable = (context.sharedContext.presentationData
""",
        """        super.init(mode: .automaticMasterDetail, theme: NavigationControllerTheme(presentationTheme: self.presentationData.theme))

        self.nagramiXTabSettingsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
            self?.applyNagramiXTabSettings()
        })
        self.nagramiXTabInterfaceSoftRestartObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.softRestartRequestedNotification, object: nil, queue: .main, using: { [weak self] _ in
            self?.softRestartNagramiXTabInterface()
        })
""" + "        \n" + """        self.presentationDataDisposable = (context.sharedContext.presentationData
""",
        "Telegram root tab settings observer",
    )
    replace_once(
        root_controller,
        """        self.storyUploadEventsDisposable?.dispose()
    }
""",
        """        self.storyUploadEventsDisposable?.dispose()
        if let nagramiXTabSettingsObserver = self.nagramiXTabSettingsObserver {
            NotificationCenter.default.removeObserver(nagramiXTabSettingsObserver)
        }
        if let nagramiXTabInterfaceSoftRestartObserver = self.nagramiXTabInterfaceSoftRestartObserver {
            NotificationCenter.default.removeObserver(nagramiXTabInterfaceSoftRestartObserver)
        }
    }
""",
        "Telegram root observer cleanup",
    )
    replace_once(
        root_controller,
        """    public func addRootControllers(showCallsTab: Bool) {
""",
        """    private func nagramiXConfiguredControllers() -> [ViewController] {
        let settings = NagramiXTabSettings.current
        var controllers: [ViewController] = []
        if !settings.hideContacts, let contactsController = self.contactsController {
            controllers.append(contactsController)
        }
        if !settings.hideCalls, let callListController = self.callListController {
            controllers.append(callListController)
        }
        if let chatListController = self.chatListController {
            controllers.append(chatListController)
        }
        if let accountSettingsController = self.accountSettingsController {
            controllers.append(accountSettingsController)
        }
        return controllers
    }

    private func applyNagramiXTabSettings() {
        guard let rootTabController = self.rootTabController as? TabBarControllerImpl else {
            return
        }
        rootTabController.setControllers(self.nagramiXConfiguredControllers(), selectedIndex: nil)
        rootTabController.updateLayout(transition: .immediate)
    }

    private func softRestartNagramiXTabInterface() {
        guard let previousTabController = self.rootTabController as? TabBarControllerImpl else {
            return
        }

        var navigationControllers = self.viewControllers
        guard let rootIndex = navigationControllers.firstIndex(where: { $0 === previousTabController }) else {
            return
        }

        let selectedController: ViewController?
        if previousTabController.selectedIndex >= 0 && previousTabController.selectedIndex < previousTabController.controllers.count {
            selectedController = previousTabController.controllers[previousTabController.selectedIndex]
        } else {
            selectedController = nil
        }

        let tabBarController = TabBarControllerImpl(theme: self.presentationData.theme, strings: self.presentationData.strings)
        tabBarController.navigationPresentation = .master
        self.rootTabController = tabBarController

        let controllers = self.nagramiXConfiguredControllers()
        let selectedIndex = selectedController.flatMap { selectedController in
            controllers.firstIndex(where: { $0 === selectedController })
        } ?? controllers.firstIndex(where: { $0 === self.accountSettingsController }) ?? 0
        previousTabController.setControllers([], selectedIndex: nil)
        tabBarController.setControllers(controllers, selectedIndex: selectedIndex)

        navigationControllers[rootIndex] = tabBarController
        self.setViewControllers(navigationControllers, animated: false)
        tabBarController.updateLayout(transition: .immediate)
    }

    public func addRootControllers(showCallsTab: Bool) {
""",
        "Telegram root tab settings helpers",
    )
    replace_once(
        root_controller,
        """        var controllers: [ViewController] = []
""" + "        \n" + """        let contactsController = ContactsController(context: self.context)
""",
        """        let contactsController = ContactsController(context: self.context)
""",
        "Telegram root temporary controllers array",
    )
    replace_once(root_controller, "        controllers.append(contactsController)\n        \n", "", "Telegram root contacts default append")
    replace_once(
        root_controller,
        """        if showCallsTab {
            controllers.append(callListController)
        }
        controllers.append(chatListController)
""" + "        \n",
        "",
        "Telegram root calls and chats default append",
    )
    replace_once(
        root_controller,
        """        accountSettingsController.parentController = self
        controllers.append(accountSettingsController)
""" + "                \n" + """        tabBarController.setControllers(controllers, selectedIndex: restoreSettignsController != nil ? (controllers.count - 1) : (controllers.count - 2))
""" + "        \n" + """        self.contactsController = contactsController
        self.callListController = callListController
        self.chatListController = chatListController
        self.accountSettingsController = accountSettingsController
        self.rootTabController = tabBarController
""",
        """        accountSettingsController.parentController = self

        self.contactsController = contactsController
        self.callListController = callListController
        self.chatListController = chatListController
        self.accountSettingsController = accountSettingsController
        self.rootTabController = tabBarController

        let controllers = self.nagramiXConfiguredControllers()
        let selectedController: ViewController = restoreSettignsController != nil ? accountSettingsController : chatListController
        let selectedIndex = controllers.firstIndex(where: { $0 === selectedController }) ?? 0
        tabBarController.setControllers(controllers, selectedIndex: selectedIndex)
""",
        "Telegram root initial NagramiX tabs",
    )
    replace_once(
        root_controller,
        """    public func updateRootControllers(showCallsTab: Bool) {
        guard let rootTabController = self.rootTabController as? TabBarControllerImpl else {
            return
        }
        var controllers: [ViewController] = []
        controllers.append(self.contactsController!)
        if showCallsTab {
            controllers.append(self.callListController!)
        }
        controllers.append(self.chatListController!)
        controllers.append(self.accountSettingsController!)
""" + "        \n" + """        rootTabController.setControllers(controllers, selectedIndex: nil)
    }
""",
        """    public func updateRootControllers(showCallsTab: Bool) {
        self.applyNagramiXTabSettings()
    }
""",
        "Telegram root updates",
    )

    tab_bar_node = source / "submodules" / "TabBarUI" / "Sources" / "TabBarContollerNode.swift"
    replace_once(
        tab_bar_node,
        "import GlassControls\n",
        "import GlassControls\nimport NagramiXCore\n",
        "Tab bar NagramiXCore import",
    )
    replace_once(
        tab_bar_node,
        """                search: self.currentController?.tabBarSearchState.flatMap { tabBarSearchState in
                    return TabBarComponent.Search(
""",
        """                search: self.currentController?.tabBarSearchState.flatMap { tabBarSearchState in
                    guard NagramiXTabSettings.current.showSearchButton else {
                        return nil
                    }
                    return TabBarComponent.Search(
""",
        "Tab bar search visibility",
    )

    video_message_camera = source / "submodules" / "TelegramUI" / "Components" / "VideoMessageCameraScreen" / "Sources" / "VideoMessageCameraScreen.swift"
    replace_once(
        video_message_camera,
        "import AccountContext\n",
        "import AccountContext\nimport NagramiXCore\n",
        "Video message camera NagramiXCore import",
    )
    replace_once(
        video_message_camera,
        '            let isFrontPosition = "".isEmpty\n',
        """            let prefersRearCamera = NagramiXTabSettings.current.useRearCameraForVideoMessages
            let isFrontPosition = !prefersRearCamera
            Logger.shared.log("NagramiX", "Round video initial camera preference: rear=\\(prefersRearCamera), position=\\(isFrontPosition ? "front" : "back")")
""",
        "Video messages start on the configured camera",
    )

    camera_output = source / "submodules" / "Camera" / "Sources" / "CameraOutput.swift"
    replace_once(
        camera_output,
        """    private var currentPosition: Camera.Position = .front
    private var lastSwitchTimestamp: Double = 0.0
""",
        """    private var currentPosition: Camera.Position = .front
    private var lastSwitchTimestamp: Double = 0.0

    func setInitialPosition(_ position: Camera.Position) {
        self.currentPosition = position
        self.lastSwitchTimestamp = 0.0
    }
""",
        "Allow the native round-video recorder to start from its configured position",
    )

    camera_context = source / "submodules" / "Camera" / "Sources" / "Camera.swift"
    replace_once(
        camera_context,
        """            self.mainDeviceContext?.output.processCodes = { [weak self] codes in
                self?.detectedCodesPipe.putNext(codes)
            }
        }
        self.session.session.startRunning()
""",
        """            self.mainDeviceContext?.output.processCodes = { [weak self] codes in
                self?.detectedCodesPipe.putNext(codes)
            }
        }

        if self.initialConfiguration.isRoundVideo {
            if self.positionValue == .back && self.mainDeviceContext?.device.videoDevice == nil {
                Logger.shared.log("NagramiX", "Round video rear camera unavailable; falling back to front")
                if enabled {
                    if self.additionalDeviceContext?.device.videoDevice != nil {
                        self.positionValue = .front
                        self._positionPromise.set(.front)
                    }
                } else if let mainDeviceContext = self.mainDeviceContext {
                    self.configure {
                        mainDeviceContext.invalidate(switchAudio: false)
                        mainDeviceContext.configure(position: .front, previewView: self.simplePreviewView, audio: self.initialConfiguration.audio, photo: self.initialConfiguration.photo, metadata: self.initialConfiguration.metadata, preferWide: true, preferLowerFramerate: true, switchAudio: false)
                    }
                    if mainDeviceContext.device.videoDevice != nil {
                        self.positionValue = .front
                        self._positionPromise.set(.front)
                    }
                }
            }

            self.mainDeviceContext?.output.setInitialPosition(self.positionValue)
            let activeDeviceContext = self.positionValue == .front && enabled ? self.additionalDeviceContext : self.mainDeviceContext
            if let device = activeDeviceContext?.device.videoDevice {
                Logger.shared.log("NagramiX", "Round video selected camera: id=\\(device.uniqueID), type=\\(device.deviceType.rawValue), position=\\(self.positionValue == .front ? "front" : "back")")
            } else {
                Logger.shared.log("NagramiX", "Round video camera selection failed for position=\\(self.positionValue == .front ? "front" : "back")")
            }
        }
        self.session.session.startRunning()
""",
        "Initialize round-video output from the native camera position",
    )

    chat_list_entries = source / "submodules" / "ChatListUI" / "Sources" / "Node" / "ChatListNodeEntries.swift"
    replace_once(
        chat_list_entries,
        "import AccountContext\n",
        "import AccountContext\nimport NagramiXCore\n",
        "Chat list entries NagramiXCore import",
    )
    replace_once(
        chat_list_entries,
        """                for item in filteredAdditionalItemEntries.reversed() {
                    guard case let .chatList(index) = item.item.index else {
""",
        """                for item in filteredAdditionalItemEntries.reversed() {
                    if case .proxy = item.promoInfo.content, NagramiXTabSettings.current.hideProxySponsorChannel {
                        continue
                    }
                    guard case let .chatList(index) = item.item.index else {
""",
        "Hide only the proxy sponsor entry when requested",
    )

    chat_list_node = source / "submodules" / "ChatListUI" / "Sources" / "Node" / "ChatListNode.swift"
    replace_once(
        chat_list_node,
        "    private let statePromise: ValuePromise<ChatListNodeState>\n",
        "    private let statePromise: ValuePromise<ChatListNodeState>\n    private let nagramiXSettingsRevision = ValuePromise<Bool>(false, ignoreRepeated: true)\n    private var nagramiXSettingsRevisionValue = false\n",
        "Chat list settings revision signal",
    )
    replace_once(
        chat_list_node,
        """            contacts,
            chatListFilters,
            accountIsPremium
        )
        |> mapToQueue { (hideArchivedFolderByDefault, displayArchiveIntro, storageInfo, savedMessagesPeer, updateAndFilter, state, contacts, chatListFilters, accountIsPremium) -> Signal<ChatListNodeListViewTransition, NoError> in
""",
        """            contacts,
            chatListFilters,
            accountIsPremium,
            self.nagramiXSettingsRevision.get()
        )
        |> mapToQueue { (hideArchivedFolderByDefault, displayArchiveIntro, storageInfo, savedMessagesPeer, updateAndFilter, state, contacts, chatListFilters, accountIsPremium, _) -> Signal<ChatListNodeListViewTransition, NoError> in
""",
        "Rebuild chat list entries after NagramiX settings changes",
    )
    replace_once(
        chat_list_node,
        """    public func updateState(_ f: (ChatListNodeState) -> ChatListNodeState) {
""",
        """    public func nagramiXRefreshSettings() {
        self.nagramiXSettingsRevisionValue = !self.nagramiXSettingsRevisionValue
        self.nagramiXSettingsRevision.set(self.nagramiXSettingsRevisionValue)
    }

    public func updateState(_ f: (ChatListNodeState) -> ChatListNodeState) {
""",
        "Expose an immediate NagramiX chat-list refresh",
    )

    chat_list_controller = source / "submodules" / "ChatListUI" / "Sources" / "ChatListController.swift"
    replace_once(
        chat_list_controller,
        "import TelegramPresentationData\n",
        "import TelegramPresentationData\nimport NagramiXCore\n",
        "Chat list NagramiXCore import",
    )
    replace_once(
        chat_list_controller,
        '''                    } else {
                        languageCode = "en"
                    }
                    return languageCode
''',
        '''                    } else {
                        languageCode = "ru"
                    }
                    return languageCode
''',
        "Keep the clean-install localization state consistent with Russian presentation strings",
    )
    replace_once(
        chat_list_controller,
        '''            |> mapToSignal({ value -> Signal<(String, SuggestedLocalizationInfo)?, NoError> in
                guard let suggestedLocalization = value.1, !suggestedLocalization.isSeen && suggestedLocalization.languageCode != "en" && suggestedLocalization.languageCode != value.0 else {
                    return .single(nil)
                }
                return context.engine.localization.suggestedLocalizationInfo(languageCode: suggestedLocalization.languageCode, extractKeys: LanguageSuggestionControllerStrings.keys)
                |> map({ suggestedLocalization -> (String, SuggestedLocalizationInfo)? in
                    return (value.0, suggestedLocalization)
                })
            })
''',
        '''            |> mapToSignal({ value -> Signal<(String, SuggestedLocalizationInfo)?, NoError> in
                let currentLanguageCode = value.0.lowercased()
                let preferredLanguageCode = Locale.preferredLanguages.first
                    .map { $0.replacingOccurrences(of: "_", with: "-").split(separator: "-").first.map(String.init) ?? $0 }
                    .map { $0.lowercased() }
                let systemSuggestionKey = preferredLanguageCode.flatMap { "nagramix.localization.systemSuggestion.\\($0)" }

                let requestedLanguageCode: String?
                if let preferredLanguageCode,
                   preferredLanguageCode != currentLanguageCode,
                   !UserDefaults.standard.bool(forKey: systemSuggestionKey ?? "") {
                    requestedLanguageCode = preferredLanguageCode
                } else if let suggestedLocalization = value.1,
                          !suggestedLocalization.isSeen,
                          suggestedLocalization.languageCode != currentLanguageCode {
                    requestedLanguageCode = suggestedLocalization.languageCode
                } else {
                    requestedLanguageCode = nil
                }
                guard let requestedLanguageCode else {
                    return .single(nil)
                }
                return context.engine.localization.suggestedLocalizationInfo(languageCode: requestedLanguageCode, extractKeys: LanguageSuggestionControllerStrings.keys)
                |> map({ suggestedLocalization -> (String, SuggestedLocalizationInfo)? in
                    guard suggestedLocalization.availableLocalizations.contains(where: { $0.languageCode == requestedLanguageCode }) else {
                        if let systemSuggestionKey {
                            UserDefaults.standard.set(true, forKey: systemSuggestionKey)
                        }
                        return nil
                    }
                    if let systemSuggestionKey, requestedLanguageCode == preferredLanguageCode {
                        UserDefaults.standard.set(true, forKey: systemSuggestionKey)
                    }
                    return (value.0, suggestedLocalization)
                })
            })
''',
        "Suggest the supported iPhone language once while keeping Russian as the initial language",
    )
    replace_once(
        chat_list_controller,
        """        let hasProxy = context.sharedContext.accountManager.sharedData(keys: [SharedDataKeys.proxySettings])
        |> map { sharedData -> (Bool, Bool) in
            if let settings = sharedData.entries[SharedDataKeys.proxySettings]?.get(ProxySettings.self) {
                return (!settings.servers.isEmpty, settings.enabled)
            } else {
                return (false, false)
            }
        }
        |> distinctUntilChanged(isEqual: { lhs, rhs in
            return lhs == rhs
        })
""",
        """        let showProxyButton = Signal<Bool, NoError> { subscriber in
            subscriber.putNext(NagramiXTabSettings.current.showProxyButton)
            let observer = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: nil, using: { _ in
                subscriber.putNext(NagramiXTabSettings.current.showProxyButton)
            })
            return ActionDisposable {
                NotificationCenter.default.removeObserver(observer)
            }
        }
        |> distinctUntilChanged
        let hasProxy = combineLatest(context.sharedContext.accountManager.sharedData(keys: [SharedDataKeys.proxySettings]), showProxyButton)
        |> map { sharedData, showProxyButton -> (Bool, Bool) in
            let settings = sharedData.entries[SharedDataKeys.proxySettings]?.get(ProxySettings.self) ?? .defaultSettings
            return (showProxyButton, settings.enabled)
        }
        |> distinctUntilChanged(isEqual: { lhs, rhs in
            return lhs == rhs
        })
""",
        "Keep the Chat proxy button visible independently from saved proxies",
    )
    replace_once(
        chat_list_controller,
        """                        self.leftButton = AnyComponentWithIdentity(id: "edit", component: AnyComponent(NavigationButtonComponent(
                            content: .text(title: presentationData.strings.Common_Edit, isBold: false),
""",
        """                        self.leftButton = AnyComponentWithIdentity(id: "edit", component: AnyComponent(NavigationButtonComponent(
                            content: .text(title: presentationData.strings.nagramiXEdit, isBold: false),
""",
        "Use the full localized Edit title on the root Chat screen",
    )
    replace_once(
        chat_list_controller,
        "    private var displayedStoriesTooltip: Bool = false\n",
        "    private var displayedStoriesTooltip: Bool = false\n    private var nagramiXSettingsObserver: NSObjectProtocol?\n    private var nagramiXLastOrderedStorySubscriptions: EngineStorySubscriptions?\n",
        "Chat list NagramiX settings observer state",
    )
    replace_once(
        chat_list_controller,
        "    public var hasStorySubscriptions: Bool {\n        if let rawStorySubscriptions = self.rawStorySubscriptions, !rawStorySubscriptions.items.isEmpty {\n",
        "    public var hasStorySubscriptions: Bool {\n        if NagramiXTabSettings.current.hideStories {\n            return false\n        }\n        if let rawStorySubscriptions = self.rawStorySubscriptions, !rawStorySubscriptions.items.isEmpty {\n",
        "Hidden stories do not report a visible subscription feed",
    )
    replace_once(
        chat_list_controller,
        "        super.init(context: context, navigationBarPresentationData: nil)\n        \n        self.accessoryPanelContainer = ASDisplayNode()\n",
        """        super.init(context: context, navigationBarPresentationData: nil)

        self.nagramiXSettingsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
            guard let self else {
                return
            }
            self.orderedStorySubscriptions = NagramiXTabSettings.current.hideStories ? nil : (self.nagramiXLastOrderedStorySubscriptions ?? self.rawStorySubscriptions)
            self.chatListDisplayNode.effectiveContainerNode.currentItemNode.nagramiXRefreshSettings()
            let transition: ContainedViewLayoutTransition = self.didAppear ? .animated(duration: 0.4, curve: .spring) : .immediate
            self.chatListDisplayNode.temporaryContentOffsetChangeTransition = transition
            self.requestLayout(transition: transition)
            self.chatListDisplayNode.temporaryContentOffsetChangeTransition = nil
            if NagramiXTabSettings.current.hideStories {
                self.chatListDisplayNode.scrollToTopIfStoriesAreExpanded()
            }
        })

        self.accessoryPanelContainer = ASDisplayNode()
""",
        "Observe immediate story visibility changes",
    )
    replace_once(
        chat_list_controller,
        "        self.globalControlPanelsContextStateDisposable?.dispose()\n    }\n",
        """        self.globalControlPanelsContextStateDisposable?.dispose()
        if let nagramiXSettingsObserver = self.nagramiXSettingsObserver {
            NotificationCenter.default.removeObserver(nagramiXSettingsObserver)
        }
    }
""",
        "Chat list observer cleanup",
    )
    replace_once(
        chat_list_controller,
        """                    self.orderedStorySubscriptions = EngineStorySubscriptions(
                        accountItem: rawStorySubscriptions.accountItem,
                        items: items,
                        hasMoreToken: rawStorySubscriptions.hasMoreToken
                    )
""",
        """                    let orderedStorySubscriptions = EngineStorySubscriptions(
                        accountItem: rawStorySubscriptions.accountItem,
                        items: items,
                        hasMoreToken: rawStorySubscriptions.hasMoreToken
                    )
                    self.nagramiXLastOrderedStorySubscriptions = orderedStorySubscriptions
                    self.orderedStorySubscriptions = NagramiXTabSettings.current.hideStories ? nil : orderedStorySubscriptions
""",
        "Hide the chat-list story feed without removing story data",
    )
    replace_once(
        chat_list_controller,
        "    func storyCameraPanGestureChanged(transitionFraction: CGFloat) {\n        guard let rootController = self.context.sharedContext.mainWindow?.viewController as? TelegramRootControllerInterface else {\n",
        "    func storyCameraPanGestureChanged(transitionFraction: CGFloat) {\n        if NagramiXTabSettings.current.disableStoryCameraSwipe && self.storyCameraTransitionInCoordinator == nil {\n            return\n        }\n        guard let rootController = self.context.sharedContext.mainWindow?.viewController as? TelegramRootControllerInterface else {\n",
        "Disable only the story-camera swipe gesture",
    )
    replace_once(
        chat_list_controller,
        """            componentView.storyComposeAction = { [weak self] offset in
                guard let self else {
                    return
                }
                self.openStoryCamera(fromList: true, gesturePullOffset: offset)
            }
""",
        """            componentView.storyComposeAction = { [weak self] offset in
                guard let self else {
                    return
                }
                guard !NagramiXTabSettings.current.disableStoryCameraSwipe else {
                    return
                }
                self.openStoryCamera(fromList: true, gesturePullOffset: offset)
            }
""",
        "Disable the story-carousel pull gesture without disabling explicit camera buttons",
    )

    story_container_screen = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryContainerScreen.swift"
    replace_once(
        story_container_screen,
        "import TelegramCore\n",
        "import TelegramCore\nimport TelegramPresentationData\nimport PhotoResources\nimport NagramiXCore\n",
        "Story viewer NagramiX imports",
    )
    replace_once(
        story_container_screen,
        "public class StoryContainerScreen: ViewControllerComponentContainer, KeyShortcutResponder {\n",
        """private final class NagramiXStoryConfirmationController: ViewController {
    private let previewSignal: Signal<(TransformImageArguments) -> DrawingContext?, NoError>?
    private let confirmed: () -> Void
    private let cancelled: () -> Void
    private var previewDisposable: Disposable?
    private var finished = false
    private let imageView = UIImageView()
    private let dimView = UIView()
    private let titleLabel = UILabel()
    private let bodyLabel = UILabel()
    private let closeButton = UIButton(type: .system)
    private let actionButton = UIButton(type: .system)

    init(previewSignal: Signal<(TransformImageArguments) -> DrawingContext?, NoError>?, title: String, body: String, action: String, confirmed: @escaping () -> Void, cancelled: @escaping () -> Void) {
        self.previewSignal = previewSignal
        self.confirmed = confirmed
        self.cancelled = cancelled
        super.init(navigationBarPresentationData: nil)
        self.navigationPresentation = .flatModal
        self.statusBar.statusBarStyle = .White
        self.titleLabel.text = title
        self.bodyLabel.text = body
        self.actionButton.setTitle(action, for: .normal)
    }

    required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit { self.previewDisposable?.dispose() }

    override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.displayNode.backgroundColor = .black
        self.displayNodeDidLoad()
        self.imageView.contentMode = .scaleAspectFill
        self.imageView.clipsToBounds = true
        self.dimView.backgroundColor = UIColor(white: 0.0, alpha: 0.48)
        self.titleLabel.textColor = .white
        self.titleLabel.font = UIFont.systemFont(ofSize: 28.0, weight: .bold)
        self.titleLabel.textAlignment = .center
        self.bodyLabel.textColor = UIColor(white: 1.0, alpha: 0.84)
        self.bodyLabel.font = UIFont.systemFont(ofSize: 17.0)
        self.bodyLabel.textAlignment = .center
        self.bodyLabel.numberOfLines = 0
        self.closeButton.setTitle("×", for: .normal)
        self.closeButton.setTitleColor(.white, for: .normal)
        self.closeButton.titleLabel?.font = UIFont.systemFont(ofSize: 36.0)
        self.closeButton.addTarget(self, action: #selector(self.closePressed), for: .touchUpInside)
        self.actionButton.setTitleColor(.white, for: .normal)
        self.actionButton.titleLabel?.font = UIFont.systemFont(ofSize: 17.0, weight: .semibold)
        self.actionButton.backgroundColor = UIColor(rgb: 0x2f80ed)
        self.actionButton.layer.cornerRadius = 14.0
        self.actionButton.addTarget(self, action: #selector(self.confirmPressed), for: .touchUpInside)
        [self.imageView, self.dimView, self.titleLabel, self.bodyLabel, self.closeButton, self.actionButton].forEach { self.displayNode.view.addSubview($0) }
        if let previewSignal = self.previewSignal {
            self.previewDisposable = (previewSignal |> deliverOnMainQueue).start(next: { [weak self] process in
                let size = CGSize(width: 1080.0, height: 1920.0)
                self?.imageView.image = process(TransformImageArguments(corners: ImageCorners(), imageSize: size, boundingSize: size, intrinsicInsets: UIEdgeInsets()))?.generateImage()
            })
        }
    }

    override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        let bounds = CGRect(origin: .zero, size: layout.size)
        transition.updateFrame(view: self.imageView, frame: bounds)
        transition.updateFrame(view: self.dimView, frame: bounds)
        let inset: CGFloat = 28.0
        transition.updateFrame(view: self.closeButton, frame: CGRect(x: layout.size.width - 60.0, y: layout.safeInsets.top + 8.0, width: 44.0, height: 44.0))
        let titleSize = self.titleLabel.sizeThatFits(CGSize(width: layout.size.width - inset * 2.0, height: 80.0))
        let bodySize = self.bodyLabel.sizeThatFits(CGSize(width: layout.size.width - inset * 2.0, height: 180.0))
        let top = floor((layout.size.height - titleSize.height - bodySize.height - 12.0) * 0.46)
        transition.updateFrame(view: self.titleLabel, frame: CGRect(x: inset, y: top, width: layout.size.width - inset * 2.0, height: titleSize.height))
        transition.updateFrame(view: self.bodyLabel, frame: CGRect(x: inset, y: top + titleSize.height + 12.0, width: layout.size.width - inset * 2.0, height: bodySize.height))
        transition.updateFrame(view: self.actionButton, frame: CGRect(x: inset, y: layout.size.height - layout.safeInsets.bottom - 72.0, width: layout.size.width - inset * 2.0, height: 52.0))
    }

    @objc private func closePressed() {
        guard !self.finished else { return }
        self.finished = true
        self.dismiss(completion: self.cancelled)
    }
    @objc private func confirmPressed() {
        guard !self.finished else { return }
        self.finished = true
        self.dismiss(completion: self.confirmed)
    }
}

public class StoryContainerScreen: ViewControllerComponentContainer, KeyShortcutResponder {
""",
        "Add a full-screen pre-view story confirmation",
    )
    replace_once(
        story_container_screen,
        """    private let context: AccountContext
    private var didAnimateIn: Bool = false
    private var isDismissed: Bool = false
""",
        """    private let context: AccountContext
    private var didAnimateIn: Bool = false
    private var isDismissed: Bool = false
    private let nagramiXContent: StoryContentContext
    private var nagramiXPresentationDisposable: Disposable?
    private var nagramiXIsPresentingConfirmation = false
    private var nagramiXApprovedStoryId: EngineStoryId?
""",
        "Story presentation and settings state",
    )
    replace_once(
        story_container_screen,
        """    ) {
        self.context = context
""" + "        \n" + """        super.init(context: context, component: StoryContainerScreenComponent(
            context: context,
            content: content,
""",
        """    ) {
        self.context = context
        self.nagramiXContent = content

        super.init(context: context, component: StoryContainerScreenComponent(
            context: context,
            content: content,
""",
        "Keep the real story context available while presentation is pending",
    )
    replace_once(
        story_container_screen,
        """    deinit {
        self.context.sharedContext.hasPreloadBlockingContent.set(.single(false))
        self.focusedItemPromise.set(.single(nil))
    }
""",
        """    deinit {
        self.nagramiXPresentationDisposable?.dispose()
        self.context.sharedContext.hasPreloadBlockingContent.set(.single(false))
        self.focusedItemPromise.set(.single(nil))
    }
""",
        "Clean up deferred story presentation state",
    )
    replace_once(
        story_container_screen,
        """    override public func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
    }
""",
        """    override public func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
    }

    fileprivate func nagramiXUpdateStoryConfirmation(slice: StoryContentContextState.FocusedSlice?) {
        guard NagramiXTabSettings.current.confirmStoryViewing, let slice, slice.peer.id != self.context.account.peerId, !slice.item.isSeen, !self.nagramiXConfirmedStoryIds.contains(slice.item.id) else {
            self.nagramiXPendingConfirmationId = nil
            self.nagramiXConfirmationOverlay?.removeFromSuperview()
            return
        }
        guard self.nagramiXPendingConfirmationId != slice.item.id else { return }
        self.nagramiXPendingConfirmationId = slice.item.id
        self.nagramiXConfirmationOverlay?.removeFromSuperview()

        let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
        let overlay = UIView()
        overlay.translatesAutoresizingMaskIntoConstraints = false
        overlay.backgroundColor = UIColor(white: 0.0, alpha: 0.30)
        let blur = UIVisualEffectView(effect: UIBlurEffect(style: .dark))
        blur.translatesAutoresizingMaskIntoConstraints = false
        blur.isUserInteractionEnabled = false
        overlay.addSubview(blur)
        let closeButton = UIButton(type: .system)
        closeButton.translatesAutoresizingMaskIntoConstraints = false
        closeButton.setTitle("×", for: .normal)
        closeButton.titleLabel?.font = UIFont.systemFont(ofSize: 42.0, weight: .light)
        closeButton.tintColor = .white
        closeButton.addTarget(self, action: #selector(self.nagramiXCancelStoryConfirmation), for: .touchUpInside)
        overlay.addSubview(closeButton)
        let titleLabel = UILabel()
        titleLabel.translatesAutoresizingMaskIntoConstraints = false
        titleLabel.text = presentationData.strings.nagramiXStoryConfirmationTitle
        titleLabel.textColor = .white
        titleLabel.font = UIFont.systemFont(ofSize: 23.0, weight: .semibold)
        titleLabel.textAlignment = .center
        overlay.addSubview(titleLabel)
        let bodyLabel = UILabel()
        bodyLabel.translatesAutoresizingMaskIntoConstraints = false
        bodyLabel.text = presentationData.strings.nagramiXStoryConfirmationText(owner: slice.effectivePeer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder))
        bodyLabel.textColor = UIColor(white: 0.78, alpha: 1.0)
        bodyLabel.font = UIFont.systemFont(ofSize: 17.0)
        bodyLabel.textAlignment = .center
        bodyLabel.numberOfLines = 0
        overlay.addSubview(bodyLabel)
        let viewButton = UIButton(type: .system)
        viewButton.translatesAutoresizingMaskIntoConstraints = false
        viewButton.setTitle(presentationData.strings.nagramiXViewStoryAction, for: .normal)
        viewButton.setTitleColor(.white, for: .normal)
        viewButton.titleLabel?.font = UIFont.systemFont(ofSize: 19.0, weight: .semibold)
        viewButton.backgroundColor = presentationData.theme.list.itemAccentColor
        viewButton.layer.cornerRadius = 14.0
        viewButton.addTarget(self, action: #selector(self.nagramiXAcceptStoryConfirmation), for: .touchUpInside)
        overlay.addSubview(viewButton)
        self.view.addSubview(overlay)
        NSLayoutConstraint.activate([
            overlay.leadingAnchor.constraint(equalTo: self.view.leadingAnchor), overlay.trailingAnchor.constraint(equalTo: self.view.trailingAnchor), overlay.topAnchor.constraint(equalTo: self.view.topAnchor), overlay.bottomAnchor.constraint(equalTo: self.view.bottomAnchor),
            blur.leadingAnchor.constraint(equalTo: overlay.leadingAnchor), blur.trailingAnchor.constraint(equalTo: overlay.trailingAnchor), blur.topAnchor.constraint(equalTo: overlay.topAnchor), blur.bottomAnchor.constraint(equalTo: overlay.bottomAnchor),
            closeButton.trailingAnchor.constraint(equalTo: overlay.safeAreaLayoutGuide.trailingAnchor, constant: -18.0), closeButton.topAnchor.constraint(equalTo: overlay.safeAreaLayoutGuide.topAnchor, constant: 4.0), closeButton.widthAnchor.constraint(equalToConstant: 48.0), closeButton.heightAnchor.constraint(equalToConstant: 48.0),
            titleLabel.leadingAnchor.constraint(equalTo: overlay.leadingAnchor, constant: 32.0), titleLabel.trailingAnchor.constraint(equalTo: overlay.trailingAnchor, constant: -32.0), titleLabel.centerYAnchor.constraint(equalTo: overlay.centerYAnchor, constant: -52.0),
            bodyLabel.leadingAnchor.constraint(equalTo: overlay.leadingAnchor, constant: 44.0), bodyLabel.trailingAnchor.constraint(equalTo: overlay.trailingAnchor, constant: -44.0), bodyLabel.topAnchor.constraint(equalTo: titleLabel.bottomAnchor, constant: 10.0),
            viewButton.leadingAnchor.constraint(equalTo: overlay.leadingAnchor, constant: 44.0), viewButton.trailingAnchor.constraint(equalTo: overlay.trailingAnchor, constant: -44.0), viewButton.topAnchor.constraint(equalTo: bodyLabel.bottomAnchor, constant: 48.0), viewButton.heightAnchor.constraint(equalToConstant: 58.0)
        ])
        self.nagramiXConfirmationOverlay = overlay
        self.requestLayout(forceUpdate: true, transition: ContainedViewLayoutTransition.immediate)
    }

    @objc private func nagramiXCancelStoryConfirmation() {
        self.dismiss()
    }

    @objc private func nagramiXAcceptStoryConfirmation() {
        guard let id = self.nagramiXPendingConfirmationId else { return }
        self.nagramiXConfirmedStoryIds.insert(id)
        self.nagramiXPendingConfirmationId = nil
        self.nagramiXConfirmationOverlay?.removeFromSuperview()
        self.nagramiXContent.markAsSeen(id: id)
        self.requestLayout(forceUpdate: true, transition: ContainedViewLayoutTransition.immediate)
    }

    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {
        action()
        return
        guard NagramiXTabSettings.current.confirmStoryViewing else {
            action()
            return
        }

        let presentForState: (StoryContentContextState) -> Void = { [weak self, weak parentController] state in
            guard let self, let parentController else {
                return
            }
            guard let slice = state.slice else {
                self.nagramiXTransitionSourceView?.isHidden = false
                return
            }
            if slice.effectivePeer.id == self.context.account.peerId {
                action()
                return
            }

            let parentId = ObjectIdentifier(parentController)
            if StoryContainerScreen.nagramiXConfirmationParentIds.contains(parentId) {
                self.nagramiXTransitionSourceView?.isHidden = false
                return
            }
            StoryContainerScreen.nagramiXConfirmationParentIds.insert(parentId)

            let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
            let actionSheet = ActionSheetController(presentationData: presentationData)
            var didAccept = false
            actionSheet.dismissed = { [weak self] _ in
                StoryContainerScreen.nagramiXConfirmationParentIds.remove(parentId)
                if !didAccept {
                    self?.nagramiXTransitionSourceView?.isHidden = false
                }
            }
            actionSheet.setItemGroups([
                ActionSheetItemGroup(items: [
                    ActionSheetTextItem(title: presentationData.strings.nagramiXStoryConfirmationTitle + "\\n" + presentationData.strings.nagramiXStoryConfirmationText),
                    ActionSheetButtonItem(title: presentationData.strings.nagramiXViewStoryAction, color: .accent, font: .bold, action: { [weak actionSheet] in
                        didAccept = true
                        StoryContainerScreen.nagramiXConfirmationParentIds.remove(parentId)
                        actionSheet?.dismissAnimated()
                        action()
                    }),
                ]),
                ActionSheetItemGroup(items: [
                    ActionSheetButtonItem(title: presentationData.strings.Common_Cancel, color: .accent, font: .bold, action: { [weak actionSheet] in
                        actionSheet?.dismissAnimated()
                    }),
                ]),
            ])
            parentController.present(actionSheet, in: .window(.root))
        }

        if let state = self.nagramiXContent.stateValue {
            presentForState(state)
        } else {
            self.nagramiXPresentationDisposable = (self.nagramiXContent.state
            |> take(1)
            |> deliverOnMainQueue).start(next: { state in
                presentForState(state)
            })
        }
    }

    public func nagramiXPush(from parentController: ViewController, completion: @escaping () -> Void = {}) {
        self.nagramiXPresent(from: parentController, action: { [weak self, weak parentController] in
            guard let self, let parentController else {
                return
            }
            parentController.push(self)
            completion()
        })
    }

    public func nagramiXPush(from navigationController: NavigationController, completion: @escaping () -> Void = {}) {
        guard let parentController = navigationController.topViewController as? ViewController else {
            navigationController.pushViewController(self)
            completion()
            return
        }
        self.nagramiXPresent(from: parentController, action: { [weak self, weak navigationController] in
            guard let self, let navigationController else {
                return
            }
            navigationController.pushViewController(self)
            completion()
        })
    }
""",
        "Confirm an external story before it is pushed onto the navigation stack",
    )
    replace_between(
        story_container_screen,
        "    fileprivate func nagramiXUpdateStoryConfirmation(slice: StoryContentContextState.FocusedSlice?) {",
        "    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {",
        "",
        "Remove the unsafe post-open story confirmation overlay",
    )
    replace_between(
        story_container_screen,
        "    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {",
        "    public func nagramiXPush(from parentController: ViewController, completion: @escaping () -> Void = {}) {",
        """    fileprivate func nagramiXConfirmNavigation(peer: EnginePeer, item: StoryContentItem, action: @escaping () -> Void) {
        guard NagramiXTabSettings.current.confirmStoryViewing, peer.id != self.context.account.peerId else {
            action()
            return
        }
        guard !self.nagramiXIsPresentingConfirmation else { return }
        self.nagramiXIsPresentingConfirmation = true

        let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
        let effectivePeer = item.itemPeer ?? peer
        let owner = effectivePeer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder)
        var previewSignal: Signal<(TransformImageArguments) -> DrawingContext?, NoError>?
        if let peerReference = PeerReference(effectivePeer) {
            switch item.storyItem.media {
            case let .image(image):
                previewSignal = chatMessagePhoto(postbox: self.context.account.postbox, userLocation: .peer(peerReference.id), userContentType: .story, photoReference: .story(peer: peerReference, id: item.storyItem.id, media: image), synchronousLoad: false, highQuality: false)
            case let .file(file):
                previewSignal = mediaGridMessageVideo(postbox: self.context.account.postbox, userLocation: .peer(peerReference.id), userContentType: .story, videoReference: .story(peer: peerReference, id: item.storyItem.id, media: file), onlyFullSize: false, useLargeThumbnail: true, synchronousLoad: false, autoFetchFullSizeThumbnail: false, overlayColor: nil, nilForEmptyResult: false, useMiniThumbnailIfAvailable: true, blurred: false)
            default:
                break
            }
        }
        let confirmationController = NagramiXStoryConfirmationController(
            previewSignal: previewSignal,
            title: presentationData.strings.nagramiXStoryConfirmationTitle,
            body: presentationData.strings.nagramiXStoryConfirmationText(owner: owner),
            action: presentationData.strings.nagramiXViewStoryAction,
            confirmed: { [weak self] in
                guard let self else { return }
                self.nagramiXIsPresentingConfirmation = false
                self.nagramiXApprovedStoryId = item.id
                action()
            },
            cancelled: { [weak self] in
                self?.nagramiXIsPresentingConfirmation = false
            }
        )
        self.present(confirmationController, in: .window(.root))
    }

    fileprivate func nagramiXCanMarkStoryAsSeen(_ id: EngineStoryId) -> Bool {
        guard NagramiXTabSettings.current.confirmStoryViewing else { return true }
        guard let slice = self.nagramiXContent.stateValue?.slice else { return false }
        if slice.effectivePeer.id == self.context.account.peerId { return true }
        guard self.nagramiXApprovedStoryId == id else { return false }
        self.nagramiXApprovedStoryId = nil
        return true
    }

    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {
        guard NagramiXTabSettings.current.confirmStoryViewing else {
            action()
            return
        }
        guard !self.nagramiXIsPresentingConfirmation else {
            return
        }

        let presentForState: (StoryContentContextState) -> Void = { [weak self, weak parentController] state in
            guard let self, let parentController else {
                return
            }
            guard let slice = state.slice else {
                action()
                return
            }
            if slice.effectivePeer.id == self.context.account.peerId {
                action()
                return
            }

            self.nagramiXIsPresentingConfirmation = true
            let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
            let owner = slice.effectivePeer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder)
            var previewSignal: Signal<(TransformImageArguments) -> DrawingContext?, NoError>?
            if let peerReference = PeerReference(slice.effectivePeer) {
                switch slice.item.storyItem.media {
                case let .image(image):
                    previewSignal = chatMessagePhoto(postbox: self.context.account.postbox, userLocation: .peer(peerReference.id), userContentType: .story, photoReference: .story(peer: peerReference, id: slice.item.storyItem.id, media: image), synchronousLoad: false, highQuality: false)
                case let .file(file):
                    previewSignal = mediaGridMessageVideo(postbox: self.context.account.postbox, userLocation: .peer(peerReference.id), userContentType: .story, videoReference: .story(peer: peerReference, id: slice.item.storyItem.id, media: file), onlyFullSize: false, useLargeThumbnail: true, synchronousLoad: false, autoFetchFullSizeThumbnail: false, overlayColor: nil, nilForEmptyResult: false, useMiniThumbnailIfAvailable: true, blurred: false)
                default:
                    break
                }
            }
            let confirmationController = NagramiXStoryConfirmationController(
                previewSignal: previewSignal,
                title: presentationData.strings.nagramiXStoryConfirmationTitle,
                body: presentationData.strings.nagramiXStoryConfirmationText(owner: owner),
                action: presentationData.strings.nagramiXViewStoryAction,
                confirmed: { [weak self] in
                    self?.nagramiXIsPresentingConfirmation = false
                    self?.nagramiXApprovedStoryId = slice.item.id
                    action()
                },
                cancelled: { [weak self] in
                    self?.nagramiXIsPresentingConfirmation = false
                }
            )
            parentController.present(confirmationController, in: .window(.root))
        }

        if let state = self.nagramiXContent.stateValue {
            presentForState(state)
        } else {
            self.nagramiXPresentationDisposable?.dispose()
            self.nagramiXPresentationDisposable = (self.nagramiXContent.state
            |> take(1)
            |> deliverOnMainQueue).start(next: { state in
                presentForState(state)
            })
        }
    }

""",
        "Present native confirmation before an unseen external story opens",
    )
    replace_once(
        story_container_screen,
        """                    if let mappedId {
                        self.pendingNavigationToItemId = mappedId
                        component.content.navigate(navigation: .item(.id(mappedId)))
                    }
""",
        """                    if let mappedId, let targetItem = slice.allItems.first(where: { $0.id == mappedId }) {
                        controller.nagramiXConfirmNavigation(peer: targetItem.itemPeer ?? slice.peer, item: targetItem, action: { [weak self] in
                            guard let self, let component = self.component else { return }
                            self.pendingNavigationToItemId = mappedId
                            component.content.navigate(navigation: .item(.id(mappedId)))
                        })
                    }
""",
        "Gate every explicit same-peer story navigation before changing the focused item",
    )
    replace_once(
        story_container_screen,
        "            guard let component = self.component, let environment = self.environment, let controller = environment.controller() as? StoryContainerScreen else {\n",
        "            guard let environment = self.environment, let controller = environment.controller() as? StoryContainerScreen else {\n",
        "Remove the now-unused navigation component binding after the per-story gate owns navigation",
    )
    replace_once(
        story_container_screen,
        "                if let component = self.component, let stateValue = self.stateValue, let _ = stateValue.slice {\n",
        "                if let component = self.component, let stateValue = self.stateValue, let _ = stateValue.slice, let environment = self.environment, let controller = environment.controller() as? StoryContainerScreen {\n",
        "Access the confirmation controller before committing a peer swipe",
    )
    replace_once(
        story_container_screen,
        "                    if let direction {\n                        component.content.navigate(navigation: .peer(direction))\n                        \n                        if case .previous = direction {\n",
        """                    if let direction {
                        let targetSlice: StoryContentContextState.FocusedSlice?
                        switch direction {
                        case .previous:
                            targetSlice = stateValue.previousSlice
                        case .next:
                            targetSlice = stateValue.nextSlice
                        }
                        if let targetSlice {
                            controller.nagramiXConfirmNavigation(peer: targetSlice.effectivePeer, item: targetSlice.item, action: { [weak self] in
                                guard let self, let component = self.component else { return }
                                component.content.navigate(navigation: .peer(direction))
                            })
                        } else {
                            component.content.navigate(navigation: .peer(direction))
                        }

                        if case .previous = direction {
""",
        "Gate peer swipes before changing to the target peer story",
    )
    replace_once(
        story_container_screen,
        """                                markAsSeen: { [weak self] id in
                                    guard let self, let component = self.component else {
                                        return
                                    }
                                    component.content.markAsSeen(id: id)
                                },
""",
        """                                markAsSeen: { [weak self] id in
                                    guard let self, let component = self.component, let environment = self.environment, let controller = environment.controller() as? StoryContainerScreen, controller.nagramiXCanMarkStoryAsSeen(id) else {
                                        return
                                    }
                                    component.content.markAsSeen(id: id)
                                },
""",
        "Reject native seen registration until the exact target story is approved",
    )

    replace_once(
        chat_list_controller,
        "            self.push(storyContainerScreen)\n",
        "            storyContainerScreen.nagramiXPush(from: self)\n",
        "Confirm chat-list stories before pushing the viewer",
    )

    message_stats_controller = source / "submodules" / "StatisticsUI" / "Sources" / "MessageStatsController.swift"
    replace_once(
        message_stats_controller,
        "            controller.push(storyContainerScreen)\n",
        "            storyContainerScreen.nagramiXPush(from: controller)\n",
        "Confirm message-stat stories before pushing the viewer",
    )

    channel_stats_controller = source / "submodules" / "StatisticsUI" / "Sources" / "ChannelStatsController.swift"
    replace_once(
        channel_stats_controller,
        "            controller.push(storyContainerScreen)\n",
        "            storyContainerScreen.nagramiXPush(from: controller)\n",
        "Confirm channel-stat stories before pushing the viewer",
    )

    open_resolved_url = source / "submodules" / "TelegramUI" / "Sources" / "OpenResolvedUrl.swift"
    replace_once(
        open_resolved_url,
        "                        navigationController?.pushViewController(storyContainerScreen)\n",
        "                        if let navigationController {\n                            storyContainerScreen.nagramiXPush(from: navigationController)\n                        }\n",
        "Confirm deep-linked stories before pushing the viewer",
    )

    open_chat_message = source / "submodules" / "TelegramUI" / "Sources" / "OpenChatMessage.swift"
    replace_once(
        open_chat_message,
        "            navigationController?.pushViewController(storyContainerScreen)\n",
        "            if let navigationController {\n                storyContainerScreen.nagramiXPush(from: navigationController)\n            }\n",
        "Confirm message-linked stories before pushing the viewer",
    )

    chat_controller = source / "submodules" / "TelegramUI" / "Sources" / "ChatController.swift"
    replace_once(
        chat_controller,
        "                self.push(storyContainerScreen)\n",
        "                storyContainerScreen.nagramiXPush(from: self)\n",
        "Confirm in-chat stories before pushing the viewer",
    )

    open_stories = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "OpenStories.swift"
    replace_once(
        open_stories,
        "            parentController?.push(storyContainerScreen)\n",
        "            if let parentController {\n                storyContainerScreen.nagramiXPush(from: parentController)\n            }\n",
        "Confirm archived stories before pushing the viewer",
    )
    replace_once(
        open_stories,
        "            parentController?.push(storyContainerScreen)\n            completion(storyContainerScreen)\n",
        "            if let parentController {\n                storyContainerScreen.nagramiXPush(from: parentController, completion: {\n                    completion(storyContainerScreen)\n                })\n            }\n",
        "Confirm peer stories before pushing the viewer",
    )

    story_item_set_component = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryItemSetContainerComponent.swift"
    replace_once(
        story_item_set_component,
        "                controller.push(storyContainerScreen)\n",
        "                storyContainerScreen.nagramiXPush(from: controller)\n",
        "Confirm repost-chain stories before pushing the viewer",
    )

    peer_info_story_pane = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoVisualMediaPaneNode" / "Sources" / "PeerInfoStoryPaneNode.swift"
    replace_once(
        peer_info_story_pane,
        "                navigationController.pushViewController(storyContainerScreen)\n",
        "                storyContainerScreen.nagramiXPush(from: navigationController)\n",
        "Confirm media-pane stories before pushing the viewer",
    )

    peer_info_open_stories = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoScreenOpenStories.swift"
    replace_once(
        peer_info_open_stories,
        "                self.controller?.push(storyContainerScreen)\n",
        "                if let controller = self.controller {\n                    storyContainerScreen.nagramiXPush(from: controller)\n                }\n",
        "Confirm profile-header stories before pushing the viewer",
    )

    peer_info_screen = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoScreen.swift"
    replace_once(
        peer_info_screen,
        "                self.controller?.push(storyContainerScreen)\n",
        "                if let controller = self.controller {\n                    storyContainerScreen.nagramiXPush(from: controller)\n                }\n",
        "Confirm profile stories before pushing the viewer",
    )

    story_footer_panel = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryFooterPanelComponent" / "Sources" / "StoryFooterPanelComponent.swift"
    replace_once(
        story_footer_panel,
        "    public let canShare: Bool\n    public let externalViews: EngineStoryItem.Views?\n",
        "    public let canShare: Bool\n    public let canRepost: Bool\n    public let externalViews: EngineStoryItem.Views?\n",
        "Story footer repost capability state",
    )
    replace_once(
        story_footer_panel,
        "        canShare: Bool,\n        externalViews: EngineStoryItem.Views?,\n",
        "        canShare: Bool,\n        canRepost: Bool,\n        externalViews: EngineStoryItem.Views?,\n",
        "Story footer repost capability argument",
    )
    replace_once(
        story_footer_panel,
        "        self.canShare = canShare\n        self.externalViews = externalViews\n",
        "        self.canShare = canShare\n        self.canRepost = canRepost\n        self.externalViews = externalViews\n",
        "Story footer repost capability assignment",
    )
    replace_once(
        story_footer_panel,
        "        if lhs.externalViews != rhs.externalViews {\n",
        "        if lhs.canRepost != rhs.canRepost {\n            return false\n        }\n        if lhs.externalViews != rhs.externalViews {\n",
        "Story footer repost capability equality",
    )
    replace_once(
        story_footer_panel,
        """                    let repostButton: ComponentView<Empty>
                    if let current = self.repostButton {
                        repostButton = current
                    } else {
                        repostButton = ComponentView()
                        self.repostButton = repostButton
                    }
""" + "                    \n" + """                    let forwardButton: ComponentView<Empty>
""",
        """                    let forwardButton: ComponentView<Empty>
""",
        "Create a repost button only when NagramiX enables it",
    )
    replace_once(
        story_footer_panel,
        """                    let repostButtonSize = repostButton.update(
                        transition: likeStatsTransition,
                        component: AnyComponent(MessageInputActionButtonComponent(
                            mode: .repost,
                            storyId: component.storyItem.id,
                            action: { [weak self] _, action, _ in
                                guard let self, let component = self.component else {
                                    return
                                }
                                guard case .up = action else {
                                    return
                                }
                                component.repostAction()
                            },
                            longPressAction: nil,
                            switchMediaInputMode: {
                            },
                            updateMediaCancelFraction: { _ in
                            },
                            lockMediaRecording: {
                            },
                            stopAndPreviewMediaRecording: {
                            },
                            moreAction: { _, _ in },
                            context: component.context,
                            theme: component.theme,
                            strings: component.strings,
                            presentController: { _ in },
                            audioRecorder: nil,
                            videoRecordingStatus: nil
                        )),
                        environment: {},
                        containerSize: CGSize(width: 33.0, height: 33.0)
                    )
                    if let repostButtonView = repostButton.view as? MessageInputActionButtonComponent.View {
                        if repostButtonView.superview == nil {
                            self.addSubview(repostButtonView)
                        }
                        var repostButtonFrame = CGRect(origin: CGPoint(x: rightContentOffset - repostButtonSize.width, y: floor((size.height - repostButtonSize.height) * 0.5)), size: repostButtonSize)
                        repostButtonFrame.origin.y += component.expandFraction * 45.0
""" + "                        \n" + """                        forwardStatsTransition.setPosition(view: repostButtonView, position: repostButtonFrame.center)
                        forwardStatsTransition.setBounds(view: repostButtonView, bounds: CGRect(origin: CGPoint(), size: repostButtonFrame.size))
                        forwardStatsTransition.setAlpha(view: repostButtonView, alpha: 1.0 - component.expandFraction)
""" + "                        \n" + """                        rightContentOffset -= repostButtonSize.width + 14.0
""" + "                        \n" + """                        if forwardStatsText.superview == nil {
                            repostButtonView.button.view.addSubview(forwardStatsText)
                        }
""" + "                        \n" + """                        forwardStatsFrame.origin.x -= repostButtonFrame.minX
                        forwardStatsFrame.origin.y -= repostButtonFrame.minY
                        forwardStatsTransition.setPosition(view: forwardStatsText, position: forwardStatsFrame.center)
                        forwardStatsTransition.setBounds(view: forwardStatsText, bounds: CGRect(origin: CGPoint(), size: forwardStatsFrame.size))
                    }
""" + "                    \n",
        """                    if component.canRepost {
                        let repostButton: ComponentView<Empty>
                        if let current = self.repostButton {
                            repostButton = current
                        } else {
                            repostButton = ComponentView()
                            self.repostButton = repostButton
                        }

                        let repostButtonSize = repostButton.update(
                            transition: likeStatsTransition,
                            component: AnyComponent(MessageInputActionButtonComponent(
                                mode: .repost,
                                storyId: component.storyItem.id,
                                action: { [weak self] _, action, _ in
                                    guard let self, let component = self.component else {
                                        return
                                    }
                                    guard case .up = action else {
                                        return
                                    }
                                    component.repostAction()
                                },
                                longPressAction: nil,
                                switchMediaInputMode: {
                                },
                                updateMediaCancelFraction: { _ in
                                },
                                lockMediaRecording: {
                                },
                                stopAndPreviewMediaRecording: {
                                },
                                moreAction: { _, _ in },
                                context: component.context,
                                theme: component.theme,
                                strings: component.strings,
                                presentController: { _ in },
                                audioRecorder: nil,
                                videoRecordingStatus: nil
                            )),
                            environment: {},
                            containerSize: CGSize(width: 33.0, height: 33.0)
                        )
                        if let repostButtonView = repostButton.view as? MessageInputActionButtonComponent.View {
                            if repostButtonView.superview == nil {
                                self.addSubview(repostButtonView)
                            }
                            var repostButtonFrame = CGRect(origin: CGPoint(x: rightContentOffset - repostButtonSize.width, y: floor((size.height - repostButtonSize.height) * 0.5)), size: repostButtonSize)
                            repostButtonFrame.origin.y += component.expandFraction * 45.0

                            forwardStatsTransition.setPosition(view: repostButtonView, position: repostButtonFrame.center)
                            forwardStatsTransition.setBounds(view: repostButtonView, bounds: CGRect(origin: CGPoint(), size: repostButtonFrame.size))
                            forwardStatsTransition.setAlpha(view: repostButtonView, alpha: 1.0 - component.expandFraction)

                            rightContentOffset -= repostButtonSize.width + 14.0

                            if forwardStatsText.superview == nil {
                                repostButtonView.button.view.addSubview(forwardStatsText)
                            }

                            forwardStatsFrame.origin.x -= repostButtonFrame.minX
                            forwardStatsFrame.origin.y -= repostButtonFrame.minY
                            forwardStatsTransition.setPosition(view: forwardStatsText, position: forwardStatsFrame.center)
                            forwardStatsTransition.setBounds(view: forwardStatsText, bounds: CGRect(origin: CGPoint(), size: forwardStatsFrame.size))
                        }
                    } else if let repostButton = self.repostButton {
                        self.repostButton = nil
                        repostButton.view?.removeFromSuperview()
                    }

""",
        "Hide the built-in repost action while keeping forwarding available",
    )

    story_item_set_component = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryItemSetContainerComponent.swift"
    replace_once(
        story_item_set_component,
        "import TelegramCore\n",
        "import TelegramCore\nimport NagramiXCore\n",
        "Story footer NagramiXCore import",
    )
    replace_once(
        story_item_set_component,
        "                                    canShare: canShare,\n                                    externalViews: nil,\n",
        "                                    canShare: canShare,\n                                    canRepost: canShare && NagramiXTabSettings.current.enableStoryRepost,\n                                    externalViews: nil,\n",
        "Combine NagramiX repost preference with Telegram forwarding restrictions",
    )

    story_send_message = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryItemSetContainerViewSendMessage.swift"
    replace_once(
        story_send_message,
        "import TelegramCore\n",
        "import TelegramCore\nimport NagramiXCore\n",
        "Story share sheet NagramiXCore import",
    )
    replace_once(
        story_send_message,
        """            let shareController = component.context.sharedContext.makeShareController(context: component.context, params: ShareControllerParams(
""",
        """            let shareStory: (() -> Void)?
            if NagramiXTabSettings.current.enableStoryRepost {
                shareStory = { [weak view] in
                    guard let view else {
                        return
                    }
                    view.openStoryEditing(repost: true)
                }
            } else {
                shareStory = nil
            }

            let shareController = component.context.sharedContext.makeShareController(context: component.context, params: ShareControllerParams(
""",
        "Prepare the optional built-in repost-to-story action",
    )
    replace_once(
        story_send_message,
        """                shareStory: { [weak view] in
                    guard let view else {
                        return
                    }
                    view.openStoryEditing(repost: true)
                }
""",
        """                shareStory: shareStory
""",
        "Hide the share-sheet repost action when disabled",
    )

    message_share_menu = source / "submodules" / "TelegramUI" / "Sources" / "ChatControllerOpenMessageShareMenu.swift"
    replace_once(
        message_share_menu,
        "import TelegramCore\n",
        "import TelegramCore\nimport NagramiXCore\n",
        "Message share sheet NagramiXCore import",
    )
    replace_once(
        message_share_menu,
        "        let shareStory: (() -> Void)? = canShareToStory ? { [weak self] in\n",
        "        let shareStory: (() -> Void)? = (canShareToStory && NagramiXTabSettings.current.enableStoryRepost) ? { [weak self] in\n",
        "Gate the built-in public-message repost action with the NagramiX setting",
    )

    app_delegate = source / "submodules" / "TelegramUI" / "Sources" / "AppDelegate.swift"
    replace_once(
        app_delegate,
        """                var icons = [
                    PresentationAppIcon(name: "BlueIcon", imageName: "BlueIcon", isDefault: buildConfig.isAppStoreBuild),
                    PresentationAppIcon(name: "New2", imageName: "New2"),
                    PresentationAppIcon(name: "New1", imageName: "New1"),
                    PresentationAppIcon(name: "BlackIcon", imageName: "BlackIcon"),
                    PresentationAppIcon(name: "BlueClassicIcon", imageName: "BlueClassicIcon"),
                    PresentationAppIcon(name: "BlackClassicIcon", imageName: "BlackClassicIcon"),
                    PresentationAppIcon(name: "BlueFilledIcon", imageName: "BlueFilledIcon"),
                    PresentationAppIcon(name: "BlackFilledIcon", imageName: "BlackFilledIcon")
                ]
                if buildConfig.isInternalBuild {
                    icons.append(PresentationAppIcon(name: "WhiteFilledIcon", imageName: "WhiteFilledIcon"))
                }
""" + "                \n" + """                icons.append(PresentationAppIcon(name: "Premium", imageName: "Premium", isPremium: true))
                icons.append(PresentationAppIcon(name: "PremiumTurbo", imageName: "PremiumTurbo", isPremium: true))
                icons.append(PresentationAppIcon(name: "PremiumBlack", imageName: "PremiumBlack", isPremium: true))
""" + "                \n" + """                return icons
""",
        """                return [
                    PresentationAppIcon(name: "NagramiX1", imageName: "NagramiX1Preview", isDefault: true),
                    PresentationAppIcon(name: "NagramiX2", imageName: "NagramiX2"),
                    PresentationAppIcon(name: "NagramiX3", imageName: "NagramiX3"),
                    PresentationAppIcon(name: "NagramiX4", imageName: "NagramiX4"),
                    PresentationAppIcon(name: "NagramiX5", imageName: "NagramiX5"),
                    PresentationAppIcon(name: "NagramiX6", imageName: "NagramiX6"),
                    PresentationAppIcon(name: "NagramiX7", imageName: "NagramiX7"),
                    PresentationAppIcon(name: "NagramiX8", imageName: "NagramiX8")
                ]
""",
        "NagramiX app icon list",
    )

    icon_item = source / "submodules" / "SettingsUI" / "Sources" / "Themes" / "ThemeSettingsAppIconItem.swift"
    replace_once(
        icon_item,
        "import TelegramPresentationData\n",
        "import TelegramPresentationData\nimport NagramiXCore\n",
        "NagramiX app icon localization import",
    )
    replace_once(
        icon_item,
        """                                case "PremiumTurbo":
                                    name = item.strings.Appearance_AppIconTurbo
                                default:
""",
        """                                case "PremiumTurbo":
                                    name = item.strings.Appearance_AppIconTurbo
                                case "NagramiX1":
                                    name = item.strings.nagramiXIconMain
                                case "NagramiX2":
                                    name = item.strings.nagramiXIconSunset
                                case "NagramiX3":
                                    name = item.strings.nagramiXIconAurora
                                case "NagramiX4":
                                    name = item.strings.nagramiXIconGraphite
                                case "NagramiX5":
                                    name = item.strings.nagramiXIconAmber
                                case "NagramiX6":
                                    name = item.strings.nagramiXIconNeon
                                case "NagramiX7":
                                    name = item.strings.nagramiXIconLime
                                case "NagramiX8":
                                    name = item.strings.nagramiXIconRuby
                                default:
""",
        "NagramiX app icon display names",
    )

    telegram_build = source / "Telegram" / "BUILD"
    replace_once(
        telegram_build,
        """alternate_icon_folders = [
    "BlackIcon",
    "BlackClassicIcon",
    "BlackFilledIcon",
    "BlueIcon",
    "BlueClassicIcon",
    "BlueFilledIcon",
    "WhiteFilledIcon",
    "New1",
    "New2",
    "Premium",
    "PremiumBlack",
    "PremiumTurbo",
]
""",
        """alternate_icon_folders = [
    "NagramiX2",
    "NagramiX3",
    "NagramiX4",
    "NagramiX5",
    "NagramiX6",
    "NagramiX7",
    "NagramiX8",
]
""",
        "NagramiX alternate icon build targets",
    )

    replace_once(
        telegram_build,
        'composer_icon_folders = ["Telegram"]\n',
        'composer_icon_folders = []\n',
        "Disable the differently scaled Icon Composer primary icon",
    )
    replace_once(
        telegram_build,
        '    app_icons = [ ":{}_icon".format(name) for name in composer_icon_folders ],\n',
        '    app_icons = [":NagramiXPrimaryIcon"],\n',
        "Use the NagramiX1 appiconset as the primary icon",
    )
    replace_once(
        telegram_build,
        '''filegroup(
    name = "DefaultIcon",
    srcs = glob([
        "Telegram-iOS/AppIcons.xcassets/BlueIcon.appiconset/*.png",
    ]),
)
''',
        '''filegroup(
    name = "DefaultIcon",
    srcs = glob([
        "Telegram-iOS/AppIcons.xcassets/NagramiX1.appiconset/*.png",
    ]),
)

filegroup(
    name = "NagramiXPrimaryIcon",
    srcs = glob([
        "Telegram-iOS/AppIcons.xcassets/NagramiX1.appiconset/**/*",
    ]),
)
''',
        "Expose the NagramiX1 appiconset to rules_apple",
    )

    chat_panel_interaction = source / "submodules" / "ChatPresentationInterfaceState" / "Sources" / "ChatPanelInterfaceInteraction.swift"
    replace_once(
        chat_panel_interaction,
        "    public let forwardMessages: ([EngineRawMessage]) -> Void\n",
        "    public let forwardMessages: ([EngineRawMessage]) -> Void\n    public let copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)?\n    public let selectMessagesByAuthor: ((EnginePeer.Id) -> Void)?\n",
        "Expose a distinct copy-as-new handler plus author selection",
    )
    replace_once(
        chat_panel_interaction,
        "        forwardMessages: @escaping ([EngineRawMessage]) -> Void,\n        updateForwardOptionsState:",
        "        forwardMessages: @escaping ([EngineRawMessage]) -> Void,\n        copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)? = nil,\n        selectMessagesByAuthor: ((EnginePeer.Id) -> Void)? = nil,\n        updateForwardOptionsState:",
        "Add optional NagramiX chat interaction callbacks",
    )
    replace_once(
        chat_panel_interaction,
        "        self.forwardMessages = forwardMessages\n        self.updateForwardOptionsState = updateForwardOptionsState\n",
        "        self.forwardMessages = forwardMessages\n        self.copyMessagesWithoutSource = copyMessagesWithoutSource\n        self.selectMessagesByAuthor = selectMessagesByAuthor\n        self.updateForwardOptionsState = updateForwardOptionsState\n",
        "Store the explicit NagramiX copy-as-new callback",
    )

    chat_controller_source = source / "submodules" / "TelegramUI" / "Sources" / "ChatController.swift"
    replace_once(
        chat_controller_source,
        "    let navigationActionDisposable = MetaDisposable()\n    let messageIndexDisposable = MetaDisposable()\n",
        "    let navigationActionDisposable = MetaDisposable()\n    let nagramiXSelectAuthorDisposable = MetaDisposable()\n    var nagramiXSelectAuthorGeneration: UInt64 = 0\n    var nagramiXIsSelectingAuthorMessages = false\n    let messageIndexDisposable = MetaDisposable()\n",
        "Own the cancellable Select From Author pagination lifecycle",
    )
    replace_once(
        chat_controller_source,
        "        self.navigationActionDisposable.dispose()\n        self.galleryHiddenMesageAndMediaDisposable.dispose()\n",
        "        self.navigationActionDisposable.dispose()\n        self.nagramiXSelectAuthorDisposable.dispose()\n        self.galleryHiddenMesageAndMediaDisposable.dispose()\n",
        "Cancel Select From Author when leaving the chat",
    )

    chat_load_node = source / "submodules" / "TelegramUI" / "Sources" / "Chat" / "ChatControllerLoadDisplayNode.swift"
    replace_once(
        chat_load_node,
        """        }, updateForwardOptionsState: { [weak self] f in
""",
        """        }, copyMessagesWithoutSource: { [weak self] messages in
            guard let self, !messages.isEmpty else {
                return
            }
            guard !self.presentAccountFrozenInfoIfNeeded(delay: true) else {
                return
            }
            self.commitPurposefulAction()
            self.forwardMessages(messageIds: messages.map { $0.id }.sorted(), transferMode: .copyAsNew)
        }, selectMessagesByAuthor: { [weak self] authorId in
            guard let self, self.isNodeLoaded, !self.nagramiXIsSelectingAuthorMessages, let peerId = self.chatLocation.peerId else {
                return
            }
            self.nagramiXIsSelectingAuthorMessages = true
            self.nagramiXSelectAuthorGeneration &+= 1
            let generation = self.nagramiXSelectAuthorGeneration
            let threadId = self.chatLocation.threadId
            let location: SearchMessagesLocation = .peer(peerId: peerId, fromId: authorId, tags: nil, reactions: nil, threadId: threadId, minDate: nil, maxDate: nil)
            let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
            let progressController = OverlayStatusController(theme: presentationData.theme, type: .loading(cancelled: { [weak self] in
                guard let self else { return }
                self.nagramiXSelectAuthorGeneration &+= 1
                self.nagramiXIsSelectingAuthorMessages = false
                self.nagramiXSelectAuthorDisposable.set(nil)
            }))
            self.present(progressController, in: .window(.root), with: ViewControllerPresentationArguments(presentationAnimation: .modalSheet))

            var requestPage: ((SearchMessagesState?) -> Void)?
            requestPage = { [weak self, weak progressController] state in
                guard let self, self.nagramiXSelectAuthorGeneration == generation, self.chatLocation.peerId == peerId, self.chatLocation.threadId == threadId else {
                    return
                }
                self.nagramiXSelectAuthorDisposable.set((self.context.engine.messages.searchMessages(location: location, query: "", state: state, limit: 100)
                |> deliverOnMainQueue).startStrict(next: { [weak self, weak progressController] result, updatedState in
                    guard let self, self.nagramiXSelectAuthorGeneration == generation, self.chatLocation.peerId == peerId, self.chatLocation.threadId == threadId else {
                        return
                    }
                    if !result.completed {
                        requestPage?(updatedState)
                        return
                    }
                    self.nagramiXIsSelectingAuthorMessages = false
                    progressController?.dismiss()
                    let messageIds = result.messages.map { $0.id }
                    guard !messageIds.isEmpty else { return }
                    let _ = self.presentVoiceMessageDiscardAlert(action: { [weak self] in
                        self?.updateChatPresentationInterfaceState(animated: true, interactive: true, { state in
                            state.updatedInterfaceState { $0.withUpdatedSelectedMessages(messageIds) }.updatedShowCommands(false)
                        })
                    }, alertAction: {}, delay: true)
                }))
            }
            requestPage?(nil)
        }, updateForwardOptionsState: { [weak self] f in
""",
        "Wire copy-as-new and loaded-author selection into ChatController",
    )

    context_menus = source / "submodules" / "TelegramUI" / "Sources" / "ChatInterfaceStateContextMenus.swift"
    replace_once(
        context_menus,
        "import AdsReportScreen\n",
        "import AdsReportScreen\nimport NagramiXCore\n",
        "NagramiX context menu localization import",
    )
    replace_once(
        context_menus,
        """        if (loggingSettings.logToFile || loggingSettings.logToConsole) && !downloadableMediaResourceInfos.isEmpty {
            actions.append(.action(ContextMenuActionItem(text: "Send Logs", icon: { theme in
                return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Message"), color: theme.actionSheet.primaryTextColor)
            }, action: { _, f in
                triggerDebugSendLogsUI(context: context, additionalInfo: "User has requested download logs for \\(downloadableMediaResourceInfos)", pushController: { c in
                    controllerInteraction.navigationController()?.pushViewController(c)
                })
                f(.default)
            })))
        }
""",
        "",
        "Remove Send Logs from the user message context menu",
    )
    replace_once(
        context_menus,
        """                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.Conversation_ContextMenuForward, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Forward"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    interfaceInteraction.forwardMessages(selectAll || isImage ? messages : [message])
                    f(.dismissWithoutContent)
                })))
""",
        """                let messagesToForward = selectAll || isImage ? messages : [message]
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXForwardWithAuthor, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Forward"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    interfaceInteraction.forwardMessages(messagesToForward)
                    f(.dismissWithoutContent)
                })))
                let canForwardWithoutAuthor = interfaceInteraction.copyMessagesWithoutSource != nil
                    && nagramiXCanCopyMessagesAsNew(messagesToForward)
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXForwardWithoutAuthor, textColor: canForwardWithoutAuthor ? .primary : .disabled, icon: { _ in
                    return nil
                }, iconAnimation: ContextMenuActionItem.IconAnimation(name: "message_preview_person_off"), action: !canForwardWithoutAuthor ? nil : { _, f in
                    interfaceInteraction.copyMessagesWithoutSource?(messagesToForward)
                    f(.dismissWithoutContent)
                })))
""",
        "Separate standard forwarding from safe copy-as-new sending",
    )

    chat_controller_forward_messages = source / "submodules" / "TelegramUI" / "Sources" / "ChatControllerForwardMessages.swift"
    replace_once(
        chat_controller_forward_messages,
        "extension ChatControllerImpl {\n",
        """enum NagramiXMessageTransferMode: Equatable {
    case forwardWithSource
    case copyAsNew
}

func nagramiXCanCopyMessagesAsNew(_ messages: [EngineRawMessage]) -> Bool {
    return nagramiXCopyMessagesAsNew(messages) != nil
}

private func nagramiXCopyMessagesAsNew(_ messages: [EngineRawMessage]) -> [EnqueueMessage]? {
    guard !messages.isEmpty else {
        return nil
    }
    var result: [EnqueueMessage] = []
    var copiedGroupingKeys: [Int64: Int64] = [:]
    for message in messages {
        if message.id.peerId.namespace == Namespaces.Peer.SecretChat
            || message.isCopyProtected()
            || message.containsSecretMedia
            || message.media.contains(where: { $0 is TelegramMediaPaidContent || $0 is TelegramMediaExpiredContent }) {
            return nil
        }

        var attributes: [EngineMessage.Attribute] = []
        var inlineStickers: [EngineMedia.Id: EngineRawMedia] = [:]
        if let entities = message.attributes.first(where: { $0 is TextEntitiesMessageAttribute }) as? TextEntitiesMessageAttribute {
            attributes.append(TextEntitiesMessageAttribute(entities: entities.entities))
            for mediaId in entities.associatedMediaIds {
                if let media = message.associatedMedia[mediaId] {
                    inlineStickers[mediaId] = media
                }
            }
        }
        if message.attributes.contains(where: { $0 is MediaSpoilerMessageAttribute }) {
            attributes.append(MediaSpoilerMessageAttribute())
        }

        var mediaReference: AnyMediaReference?
        for media in message.media {
            if media is TelegramMediaWebpage {
                continue
            } else if mediaReference == nil && (media is TelegramMediaImage || media is TelegramMediaFile || media is TelegramMediaContact || media is TelegramMediaMap) {
                mediaReference = .message(message: MessageReference(message), media: media)
            } else {
                return nil
            }
        }
        if message.text.isEmpty && mediaReference == nil {
            return nil
        }

        var localGroupingKey: Int64?
        if let groupingKey = message.groupingKey {
            if let existing = copiedGroupingKeys[groupingKey] {
                localGroupingKey = existing
            } else {
                let generated = Int64.random(in: Int64.min ... Int64.max)
                copiedGroupingKeys[groupingKey] = generated
                localGroupingKey = generated
            }
        }
        result.append(.message(text: message.text, attributes: attributes, inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: localGroupingKey, correlationId: nil, bubbleUpEmojiOrStickersets: []))
    }
    return result
}

extension ChatControllerImpl {
""",
        "Add an explicit message transfer mode",
    )
    replace_once(
        chat_controller_forward_messages,
        "    func forwardMessages(messageIds: [EngineMessage.Id], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool = false) {\n",
        "    func forwardMessages(messageIds: [EngineMessage.Id], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool = false, transferMode: NagramiXMessageTransferMode = .forwardWithSource) {\n",
        "Accept the typed transfer mode",
    )
    replace_once(
        chat_controller_forward_messages,
        "            self?.forwardMessages(messages: sortedMessages, options: options, resetCurrent: resetCurrent)\n",
        "            self?.forwardMessages(messages: sortedMessages, options: options, resetCurrent: resetCurrent, transferMode: transferMode)\n",
        "Propagate the transfer mode after loading",
    )
    replace_once(
        chat_controller_forward_messages,
        "    func forwardMessages(messages: [EngineRawMessage], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool) {\n",
        "    func forwardMessages(messages: [EngineRawMessage], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool, transferMode: NagramiXMessageTransferMode = .forwardWithSource) {\n",
        "Keep classic forwarding as the default",
    )
    replace_once(
        chat_controller_forward_messages,
        "            }, multipleSelection: true, forwardedMessageIds: messages.map { $0.id }, selectForumThreads: true))\n",
        "            }, multipleSelection: true, forwardedMessageIds: transferMode == .forwardWithSource ? messages.map { $0.id } : [], selectForumThreads: true))\n",
        "Keep forward-only picker metadata out of copy-as-new mode",
    )
    replace_once(
        chat_controller_forward_messages,
        """            var attemptSelectionImpl: ((EnginePeer, ChatListDisabledPeerReason) -> Void)?
            let controller = self.context.sharedContext.makePeerSelectionController(""",
        """            var attemptSelectionImpl: ((EnginePeer, ChatListDisabledPeerReason) -> Void)?
            var nagramiXCopyThreadIds: [EnginePeer.Id: Int64] = [:]
            let controller = self.context.sharedContext.makePeerSelectionController(""",
        "Preserve selected destination topics in copy-as-new mode",
    )
    replace_once(
        chat_controller_forward_messages,
        """                                for (peer, shouldDivert) in targetPeersShouldDivert {
                                    var peerMessages = result
                                    if shouldDivert {
""",
        """                                for (peer, shouldDivert) in targetPeersShouldDivert {
                                    var peerMessages = result
                                    if transferMode == .copyAsNew, let threadId = nagramiXCopyThreadIds[peer.id] {
                                        peerMessages = peerMessages.map { $0.withUpdatedThreadId(threadId) }
                                    }
                                    if shouldDivert {
""",
        "Apply only the destination thread id without copying any source reply",
    )
    replace_once(
        chat_controller_forward_messages,
        """                        var attributes: [EngineMessage.Attribute] = []
                        attributes.append(ForwardOptionsMessageAttribute(hideNames: forwardOptions?.hideNames == true, hideCaptions: forwardOptions?.hideCaptions == true))
""" + "                        \n" + """                        result.append(contentsOf: messages.map { message -> EnqueueMessage in
                            return .forward(source: message.id, threadId: nil, grouping: .auto, attributes: attributes, correlationId: nil)
                        })
""",
        """                        switch transferMode {
                        case .forwardWithSource:
                            var attributes: [EngineMessage.Attribute] = []
                            attributes.append(ForwardOptionsMessageAttribute(hideNames: forwardOptions?.hideNames == true, hideCaptions: forwardOptions?.hideCaptions == true))
                            result.append(contentsOf: messages.map { message -> EnqueueMessage in
                                return .forward(source: message.id, threadId: nil, grouping: .auto, attributes: attributes, correlationId: nil)
                            })
                        case .copyAsNew:
                            guard let copiedMessages = nagramiXCopyMessagesAsNew(messages) else {
                                return
                            }
                            result.append(contentsOf: copiedMessages)
                        }
""",
        "Build fresh messages without forward or reply metadata",
    )
    replace_once(
        chat_controller_forward_messages,
        """                let peerId = peer.id
                let accountPeerId = strongSelf.context.account.peerId
""" + "                \n" + """                if resetCurrent {
""",
        """                let peerId = peer.id
                let accountPeerId = strongSelf.context.account.peerId

                if transferMode == .copyAsNew {
                    if let threadId {
                        nagramiXCopyThreadIds[peer.id] = threadId
                    }
                    strongController.multiplePeersSelected?([peer], [peer.id: peer], NSAttributedString(string: ""), .generic, nil, nil)
                    return
                }

                if resetCurrent {
""",
        "Route single-destination copy mode through the real send-as-new commit path",
    )
    replace_once(
        context_menus,
        """            if messages.count > 1 {
""",
        """            if let authorId = message.author?.id, interfaceInteraction.selectMessagesByAuthor != nil {
                if !actions.isEmpty && !didAddSeparator {
                    didAddSeparator = true
                    actions.append(.separator)
                }
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXSelectFromAuthor, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/SelectAll"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    interfaceInteraction.selectMessagesByAuthor?(authorId)
                    f(.dismissWithoutContent)
                })))
            }

            if messages.count > 1 {
""",
        "Add Select by Author after the standard Select action",
    )

    peer_info_profile_items = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoProfileItems.swift"
    replace_once(
        peer_info_profile_items,
        "import BoostLevelIconComponent\n",
        "import BoostLevelIconComponent\nimport UndoUI\nimport NagramiXCore\n",
        "NagramiX profile metadata import",
    )
    replace_once(
        peer_info_profile_items,
        """private let enabledPrivateBioEntities: EnabledEntityTypes = [.internalUrl, .mention, .hashtag]
""",
        """private let enabledPrivateBioEntities: EnabledEntityTypes = [.internalUrl, .mention, .hashtag]

private func nagramiXCopyProfileId(_ value: Int64, presentationData: PresentationData, interaction: PeerInfoInteraction) {
    UIPasteboard.general.string = "\\(value)"
    interaction.getController()?.present(
        UndoOverlayController(
            presentationData: presentationData,
            content: .copy(text: presentationData.strings.nagramiXProfileIdCopied),
            elevatedLayout: false,
            animateInAsReplacement: false,
            action: { _ in false }
        ),
        in: .current
    )
}
""",
        "Copy profile IDs through the native Telegram confirmation overlay",
    )
    replace_once(
        peer_info_profile_items,
        "        let ItemCommunity = 10000\n",
        """        let ItemCommunity = 10000
        let ItemNagramiXProfileId = 11000
        let ItemNagramiXRegistration = 11001

        let nagramiXSettings = NagramiXTabSettings.current
        if nagramiXSettings.showProfileIds {
            items[currentPeerInfoSection]!.append(PeerInfoScreenLabeledValueItem(id: ItemNagramiXProfileId, label: presentationData.strings.nagramiXProfileId, text: "\\(user.id.id._internalGetInt64Value())", textColor: .accent, action: { _, _ in
                nagramiXCopyProfileId(user.id.id._internalGetInt64Value(), presentationData: presentationData, interaction: interaction)
            }, requestLayout: { animated in
                interaction.requestLayout(animated)
            }))
        }
        if nagramiXSettings.showRegistrationDate {
            let year = NagramiXPeerMetadata.approximateRegistrationYear(peerId: user.id.id._internalGetInt64Value())
            items[currentPeerInfoSection]!.append(PeerInfoScreenLabeledValueItem(id: ItemNagramiXRegistration, label: presentationData.strings.nagramiXRegistrationDate, text: presentationData.strings.nagramiXApproximateRegistration(year), textColor: .primary, action: nil, requestLayout: { animated in
                interaction.requestLayout(animated)
            }))
        }
""",
        "Show optional NagramiX user metadata",
    )
    replace_once(
        peer_info_profile_items,
        "        let ItemCommunity = 12\n",
        """        let ItemCommunity = 12
        let ItemNagramiXProfileId = 13

        let nagramiXSettings = NagramiXTabSettings.current
        if nagramiXSettings.showProfileIds {
            items[currentPeerInfoSection]!.append(PeerInfoScreenLabeledValueItem(id: ItemNagramiXProfileId, label: presentationData.strings.nagramiXProfileId, text: "\\(channel.id.id._internalGetInt64Value())", textColor: .accent, action: { _, _ in
                nagramiXCopyProfileId(channel.id.id._internalGetInt64Value(), presentationData: presentationData, interaction: interaction)
            }, requestLayout: { animated in
                interaction.requestLayout(animated)
            }))
        }
""",
        "Show optional NagramiX channel metadata",
    )
    replace_once(
        peer_info_profile_items,
        """    } else if case let .legacyGroup(group) = data.peer {
        if let cachedData = data.cachedData as? CachedGroupData {
""",
        """    } else if case let .legacyGroup(group) = data.peer {
        let ItemNagramiXProfileId = 1

        let nagramiXSettings = NagramiXTabSettings.current
        if nagramiXSettings.showProfileIds {
            items[currentPeerInfoSection]!.append(PeerInfoScreenLabeledValueItem(id: ItemNagramiXProfileId, label: presentationData.strings.nagramiXProfileId, text: "\\(group.id.id._internalGetInt64Value())", textColor: .accent, action: { _, _ in
                nagramiXCopyProfileId(group.id.id._internalGetInt64Value(), presentationData: presentationData, interaction: interaction)
            }, requestLayout: { animated in
                interaction.requestLayout(animated)
            }))
        }
        if let cachedData = data.cachedData as? CachedGroupData {
""",
        "Show optional NagramiX legacy-group metadata",
    )

    contacts_peer_item = source / "submodules" / "ContactsPeerItem" / "Sources" / "ContactsPeerItem.swift"
    contacts_peer_item_build = source / "submodules" / "ContactsPeerItem" / "BUILD"
    if contacts_peer_item.exists():
        replace_once(
            contacts_peer_item,
            "import TelegramCore\n",
            "import TelegramCore\nimport NagramiXCore\n",
            "Read the mutual-contact badge preference in native contact cells",
        )
        replace_once(
            contacts_peer_item,
            """            switch item.status {
""",
            """            if NagramiXTabSettings.current.showMutualContactIcon,
               case let .peer(peer, _) = item.peer,
               let peer,
               case let .user(user) = peer,
               peer.id != item.context.account.peerId,
               user.botInfo == nil,
               user.flags.contains(.mutualContact),
               !(user.firstName ?? "").isEmpty || !(user.lastName ?? "").isEmpty,
               let currentTitle = titleAttributedString {
                let updatedTitle = NSMutableAttributedString(attributedString: currentTitle)
                if #available(iOS 13.0, *), let icon = UIImage(systemName: "person.2.fill", withConfiguration: UIImage.SymbolConfiguration(pointSize: 12.0, weight: .semibold))?.withTintColor(item.presentationData.theme.list.itemAccentColor, renderingMode: .alwaysOriginal) {
                    updatedTitle.append(NSAttributedString(string: " "))
                    let attachment = NSTextAttachment()
                    attachment.image = icon
                    attachment.bounds = CGRect(x: 0.0, y: -1.0, width: 14.0, height: 12.0)
                    updatedTitle.append(NSAttributedString(attachment: attachment))
                    titleAttributedString = updatedTitle
                }
            }

            switch item.status {
""",
            "Append a theme-tinted mutual-contact icon to real mutual users",
        )
        replace_once(
            contacts_peer_item_build,
            '        "//submodules/TelegramCore:TelegramCore",\n',
            '        "//submodules/TelegramCore:TelegramCore",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
            "Link contact cells with NagramiX settings",
        )

    account_utils = source / "submodules" / "AccountUtils" / "Sources" / "AccountUtils.swift"
    replace_once(
        account_utils,
        "public let maximumNumberOfAccounts = 3\n",
        "public let maximumNumberOfAccounts = 5\n",
        "Allow up to five native Telegram accounts",
    )

    account_context = source / "submodules" / "TelegramUI" / "Sources" / "AccountContext.swift"
    replace_once(
        account_context,
        "import DirectMediaImageCache\n",
        "import DirectMediaImageCache\nimport NagramiXCore\n",
        "Outgoing call confirmation settings import",
    )
    replace_once(
        account_context,
        """    public func requestCall(peerId: PeerId, isVideo: Bool, completion: @escaping () -> Void) {
        guard let callResult = self.sharedContext.callManager?.requestCall(context: self, peerId: peerId, isVideo: isVideo, endCurrentIfAny: false) else {
""",
        """    public func requestCall(peerId: PeerId, isVideo: Bool, completion: @escaping () -> Void) {
        self.requestCall(peerId: peerId, isVideo: isVideo, completion: completion, skipNagramiXConfirmation: false)
    }

    private func requestCall(peerId: PeerId, isVideo: Bool, completion: @escaping () -> Void, skipNagramiXConfirmation: Bool) {
        if NagramiXTabSettings.current.confirmOutgoingCalls && !skipNagramiXConfirmation {
            let presentationData = self.sharedContext.currentPresentationData.with { $0 }
            self.sharedContext.mainWindow?.present(textAlertController(
                context: self,
                title: presentationData.strings.nagramiXCallConfirmationTitle,
                text: presentationData.strings.nagramiXCallConfirmationText,
                actions: [
                    TextAlertAction(type: .defaultAction, title: presentationData.strings.Common_Cancel, action: {}),
                    TextAlertAction(type: .genericAction, title: presentationData.strings.nagramiXCallAction, action: { [weak self] in
                        self?.requestCall(peerId: peerId, isVideo: isVideo, completion: completion, skipNagramiXConfirmation: true)
                    }),
                ]
            ), on: .root)
            return
        }
        guard let callResult = self.sharedContext.callManager?.requestCall(context: self, peerId: peerId, isVideo: isVideo, endCurrentIfAny: false) else {
""",
        "Confirm native outgoing calls before starting them",
    )

    message_archive_overlay = overlay / "Sources" / "TelegramCore" / "NagramiXMessageArchive.swift"
    message_archive_target = source / "submodules" / "TelegramCore" / "Sources" / "Utils" / message_archive_overlay.name
    shutil.copy2(message_archive_overlay, message_archive_target)

    replace_unique(
        account_source,
        """    public let supplementary: Bool
    public let isSupportUser: Bool
    public let postbox: Postbox
    public let network: Network
""",
        """    public let supplementary: Bool
    public let isSupportUser: Bool
    public let postbox: Postbox
    public let nagramiXMessageArchive: NagramiXMessageArchive
    public let network: Network
""",
        "Account-owned NagramiX message archive",
    )
    replace_unique(
        account_source,
        """        self.networkArguments = networkArguments
        self.peerId = peerId
""" + "        \n" + """        self.auxiliaryMethods = auxiliaryMethods
""",
        """        self.networkArguments = networkArguments
        self.peerId = peerId
        self.nagramiXMessageArchive = NagramiXMessageArchive(postbox: postbox, accountPeerId: peerId, basePath: basePath)
""" + "        \n" + """        self.auxiliaryMethods = auxiliaryMethods
""",
        "Initialize the per-account local message archive",
    )

    state_management = source / "submodules" / "TelegramCore" / "Sources" / "State" / "AccountStateManagementUtils.swift"
    replace_unique(
        state_management,
        """                let _ = transaction.addMessages(messages, location: location)
                if case .UpperHistoryBlock = location {
""",
        """                let _ = transaction.addMessages(messages, location: location)
                if let messageArchive = NagramiXMessageArchive.forPostbox(postbox) {
                    for message in messages {
                        var archivePeers: [PeerId: Peer] = [:]
                        var archivePeerIds = Set<PeerId>([message.id.peerId])
                        if let authorId = message.authorId {
                            archivePeerIds.insert(authorId)
                        }
                        for media in message.media {
                            archivePeerIds.formUnion(media.peerIds)
                        }
                        for peerId in archivePeerIds {
                            if let peer = transaction.getPeer(peerId) {
                                archivePeers[peerId] = peer
                            }
                        }
                        messageArchive.captureIncoming(message, peers: archivePeers)
                    }
                }
                if case .UpperHistoryBlock = location {
""",
        "Capture incoming messages after native Postbox insertion",
    )
    replace_unique(
        state_management,
        """                    let peers: [PeerId:Peer] = previousMessage.peers.reduce([:], { current, value in
                        var current = current
                        current[value.0] = value.1
                        return current
                    })
""" + "                    \n" + """                    if previousMessage.text == message.text {
""",
        """                    let peers: [PeerId:Peer] = previousMessage.peers.reduce([:], { current, value in
                        var current = current
                        current[value.0] = value.1
                        return current
                    })
                    NagramiXMessageArchive.forPostbox(postbox)?.recordIncomingEdit(previousMessage: previousMessage, replacementMessage: message, peers: peers, receivedAt: Int32(CFAbsoluteTimeGetCurrent() + kCFAbsoluteTimeIntervalSince1970))
""" + "                    \n" + """                    if previousMessage.text == message.text {
""",
        "Store the previous received content before applying an edit",
    )
    replace_unique(
        state_management,
        """            case let .DeleteMessagesWithGlobalIds(ids):
                var resourceIds: [MediaResourceId] = []
""",
        """            case let .DeleteMessagesWithGlobalIds(ids):
                NagramiXMessageArchive.forPostbox(postbox)?.archiveServerDeletion(globalIds: ids, deletedAt: Int32(CFAbsoluteTimeGetCurrent() + kCFAbsoluteTimeIntervalSince1970))
                var resourceIds: [MediaResourceId] = []
""",
        "Archive non-channel server deletions before native removal",
    )
    replace_unique(
        state_management,
        """            case let .DeleteMessages(ids):
                _internal_deleteMessages(transaction: transaction, mediaBox: mediaBox, ids: ids, manualAddMessageThreadStatsDifference: { id, add, remove in
""",
        """            case let .DeleteMessages(ids):
                NagramiXMessageArchive.forPostbox(postbox)?.archiveServerDeletion(messageIds: ids, deletedAt: Int32(CFAbsoluteTimeGetCurrent() + kCFAbsoluteTimeIntervalSince1970))
                _internal_deleteMessages(transaction: transaction, mediaBox: mediaBox, ids: ids, manualAddMessageThreadStatsDifference: { id, add, remove in
""",
        "Archive channel server deletions before native removal",
    )

    interactive_delete = source / "submodules" / "TelegramCore" / "Sources" / "TelegramEngine" / "Messages" / "DeleteMessagesInteractively.swift"
    replace_unique(
        interactive_delete,
        """    _internal_deleteMessages(transaction: transaction, mediaBox: postbox.mediaBox, ids: messageIds.map(\\.messageId))
""",
        """    NagramiXMessageArchive.forPostbox(postbox)?.removeLocal(messageIds: messageIds.map(\\.messageId))
    _internal_deleteMessages(transaction: transaction, mediaBox: postbox.mediaBox, ids: messageIds.map(\\.messageId))
""",
        "Respect explicit local deletion of every expanded message/group id",
    )
    replace_unique(
        interactive_delete,
        """func _internal_clearHistoryInRangeInteractively(postbox: Postbox, peerId: PeerId, threadId: Int64?, minTimestamp: Int32, maxTimestamp: Int32, type: InteractiveHistoryClearingType) -> Signal<Void, NoError> {
    return postbox.transaction { transaction -> Void in
""",
        """func _internal_clearHistoryInRangeInteractively(postbox: Postbox, peerId: PeerId, threadId: Int64?, minTimestamp: Int32, maxTimestamp: Int32, type: InteractiveHistoryClearingType) -> Signal<Void, NoError> {
    NagramiXMessageArchive.forPostbox(postbox)?.clear(peerId: peerId)
    return postbox.transaction { transaction -> Void in
""",
        "Clear the local archive with an interactive range clear",
    )
    replace_unique(
        interactive_delete,
        """func _internal_clearHistoryInteractively(postbox: Postbox, peerId: PeerId, threadId: Int64?, type: InteractiveHistoryClearingType) -> Signal<Void, NoError> {
    return postbox.transaction { transaction -> Void in
""",
        """func _internal_clearHistoryInteractively(postbox: Postbox, peerId: PeerId, threadId: Int64?, type: InteractiveHistoryClearingType) -> Signal<Void, NoError> {
    NagramiXMessageArchive.forPostbox(postbox)?.clear(peerId: peerId)
    return postbox.transaction { transaction -> Void in
""",
        "Clear the local archive with an interactive history clear",
    )

    chat_history_list = source / "submodules" / "TelegramUI" / "Sources" / "ChatHistoryListNode.swift"
    replace_unique(
        chat_history_list,
        """        let previousView = self.previousView
        let automaticDownloadNetworkType = context.account.networkType
""",
        """        historyViewUpdate = combineLatest(historyViewUpdate, context.account.nagramiXMessageArchive.updates)
        |> map { update, _ in
            return update
        }

        let previousView = self.previousView
        let automaticDownloadNetworkType = context.account.networkType
""",
        "Refresh an open chat when its local archive changes",
    )

    chat_history_entries = source / "submodules" / "TelegramUI" / "Sources" / "ChatHistoryEntriesForView.swift"
    replace_unique(
        chat_history_entries,
        """    var count = 0
    loop: for entry in view.entries {
""",
        """    var sourceEntries = view.entries
    if let peerId = location.peerId {
        let existingIds = Set(sourceEntries.map { $0.message.id })
        let firstIndex = sourceEntries.first?.message.index
        let lastIndex = sourceEntries.last?.message.index
        let archivedMessages = context.account.nagramiXMessageArchive.deletedMessages(
            peerId: peerId,
            threadId: location.threadId,
            minIndex: view.earlierId == nil ? nil : firstIndex,
            maxIndex: view.laterId == nil ? nil : lastIndex
        )
        for message in archivedMessages where !existingIds.contains(message.id) {
            let withinEarlierBoundary = firstIndex.map { message.index >= $0 || view.earlierId == nil } ?? true
            let withinLaterBoundary = lastIndex.map { message.index <= $0 || view.laterId == nil } ?? true
            if withinEarlierBoundary && withinLaterBoundary {
                sourceEntries.append(MessageHistoryEntry(message: message, isRead: true, location: nil, monthLocation: nil, attributes: MutableMessageHistoryEntryAttributes(authorIsContact: false)))
            }
        }
        sourceEntries.sort(by: { $0.message.index < $1.message.index })
    }

    var count = 0
    loop: for entry in sourceEntries {
""",
        "Inject display-only deleted snapshots into the open history range",
    )

    text_bubble = source / "submodules" / "TelegramUI" / "Components" / "Chat" / "ChatMessageTextBubbleContentNode" / "Sources" / "ChatMessageTextBubbleContentNode.swift"
    replace_unique(
        text_bubble,
        "import TelegramCore\n",
        "import TelegramCore\nimport NagramiXCore\n",
        "Deleted-message marker localization import",
    )
    replace_unique(
        text_bubble,
        """                var customTruncationToken: ((UIFont, Bool) -> NSAttributedString?)?
""",
        """                if item.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {
                    let markedText = NSMutableAttributedString(attributedString: attributedText)
                    markedText.append(NSAttributedString(string: "\\n"))
                    if let image = generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Delete"), color: messageTheme.accentTextColor) {
                        let attachment = NSTextAttachment()
                        attachment.image = image
                        attachment.bounds = CGRect(x: 0.0, y: -2.0, width: 13.0, height: 13.0)
                        markedText.append(NSAttributedString(attachment: attachment))
                        markedText.append(NSAttributedString(string: " "))
                    }
                    markedText.append(NSAttributedString(string: item.presentationData.strings.nagramiXDeleted, font: Font.semibold(12.0), textColor: messageTheme.accentTextColor))
                    attributedText = markedText
                }

                var customTruncationToken: ((UIFont, Bool) -> NSAttributedString?)?
""",
        "Render a tinted trash icon and Deleted label in archived bubbles",
    )

    context_menus = source / "submodules" / "TelegramUI" / "Sources" / "ChatInterfaceStateContextMenus.swift"
    replace_unique(
        context_menus,
        "import NagramiXCore\n",
        "import NagramiXCore\nimport AlertUI\nimport TextFormat\n",
        "Edit-history alert imports",
    )
    replace_unique(
        context_menus,
        """        return ContextController.Items(content: .list(actions), tip: nil)
""",
        """        let currentEntities = message.textEntitiesAttribute?.entities ?? []
        let archivedAttribute = message.attributes.first(where: { $0 is NagramiXArchivedMessageAttribute }) as? NagramiXArchivedMessageAttribute
        let editHistory = context.account.nagramiXMessageArchive.revisions(messageId: message.id, currentText: message.text, currentEntities: currentEntities)
        let editHistoryAction: ContextMenuItem?
        if !editHistory.isEmpty {
            editHistoryAction = .action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXEditHistory, icon: { theme in
                return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Edit"), color: theme.actionSheet.primaryTextColor)
            }, action: { c, _ in
                c?.dismiss(completion: {
                    let presentationData = context.sharedContext.currentPresentationData.with { $0 }
                    let title = NSAttributedString(string: presentationData.strings.nagramiXEditHistory, font: Font.semibold(presentationData.listsFontSize.baseDisplaySize), textColor: presentationData.theme.actionSheet.primaryTextColor, paragraphAlignment: .center)
                    let body = NSMutableAttributedString()
                    let formatter = DateFormatter()
                    formatter.locale = Locale.current
                    formatter.dateStyle = .short
                    formatter.timeStyle = .short
                    for i in 0 ..< editHistory.count {
                        if i != 0 {
                            body.append(NSAttributedString(string: "\\n\\n"))
                        }
                        let date = formatter.string(from: Date(timeIntervalSince1970: TimeInterval(editHistory[i].timestamp)))
                        let label = i == 0 ? presentationData.strings.nagramiXOriginalVersion + " · " + date : (i == editHistory.count - 1 ? presentationData.strings.nagramiXCurrentVersion + " · " + date : date)
                        body.append(NSAttributedString(string: label + "\\n", font: Font.semibold(13.0), textColor: presentationData.theme.actionSheet.controlAccentColor))
                        body.append(stringWithAppliedEntities(editHistory[i].text, entities: editHistory[i].entities, baseColor: presentationData.theme.actionSheet.primaryTextColor, linkColor: presentationData.theme.actionSheet.controlAccentColor, baseFont: Font.regular(15.0), linkFont: Font.regular(15.0), boldFont: Font.semibold(15.0), italicFont: Font.italic(15.0), boldItalicFont: Font.semiboldItalic(15.0), fixedFont: Font.monospace(15.0), blockQuoteFont: Font.regular(15.0), message: nil))
                    }
                    controllerInteraction.presentController(richTextAlertController(context: context, title: title, text: body, actions: [TextAlertAction(type: .defaultAction, title: presentationData.strings.Common_OK, action: {})]), nil)
                })
            }))
            if let editHistoryAction {
                actions.append(editHistoryAction)
            }
        } else {
            editHistoryAction = nil
        }
        if archivedAttribute != nil {
            actions.removeAll()
            if !message.text.isEmpty {
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.Conversation_ContextMenuCopy, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Copy"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    storeMessageTextInPasteboard(message.text, entities: currentEntities)
                    f(.default)
                })))
            }
            if let editHistoryAction {
                actions.append(editHistoryAction)
            }
            actions.append(.separator)
            actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.Conversation_ContextMenuDelete, textColor: .destructive, icon: { theme in
                return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Delete"), color: theme.actionSheet.destructiveActionTextColor)
            }, action: { _, f in
                context.account.nagramiXMessageArchive.removeLocal(messageIds: [message.id])
                f(.dismissWithoutContent)
            })))
        }
        return ContextController.Items(content: .list(actions), tip: nil)
""",
        "Expose edit history and restrict archived messages to local-safe actions",
    )

    print("Applied isolated NagramiX next-version feature overlay")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telegram-dir", required=True, type=Path, help="Path to a clean Telegram-iOS 12.9.2 checkout")
    arguments = parser.parse_args()
    apply_features(arguments.telegram_dir.resolve())
