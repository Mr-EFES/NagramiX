import Foundation
import Postbox

public class TranslationMessageAttribute: MessageAttribute, Equatable {
    public struct Additional : PostboxCoding, Equatable {
        public let text: String
        public let entities: [MessageTextEntity]
        
        public init(text: String, entities: [MessageTextEntity]) {
            self.text = text
            self.entities = entities
        }
        
        public init(decoder: PostboxDecoder) {
            self.text = decoder.decodeStringForKey("text", orElse: "")
            self.entities = decoder.decodeObjectArrayWithDecoderForKey("entities")
        }
        
        public func encode(_ encoder: PostboxEncoder) {
            encoder.encodeString(self.text, forKey: "text")
            encoder.encodeObjectArray(self.entities, forKey: "entities")
        } 
    }
    
    public let text: String
    public let entities: [MessageTextEntity]
    public let toLang: String
    public let nagramiXInlineRevision: String?
    public let nagramiXInlineSource: String?
    public let nagramiXInlineHidden: Bool

    public let additional: [Additional]
    public let pollSolution: Additional?
    /// The translated rich content, for messages carrying a `RichTextMessageAttribute` (translated via
    /// `messages.translateRichMessage`). `text`/`entities` stay empty for those.
    public let instantPage: InstantPage?

    public var associatedPeerIds: [PeerId] {
        return []
    }

    public init(
        text: String,
        entities: [MessageTextEntity],
        additional:[Additional] = [],
        pollSolution: Additional? = nil,
        toLang: String,
        instantPage: InstantPage? = nil,
        nagramiXInlineRevision: String? = nil,
        nagramiXInlineSource: String? = nil,
        nagramiXInlineHidden: Bool = false
    ) {
        self.text = text
        self.entities = entities
        self.toLang = toLang
        self.additional = additional
        self.pollSolution = pollSolution
        self.instantPage = instantPage
        self.nagramiXInlineRevision = nagramiXInlineRevision
        self.nagramiXInlineSource = nagramiXInlineSource
        self.nagramiXInlineHidden = nagramiXInlineHidden
    }

    required public init(decoder: PostboxDecoder) {
        self.text = decoder.decodeStringForKey("text", orElse: "")
        self.entities = decoder.decodeObjectArrayWithDecoderForKey("entities")
        self.additional = decoder.decodeObjectArrayWithDecoderForKey("additional")
        self.toLang = decoder.decodeStringForKey("toLang", orElse: "")
        self.nagramiXInlineRevision = decoder.decodeOptionalStringForKey("nxr")
        self.nagramiXInlineSource = decoder.decodeOptionalStringForKey("nxs")
        self.nagramiXInlineHidden = decoder.decodeInt32ForKey("nxh", orElse: 0) != 0
        self.pollSolution = decoder.decodeObjectForKey("pollSolution") as? Additional
        self.instantPage = decoder.decodeObjectForKey("ipage", decoder: { InstantPage(decoder: $0) }) as? InstantPage
    }

    public func encode(_ encoder: PostboxEncoder) {
        encoder.encodeString(self.text, forKey: "text")
        encoder.encodeObjectArray(self.entities, forKey: "entities")
        encoder.encodeString(self.toLang, forKey: "toLang")
        if let revision = self.nagramiXInlineRevision { encoder.encodeString(revision, forKey: "nxr") }
        else { encoder.encodeNil(forKey: "nxr") }
        if let source = self.nagramiXInlineSource { encoder.encodeString(source, forKey: "nxs") }
        else { encoder.encodeNil(forKey: "nxs") }
        encoder.encodeInt32(self.nagramiXInlineHidden ? 1 : 0, forKey: "nxh")
        encoder.encodeObjectArray(self.additional, forKey: "additional")

        if let pollSolution {
            encoder.encodeObject(pollSolution, forKey: "pollSolution")
        } else {
            encoder.encodeNil(forKey: "pollSolution")
        }
        if let instantPage {
            encoder.encodeObject(instantPage, forKey: "ipage")
        } else {
            encoder.encodeNil(forKey: "ipage")
        }
    }

    public static func ==(lhs: TranslationMessageAttribute, rhs: TranslationMessageAttribute) -> Bool {
        if lhs.nagramiXInlineRevision != rhs.nagramiXInlineRevision || lhs.nagramiXInlineSource != rhs.nagramiXInlineSource || lhs.nagramiXInlineHidden != rhs.nagramiXInlineHidden { return false }
        if lhs.text != rhs.text {
            return false
        }
        if lhs.entities != rhs.entities {
            return false
        }
        if lhs.toLang != rhs.toLang {
            return false
        }
        if lhs.additional != rhs.additional {
            return false
        }
        if lhs.pollSolution != rhs.pollSolution {
            return false
        }
        if lhs.instantPage != rhs.instantPage {
            return false
        }
        return true
    }
}

// Lives in TelegramCore so message components need no dependency on TranslateUI.
// Original text/entities remain in Message; only local attributes are changed.
public func nagramiXInlineTranslationFingerprint(_ message: Message) -> String {
    let entities = (message.attributes.first { $0 is TextEntitiesMessageAttribute } as? TextEntitiesMessageAttribute)?.entities ?? []
    return message.text + String(reflecting: entities)
}

private enum NagramiXInlineTranslationConfiguration {
    private static let lock = NSLock()
    private static var lastData: Data?
    private static var enabledRevision: String? = "initial"
    static func revision() -> String? {
        let data = UserDefaults.standard.data(forKey: "nagramix.translation.configuration.v1")
        self.lock.lock(); defer { self.lock.unlock() }
        if data != self.lastData {
            self.lastData = data
            self.enabledRevision = "initial"
            if let data, let settings = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                self.enabledRevision = settings["revision"] as? String ?? "initial"
            }
        }
        return self.enabledRevision
    }
}

public func nagramiXInlineTranslationTarget(_ message: Message) -> String? {
    guard let translation = message.attributes.first(where: { ($0 as? TranslationMessageAttribute)?.nagramiXInlineRevision != nil }) as? TranslationMessageAttribute,
          let revision = translation.nagramiXInlineRevision,
          translation.nagramiXInlineSource == nagramiXInlineTranslationFingerprint(message),
          NagramiXInlineTranslationConfiguration.revision() == revision else { return nil }
    return translation.toLang
}
