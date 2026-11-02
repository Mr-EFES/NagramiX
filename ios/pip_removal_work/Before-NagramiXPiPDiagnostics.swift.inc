import Foundation
import TelegramCore

// Explicit PiP attempts only. No message IDs, filenames, URLs or video content.
// The user can copy this bounded trace from an unsuccessful request's alert.
enum NagramiXPiPDiagnostics {
    private static let key = "nagramix.debug.pip.lastAttempt"
    private static let lock = NSLock()

    static func begin(_ origin: String) {
        self.lock.lock()
        UserDefaults.standard.set(["request=" + origin], forKey: self.key)
        self.lock.unlock()
        Logger.shared.log("NagramiXPiP", "request=" + origin)
    }
    static func record(_ stage: String) {
        self.lock.lock()
        var events = UserDefaults.standard.stringArray(forKey: self.key) ?? []
        events.append(String(stage.prefix(160)))
        UserDefaults.standard.set(Array(events.suffix(32)), forKey: self.key)
        self.lock.unlock()
        Logger.shared.log("NagramiXPiP", stage)
    }
    static var report: String {
        self.lock.lock()
        let events = UserDefaults.standard.stringArray(forKey: self.key) ?? []
        self.lock.unlock()
        let info = Bundle.main.infoDictionary ?? [:]
        let version = info["CFBundleShortVersionString"] as? String ?? "?"
        let build = info["CFBundleVersion"] as? String ?? "?"
        return "NagramiX \(version) (\(build)) PiP\n" + events.joined(separator: "\n")
    }
}
