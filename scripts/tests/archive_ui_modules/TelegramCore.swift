public import Postbox

// Match the public aliases of the pinned TelegramCore, without re-exporting
// Postbox's unqualified names or making Core's private settings public.
public enum EngineMessage { public typealias Id = MessageId }
public enum EnginePeer { public typealias Id = PeerId }
public typealias EngineRawMessage = Message
public enum Namespaces { public enum Peer { public static let SecretChat: Int32 = 99 } }
private struct NagramiXMessageArchiveSettings {
    let showDeletedMessages: Bool
    static var current: Self { fatalError("private interface") }
}
public struct NagramiXArchivePostDeletionPlan {
    public let liveMessageIds: Set<EngineMessage.Id>
    public let localMessageIds: Set<EngineMessage.Id>
}
public final class NagramiXMessageArchive {
    public func postMessageIds(messageIds: Set<EngineMessage.Id>, messages: [EngineRawMessage]) -> Set<EngineMessage.Id> { fatalError("interface only") }
    public func localPostDeletionCandidates(messages: [EngineRawMessage]) -> Set<EngineMessage.Id> { fatalError("interface only") }
}
public enum MessageReaction { public enum Reaction: Hashable { case builtin(String) } }
