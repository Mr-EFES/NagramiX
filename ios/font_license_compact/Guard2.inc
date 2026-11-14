import Foundation
import UIKit
import CoreText
import ObjectiveC
import SwiftSignalKit
import NagramiXMediaSettings

private final class NagramiXFontBundleMarker {}

public enum NagramiXFontManager {
    private static let lock = NSLock()
    private static var cache: [String: UIFont] = [:]
    private static let nativeKey = "NagramiXFonts.NativeScope"
    private static let bundle: Bundle? = {
        for parent in [Bundle(for: NagramiXFontBundleMarker.self), Bundle.main] + Bundle.allFrameworks {
            if let url = parent.url(forResource: "NagramiXFontsResources", withExtension: "bundle"), let bundle = Bundle(url: url) { return bundle }
        }
        return nil
    }()
    private static let initialized: Void = {
        UIFont.nagramiXInstallFontHooks()
    }()
    private static let bundledInitialized: Void = {
        if let bundle = NagramiXFontManager.bundle {
            for url in bundle.urls(forResourcesWithExtension: "ttf", subdirectory: nil) ?? [] {
                NagramiXFontManager.withNativeFonts {
                    _ = CTFontManagerRegisterFontsForURL(url as CFURL, .process, nil)
                }
            }
        }
    }()

    fileprivate static var usesNativeFonts: Bool { return Thread.current.threadDictionary[self.nativeKey] as? Bool == true }

    public static func withNativeFonts<T>(_ body: () -> T) -> T {
        let previous = Thread.current.threadDictionary[self.nativeKey]
        Thread.current.threadDictionary[self.nativeKey] = true
        defer {
            if let previous { Thread.current.threadDictionary[self.nativeKey] = previous }
            else { Thread.current.threadDictionary.removeObject(forKey: self.nativeKey) }
        }
        return body()
    }

    public static func settingsSignal() -> Signal<String, NoError> {
        _ = self.initialized
        return Signal { subscriber in
            let observer = NotificationCenter.default.addObserver(forName: NagramiXFontSettings.changed, object: nil, queue: nil) { _ in
                subscriber.putNext(NagramiXFontSettings.current.selectionKey)
            }
            subscriber.putNext(NagramiXFontSettings.current.selectionKey)
            return ActionDisposable { NotificationCenter.default.removeObserver(observer) }
        } |> distinctUntilChanged
    }

    public static func available(_ entry: NagramiXFontEntry) -> Bool {
        _ = self.initialized
        guard let name = entry.postscriptName else { return true }
        if entry.kind == .bundled { _ = self.bundledInitialized }
        return self.withNativeFonts { UIFont(name: name, size: 17) != nil }
    }

    public static func missingCharacters(_ entry: NagramiXFontEntry, sample: String) -> Bool {
        guard let name = entry.postscriptName else { return false }
        let characters = CTFontCopyCharacterSet(CTFontCreateWithName(name as CFString, 17, nil))
        return sample.unicodeScalars.contains { !CharacterSet.whitespacesAndNewlines.contains($0) && !CFCharacterSetIsLongCharacterMember(characters, $0.value) }
    }

    public static func previewFont(_ entry: NagramiXFontEntry, size: CGFloat) -> UIFont {
        return self.font(size: size, selection: entry.id) ?? self.withNativeFonts { UIFont.systemFont(ofSize: size) }
    }

