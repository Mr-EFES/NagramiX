// Native presentation and transport boundary for the settings caller.
struct TextAlertAction {
    enum Kind { case genericAction, defaultAction }
    let type: Kind
    let title: String
    let action: () -> Void
}
enum Layout { case vertical }
struct Dialog {
    let title: String?
    let text: String
    let actions: [TextAlertAction]
}
final class Context {
    let account = 1
    let sharedContext: Presentation
    init(strings: PresentationStrings) { sharedContext = Presentation(strings: strings) }
}
struct Presentation {
    let strings: PresentationStrings
    var currentPresentationData: Self { self }
    func with<T>(_ f: (Self) -> T) -> T { f(self) }
}
func textAlertController(context: Context, title: String?, text: String, actions: [TextAlertAction], actionLayout: Layout) -> Dialog {
    Dialog(title: title, text: text, actions: actions)
}
struct NoError {}
struct Signal<T, E> {
    let value: T
    func startStandalone(next: (T) -> Void) -> Bool { next(value); return true }
}
infix operator |> : AdditionPrecedence
func |> <T, U>(a: T, b: (T) -> U) -> U { b(a) }
func deliverOnMainQueue<T>(_ signal: T) -> T { signal }
final class NagramiXBulkReadBatch {
    static var retries = 0
    func send() -> Signal<NagramiXBulkReadBatch?, NoError> {
        Self.retries += 1
        return Signal(value: nil)
    }
}
var requests: [Bool] = []
func nagramiXBulkReadMessages(account: Int, onServer: Bool) -> Signal<NagramiXBulkReadBatch?, NoError> {
    requests.append(onServer)
    return Signal(value: onServer ? NagramiXBulkReadBatch() : nil)
}
@main struct BulkReadAlerts {
    static func main() {
        let context = Context(strings: PresentationStrings(language: "ru", dictionary: catalog))
        var dialog: Dialog?
        let presentControllerImpl: ((Dialog) -> Void)? = { dialog = $0 }
        // PRODUCTION_CALLBACKS
        show(false)
        precondition(dialog!.title == "Прочитать локально?" && dialog!.actions.count == 2)
        dialog!.actions[1].action()
        precondition(requests.isEmpty)
        show(false)
        dialog!.actions[0].action()
        precondition(requests == [false])
        show(true)
        precondition(dialog!.title == "Отправить все прочтения?" && dialog!.text.contains("NagramiX"))
        dialog!.actions[0].action()
        precondition(requests == [false, true] && dialog!.text == "Не все отметки отправлены")
        dialog!.actions[0].action()
        precondition(NagramiXBulkReadBatch.retries == 1 && requests == [false, true])
        print("PASS real settings callbacks and Russian getters, cancellation, confirm and retry")
    }
}
