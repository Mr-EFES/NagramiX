import Foundation

// UIKit/component/document boundaries only. Production routing, mode changes,
// footer geometry and the native structural select-all facade are extracted.
final class EmptyInputView: UIView {}
struct ExpandedState {
    var hasSelection = false, code = false, spoiler = false, isPullQuote = false
}
struct TextBlock { var text: String }
enum DocumentBlock {
    case paragraph(TextBlock), code(TextBlock), pullQuote(TextBlock)
    case media, table, blockQuote, details, buttonRow
}
struct ExpandedDocument { var blocks: [DocumentBlock] = [] }
final class CanvasBoundary {
    var documentSizeValue = 0
    var selected: (Int, Int)?
    func setSelectedGlobalRange(from: Int, to: Int) { self.selected = (from, to) }
}
final class RichEditorBoundary {
    let canvas = CanvasBoundary()
    var state = ExpandedState()
    var document = ExpandedDocument()
    var customInputView: UIView? { didSet { if customInputView == nil { nilInputWrites += 1 } } }
    var nilInputWrites = 0, focuses = 0
    var calls: [String] = []
    func currentState() -> ExpandedState { self.state }
    func becomeFirstResponder() -> Bool { focuses += 1; return true }
    func wrapInBlockQuote() { calls.append("quote") }
    func toggleSpoiler() { calls.append("spoiler") }
    func toggleBold() { calls.append("bold") }
    func toggleItalic() { calls.append("italic") }
    func toggleInlineCode() { calls.append("monospace") }
    func toggleStrikethrough() { calls.append("strikethrough") }
    func toggleUnderline() { calls.append("underline") }
    func makeCodeBlock() { calls.append("code") }
    func makePullQuote() { calls.append("pullQuote") }
    // NATIVE_SELECT_ALL
}
final class LegacySelectionBoundary {
    var content = NSAttributedString(string: "")
    var attributedText: NSAttributedString? { content }
    var selectedRange = NSRange(location: 0, length: 0)
    // LEGACY_SELECT_ALL
}
final class NativeSelectionBoundary {
    let editorView = RichEditorBoundary()
    // NATIVE_SELECTION_ADAPTER
}
enum ExpandedTransition { case immediate; static func spring(duration: Double) -> Self { .immediate } }
final class ExpandedComponentState {
    var updates = 0
    var onUpdate: (() -> Void)?
    func updated(transition: ExpandedTransition) { updates += 1; onUpdate?() }
}
final class EmojiModeBoundary {
    var isEmojiMode = false
    weak var editor: RichEditorBoundary?
    var requestLayout: () -> Void = {}
    func toggle() { self.setEmojiMode(!self.isEmojiMode) }
    // EMOJI_MODE
}
final class ExpandedFormattingHost {
    var nagramiXFormattingActive = false
    var nagramiXFormattingGeneration = 0
    var nagramiXFormattingInputView: UIView?
    var componentState: ExpandedComponentState? = ExpandedComponentState()
    let editor = RichEditorBoundary()
    var emojiKeyboard: EmojiModeBoundary? = EmojiModeBoundary()
    init() {
        self.emojiKeyboard?.editor = self.editor
        self.emojiKeyboard?.requestLayout = { [weak self] in self?.componentState?.updated(transition: .immediate) }
    }
    func presentLinkPrompt() { self.editor.calls.append("link") }
    // EXPANDED_METHODS
}
