import Foundation
#if canImport(AppKit)
import AppKit
import CoreText
#endif

enum AlertScreen {
    // CONFIGURATION
}

let config: AlertScreen.Configuration = ALERT_CONFIG
let width: CGFloat = ALERT_WIDTH - 2 * (config.contentSideInset + TEXT_INSET)
precondition(ALERT_WIDTH == 300 && AlertScreen.Configuration().contentSideInset == 30)
precondition(config.allowInputInset && width == 268)
let resource = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let catalog = try PropertyListSerialization.propertyList(from: resource, format: nil) as! [String: String]
let message = catalog["NagramiX.Network.DNS.CustomUnavailable"]!
let lines = message.components(separatedBy: "\n")
precondition(lines == ["DoH-сервер не ответил корректно.", "Проверьте адрес и подключение."])
#if canImport(AppKit)
let text = NSAttributedString(string: message, attributes: [.font: NSFont.systemFont(ofSize: FONT_SIZE)])
let setter = CTTypesetterCreateWithAttributedString(text as CFAttributedString)
let first = CTTypesetterSuggestLineBreak(setter, 0, Double(width))
precondition(first == (lines[0] as NSString).length + 1)
precondition(first + CTTypesetterSuggestLineBreak(setter, first, Double(width)) == text.length)
#endif
print("PASS: standard alert width, two localized sentences, keyboard-aware error presentation")
