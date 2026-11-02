import Foundation

// UIApplication owns the applied icon. Keep a separate, last-confirmed choice
// only so an installation/update that resets SpringBoard can be recovered.
// All state and UIKit callbacks are serialized by performOnMain.
final class NagramiXAppIconController {
    static let preferenceKey = "nagramix.appearance.appIcon"
    static let primaryName = "NagramiX1"
    static let alternateNames = Set((2...8).map { "NagramiX\($0)" })

    private let defaults: UserDefaults
    private let canChange: () -> Bool
    private let declaredNames: () -> Set<String>
    private let currentName: () -> String?
    private let apply: (String?, @escaping (Bool) -> Void) -> Void
    private let performOnMain: (@escaping () -> Void) -> Void
    private var inFlight: UUID?
    private var restoreAttempted = false

    init(defaults: UserDefaults, canChange: @escaping () -> Bool,
         declaredNames: @escaping () -> Set<String>, currentName: @escaping () -> String?,
         apply: @escaping (String?, @escaping (Bool) -> Void) -> Void,
         performOnMain: @escaping (@escaping () -> Void) -> Void) {
        self.defaults = defaults
        self.canChange = canChange
        self.declaredNames = declaredNames
        self.currentName = currentName
        self.apply = apply
        self.performOnMain = performOnMain
    }

    func request(_ name: String?, completion: @escaping (Bool) -> Void) {
        self.performOnMain { [weak self] in
            guard let self else {
                completion(false)
                return
            }
            // A manual choice must never race a foreground restore of an older
            // choice, even when this particular change is refused by iOS.
            self.restoreAttempted = true
            self.requestOnMain(name, completion: completion)
        }
    }

    func restoreIfNeeded() {
        self.performOnMain { [weak self] in
            guard let self, !self.restoreAttempted, self.inFlight == nil,
                  self.canChange() else {
                return
            }
            self.restoreAttempted = true
            guard let saved = self.defaults.string(forKey: Self.preferenceKey) else {
                // Upgrade from a release with no preference: adopt the OS
                // selection instead of resetting an existing alternate icon.
                if let current = self.currentName(), Self.alternateNames.contains(current),
                   self.declaredNames().contains(current) {
                    self.defaults.set(current, forKey: Self.preferenceKey)
                }
                return
            }
            guard saved == Self.primaryName || Self.alternateNames.contains(saved) else {
                return
            }
            let target = saved == Self.primaryName ? nil : saved
            // At most one restore per process. In particular, the native icon
            // confirmation's active/inactive notifications cannot cause a loop.
            self.requestOnMain(target, completion: { _ in })
        }
    }

    private func requestOnMain(_ name: String?, completion: @escaping (Bool) -> Void) {
        guard self.inFlight == nil, self.canChange() else {
            completion(false)
            return
        }
        if let name, !Self.alternateNames.contains(name) || !self.declaredNames().contains(name) {
            completion(false)
            return
        }
        if self.currentName() == name {
            self.defaults.set(name ?? Self.primaryName, forKey: Self.preferenceKey)
            completion(true)
            return
        }
        let token = UUID()
        self.inFlight = token
        self.apply(name) { [weak self] succeeded in
            guard let self else {
                completion(false)
                return
            }
            self.performOnMain { [weak self] in
                guard let self, self.inFlight == token else {
                    return
                }
                let confirmed = succeeded && self.currentName() == name
                if confirmed {
                    self.defaults.set(name ?? Self.primaryName, forKey: Self.preferenceKey)
                }
                self.inFlight = nil
                completion(confirmed)
            }
        }
    }
}
