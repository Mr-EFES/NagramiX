import Foundation
import Security

enum NagramiXTranscriptionKeys {
    private static let serviceName = (Bundle.main.bundleIdentifier ?? "NagramiX") + ".transcription.keys"
    private static func query(_ provider: NagramiXTranscriptionProvider, service: String = NagramiXTranscriptionKeys.serviceName) -> [String: Any] {
        [kSecClass as String:kSecClassGenericPassword, kSecAttrService as String:service, kSecAttrAccount as String:provider.rawValue,
         kSecAttrSynchronizable as String:false]
    }
    static func read(_ provider: NagramiXTranscriptionProvider) -> String? {
        guard provider.cloud else { return nil }
        var query = self.query(provider); query[kSecReturnData as String] = true; query[kSecMatchLimit as String] = kSecMatchLimitOne
        var output: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &output) == errSecSuccess, let data = output as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    static func importTranslationKey(_ provider: NagramiXTranscriptionProvider) -> String? {
        guard provider == .gemini || provider == .chatgpt else { return nil }
        let service = (Bundle.main.bundleIdentifier ?? "NagramiX") + ".translation.keys"
        var query = self.query(provider, service: service); query[kSecReturnData as String] = true; query[kSecMatchLimit as String] = kSecMatchLimitOne
        var output: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &output) == errSecSuccess, let data = output as? Data,
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        return object["key"] as? String
    }
    static func save(_ key: String?, provider: NagramiXTranscriptionProvider) -> Bool {
        guard provider.cloud else { return false }
        let query = self.query(provider)
        if let key, !key.isEmpty {
            guard key.utf8.count <= 4096, !key.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else { return false }
            let changes: [String: Any] = [kSecValueData as String:Data(key.utf8), kSecAttrAccessible as String:kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]
            let status = SecItemUpdate(query as CFDictionary, changes as CFDictionary)
            if status == errSecItemNotFound {
                var item = query; changes.forEach { item[$0.key] = $0.value }
                guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { return false }
            } else if status != errSecSuccess { return false }
        } else {
            let status = SecItemDelete(query as CFDictionary)
            guard status == errSecSuccess || status == errSecItemNotFound else { return false }
        }
        NagramiXTranscriptionSettings.credentialsChanged(); return true
    }
}