    /// nil preserves every upstream path, including semantic code and camera typography.
    public static func font(size: CGFloat, design: Font.Design = .regular, weight: UIFont.Weight = .regular, width: Font.Width = .standard, traits: Font.Traits = [], selection: String? = nil) -> UIFont? {
        _ = self.initialized
        guard size.isFinite, size > 0 else { return nil }
        if selection == nil && (self.usesNativeFonts || design == .camera || design == .monospace) { return nil }
        let settings = NagramiXFontSettings.current
        guard selection != nil || settings.enabled else { return nil }
        let entry = NagramiXFontEntry.entry(selection ?? settings.fontId)
        guard entry.id != "system" || selection != nil else { return nil }
        if entry.kind == .bundled { _ = self.bundledInitialized }
        let key = "\(entry.id):\(size):\(weight.rawValue):\(width.key):\(traits.rawValue)"
        self.lock.lock(); let cached = self.cache[key]; self.lock.unlock()
        if let cached { return cached }
        let result: UIFont? = self.withNativeFonts {
            let native = UIFont.systemFont(ofSize: size, weight: weight)
            var base = native
            if let name = entry.postscriptName {
                var selectedName = name
                let italic = traits.contains(.italic)
                if entry.kind == .bundled {
                    let prefix: String
                    let style: String
                    if entry.id == "bundled.roboto" {
                        prefix = "Roboto"
                        if weight.rawValue >= UIFont.Weight.heavy.rawValue { style = "Black" }
                        else if weight.rawValue >= UIFont.Weight.semibold.rawValue { style = "Bold" }
                        else if weight.rawValue >= UIFont.Weight.medium.rawValue { style = "Medium" }
                        else if weight.rawValue <= UIFont.Weight.thin.rawValue { style = "Thin" }
                        else if weight.rawValue <= UIFont.Weight.light.rawValue { style = "Light" }
                        else { style = "Regular" }
                    } else {
                        prefix = entry.id == "bundled.astra-sans" ? "PTAstraSans" : "PTAstraSerif"
                        style = weight.rawValue >= UIFont.Weight.semibold.rawValue ? "Bold" : "Regular"
                    }
                    selectedName = prefix + "-" + (italic ? (style == "Regular" ? "Italic" : style + "Italic") : style)
                }
                guard let named = UIFont(name: selectedName, size: size) ?? UIFont(name: name, size: size) else { return nil }
                base = named
            }
            var descriptor = base.fontDescriptor
            if entry.kind == .system {
                let systemDesign: UIFontDescriptor.SystemDesign
                switch entry.id {
                case "system.rounded": systemDesign = .rounded
                case "system.serif": systemDesign = .serif
                case "system.monospace": systemDesign = .monospaced
                default: systemDesign = .default
                }
                descriptor = descriptor.withDesign(systemDesign) ?? descriptor
            }
            var symbolic = descriptor.symbolicTraits
            if traits.contains(.italic) { symbolic.insert(.traitItalic) }
            if weight.rawValue >= UIFont.Weight.semibold.rawValue { symbolic.insert(.traitBold) }
            descriptor = descriptor.withSymbolicTraits(symbolic) ?? descriptor
            var descriptorTraits = descriptor.object(forKey: .traits) as? [UIFontDescriptor.TraitKey: Any] ?? [:]
            descriptorTraits[.weight] = weight
            if #available(iOS 16.0, *), width != .standard { descriptorTraits[.width] = width.width }
            var attributes: [UIFontDescriptor.AttributeName: Any] = [.traits: descriptorTraits, .cascadeList: [native.fontDescriptor]]
            var features: [[String: Any]] = []
            if traits.contains(.monospacedNumbers) {
                features.append([UIFontDescriptor.FeatureKey.type.rawValue: kNumberSpacingType, UIFontDescriptor.FeatureKey.selector.rawValue: kMonospacedNumbersSelector])
            }
            if traits.contains(.alternateDollarSign) { features.append([kCTFontOpenTypeFeatureTag as String: "cv09", kCTFontOpenTypeFeatureValue as String: 1]) }
            if !features.isEmpty { attributes[.featureSettings] = features }
            descriptor = descriptor.addingAttributes(attributes)
            return UIFont(descriptor: descriptor, size: size)
        }
        if let result {
            self.lock.lock()
            if self.cache.count >= 512 { self.cache.removeAll() }
            self.cache[key] = result
            self.lock.unlock()
        }
        return result
    }

