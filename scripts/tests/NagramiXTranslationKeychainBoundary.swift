import Foundation

// Security.framework is an explicit boundary. This checks the actual query,
// update/add/delete and error paths, not the iPhone Keychain implementation.
typealias CFDictionary = [String:Any]
typealias CFTypeRef = Any
let kSecClass = "class", kSecClassGenericPassword = "generic", kSecAttrService = "service", kSecAttrAccount = "account"
let kSecAttrSynchronizable = "synchronizable", kSecReturnData = "returnData", kSecMatchLimit = "limit", kSecMatchLimitOne = "one"
let kSecValueData = "data", kSecAttrAccessible = "accessible", kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly = "local-after-first-unlock"
let errSecSuccess: Int32 = 0, errSecItemNotFound: Int32 = -25300, errSecDenied: Int32 = -1
enum KeychainBoundary {
    static var items: [String:Data] = [:]
    static var denied = false
    static var lastQuery: CFDictionary = [:]
    static var lastChanges: CFDictionary = [:]
    static func key(_ value: CFDictionary) -> String { "\(value[kSecAttrService] ?? ""):\(value[kSecAttrAccount] ?? "")" }
}
func SecItemCopyMatching(_ query: CFDictionary, _ result: UnsafeMutablePointer<CFTypeRef?>) -> Int32 {
    KeychainBoundary.lastQuery = query
    if KeychainBoundary.denied { return errSecDenied }
    guard let value = KeychainBoundary.items[KeychainBoundary.key(query)] else { return errSecItemNotFound }
    result.pointee = value; return errSecSuccess
}
func SecItemUpdate(_ query: CFDictionary, _ changes: CFDictionary) -> Int32 {
    KeychainBoundary.lastQuery = query; KeychainBoundary.lastChanges = changes
    if KeychainBoundary.denied { return errSecDenied }
    let key = KeychainBoundary.key(query)
    guard KeychainBoundary.items[key] != nil, let data = changes[kSecValueData] as? Data else { return errSecItemNotFound }
    KeychainBoundary.items[key] = data; return errSecSuccess
}
func SecItemAdd(_ query: CFDictionary, _ result: UnsafeMutablePointer<CFTypeRef?>?) -> Int32 {
    KeychainBoundary.lastQuery = query
    if KeychainBoundary.denied { return errSecDenied }
    guard let data = query[kSecValueData] as? Data else { return errSecDenied }
    KeychainBoundary.items[KeychainBoundary.key(query)] = data; return errSecSuccess
}
func SecItemDelete(_ query: CFDictionary) -> Int32 {
    KeychainBoundary.lastQuery = query
    if KeychainBoundary.denied { return errSecDenied }
    return KeychainBoundary.items.removeValue(forKey: KeychainBoundary.key(query)) == nil ? errSecItemNotFound : errSecSuccess
}
