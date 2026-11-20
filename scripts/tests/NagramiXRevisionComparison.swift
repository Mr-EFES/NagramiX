import Foundation

// COMPARISON

@main
enum RevisionComparisonTests {
    static func main() {
        func marked(_ older: String, _ newer: String, after: Bool) -> String {
            let text = (after ? newer : older) as NSString
            return NagramiXRevisionComparison.changedRanges(older: older, newer: newer, showingNewer: after)
                .map { text.substring(with: $0) }.joined()
        }
        func check(_ old: String, _ new: String, removed: String, inserted: String) {
            let actualRemoved = marked(old, new, after: false)
            precondition(actualRemoved == removed, "removed from [\(old)]: [\(actualRemoved)]")
            let actualInserted = marked(old, new, after: true)
            precondition(actualInserted == inserted, "inserted in [\(new)]: [\(actualInserted)]")
        }
        check("Как час чего не спишь?", "Как сам, чего не спишь?", removed: "час", inserted: "сам,")
        check("a x b y c", "a 1 b 2 c", removed: "xy", inserted: "12")
        check("same", "same", removed: "", inserted: "")
        check("🐱", "", removed: "🐱", inserted: "")
        check("", "e\u{301}👩🏽‍🏫", removed: "", inserted: "e\u{301}👩🏽‍🏫")
        check("你好吗", "你真好", removed: "吗", inserted: "真")
        check("🙂 A 👨‍👩‍👦", "🙂 B 👨‍👩‍👦", removed: "A", inserted: "B")
        check("A\nB", "A B", removed: "\n", inserted: " ")
        precondition(["go ", " go"].contains(marked("go go!", "go!", after: false)))
        precondition(marked("go go!", "go!", after: true).isEmpty)
        let repetitions = 2048
        check(String(repeating: "a ", count: repetitions), String(repeating: "b ", count: repetitions),
              removed: String(repeating: "a", count: repetitions), inserted: String(repeating: "b", count: repetitions))
        checkCardActions()
        print("PASS: revision comparison, newest-first ordering, per-revision export actions and export restrictions")
    }
}

// Only the integration boundaries are stand-ins. The validator inserts the app's
// cellForRowAt and snapshot functions verbatim, including all four tap handlers.
private struct NagramiXMessageRevision {
    let text: String
    let entities: [String]
}

private struct TextEntitiesMessageAttribute { let entities: [String] }
private struct NagramiXArchivedMessageAttribute {
    let deletedAt: Int
    let revisions: [String]
}

private struct EngineRawMessage {
    var text: String
    var media: [String] = []
    var attributes: [Any] = []
    func withUpdatedText(_ text: String) -> Self {
        var message = self
        message.text = text
        return message
    }
    func withUpdatedMedia(_ media: [String]) -> Self {
        var message = self
        message.media = media
        return message
    }
    func withUpdatedAttributes(_ attributes: [Any]) -> Self {
        var message = self
        message.attributes = attributes
        return message
    }
}

// SNAPSHOT

private struct IndexPath { let row: Int }
private class UITableViewCell {}
private final class UITableView {
    func dequeueReusableCell(withIdentifier: String, for: IndexPath) -> UITableViewCell { NagramiXEditHistoryCell() }
}
private final class NagramiXEditHistoryCell: UITableViewCell {
    var ordinal = 0
    var text = ""
    var neighborText: String?
    var actions: [() -> Void] = []
    func configure(revision: NagramiXMessageRevision, index: Int, count: Int, neighbor: NagramiXMessageRevision?, presentationData: PresentationData, canExport: Bool, canForward: Bool, canBroadcast: Bool, copy: @escaping () -> Void, forward: @escaping () -> Void, broadcast: @escaping () -> Void, share: @escaping () -> Void) {
        ordinal = index + 1
        text = revision.text
        neighborText = neighbor?.text
        actions = [copy, forward, broadcast, share]
    }
}
private struct PresentationData {
    struct Strings { let Conversation_MessageCopied = "Copied" }
    let strings = Strings()
}
private class Controller {}
private final class UndoOverlayController: Controller {
    enum Content { case copy(text: String) }
    init(presentationData: PresentationData, content: Content, elevatedLayout: Bool, animateInAsReplacement: Bool, action: (Bool) -> Bool) {}
    func dismissWithCommitActionAndReplacementAnimation() {}
}
private struct ShareControllerParams {
    enum Subject { case text(String) }
    let subject: Subject
    let externalShare: Bool
    let immediateExternalShare: Bool
}
private final class Context {
    var sharedText: String?
    var sharedContext: Context { self }
    func makeShareScreen(context: Context, params: ShareControllerParams) -> Controller {
        precondition(params.externalShare && params.immediateExternalShare)
        if case let .text(value) = params.subject { sharedText = value }
        return Controller()
    }
}
private final class History {
    enum Window { case root }
    enum Destination { case current, window(Window) }
    let message = EngineRawMessage(text: "live", media: ["live attachment"])
    let presentationData = PresentationData()
    let context = Context()
    var revisions: [NagramiXMessageRevision] = []
    var canExport = true
    var forwardRevision: ((EngineRawMessage) -> Void)?
    var broadcastRevision: (([EngineRawMessage]) -> Void)?
    var copied: NagramiXMessageRevision?
    var copyOverlay: UndoOverlayController?
    func present(_ controller: Controller, in destination: Destination) {}
    func storeMessageTextInPasteboard(_ text: String, entities: [String]) {
        copied = NagramiXMessageRevision(text: text, entities: entities)
    }
    // ROW
}

private func checkCardActions() {
    let history = History()
    let table = UITableView()
    let texts = ["A", "B", "A", "D", "E"]
    history.revisions = texts.enumerated().map { .init(text: $0.element, entities: [String($0.offset)]) }
    var forwarded: [EngineRawMessage] = []
    var broadcast: [[EngineRawMessage]] = []
    history.forwardRevision = { forwarded.append($0) }
    history.broadcastRevision = { broadcast.append($0) }
    let cells = texts.indices.map { history.tableView(table, cellForRowAt: IndexPath(row: $0)) as! NagramiXEditHistoryCell }
    precondition(cells.map(\.ordinal) == [5, 4, 3, 2, 1])
    precondition(cells.map(\.text) == texts.reversed())
    precondition(cells.map(\.neighborText) == ["D", "E", "D", "A", "B"])
    history.revisions.append(.init(text: "fresh edit", entities: []))
    for cell in cells {
        let entities = [String(cell.ordinal - 1)]
        cell.actions.forEach { $0() }
        precondition(history.copied?.text == cell.text && history.copied?.entities == entities)
        precondition(history.context.sharedText == cell.text && broadcast.last?.count == 1)
        for message in [forwarded.last!, broadcast.last!.first!] {
            precondition(message.text == cell.text && message.media.isEmpty)
            precondition((message.attributes.first as? TextEntitiesMessageAttribute)?.entities == entities)
            precondition(message.attributes.last is NagramiXArchivedMessageAttribute)
        }
    }
    history.canExport = false
    history.copied = nil
    history.context.sharedText = nil
    cells[0].actions.forEach { $0() }
    precondition(history.copied == nil && history.context.sharedText == nil)
    precondition(forwarded.count == 5 && broadcast.count == 5)
}
