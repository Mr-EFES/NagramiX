import Foundation

private var checks = 0
private func expect(_ value: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    if !value() {
        print("FAIL: \(label)")
        exit(1)
    }
}

private final class SystemIconBoundary {
    var name: String?
    var supported = true
    var declared = NagramiXAppIconController.alternateNames
    var calls: [String?] = []
    var completions: [(Bool) -> Void] = []
    var mainActions: [() -> Void] = []
    var deferMain = false

    func controller(_ defaults: UserDefaults) -> NagramiXAppIconController {
        return NagramiXAppIconController(defaults: defaults,
            canChange: { self.supported }, declaredNames: { self.declared },
            currentName: { self.name }, apply: { name, done in
                self.calls.append(name)
                self.completions.append(done)
            }, performOnMain: { action in
                if self.deferMain { self.mainActions.append(action) } else { action() }
            })
    }
    func finish(_ index: Int, success: Bool, applied: String?) {
        self.name = applied
        self.completions[index](success)
    }
    func flush() {
        let actions = self.mainActions
        self.mainActions.removeAll()
        actions.forEach { $0() }
    }
}

@main struct AppIconTests {
    static func main() {
        let defaults = UserDefaults.standard
        let key = NagramiXAppIconController.preferenceKey
        let args = CommandLine.arguments
        if args.count > 1 {
            switch args[1] {
            case "fresh":
                expect(defaults.object(forKey: key) == nil, "fresh install has no forced choice")
                let os = SystemIconBoundary()
                let controller = os.controller(defaults)
                controller.restoreIfNeeded()
                expect(os.calls.isEmpty, "fresh launch never changes icon")
            case "write":
                let os = SystemIconBoundary(), controller = os.controller(defaults)
                let selected = args[2] == "NagramiX1" ? nil : args[2]
                os.name = selected == nil ? "NagramiX2" : nil
                controller.request(selected) { expect($0, "cold writer confirmed") }
                os.finish(0, success: true, applied: selected)
                expect(defaults.string(forKey: key) == args[2], "confirmed choice persisted")
                // corelibs Foundation does not have Darwin's cfprefsd service;
                // flush only at this command-line process-exit test boundary.
                _ = defaults.synchronize()
            case "read":
                expect(defaults.string(forKey: key) == args[2], "choice survives new process")
                let os = SystemIconBoundary(), controller = os.controller(defaults)
                let selected = args[2] == "NagramiX1" ? nil : args[2]
                os.name = selected == nil ? "NagramiX3" : nil
                controller.restoreIfNeeded()
                expect(os.calls.count == 1 && os.calls[0] == selected, "cold restore targets saved choice")
                os.finish(0, success: true, applied: selected)
                controller.restoreIfNeeded()
                expect(os.calls.count == 1, "restore idempotent after system alert")
            default: exit(2)
            }
            print("PASS \(checks) cold icon checks")
            return
        }

        func reset(_ saved: String? = nil) {
            defaults.removeObject(forKey: key)
            if let saved { defaults.set(saved, forKey: key) }
        }
        for name in [NagramiXAppIconController.primaryName] + NagramiXAppIconController.alternateNames.sorted() {
            reset("NagramiX4")
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            let target = name == "NagramiX1" ? nil : name
            os.name = target == nil ? "NagramiX2" : nil
            var results: [Bool] = []
            controller.request(target) { results.append($0) }
            expect(os.calls.count == 1 && os.calls[0] == target, "all eight variants map to native names")
            expect(results.isEmpty && defaults.string(forKey: key) == "NagramiX4", "no optimistic persistence")
            os.finish(0, success: true, applied: target)
            expect(results == [true] && defaults.string(forKey: key) == name, "commit only native confirmation")
            os.finish(0, success: false, applied: target)
            expect(results == [true], "duplicate callback ignored")
            controller.request(target) { results.append($0) }
            expect(os.calls.count == 1 && results == [true, true], "same icon is harmless without second system prompt")
        }
        for success in [false, true] {
            reset("NagramiX3")
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            os.name = "NagramiX3"
            var result: Bool?
            controller.request("NagramiX6") { result = $0 }
            os.finish(0, success: success, applied: "NagramiX3")
            expect(result == false && defaults.string(forKey: key) == "NagramiX3", "error or unconfirmed success cannot overwrite selection")
            controller.request("NagramiX6") { result = $0 }
            os.finish(1, success: true, applied: "NagramiX6")
            expect(result == true, "manual retry works after failure")
        }
        reset("NagramiX2")
        do {
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            var first: Bool?, second: Bool?
            controller.request("NagramiX5") { first = $0 }
            controller.request("NagramiX7") { second = $0 }
            expect(first == nil && second == false && os.calls.count == 1, "overlapping native changes serialized")
            controller.restoreIfNeeded()
            expect(os.calls.count == 1, "manual selection excludes restore race")
            os.finish(0, success: true, applied: "NagramiX5")
            expect(first == true && defaults.string(forKey: key) == "NagramiX5", "in-flight result preserved")
        }
        for target in ["BlueIcon", "../../unknown", "NagramiX9", "NagramiX1"] {
            reset("NagramiX3")
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            controller.request(target) { expect(!$0, "invalid native name rejected") }
            expect(os.calls.isEmpty && defaults.string(forKey: key) == "NagramiX3", "invalid name has no system or settings mutation")
        }
        for missing in [false, true] {
            reset("NagramiX5")
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            if missing { os.declared.remove("NagramiX6") } else { os.supported = false }
            controller.request("NagramiX6") { expect(!$0, "unsupported or stripped icon rejected") }
            expect(os.calls.isEmpty && defaults.string(forKey: key) == "NagramiX5", "signer metadata failure retains saved choice")
        }
        reset("NagramiX8")
        do {
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            controller.restoreIfNeeded()
            expect(os.calls == ["NagramiX8"], "restore after OS reset")
            controller.restoreIfNeeded()
            expect(os.calls.count == 1, "no second restore in flight")
            os.finish(0, success: false, applied: nil)
            for _ in 0..<10 { controller.restoreIfNeeded() }
            expect(os.calls.count == 1 && defaults.string(forKey: key) == "NagramiX8", "failed restore bounded and preference retained")
            let nextLaunch = os.controller(defaults)
            nextLaunch.restoreIfNeeded()
            expect(os.calls.count == 2, "later launch may recover failed restore")
            os.finish(1, success: true, applied: "NagramiX8")
        }
        reset("NagramiX2")
        do {
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            os.name = "NagramiX2"
            controller.restoreIfNeeded()
            expect(os.calls.isEmpty, "correct existing OS choice never reprompted")
        }
        reset()
        do {
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            os.name = "NagramiX7"
            controller.restoreIfNeeded()
            expect(os.calls.isEmpty && defaults.string(forKey: key) == "NagramiX7", "upgrade adopts system icon without reset")
        }
        reset("removed-or-corrupt")
        do {
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            os.name = "NagramiX4"
            controller.restoreIfNeeded()
            expect(os.calls.isEmpty && os.name == "NagramiX4", "unknown preference never resets system icon")
        }
        reset()
        do {
            let os = SystemIconBoundary(), controller = os.controller(defaults)
            os.deferMain = true
            var result: Bool?
            controller.request("NagramiX2") { result = $0 }
            expect(os.calls.isEmpty, "request marshaled onto main boundary")
            os.flush()
            expect(os.calls.count == 1, "native request executed on main boundary")
            os.finish(0, success: true, applied: "NagramiX2")
            expect(result == nil && defaults.object(forKey: key) == nil, "background native callback cannot mutate UI or preference")
            os.flush()
            expect(result == true && defaults.string(forKey: key) == "NagramiX2", "callback marshaled and committed on main boundary")
        }
        reset()
        runIconPickerTests()
        print("PASS \(checks) app icon lifecycle checks; UIKit/SpringBoard are boundaries")
    }
}

