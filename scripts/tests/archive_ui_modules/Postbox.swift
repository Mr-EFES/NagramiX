// Explicit interface fixture: these names must remain invisible to UI clients.
public struct PeerId: Hashable, Comparable {
    public let namespace: Int32
    public static func < (lhs: Self, rhs: Self) -> Bool { lhs.namespace < rhs.namespace }
}
public struct MessageId: Hashable, Comparable {
    public let peerId: PeerId
    public let namespace: Int32
    public static func < (lhs: Self, rhs: Self) -> Bool { lhs.namespace < rhs.namespace }
}
public struct Message {
    public let id: MessageId
    public let groupingKey: Int64?
    public let threadId: Int64?
}
