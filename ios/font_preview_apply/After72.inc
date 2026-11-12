import Foundation

public struct NagramiXFontEntry: Equatable {
    public enum Kind: Equatable { case system, bundled, ios }
    public let id: String
    public let name: String
    public let postscriptName: String?
    public let titleKey: String?
    public let kind: Kind

    public static let system = NagramiXFontEntry(id: "system", name: "SF Pro", postscriptName: nil, titleKey: "NagramiX.Network.DNS.System", kind: .system)
    public static let catalog: [NagramiXFontEntry] = [
        .system,
        .init(id: "system.rounded", name: "SF Pro Rounded", postscriptName: nil, titleKey: "NagramiX.Fonts.Rounded", kind: .system),
        .init(id: "system.serif", name: "New York", postscriptName: nil, titleKey: "NagramiX.Fonts.Serif", kind: .system),
        .init(id: "system.monospace", name: "SF Mono", postscriptName: nil, titleKey: "NagramiX.Fonts.Monospace", kind: .system),
        .init(id: "bundled.astra-sans", name: "PT Astra Sans", postscriptName: "PTAstraSans-Regular", titleKey: nil, kind: .bundled),
        .init(id: "bundled.astra-serif", name: "PT Astra Serif", postscriptName: "PTAstraSerif-Regular", titleKey: nil, kind: .bundled),
        .init(id: "bundled.roboto", name: "Roboto", postscriptName: "Roboto-Regular", titleKey: nil, kind: .bundled),
        .init(id: "ios.helvetica-neue", name: "Helvetica Neue", postscriptName: "HelveticaNeue", titleKey: nil, kind: .ios),
        .init(id: "ios.arial", name: "Arial", postscriptName: "ArialMT", titleKey: nil, kind: .ios),
        .init(id: "ios.avenir-next", name: "Avenir Next", postscriptName: "AvenirNext-Regular", titleKey: nil, kind: .ios),
        .init(id: "ios.gill-sans", name: "Gill Sans", postscriptName: "GillSans", titleKey: nil, kind: .ios),
        .init(id: "ios.trebuchet", name: "Trebuchet MS", postscriptName: "TrebuchetMS", titleKey: nil, kind: .ios),
        .init(id: "ios.verdana", name: "Verdana", postscriptName: "Verdana", titleKey: nil, kind: .ios),
        .init(id: "ios.georgia", name: "Georgia", postscriptName: "Georgia", titleKey: nil, kind: .ios),
        .init(id: "ios.times", name: "Times New Roman", postscriptName: "TimesNewRomanPSMT", titleKey: nil, kind: .ios),
        .init(id: "ios.palatino", name: "Palatino", postscriptName: "Palatino-Roman", titleKey: nil, kind: .ios),
        .init(id: "ios.baskerville", name: "Baskerville", postscriptName: "Baskerville", titleKey: nil, kind: .ios),
        .init(id: "ios.charter", name: "Charter", postscriptName: "Charter-Roman", titleKey: nil, kind: .ios),
        .init(id: "ios.cochin", name: "Cochin", postscriptName: "Cochin", titleKey: nil, kind: .ios),
        .init(id: "ios.hoefler", name: "Hoefler Text", postscriptName: "HoeflerText-Regular", titleKey: nil, kind: .ios),
        .init(id: "ios.iowan", name: "Iowan Old Style", postscriptName: "IowanOldStyle-Roman", titleKey: nil, kind: .ios),
        .init(id: "ios.rockwell", name: "Rockwell", postscriptName: "Rockwell-Regular", titleKey: nil, kind: .ios),
        .init(id: "ios.typewriter", name: "American Typewriter", postscriptName: "AmericanTypewriter", titleKey: nil, kind: .ios),
        .init(id: "ios.marker", name: "Marker Felt", postscriptName: "MarkerFelt-Thin", titleKey: nil, kind: .ios),
        .init(id: "ios.noteworthy", name: "Noteworthy", postscriptName: "Noteworthy-Light", titleKey: nil, kind: .ios),
        .init(id: "ios.chalkboard", name: "Chalkboard SE", postscriptName: "ChalkboardSE-Regular", titleKey: nil, kind: .ios),
        .init(id: "ios.menlo", name: "Menlo", postscriptName: "Menlo-Regular", titleKey: nil, kind: .ios),
        .init(id: "ios.courier", name: "Courier New", postscriptName: "CourierNewPSMT", titleKey: nil, kind: .ios),
        .init(id: "ios.futura", name: "Futura", postscriptName: "Futura-Medium", titleKey: nil, kind: .ios),
        .init(id: "ios.optima", name: "Optima", postscriptName: "Optima-Regular", titleKey: nil, kind: .ios),
        .init(id: "ios.didot", name: "Didot", postscriptName: "Didot", titleKey: nil, kind: .ios),
        .init(id: "ios.bodoni", name: "Bodoni 72", postscriptName: "BodoniSvtyTwoITCTT-Book", titleKey: nil, kind: .ios)
    ]

