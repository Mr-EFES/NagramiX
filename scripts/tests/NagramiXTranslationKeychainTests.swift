import Foundation

@main struct TranslationKeychainTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ message: String) {
            checks += 1
            if !value() { FileHandle.standardError.write(Data(("FAIL: " + message + "\n").utf8)); exit(1) }
        }
        check(NagramiXTranslationKeys.read(.apple) == nil, "Apple never reads an API key")
        for provider in NagramiXTranslationProvider.allCases.filter({ $0 != .apple }) {
            check(NagramiXTranslationKeys.read(provider) == nil, "absent key has no shared/default credential")
            let value = NagramiXTranslationCredential(key: "test-owned-" + provider.rawValue, folder: "test-folder")
            check(NagramiXTranslationKeys.save(value, provider: provider), "actual add succeeds")
            check(KeychainBoundary.lastQuery[kSecAttrSynchronizable] as? Bool == false, "keys never sync via this query")
            check(KeychainBoundary.lastQuery[kSecAttrAccessible] as? String == kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly, "device-only accessibility used on add")
            check(NagramiXTranslationKeys.read(provider)?.key == value.key, "provider reads its own exact saved key")
            let next = NagramiXTranslationCredential(key: value.key + "-new", folder: "another-folder")
            check(NagramiXTranslationKeys.save(next, provider: provider), "actual update succeeds")
            check(NagramiXTranslationKeys.read(provider)?.key == next.key, "replacement key wins over previous value")
        }
        KeychainBoundary.denied = true
        check(!NagramiXTranslationKeys.save(.init(key: "bad", folder: ""), provider: .google), "write failure not reported as success")
        check(!NagramiXTranslationKeys.save(nil, provider: .google), "delete failure not reported as success")
        check(NagramiXTranslationKeys.read(.google) == nil, "locked/error read has no fallback token")
        KeychainBoundary.denied = false
        check(NagramiXTranslationKeys.read(.google)?.key == "test-owned-google-new", "failed write/delete retain existing key")
        check(NagramiXTranslationKeys.save(nil, provider: .google) && NagramiXTranslationKeys.read(.google) == nil, "delete removes selected provider")
        check(NagramiXTranslationKeys.read(.deepseek)?.key == "test-owned-deepseek-new", "deleting Google does not touch DeepSeek")
        check(NagramiXTranslationKeys.save(nil, provider: .google), "deleting an absent key is idempotent")
        let defaults = UserDefaults.standard.dictionaryRepresentation().values.map { String(describing: $0) }.joined()
        check(!defaults.contains("test-owned-"), "secrets absent from UserDefaults")
        print("PASS: \(checks) actual Keychain query/add/update/delete/failure/isolation checks; Security.framework is a boundary")
    }
}
