import Foundation

public enum NagramiXFormattingSettings {
    private static let key = "nagramix.messages.quickFormatting"
    public static let changedNotification = Notification.Name("NagramiXQuickFormattingChanged")

    public static var enabled: Bool {
        return UserDefaults.standard.object(forKey: self.key) as? Bool ?? false
    }

    public static func setEnabled(_ enabled: Bool) {
        UserDefaults.standard.set(enabled, forKey: self.key)
        NotificationCenter.default.post(name: self.changedNotification, object: nil)
        NotificationCenter.default.post(name: NagramiXTabSettings.changedNotification, object: nil)
    }
}

public enum NagramiXFormattingAction: Int, CaseIterable {
    case quote, spoiler, bold, italic, monospace, link, date, strikethrough, underline, code

    public func isAvailable(selection: NSRange, textLength: Int, secret: Bool, native: Bool,
                            containsSpoiler: Bool, containsMonospace: Bool) -> Bool {
        guard selection.location != NSNotFound, selection.location >= 0, selection.length > 0,
              selection.location <= textLength, selection.length <= textLength - selection.location else { return false }
        if secret && (self == .quote || self == .spoiler || self == .date) { return false }
        // The pinned rich editor has no timestamp-entity representation. Do not
        // offer its no-op action or flatten a structured document as a fallback.
        if native && self == .date { return false }
        if self == .spoiler && containsMonospace { return false }
        if self == .monospace && containsSpoiler { return false }
        return true
    }
}

/// A read-only snapshot. Formatting always uses the editor's live selection,
/// never a saved range from when the keyboard was opened.
public struct NagramiXFormattingSelection {
    public let text: NSAttributedString
    public let range: NSRange
    public var valid: Bool {
        return self.range.location != NSNotFound && self.range.location >= 0 && self.range.length > 0
            && self.range.location <= self.text.length && self.range.length <= self.text.length - self.range.location
    }
    public init(text: NSAttributedString, range: NSRange) {
        self.text = text; self.range = range
    }
    public func contains(_ key: NSAttributedString.Key) -> Bool {
        guard self.valid else { return false }
        var found = false
        self.text.enumerateAttribute(key, in: self.range) { value, _, _ in
            if value != nil { found = true }
        }
        return found
    }
    public func covers(_ key: NSAttributedString.Key, matching: (Any) -> Bool = { _ in true }) -> Bool {
        guard self.valid else { return false }
        var covered = true
        self.text.enumerateAttribute(key, in: self.range) { value, _, stop in
            if let value, matching(value) {} else { covered = false; stop.pointee = true }
        }
        return covered
    }
}