    public static func entry(_ id: String) -> NagramiXFontEntry {
        return self.catalog.first(where: { $0.id == id }) ?? .system
    }
}

public struct NagramiXFontSettings: Equatable {
    public static let changed = Notification.Name("NagramiXFontSettingsChanged")
    private static let lock = NSRecursiveLock()
    public var enabled: Bool
    public var fontId: String

    public init(enabled: Bool = true, fontId: String = "system") {
        self.enabled = enabled
        self.fontId = NagramiXFontEntry.entry(fontId).id
    }

    public var selectionKey: String { return (self.enabled ? "on:" : "off:") + self.fontId }

    public static func read(from defaults: UserDefaults) -> NagramiXFontSettings {
        self.lock.lock(); defer { self.lock.unlock() }
        return .init(enabled: defaults.object(forKey: "nagramix.fonts.enabled") as? Bool ?? true,
                     fontId: defaults.string(forKey: "nagramix.fonts.selection.v1") ?? "system")
    }

    public static var current: NagramiXFontSettings { return self.read(from: .standard) }

    public static func update(_ transform: (inout NagramiXFontSettings) -> Void) {
        self.lock.lock()
        var value = self.current
        let previous = value
        transform(&value)
        value.fontId = NagramiXFontEntry.entry(value.fontId).id
        guard value != previous else { self.lock.unlock(); return }
        UserDefaults.standard.set(value.enabled, forKey: "nagramix.fonts.enabled")
        UserDefaults.standard.set(value.fontId, forKey: "nagramix.fonts.selection.v1")
        self.lock.unlock()
        NotificationCenter.default.post(name: self.changed, object: nil)
    }
}

/// A screen-local draft. Only the explicit Apply action may persist it.
public struct NagramiXFontSelectionDraft {
    public private(set) var applied: NagramiXFontSettings
    public private(set) var fontId: String
    private var edited = false

    public init(_ settings: NagramiXFontSettings) {
        self.applied = settings
        self.fontId = settings.fontId
    }
    public var proposed: NagramiXFontSettings { return .init(enabled: true, fontId: self.fontId) }
    public var canApply: Bool { return self.proposed != self.applied }
    public mutating func select(_ id: String) {
        guard NagramiXFontEntry.catalog.contains(where: { $0.id == id }) else { return }
        self.fontId = id
        self.edited = true
    }
    public mutating func synchronize(_ settings: NagramiXFontSettings) {
        if !self.edited { self.fontId = settings.fontId }
        self.applied = settings
        if self.proposed == settings { self.edited = false }
    }
}

public enum NagramiXFontLicenseLayout {
    /// Remove hard line wrapping, retaining every original word, clause and notice.
    public static func paragraphs(_ text: String) -> [String] {
        var result: [String] = []
        var lines: [String] = []
        for line in text.replacingOccurrences(of: "\r\n", with: "\n").components(separatedBy: "\n") {
            let words = line.split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
            if words.isEmpty {
                if !lines.isEmpty { result.append(lines.joined(separator: " ")); lines.removeAll() }
            } else { lines.append(words) }
        }
        if !lines.isEmpty { result.append(lines.joined(separator: " ")) }
        return result
    }
}
