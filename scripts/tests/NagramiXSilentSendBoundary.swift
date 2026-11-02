import Foundation

// Native notification flags/class, EnqueueMessage case declarations and
// withUpdatedAttributes, new setting/policy and native send snippets are extracted.
// Postbox storage, media payloads, network and UIKit remain controlled boundaries.
protocol MessageAttribute: AnyObject {}
typealias MediaId=Int
protocol Media: AnyObject {}
typealias StoryId=Int
typealias ItemCollectionId=Int
typealias MessageId=Int
struct AnyMediaReference: Equatable { let id: Int }
struct EngineMessageReplySubject: Equatable { let id: Int }
final class PostboxDecoder {
    let raw: Int32
    init(_ raw: Int32) { self.raw=raw }
    func decodeInt32ForKey(_ key: String,orElse: Int32) -> Int32 { raw }
}
final class PostboxEncoder {
    var raw: Int32=0
    func encodeInt32(_ value: Int32,forKey: String) { raw=value }
}
final class Sentinel: MessageAttribute { let id: Int;init(_ id: Int) { self.id=id } }
struct ShareMessage { let isSilent: Bool }
enum NagramiXTabSettings { static let current=0 }
final class SettingsPromise { var count=0;func set(_ value: Int) { count += 1 } }
