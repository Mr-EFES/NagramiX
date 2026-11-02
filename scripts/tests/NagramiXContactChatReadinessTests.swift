import Foundation

// Promise, Signal, then, mapToSignal and all 26-way combineLatest operations
// come from the audited upstream SwiftSignalKit, not a replacement signal model.
// OS contacts and the other 25 history inputs are deterministic boundaries.
struct DeviceContactNormalizedPhoneNumber: Hashable { let rawValue: String }
typealias ImportableDeviceContactData = Int
typealias ContactSnapshot = [DeviceContactNormalizedPhoneNumber: ImportableDeviceContactData]
typealias ContactSignal = Signal<ContactSnapshot, NoError>
struct ContactsSettings: Equatable {
    let synchronizeContacts: Bool
    static let defaultSettings = ContactsSettings(synchronizeContacts: true)
}
struct TestPreferences: Equatable {
    let value: ContactsSettings
    func get(_ type: ContactsSettings.Type) -> ContactsSettings { self.value }
}
func cleanPhoneNumber(_ value: String) -> String { value }
final class TestAccount { let importableContacts = Promise<ContactSnapshot>() }
final class TestSharedContext { let deviceContactPhoneNumbers = Promise<Set<String>>(Set()) }
final class TestContext {
    let account = TestAccount()
    let sharedContext = TestSharedContext()
}
final class TestBinding { let context = TestContext() }

