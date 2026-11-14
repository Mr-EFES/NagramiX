import Foundation

/// Согласие действует только в текущем просмотрщике и для точного account/peer/story.
public final class NagramiXStoryViewDisclosure {
    public struct Key: Hashable {
        public let accountId: Int64
        public let peerId: Int64
        public let storyId: Int32
        public init(accountId: Int64, peerId: Int64, storyId: Int32) {
            self.accountId = accountId; self.peerId = peerId; self.storyId = storyId
        }
    }
    public enum Status { case anonymous, pending, recorded }
    private var recorded = Set<Key>()
    private var pending: [Key: UUID] = [:]
    public init() {}
    public func status(for key: Key) -> Status {
        if self.recorded.contains(key) { return .recorded }
        return self.pending[key] == nil ? .anonymous : .pending
    }
    public func begin(_ key: Key) -> UUID? {
        guard key.storyId > 0, key.peerId != key.accountId, self.status(for: key) == .anonymous else { return nil }
        let request = UUID()
        self.pending[key] = request
        return request
    }
    @discardableResult
    public func complete(_ key: Key, request: UUID, success: Bool) -> Bool {
        guard self.pending[key] == request else { return false }
        self.pending[key] = nil
        if success { self.recorded.insert(key) }
        return true
    }
}
