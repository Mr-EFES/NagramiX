import Foundation
import TelegramCore
import SwiftSignalKit

public struct CallListSettings: Codable, Equatable {
    public var _showTab: Bool?
    private var hasUnifiedTabVisibility = false
    
    public static var defaultSettings: CallListSettings {
        return CallListSettings(showTab: nil)
    }
    
    public var showTab: Bool {
        get {
            if let value = self._showTab {
                return value
            } else {
                return true
            }
        } set {
            self._showTab = newValue
            self.hasUnifiedTabVisibility = true
        }
    }
    
    public init(showTab: Bool?) {
        self._showTab = showTab
        self.hasUnifiedTabVisibility = showTab != nil
    }

    public func migratingCallsTabVisibility(legacyHidden: Bool?) -> CallListSettings {
        guard !self.hasUnifiedTabVisibility else { return self }
        // Keep the previously displayed choice, then an explicit native preference.
        let visible = legacyHidden.map { !$0 } ?? self._showTab ?? false
        return self.withUpdatedShowTab(visible)
    }
    
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: StringCodingKey.self)

        self.hasUnifiedTabVisibility = try container.decodeIfPresent(Int32.self, forKey: "nagramiXUnifiedTab") == 1
        if let value = try container.decodeIfPresent(Int32.self, forKey: "showTab") {
            self._showTab = value != 0
        }
    }
    
    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: StringCodingKey.self)

        if self.hasUnifiedTabVisibility {
            try container.encode(Int32(1), forKey: "nagramiXUnifiedTab")
        }
        if let showTab = self._showTab {
            try container.encode((showTab ? 1 : 0) as Int32, forKey: "showTab")
        } else {
            try container.encodeNil(forKey: "showTab")
        }
    }
    
    public static func ==(lhs: CallListSettings, rhs: CallListSettings) -> Bool {
        return lhs._showTab == rhs._showTab && lhs.hasUnifiedTabVisibility == rhs.hasUnifiedTabVisibility
    }
    
    public func withUpdatedShowTab(_ showTab: Bool) -> CallListSettings {
        return CallListSettings(showTab: showTab)
    }
}

public func updateCallListSettingsInteractively(accountManager: AccountManager<TelegramAccountManagerTypes>, _ f: @escaping (CallListSettings) -> CallListSettings) -> Signal<Void, NoError> {
    return accountManager.transaction { transaction -> Void in
        transaction.updateSharedData(ApplicationSpecificSharedDataKeys.callListSettings, { entry in
            let currentSettings: CallListSettings
            if let entry = entry?.get(CallListSettings.self) {
                currentSettings = entry
            } else {
                currentSettings = CallListSettings.defaultSettings
            }
            return SharedPreferencesEntry(f(currentSettings))
        })
    }
}
