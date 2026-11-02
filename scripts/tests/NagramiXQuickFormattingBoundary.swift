import Foundation

// Only UIKit/editor boundaries are doubles. Production command routing,
// selection inspection, availability and keyboard ownership are extracted.
enum NagramiXTabSettings { static let changedNotification = Notification.Name("TabsChanged") }
class UIView {}
final class NagramiXFormattingKeyboard: UIView {
    var action: ((NagramiXFormattingAction) -> Void)?
    init(title: String) {}
}
enum ChatRichTextFormatAction: String { case quote, spoiler, bold, italic, monospace, strikethrough, underline, code }
enum ChatTextInputAttributes {
    static let bold = NSAttributedString.Key("bold"), italic = NSAttributedString.Key("italic")
    static let monospace = NSAttributedString.Key("monospace"), spoiler = NSAttributedString.Key("spoiler")
    static let strikethrough = NSAttributedString.Key("strikethrough"), underline = NSAttributedString.Key("underline")
    static let textUrl = NSAttributedString.Key("textUrl"), block = NSAttributedString.Key("block"), date = NSAttributedString.Key("date")
}
final class ChatTextInputTextQuoteAttribute: NSObject {
    enum Kind { case quote, code(language: String?) }
    let kind: Kind
    init(_ kind: Kind) { self.kind = kind }
}
enum Namespaces { enum Peer { static let SecretChat = 1 } }
enum InputMode { case text, media, none }
enum Transition { case immediate }
final class ChatPresentationInterfaceState {
    struct TextPanel { var mediaRecordingState: Int? }
    struct Interface { var mediaDraftState: Int? }
    struct PeerId { let namespace: Int }
    struct Location { var peerId: PeerId? }
    struct Buttons { var id: Int }
    struct Strings { var TextFormat_Format = "Format" }
    var inputTextPanelState = TextPanel(), interfaceState = Interface(), chatLocation = Location()
    var keyboardButtonsMessage: Buttons?, strings = Strings(), inputMode = InputMode.text
}
final class Editor {
    var keyboardInputView: UIView?
    var isInputFirstResponder = true, usesNativeRichTextEngine = false
    var selectedRange = NSRange(location: 0, length: 0)
    var content = NSAttributedString(string: "")
    var attributedText: NSAttributedString? { content } // read-only: catches accidental flat writes
    var calls: [String] = [], reloads = 0, focuses = 0
    func reloadInputViews() { reloads += 1 }
    func makeInputFirstResponder() { isInputFirstResponder = true; focuses += 1 }
    func performFormatAction(_ action: ChatRichTextFormatAction) { calls.append(action.rawValue) }
}
final class Interaction {
    let state: ChatPresentationInterfaceState
    init(_ state: ChatPresentationInterfaceState) { self.state = state }
    func updateInputModeAndDismissedButtonKeyboardMessageId(_ update: (ChatPresentationInterfaceState) -> (InputMode, Int?)) {
        state.inputMode = update(state).0
    }
}
// FORMATTING_PANEL
