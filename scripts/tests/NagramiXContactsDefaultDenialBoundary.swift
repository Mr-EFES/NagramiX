import Foundation

// Real SwiftSignalKit is compiled by the validator. Only OS contacts, UI,
// scheduling and Postbox preference values are boundaries in this test.
public final class Queue { func async(_ f: () -> Void) { f() } }
public func deliverOn<T,E>(_ queue: Queue) -> (Signal<T,E>) -> Signal<T,E> { { _ in fatalError("Unexpected native scheduling") } }
func deliverOnMainQueue<T,E>(_ source: Signal<T,E>) -> Signal<T,E> { source }
struct DeviceContactNormalizedPhoneNumber: Hashable { let rawValue: String }
typealias DeviceContactStableId = String
struct Phone: Equatable { let value: String }
struct DeviceContactBasicData: Equatable { let firstName: String; let lastName: String; let phoneNumbers: [Phone] }
struct ImportableDeviceContactData: Equatable { let firstName: String; let lastName: String; let localIdentifiers: [String] }
struct DeviceContactBasicDataWithReference { let stableId: String }
enum EnginePeer { typealias Id = Int }
func formatPhoneNumber(_ value: String) -> String { value }
func cleanPhoneNumber(_ value: String) -> String { value }
final class BasicDataForNormalizedNumberContext {
    var value: [(DeviceContactStableId, DeviceContactBasicData)] = []
    let subscribers = Bag<([(DeviceContactStableId, DeviceContactBasicData)]) -> Void>()
}
typealias ContactSnapshot = [DeviceContactNormalizedPhoneNumber: ImportableDeviceContactData]
typealias ContactSignal = Signal<ContactSnapshot, NoError>
struct ContactsSettings: Equatable { let synchronizeContacts: Bool; static let defaultSettings = Self(synchronizeContacts:true) }
struct TestPreferences { let value: ContactsSettings; func get(_ type: ContactsSettings.Type) -> ContactsSettings { value } }
final class TestAccount { let importableContacts = Promise<ContactSnapshot>() }
final class TestSharedContext { let deviceContactPhoneNumbers = Promise<Set<String>>(Set()) }
final class TestContext { let account = TestAccount(); let sharedContext = TestSharedContext() }
final class TestBinding { let context = TestContext() }
enum AccessType: Equatable { case notDetermined, allowed, denied, limited, unreachable }
enum CNAuthorizationStatus { case notDetermined, authorized, denied, restricted, limited }
final class CNContactStore {
    enum Entity { case contacts }
    static var status = CNAuthorizationStatus.notDetermined
    static var requests = 0
    static var pending: ((Bool, Int?) -> Void)? = nil
    static func authorizationStatus(for entity: Entity) -> CNAuthorizationStatus { status }
    func requestAccess(for entity: Entity, completionHandler: @escaping (Bool, Int?) -> Void) { Self.requests += 1; Self.pending = completionHandler }
    static func reply(_ allow: Bool) { status = allow ? .authorized : .denied; let callback = pending; pending = nil; callback?(allow,nil) }
}
final class DeviceContactDataModernContext {
    static var constructions = 0
    let updated: ([DeviceContactStableId:DeviceContactBasicData]) -> Void
    init(queue: Queue, accountManager: Int, updated: @escaping ([DeviceContactStableId:DeviceContactBasicData]) -> Void, appSpecificReferencesUpdated: @escaping ([EnginePeer.Id:DeviceContactBasicDataWithReference]) -> Void) {
        Self.constructions += 1; self.updated = updated
        updated([:]); appSpecificReferencesUpdated([:])
    }
    func personNameDisplayOrder() -> Int { 0 }
}
enum PermissionKind: CaseIterable, Equatable { case contacts, notifications, cellularData, siri }
enum PermissionStatus { case requestable, allowed, denied }
enum PermissionState {
    case contacts(PermissionStatus), notifications(PermissionStatus), cellularData(PermissionStatus), siri(PermissionStatus)
    var status: PermissionStatus { switch self { case let .contacts(s), let .notifications(s), let .cellularData(s), let .siri(s): return s } }
}
enum Variation { case `default`, modal }
struct Config { var order: [PermissionKind]; var contacts: Variation = .default; var notifications: Variation = .default }
struct SplitTest { let configuration: Config }
struct NoticeValue { let value: Int32? }
final class NoticeAccountManager { var writes: [Int32] = [] }
struct NoticeSharedContext { let accountManager = NoticeAccountManager() }
struct NoticeContext { let sharedContext = NoticeSharedContext() }
enum ApplicationSpecificNotice {
    static func getTimestampValue(_ value: Int32) -> Int32? { value }
    static func setPermissionWarning(accountManager: NoticeAccountManager, permission: PermissionKind, value: Int32) { precondition(permission == .contacts); accountManager.writes.append(value) }
}
