@main enum ContactsDefaultDenialTests {
    static var checks = 0
    static func check(_ value: @autoclosure () -> Bool, _ text: String) { precondition(value(),text); checks += 1 }
    static func book() -> [String:DeviceContactBasicData] { ["local-id":DeviceContactBasicData(firstName:"Test",lastName:"Contact",phoneNumbers:[Phone(value:"15550001")])] }
    static func main() {
        for notice: Int32? in [nil,0,1,123456] {
            for contacts: Variation in [.default,.modal] {
                for order in [[PermissionKind.contacts,.notifications], [.siri,.contacts,.notifications], [.notifications,.contacts,.contacts]] {
                    let config = Config(order:order,contacts:contacts)
                    let result = productionRequests(config, saved:notice)
                    check(!result.0.contains(.contacts), "startup must not request the phone book, including experiment reorder/modal")
                    check(result.1 == (notice == 0 ? [] : [0]), "notice must get the native acknowledged value exactly once")
                    check(result.0.filter { $0 == .notifications }.count == 1, "other permission requests preserved")
                }
            }
        }
        // Build113's seed only unsticks rendering; the actual import producer
        // still waits for an OS decision. Reproduce both signals independently.
        do {
            let manager = Manager(); let binding = TestBinding()
            binding.bindPrevious(productionImportable(settings:.single(nil),book:manager.signal()))
            var history: [Set<String>] = [], imports: [ContactSnapshot] = []
            let hd = observeHistory(binding.context) { history.append($0) }
            let id = binding.context.account.importableContacts.get().start(next:{ imports.append($0) })
            manager.receivePrevious(.notDetermined)
            check(history == [Set()], "old display workaround reproduced")
            check(imports.isEmpty && !manager.accessInitialized, "old undecided manager remains pending rather than denied")
            hd.dispose(); id.dispose()
        }
        // Execute the actual manager's callback/updateAll/subscription methods,
        // native import selection and restored binding with a 26-way history.
        for initial in [AccessType.notDetermined,.denied,.limited] {
            for sync: Bool? in [nil,false,true] {
                for afterSubscription in [false,true] {
                    let manager = Manager(); let binding = TestBinding()
                    if !afterSubscription { manager.receive(initial) }
                    let prefs = sync.map { TestPreferences(value:ContactsSettings(synchronizeContacts:$0)) }
                    binding.bindCurrent(productionImportable(settings:.single(prefs),book:manager.signal()))
                    var history: [Set<String>] = [], imports: [ContactSnapshot] = []
                    let hd = observeHistory(binding.context) { history.append($0) }
                    let id = binding.context.account.importableContacts.get().start(next:{ imports.append($0) })
                    if afterSubscription { manager.receive(initial) }
                    check(manager.accessInitialized, "unrequested phone book completes native access initialization")
                    check(!history.isEmpty && history.last == Set(), "chat history must get a native empty phone-book snapshot")
                    check(!imports.isEmpty && imports.allSatisfy { $0.isEmpty }, "actual import producer has normal no-access data, not a display-only seed")
                    check(manager.dataContext == nil, "unavailable permission must not open iOS contact data")
                    check(CNContactStore.requests == 0, "cold startup must never call requestAccess")
                    hd.dispose(); id.dispose()
                }
            }
        }
        do {
            let manager = Manager(); manager.receive(.notDetermined)
            let binding = TestBinding(); binding.bindCurrent(productionImportable(settings:.single(nil),book:manager.signal()))
            let realHistory = ValuePromise<Bool>()
            var history: [Set<String>] = []
            let d = observeHistory(binding.context,history:realHistory.get()) { history.append($0) }
            check(history.isEmpty,"native contacts availability must not bypass a genuinely pending history")
            realHistory.set(true); check(history == [Set()],"native history opens after its own readiness")
            d.dispose()
        }
        for synchronize in [true,false] {
            DeviceAccess.reset(); CNContactStore.status = .notDetermined; CNContactStore.requests = 0
            let manager = Manager(); let binding = TestBinding()
            let permission = DeviceAccess.status().start(next:{ manager.receive($0) })
            binding.bindCurrent(productionImportable(settings:.single(TestPreferences(value:ContactsSettings(synchronizeContacts:synchronize))),book:manager.signal()))
            var history: [Set<String>] = [], imports: [ContactSnapshot] = []
            let hd = observeHistory(binding.context) { history.append($0) }
            let id = binding.context.account.importableContacts.get().start(next:{ imports.append($0) })
            var cache: [Bool?] = []; let cd = DeviceAccess.cached().start(next:{ cache.append($0) })
            check(cache.count == 1 && cache[0] == nil,"silent denial must not poison the actual OS authorization promise")
            check(CNContactStore.requests == 0 && manager.dataContext == nil,"no automatic prompt or book read")
            DeviceAccess.request { _ in }
            check(CNContactStore.requests == 1,"an explicit user action still requests iOS permission")
            check(manager.dataContext == nil,"unanswered prompt does not imply consent")
            CNContactStore.reply(true)
            check(cache.last! == true && manager.dataContext != nil,"real grant reaches native manager")
            manager.dataContext?.updated(book())
            if synchronize {
                check(history.last == Set(["15550001"]),"later granted contacts update display")
                check(imports.last?.keys.first?.rawValue == "15550001","later granted contacts reach native importer")
            } else {
                check(history.allSatisfy { $0.isEmpty } && imports.allSatisfy { $0.isEmpty },"saved synchronization OFF remains effective after a grant")
            }
            cd.dispose(); hd.dispose(); id.dispose(); permission.dispose()
        }
        do {
            DeviceAccess.reset(); CNContactStore.status = .notDetermined; CNContactStore.requests = 0
            let manager = Manager(); let status = DeviceAccess.status().start(next:{ manager.receive($0) })
            var values: [ContactSnapshot] = []; let d = manager.signal().start(next:{ values.append($0) })
            DeviceAccess.request { _ in }; CNContactStore.reply(false)
            check(values.count >= 2 && values.allSatisfy { $0.isEmpty },"explicit real denial continues normal empty phone-book mechanics")
            check(manager.dataContext == nil && manager.accessInitialized,"denial must not open the book or stall producers")
            status.dispose(); d.dispose()
        }
        do {
            DeviceAccess.reset(); CNContactStore.status = .authorized; CNContactStore.requests = 0
            let manager = Manager(); let d = DeviceAccess.status().start(next:{ manager.receive($0) })
            check(manager.dataContext != nil && CNContactStore.requests == 0,"existing permission is respected without reset or new prompt")
            d.dispose()
        }
        // The shared device manager can feed two accounts without persisting a
        // fake permission or resetting either account's sync preference.
        let manager = Manager(); manager.receive(.notDetermined)
        let first = TestBinding(), second = TestBinding()
        first.bindCurrent(productionImportable(settings:.single(nil),book:manager.signal()))
        second.bindCurrent(productionImportable(settings:.single(nil),book:manager.signal()))
        var a: [Set<String>] = [], b: [Set<String>] = []
        let da = observeHistory(first.context) { a.append($0) }, db = observeHistory(second.context) { b.append($0) }
        check(a == [Set()] && b == [Set()],"both accounts are ready without phone-book consent")
        da.dispose(); manager.receive(.allowed); manager.dataContext?.updated(book())
        check(a == [Set()] && b.last == Set(["15550001"]),"disposed account subscription does not disturb the current one")
        db.dispose()
        print("PASS: \(checks) real SwiftSignalKit/native contact denial and explicit grant checks")
    }
}
