private func checkLaunchStorage(_ directory: URL) throws {
    let files = FileManager.default
    let identifier = "com.nagramix.ios"
    let group = "group." + identifier
    let support = directory.appendingPathComponent("support")
    let shared = directory.appendingPathComponent("shared")
    try files.createDirectory(at: shared, withIntermediateDirectories: true)

    func resolve(_ url: URL?, _ support: URL, standalone: Bool = true) throws -> NagramiXLaunchStorage {
        return try NagramiXLaunchStorage.resolve(group: group, groupURL: url, standalone: standalone) { support }
    }

    let local = try resolve(nil, support)
    precondition(local.sharedGroup == nil && local.baseURL.path.hasPrefix(support.path + "/"))
    let root = URL(fileURLWithPath: rootPathForBasePath(local.baseURL.path))
    let sample = root.appendingPathComponent("existing-account")
    try Data([42]).write(to: sample)
    let fresh = try resolve(shared, directory.appendingPathComponent("fresh"))
    precondition(fresh.sharedGroup == nil)
    let native = try resolve(shared, support, standalone: false)
    precondition(native.baseURL == shared && native.sharedGroup == group)

    let sharedRoot = URL(fileURLWithPath: rootPathForBasePath(shared.path))
    try files.createDirectory(at: sharedRoot, withIntermediateDirectories: true)
    let retained = try resolve(shared, support)
    let content = try Data(contentsOf: sample)
    precondition(retained.baseURL == local.baseURL && content == Data([42]))
    func unexpectedGroupLookup() -> URL? { preconditionFailure("local storage probed an App Group") }
    _ = try NagramiXLaunchStorage.resolve(group: group, groupURL: unexpectedGroupLookup(), standalone: true) { support }
    let upgradeSupport = directory.appendingPathComponent("upgrade")
    let upgrade = try resolve(shared, upgradeSupport)
    precondition(upgrade.baseURL == shared && upgrade.sharedGroup == group)
    do {
        _ = try resolve(nil, upgradeSupport)
        preconditionFailure("lost entitlement silently changed an existing data domain")
    } catch let error as CocoaError {
        precondition(error.code == .fileReadNoPermission)
    }
    let recovered = try resolve(shared, upgradeSupport)
    precondition(recovered.baseURL == shared)
    let marker = support.appendingPathComponent("NagramiXStorage/container")
    try Data([0]).write(to: marker)
    do {
        _ = try resolve(shared, support)
        preconditionFailure("corrupt selection accepted")
    } catch let error as CocoaError {
        precondition(error.code == .fileReadCorruptFile)
    }

    let personal = PasscodeEnvironment()
    let privateGroup = "TESTTEAM." + identifier
    try personal.configure(PasscodeConfiguration(appGroupIdentifier: group, processRole: .mainApp, appOnlyStorage: true)) { privateGroup }
    let secrets = try personal.sharedAccessGroup()
    let biometrics = try personal.privateAccessGroup()
    precondition(secrets == privateGroup && biometrics == privateGroup)
    let standard = PasscodeEnvironment()
    try standard.configure(PasscodeConfiguration(appGroupIdentifier: group, processRole: .mainApp)) { privateGroup }
    let standardSecrets = try standard.sharedAccessGroup()
    precondition(standardSecrets == group)
    let prefix = "org.telegram.ton-wallet."
    let oldService = standard.storageKeychainService(prefix + "wallet")
    let privateService = personal.storageKeychainService(prefix + "wallet")
    precondition(oldService != privateService)
    precondition(!privateService.hasPrefix(standard.storageKeychainService(prefix)))
    precondition(!oldService.hasPrefix(personal.storageKeychainService(prefix)))
    precondition(privateService.hasPrefix(personal.storageKeychainService(prefix)))
    let unavailable = PasscodeEnvironment()
    try unavailable.configure(PasscodeConfiguration(appGroupIdentifier: group, processRole: .mainApp, appOnlyStorage: true)) { nil }
    do {
        _ = try unavailable.sharedAccessGroup()
        preconditionFailure("missing private Keychain group was accepted")
    } catch PasscodeError.unavailable { }
    do {
        try PasscodeEnvironment().configure(PasscodeConfiguration(appGroupIdentifier: group, processRole: .appExtension, appOnlyStorage: true))
        preconditionFailure("extension gained access to main app storage")
    } catch PasscodeError.unavailable { }
}

@main
private enum StandaloneLaunchStorageTests {
    static func main() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        try checkLaunchStorage(directory)
    }
}
