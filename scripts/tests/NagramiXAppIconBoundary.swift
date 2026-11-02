// Only Telegram UI / queue boundaries. The controller, picker action and
// UserDefaults persistence under test are actual production code/Foundation.
import Foundation

struct PresentationAppIcon {
    let name: String
    let isDefault: Bool
}
final class IconBindings {
    var current: String?
    var calls = 0
    var done: ((Bool) -> Void)?
    func getAlternateIconName() -> String? { return current }
    func getAvailableAlternateIcons() -> [PresentationAppIcon] {
        return (1...8).map { PresentationAppIcon(name: "NagramiX\($0)", isDefault: $0 == 1) }
    }
    func requestSetAlternateIconName(_ name: String?, _ completion: @escaping (Bool) -> Void) {
        calls += 1
        done = completion
    }
}
struct IconStrings {
    var nagramiXAppIconChangeFailed: String { "error" }
    var Common_OK: String { "OK" }
}
struct IconPresentationData { let strings = IconStrings() }
struct IconData {
    func with<T>(_ f: (IconPresentationData) -> T) -> T { f(IconPresentationData()) }
}
final class IconSharedContext {
    let applicationBindings = IconBindings()
    let currentPresentationData = IconData()
}
final class IconContext { let sharedContext = IconSharedContext() }
final class IconPromise {
    var name: String?
    func set(_ name: String?) { self.name = name }
}
struct TextAlertAction {
    enum Kind { case defaultAction }
    init(type: Kind, title: String, action: () -> Void) {}
}
func textAlertController(context: IconContext, title: String?, text: String, actions: [TextAlertAction]) -> Int { 1 }
final class Queue {
    private static let shared = Queue()
    private var actions: [() -> Void] = []
    static func mainQueue() -> Queue { shared }
    func async(_ action: @escaping () -> Void) { actions.append(action) }
    func flush() {
        let pending = actions
        actions.removeAll()
        pending.forEach { $0() }
    }
}