    public static var licenseDocuments: [(name: String, text: String)] {
        _ = self.initialized
        let documents = [("PTAstraSans-LICENSE", "PT Astra Sans"), ("PTAstraSerif-LICENSE", "PT Astra Serif"), ("Roboto-NOTICE", "Roboto · NOTICE"), ("Roboto-LICENSE", "Roboto · Apache License 2.0")]
        return documents.compactMap { resource, name in
            guard let url = self.bundle?.url(forResource: resource, withExtension: "txt"), let text = try? String(contentsOf: url, encoding: .utf8) else { return nil }
            return (name: name, text: text)
        }
    }

    public static var licenseText: String {
        return self.licenseDocuments.map { $0.text }.joined(separator: "\n\n")
    }

}

private extension UIFont {
    static func nagramiXInstallFontHooks() {
        let methods: [(Selector, Selector)] = [
            (#selector(UIFont.systemFont(ofSize:)), #selector(UIFont.nagramiXSystemFont(ofSize:))),
            (#selector(UIFont.systemFont(ofSize:weight:)), #selector(UIFont.nagramiXWeightedFont(ofSize:weight:))),
            (#selector(UIFont.boldSystemFont(ofSize:)), #selector(UIFont.nagramiXBoldFont(ofSize:))),
            (#selector(UIFont.italicSystemFont(ofSize:)), #selector(UIFont.nagramiXItalicFont(ofSize:))),
            (#selector(UIFont.preferredFont(forTextStyle:)), #selector(UIFont.nagramiXPreferredFont(forTextStyle:)))
        ]
        for (original, replacement) in methods {
            guard let first = class_getClassMethod(UIFont.self, original), let second = class_getClassMethod(UIFont.self, replacement),
                  let firstEncoding = method_getTypeEncoding(first), let secondEncoding = method_getTypeEncoding(second),
                  strcmp(firstEncoding, secondEncoding) == 0 else { continue }
            method_exchangeImplementations(first, second)
        }
    }

    @objc class func nagramiXSystemFont(ofSize size: CGFloat) -> UIFont {
        let native = NagramiXFontManager.withNativeFonts { self.nagramiXSystemFont(ofSize: size) }
        return NagramiXFontManager.font(size: native.pointSize) ?? native
    }
    // UIFontWeight is CGFloat in Objective-C. Keep that exact ABI and verify encodings.
    @objc class func nagramiXWeightedFont(ofSize size: CGFloat, weight: CGFloat) -> UIFont {
        let native = NagramiXFontManager.withNativeFonts { self.nagramiXWeightedFont(ofSize: size, weight: weight) }
        return NagramiXFontManager.font(size: native.pointSize, weight: UIFont.Weight(rawValue: weight)) ?? native
    }
    @objc class func nagramiXBoldFont(ofSize size: CGFloat) -> UIFont {
        let native = NagramiXFontManager.withNativeFonts { self.nagramiXBoldFont(ofSize: size) }
        return NagramiXFontManager.font(size: native.pointSize, weight: .bold) ?? native
    }
    @objc class func nagramiXItalicFont(ofSize size: CGFloat) -> UIFont {
        let native = NagramiXFontManager.withNativeFonts { self.nagramiXItalicFont(ofSize: size) }
        return NagramiXFontManager.font(size: native.pointSize, traits: [.italic]) ?? native
    }
    // UIFontTextStyle is NSString in Objective-C; no private selectors are used.
    @objc class func nagramiXPreferredFont(forTextStyle style: String) -> UIFont {
        let native = NagramiXFontManager.withNativeFonts { self.nagramiXPreferredFont(forTextStyle: style) }
        let traits = native.fontDescriptor.object(forKey: .traits) as? [UIFontDescriptor.TraitKey: Any]
        let weight = (traits?[.weight] as? NSNumber)?.doubleValue ?? 0
        let italic = native.fontDescriptor.symbolicTraits.contains(.traitItalic)
        guard let selected = NagramiXFontManager.font(size: native.pointSize, weight: UIFont.Weight(rawValue: CGFloat(weight)), traits: italic ? [.italic] : []) else { return native }
        return UIFont(descriptor: selected.fontDescriptor.addingAttributes([.textStyle: style]), size: native.pointSize)
    }
}
