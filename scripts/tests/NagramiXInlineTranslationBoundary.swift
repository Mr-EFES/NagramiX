import Foundation

// Storage-only stand-ins for Postbox, so the real attribute/settings can be
// exercised without Apple SDK. No translation/selection policy is reimplemented.
public protocol PostboxCoding {
    init(decoder: PostboxDecoder)
    func encode(_ encoder: PostboxEncoder)
}
public protocol MessageAttribute: PostboxCoding {}
public struct PeerId: Hashable { public let value: Int64 }
public struct MessageTextEntity: Equatable {
    public let range: Range<Int>
    public let type: String
}
public final class PostboxEncoder {
    public var values: [String: Any] = [:]
    public func encodeString(_ value: String, forKey key: String) { self.values[key] = value }
    public func encodeNil(forKey key: String) { self.values.removeValue(forKey: key) }
    public func encodeInt32(_ value: Int32, forKey key: String) { self.values[key] = value }
    public func encodeObject<T>(_ value: T, forKey key: String) { self.values[key] = value }
    public func encodeObjectArray<T>(_ value: [T], forKey key: String) { self.values[key] = value }
}
public final class PostboxDecoder {
    public let values: [String: Any]
    public init(_ values: [String: Any]) { self.values = values }
    public func decodeStringForKey(_ key: String, orElse fallback: String) -> String { self.values[key] as? String ?? fallback }
    public func decodeOptionalStringForKey(_ key: String) -> String? { self.values[key] as? String }
    public func decodeInt32ForKey(_ key: String, orElse fallback: Int32) -> Int32 { self.values[key] as? Int32 ?? fallback }
    public func decodeObjectArrayWithDecoderForKey<T>(_ key: String) -> [T] { self.values[key] as? [T] ?? [] }
    public func decodeObjectForKey(_ key: String) -> Any? { self.values[key] }
    public func decodeObjectForKey(_ key: String, decoder: (PostboxDecoder) -> Any) -> Any? { self.values[key] }
}
public struct InstantPage: Equatable, PostboxCoding {
    public init(decoder: PostboxDecoder) {}
    public func encode(_ encoder: PostboxEncoder) {}
}
public final class TextEntitiesMessageAttribute: MessageAttribute {
    public let entities: [MessageTextEntity]
    public init(_ entities: [MessageTextEntity]) { self.entities = entities }
    public init(decoder: PostboxDecoder) { self.entities = [] }
    public func encode(_ encoder: PostboxEncoder) {}
}
public struct Message {
    public let text: String
    public let attributes: [MessageAttribute]
}
