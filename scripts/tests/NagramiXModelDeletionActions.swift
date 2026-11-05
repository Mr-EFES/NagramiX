// UIKit, model leases and the localization adapter are explicit boundaries.
// The complete production swipe-action method is inserted into Controller.
struct IndexPath { let section: Int; let row: Int }
final class UITableView {}
final class UIContextualAction {
    enum Style { case destructive }
    let title: String
    let handler: (UIContextualAction, Int, @escaping (Bool) -> Void) -> Void
    init(style: Style, title: String, handler: @escaping (UIContextualAction, Int, @escaping (Bool) -> Void) -> Void) {
        self.title = title; self.handler = handler
    }
}
final class UISwipeActionsConfiguration {
    let actions: [UIContextualAction]
    init(actions: [UIContextualAction]) { self.actions = actions }
}
struct NagramiXWhisperModel {}
struct NagramiXVoskModel {
    let name: String
    static let all = [NagramiXVoskModel(name: "ru")]
}
final class NagramiXVoskModels {
    static let shared = NagramiXVoskModels()
    var result = false; var removals = 0; var cancellations = 0
    func remove(_ model: NagramiXVoskModel) -> Bool { removals += 1; return result }
    func cancel(_ model: NagramiXVoskModel) { cancellations += 1 }
}
final class NagramiXWhisperModels {
    static let shared = NagramiXWhisperModels()
    var result = false; var removals = 0; var present = true
    func remove(_ model: NagramiXWhisperModel) -> Bool { removals += 1; return result }
    func installed(_ model: NagramiXWhisperModel) -> Bool { present }
}
enum RowAction { case voskModel(String), model(NagramiXWhisperModel), other }
struct Row { let action: RowAction }
struct Strings {
    var language = "en"
    func nagramiXUILocalized(_ value: String) -> String { language + "|" + value }
}
struct PresentationData { var strings = Strings() }
var alerts: [String] = []
final class Controller {
    var sections: [(String, [Row])]
    var presentationData = PresentationData()
    init(_ action: RowAction) { sections = [("", [Row(action: action)])] }
    func alert(_ value: String) { alerts.append(value) }
    // ACTUAL_SWIPE_ACTIONS
}
var checkCount = 0
func require(_ value: @autoclosure () -> Bool, _ message: String) {
    checkCount += 1
    if !value() { fatalError("model deletion regression: " + message) }
}
@main enum ModelDeletionChecks {
    static func main() {
        for engine in ["vosk", "whisper"] {
            for success in [false, true] {
                for alive in [false, true] {
                    alerts = []
                    let vosk = NagramiXVoskModels.shared
                    let whisper = NagramiXWhisperModels.shared
                    vosk.result = success; vosk.removals = 0; vosk.cancellations = 0
                    whisper.result = success; whisper.removals = 0; whisper.present = true
                    var owner: Controller? = Controller(engine == "vosk" ? .voskModel("ru") : .model(NagramiXWhisperModel()))
                    let configuration = owner!.tableView(UITableView(), trailingSwipeActionsConfigurationForRowAt: IndexPath(section: 0, row: 0))!
                    require(configuration.actions.count == 1 && configuration.actions[0].title == "en|Удалить", "localized delete action")
                    owner!.presentationData.strings.language = "de"
                    weak var weakOwner = owner
                    if !alive { owner = nil; require(weakOwner == nil, "action must not retain screen") }
                    weakOwner = nil
                    let action = configuration.actions[0]
                    var completions: [Bool] = []
                    action.handler(action, 0) { completions.append($0) }
                    require(completions == [success], "complete exactly once, including closed screen")
                    require((engine == "vosk" ? vosk.removals : whisper.removals) == 1, "model removal still executes")
                    require(vosk.cancellations == (engine == "vosk" && !success ? 1 : 0), "Vosk cancellation preserved")
                    require(alerts.count == (alive && !success ? 1 : 0), "only visible failure alerts")
                    if alive && !success { require(alerts[0].hasPrefix("de|"), "alert uses current app language") }
                }
            }
        }
        let table = UITableView()
        let owner = Controller(.other)
        require(owner.tableView(table, trailingSwipeActionsConfigurationForRowAt: IndexPath(section: 1, row: 0)) == nil, "unknown section")
        require(owner.tableView(table, trailingSwipeActionsConfigurationForRowAt: IndexPath(section: 0, row: 1)) == nil, "unknown row")
        require(owner.tableView(table, trailingSwipeActionsConfigurationForRowAt: IndexPath(section: 0, row: 0)) == nil, "non-model row")
        owner.sections = [("", [Row(action: .voskModel("missing"))])]
        require(owner.tableView(table, trailingSwipeActionsConfigurationForRowAt: IndexPath(section: 0, row: 0)) == nil, "unknown Vosk model")
        owner.sections = [("", [Row(action: .model(NagramiXWhisperModel()))])]
        NagramiXWhisperModels.shared.present = false
        require(owner.tableView(table, trailingSwipeActionsConfigurationForRowAt: IndexPath(section: 0, row: 0)) == nil, "uninstalled Whisper model")
        print("PASS: \(checkCount) actual model-deletion callback checks")
    }
}