@main enum ContactChatReadinessTests {
    static var checks = 0
    static func expect(_ condition: @autoclosure () -> Bool, _ text: String) {
        precondition(condition(), text)
        self.checks += 1
    }
    static func contacts(_ values: String...) -> ContactSnapshot {
        Dictionary(uniqueKeysWithValues: values.enumerated().map {
            (DeviceContactNormalizedPhoneNumber(rawValue: $0.element), $0.offset)
        })
    }
    static func main() {
        // Reproduce exactly the user's failure and the workaround in build112.
        do {
            let binding = TestBinding()
            let permissionPendingBook = ValuePromise<ContactSnapshot>()
            let settings = ValuePromise<TestPreferences?>(TestPreferences(value: .defaultSettings))
            binding.bindBefore(productionImportable(settings: settings.get(), book: permissionPendingBook.get()))
            var history: [Set<String>] = []
            let d = observeHistory(binding.context) { history.append($0) }
            expect(history.isEmpty, "build112 must reproduce the missing first history transition")
            settings.set(TestPreferences(value: ContactsSettings(synchronizeContacts: false)))
            expect(history == [Set()], "cancelling sync must reproduce the user's recovery")
            d.dispose()
        }
        do {
            let binding = TestBinding()
            binding.bindAfter(productionImportable(settings: .single(nil), book: .never()))
            var history: [Set<String>] = []
            let d = observeHistory(binding.context) { history.append($0) }
            expect(history == [Set()], "fresh installation without saved sync settings blocked chat")
            d.dispose()
        }
        // Seed the optional input, not the actual history/readiness gate.
        do {
            let binding = TestBinding(); binding.bindAfter(.never())
            let realHistoryPending = ValuePromise<Bool>()
            var history: [Set<String>] = []
            let d = observeHistory(binding.context, history: realHistoryPending.get()) { history.append($0) }
            expect(history.isEmpty, "contact fallback bypassed pending native history")
            realHistoryPending.set(true)
            expect(history == [Set()], "ready native history still waited for permission")
            d.dispose()
        }
        // The same native history gate is shared by peers, groups and channels.
        for chat in ["private", "group", "channel", "saved", "forum"] {
            let binding = TestBinding()
            let book = ValuePromise<ContactSnapshot>()
            let settings = ValuePromise<TestPreferences?>(TestPreferences(value: .defaultSettings))
            binding.bindAfter(productionImportable(settings: settings.get(), book: book.get()))
            var history: [Set<String>] = []
            var imports: [ContactSnapshot] = []
            let d = observeHistory(binding.context) { history.append($0) }
            let importD = binding.context.account.importableContacts.get().start(next: { imports.append($0) })
            expect(history == [Set()], "undecided permission blocks " + chat)
            expect(imports.isEmpty, "display fallback must not start address-book import")
            settings.set(TestPreferences(value: ContactsSettings(synchronizeContacts: false)))
            expect(history == [Set()], "sync OFF must leave an already opened chat usable")
            expect(imports.count == 1 && imports[0].isEmpty, "native sync OFF behavior changed")
            book.set(contacts("15550001"))
            expect(history == [Set()] && imports.count == 1, "sync OFF leaked contact data")
            settings.set(TestPreferences(value: .defaultSettings))
            expect(history.last == Set(["15550001"]), "later permitted source did not update history")
            expect(imports.last == contacts("15550001"), "later native import was lost")
            book.set(contacts("15550002", "15550003"))
            expect(history.last == Set(["15550002", "15550003"]), "live address-book update lost")
            book.set([:])
            expect(history.last?.isEmpty == true, "denial/revocation's empty snapshot was lost")
            d.dispose(); importD.dispose()
        }
        // Immediate allowed/denied sources, no contacts manager and completed
        // sources must not erase readiness or leak a synthetic import event.
        for snapshot in [ContactSnapshot(), contacts("15550100")] {
            let binding = TestBinding()
            binding.bindAfter(.single(snapshot))
            var history: [Set<String>] = []
            var imports: [ContactSnapshot] = []
            let d = observeHistory(binding.context) { history.append($0) }
            let i = binding.context.account.importableContacts.get().start(next: { imports.append($0) })
            expect(history == [Set(snapshot.keys.map(\.rawValue))], "cached native snapshot changed")
            expect(imports == [snapshot], "display seed reached import pipeline")
            d.dispose(); i.dispose()
        }
        for source in [ContactSignal.never(), ContactSignal.complete()] {
            let binding = TestBinding(); binding.bindAfter(source)
            var history: [Set<String>] = []
            let d = observeHistory(binding.context) { history.append($0) }
            expect(history == [Set()], "silent/completed optional stream blocked chat")
            d.dispose()
        }
        // A persisted sync OFF stays OFF; no unsolicited contacts are exposed.
        do {
            let binding = TestBinding()
            let settings = ValuePromise<TestPreferences?>(TestPreferences(value: ContactsSettings(synchronizeContacts: false)))
            let book = ValuePromise(contacts("15550200"))
            binding.bindAfter(productionImportable(settings: settings.get(), book: book.get()))
            var history: [Set<String>] = []
            let d = observeHistory(binding.context) { history.append($0) }
            expect(history == [Set()], "saved sync OFF was reset")
            d.dispose()
        }
        // Rebinding must clear the former account's phone numbers, retain
        // readiness while the next source is pending, and dispose old sources.
        do {
            let binding = TestBinding()
            let oldBook = ValuePromise(contacts("15550300"))
            binding.bindAfter(oldBook.get())
            var history: [Set<String>] = []
            let d = observeHistory(binding.context) { history.append($0) }
            expect(history.last == Set(["15550300"]), "first account snapshot missing")
            binding.bindAfter(.never())
            expect(history.last == Set(), "new pending account retained private phone data")
            let count = history.count
            oldBook.set(contacts("15550301"))
            expect(history.count == count, "disposed old account still updates chat")
            d.dispose()
        }
        // Repeated subscribers after cold bootstrap get the cached fallback.
        do {
            let binding = TestBinding(); binding.bindAfter(.never())
            for _ in 0..<100 {
                var ready = 0
                let d = observeHistory(binding.context) { _ in ready += 1 }
                expect(ready == 1, "subsequent chat failed to receive cached snapshot")
                d.dispose()
            }
        }
        print("PASS: \(checks) real SwiftSignalKit chat-readiness/import/consent checks; old112 stall and sync-cancel workaround reproduced")
    }
}
