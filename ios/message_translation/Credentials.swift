import Foundation
import Security

enum NagramiXTranslationKeys {
    private static let service = (Bundle.main.bundleIdentifier ?? "NagramiX") + ".translation.keys"
    private static func query(_ provider: NagramiXTranslationProvider) -> [String: Any] {
        return [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: self.service,
                kSecAttrAccount as String: provider.rawValue, kSecAttrSynchronizable as String: false]
    }
    static func read(_ provider: NagramiXTranslationProvider) -> NagramiXTranslationCredential? {
        guard provider != .apple else { return nil }
        var query = self.query(provider)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess, let data = result as? Data else { return nil }
        return try? JSONDecoder().decode(NagramiXTranslationCredential.self, from: data)
    }
    static func save(_ value: NagramiXTranslationCredential?, provider: NagramiXTranslationProvider) -> Bool {
        guard provider != .apple else { return false }
        let query = self.query(provider)
        if let value {
            guard let data = try? JSONEncoder().encode(value) else { return false }
            let changes: [String: Any] = [kSecValueData as String: data,
                kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]
            let status = SecItemUpdate(query as CFDictionary, changes as CFDictionary)
            if status == errSecItemNotFound {
                var item = query
                changes.forEach { item[$0.key] = $0.value }
                guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { return false }
            } else if status != errSecSuccess { return false }
        } else {
            let status = SecItemDelete(query as CFDictionary)
            guard status == errSecSuccess || status == errSecItemNotFound else { return false }
        }
        NagramiXTranslationSettings.credentialsChanged()
        return true
    }
}