// The action below is extracted from ThemeSettingsController by the validator.
func runIconPickerTests() {
    let context = IconContext()
    let bindings = context.sharedContext.applicationBindings
    let currentAppIconName = IconPromise()
    currentAppIconName.set("NagramiX1")
    var nagramiXIsChangingAppIcon = false
    var alerts = 0
    let presentControllerImpl: ((Int, Int?) -> Void)? = { _, _ in alerts += 1 }
    let icon = PresentationAppIcon(name: "NagramiX2", isDefault: false)
    func tap() {
        NAGRAMIX_NATIVE_PICKER_ACTION
    }
    tap()
    expect(currentAppIconName.name == "NagramiX1" && nagramiXIsChangingAppIcon, "picker waits for native result")
    tap()
    expect(bindings.calls == 1, "picker ignores repeated taps while changing")
    bindings.done?(false)
    Queue.mainQueue().flush()
    expect(currentAppIconName.name == "NagramiX1" && !nagramiXIsChangingAppIcon && alerts == 1, "failed choice shows actual icon and visible error")
    tap()
    bindings.current = "NagramiX2"
    bindings.done?(true)
    Queue.mainQueue().flush()
    expect(currentAppIconName.name == "NagramiX2" && alerts == 1, "successful choice shows confirmed system icon")
}
