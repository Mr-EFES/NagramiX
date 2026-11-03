import Foundation

public struct PeerId: Hashable {
    public let isVerificationCodes: Bool
    public init(isVerificationCodes: Bool = false) { self.isVerificationCodes = isVerificationCodes }
}
public struct MessageId: Hashable {
    public let peerId: PeerId
    public let value: Int
    public init(_ value: Int, codes: Bool = false) { self.value = value; self.peerId = PeerId(isVerificationCodes: codes) }
}
public struct RestrictionRule {
    let platform: String
    let reason: String
    let text: String
}
public struct PeerAccessRestrictionInfo { let rules: [RestrictionRule] }
public protocol Peer {}
public final class TelegramUser: Peer {
    let restrictionInfo: PeerAccessRestrictionInfo?
    init(_ rules: [RestrictionRule]?) { restrictionInfo = rules.map { PeerAccessRestrictionInfo(rules: $0) } }
}
public final class TelegramChannel: Peer {
    let restrictionInfo: PeerAccessRestrictionInfo?
    init(_ rules: [RestrictionRule]?) { restrictionInfo = rules.map { PeerAccessRestrictionInfo(rules: $0) } }
}
private final class OrdinaryPeer: Peer {}
public final class RestrictedContentMessageAttribute {
    let rules: [RestrictionRule]
    init(_ rules: [RestrictionRule]) { self.rules = rules }
}
public final class Message {
    let id: MessageId
    let restrictedContentAttribute: RestrictedContentMessageAttribute?
    let paidContent: Int?
    init(_ value: Int, rules: [RestrictionRule]? = nil, paid: Bool = false, codes: Bool = false) {
        id = MessageId(value, codes: codes)
        restrictedContentAttribute = rules.map(RestrictedContentMessageAttribute.init)
        paidContent = paid ? 1 : nil
    }
}
public typealias EngineRawMessage = Message

private struct Item { let content: [(Message, Int)] }
private class ItemNode {}
private final class ChatMessageItemView: ItemNode {
    let item: Item?
    init(_ messages: [Message]?) { item = messages.map { Item(content: $0.map { ($0, 0) }) } }
}
private final class HistoryNode {
    var nodes: [ItemNode] = []
    var updated: [MessageId] = []
    func forEachItemNode(_ body: (ItemNode) -> Void) { nodes.forEach(body) }
    func requestMessageUpdate(_ id: MessageId) { updated.append(id) }
}
private final class DisplayNode { let historyNode = HistoryNode() }
private enum ContainedViewLayoutTransition { case immediate }
