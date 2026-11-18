import Foundation

public struct PeerId: Hashable {
    var value: Int
    var namespace: Int = 0
    var isVerificationCodes: Bool { value == 777 }
}
public struct MessageId: Hashable {
    let peerId: PeerId
    let namespace: Int32
    let id: Int
}
enum Namespaces {
    enum Peer { static let SecretChat = 3 }
    enum Message { static let SecretIncoming: Int32 = 2, Local: Int32 = 1, Cloud: Int32 = 0 }
}
enum EngineMessage { typealias Id = MessageId }
struct Peer {}
protocol Media {}
struct TelegramMediaExpiredContent: Media {}
public struct Message {
    let id: MessageId
    var groupingKey: Int64? = nil
    var threadId: Int64? = nil
    var peers: [PeerId: Peer] = [:]
    var media: [Media] = []
    var allowsArchive = true
    var isTemporary = false
}
func nagramiXCanRetainTemporaryMessage(_ message: Message) -> Bool { message.isTemporary && message.allowsArchive }

public struct Transaction {
    var live: [MessageId: Message]
    func getMessage(_ id: MessageId) -> Message? { live[id] }
    func getMessageGroup(_ id: MessageId) -> [Message]? { nil }
}
struct ReadState<Value> {
    var value: Value
    func with<R>(_ action: (Value) -> R) -> R { action(value) }
}
struct NagramiXArchivedRecord {
    let messageId: MessageId
    var namespace: Int32 { messageId.namespace }
    var threadId: Int64? = nil
    var groupingKey: Int64? = nil
    var hasLocalRemovalOwnership = true
    var wasTemporary = false
}
struct ArchiveState { var records: [String: NagramiXArchivedRecord] }
struct NagramiXMessageArchiveSettings {
    static var current = Self()
    var showDeletedMessages = true
    var saveTemporaryMessages = false
}
enum NagramiXTabSettings {
    static var current: NagramiXMessageArchiveSettings { NagramiXMessageArchiveSettings.current }
}

enum NoError: Error {}
struct Signal<V, E: Error> {
    let perform: (@escaping () -> Void) -> Void
    static func complete() -> Self { .init(perform: { $0() }) }
    func startStandalone(completed: @escaping () -> Void) { perform(completed) }
}
precedencegroup SignalPipeline {
    associativity: left
}
infix operator |> : SignalPipeline
func |> <A, B>(value: A, transform: (A) -> B) -> B { transform(value) }
func then(_ next: Signal<Void, NoError>) -> (Signal<Void, NoError>) -> Signal<Void, NoError> {
    return { first in .init(perform: { finish in first.perform { next.perform(finish) } }) }
}
func deliverOnMainQueue(_ signal: Signal<Void, NoError>) -> Signal<Void, NoError> { signal }

// ACTUAL_ARCHIVE_PLAN

final class Archive {
    var accountPeerId = PeerId(value: 1)
    var state = ReadState(value: ArchiveState(records: [:]))
    var purgedKeys = ReadState(value: Set<String>())
    private(set) var purges: [Set<MessageId>] = []
    private static func key(_ id: MessageId) -> String { "\(id.peerId.value):\(id.namespace):\(id.id)" }
    private static func makeRecord(message: Message, peers: [PeerId: Peer]) -> NagramiXArchivedRecord? {
        guard message.allowsArchive, !message.id.peerId.isVerificationCodes,
              !message.media.contains(where: { $0 is TelegramMediaExpiredContent }) else { return nil }
        return NagramiXArchivedRecord(messageId: message.id, threadId: message.threadId, groupingKey: message.groupingKey, wasTemporary: message.isTemporary)
    }
    func addRecord(_ record: NagramiXArchivedRecord) {
        state.value.records[Self.key(record.messageId)] = record
    }
    func preventCapture(_ id: MessageId) { purgedKeys.value.insert(Self.key(id)) }

    func deleteArchivedPosts(messageIds: Set<MessageId>, allowingLiveTemporaryMessageIds: Set<MessageId>) -> Signal<Void, NoError> {
        Signal { finish in
            if !messageIds.isEmpty { self.purges.append(messageIds) }
            finish()
        }
    }
// ACTUAL_ARCHIVE_METHODS
}

enum InteractiveMessagesDeletionType: Equatable { case forEveryone, forLocalPeer }
final class EngineMessages {
    var calls: [(Set<MessageId>, InteractiveMessagesDeletionType)] = []
    var finish: (() -> Void)?
    func deleteMessagesInteractively(messageIds: [MessageId], type: InteractiveMessagesDeletionType) -> Signal<Void, NoError> {
        Signal { finish in
            self.calls.append((Set(messageIds), type))
            self.finish = finish
        }
    }
}
struct Account { var peerId = PeerId(value: 1); let nagramiXMessageArchive: Archive }
struct Engine { let messages = EngineMessages() }
struct Strings {
    func Chat_MessagesDeletedToast_Text(_ count: Int32) -> String { String(count) }
}
struct PresentationData { let strings = Strings() }
struct CurrentPresentationData {
    func with<V>(_ body: (PresentationData) -> V) -> V { body(PresentationData()) }
}
struct SharedContext { let currentPresentationData = CurrentPresentationData() }
struct Context { let account: Account; let engine = Engine(); let sharedContext = SharedContext() }
enum ChatLocation {
    case peer(PeerId)
    var peerId: PeerId? {
        switch self { case let .peer(id): return id }
    }
}
final class HistoryNode {
    var ignoreMessageIds: Set<MessageId> = []
// ACTUAL_HISTORY_STATE
}
struct ChatDisplayNode { var historyNode = HistoryNode() }
enum UndoOverlayAction: Equatable { case commit, undo }
struct UndoOverlayController {
    enum Content { case removedChat(context: Context, title: NSAttributedString, text: String?) }
    enum Position { case top }
    let presentationData: PresentationData
    let content: Content
    let elevatedLayout: Bool
    let position: Position
    let action: (UndoOverlayAction) -> Bool
}
final class ChatControllerImpl {
    let chatDisplayNode = ChatDisplayNode()
    let context: Context
    let presentationData = PresentationData()
    var chatLocation = ChatLocation.peer(PeerId(value: 2))
    var overlays: [UndoOverlayController] = []
    var nativeFallbacks: [Set<MessageId>] = []
    enum Destination { case current }

    init(archive: Archive) { self.context = Context(account: Account(nagramiXMessageArchive: archive)) }
    func nagramiXBeginNativeDeleteMessagesWithUndo(messageIds: Set<MessageId>, type: InteractiveMessagesDeletionType) {
        nativeFallbacks.append(messageIds)
    }
    func present(_ controller: UndoOverlayController, in destination: Destination) { overlays.append(controller) }
// ACTUAL_CONTROLLER_METHOD
}

@main enum LocalDeleteChecks {
    static func main() {
        let peer = PeerId(value: 2)
        func id(_ value: Int, peer: PeerId = peer) -> MessageId { MessageId(peerId: peer, namespace: 0, id: value) }
        let round = Message(id: id(10), isTemporary: true)
        let voice = Message(id: id(20), isTemporary: true)
        let ordinary = Message(id: id(30))
        let protected = Message(id: id(40), allowsArchive: false)
        let purged = Message(id: id(50))
        let copyId = id(60)
        let saved = Message(id: id(70, peer: PeerId(value: 1)))
        let priorIgnore = id(90)
        let archive = Archive()
        archive.preventCapture(purged.id)
        archive.addRecord(.init(messageId: copyId))
        let live = [round, voice, ordinary, protected, purged, saved]
        let transaction = Transaction(live: Dictionary(uniqueKeysWithValues: live.map { ($0.id, $0) }))
        let ids = Set(live.map(\.id)).union([copyId])
        let retained: Set<MessageId> = [round.id, voice.id, ordinary.id]
        let plan = archive.postDeletionPlan(transaction: transaction, messageIds: ids, localCandidates: [copyId])
        precondition(plan.keepVisibleUntilDeletionIds == retained)
        precondition(plan.localMessageIds == [copyId])

        let chat = ChatControllerImpl(archive: archive)
        let history = chat.chatDisplayNode.historyNode
        history.ignoreMessageIds.insert(priorIgnore)
        chat.confirm(plan: plan, type: .forLocalPeer)
        precondition(history.ignoreMessageIds == ids.subtracting(retained).union([priorIgnore]), "retained rows must keep their list identity while Undo is open")
        precondition(history.nagramiXPendingRetainedDeletionIds == retained && chat.context.engine.messages.calls.isEmpty)
        let repeatPlan = archive.postDeletionPlan(transaction: transaction, messageIds: retained, localCandidates: [])
        chat.confirm(plan: repeatPlan, type: .forLocalPeer)
        precondition(chat.overlays.count == 1, "one pending delete per retained row")
        precondition(chat.overlays[0].action(.undo) && !chat.overlays[0].action(.commit))
        precondition(history.ignoreMessageIds == [priorIgnore] && history.nagramiXPendingRetainedDeletionIds.isEmpty && archive.purges.isEmpty)

        chat.confirm(plan: plan, type: .forLocalPeer)
        precondition(chat.overlays.last?.action(.commit) == true)
        precondition(chat.context.engine.messages.calls.count == 1 && chat.context.engine.messages.calls[0].0 == Set(live.map(\.id)) && chat.context.engine.messages.calls[0].1 == .forLocalPeer)
        precondition(archive.purges == [[copyId]])
        precondition(history.ignoreMessageIds.isDisjoint(with: retained), "no ignored IDs suppress native-to-archive handoff")
        chat.context.engine.messages.finish?()
        precondition(history.ignoreMessageIds == [priorIgnore] && history.nagramiXPendingRetainedDeletionIds.isEmpty)
        precondition(chat.overlays.last?.action(.undo) == false, "a committed action cannot run twice")

        let everyone = ChatControllerImpl(archive: archive)
        everyone.confirm(plan: repeatPlan, type: .forEveryone)
        precondition(everyone.overlays.isEmpty && everyone.chatDisplayNode.historyNode.ignoreMessageIds.isEmpty)
        precondition(everyone.context.engine.messages.calls.count == 1 && everyone.context.engine.messages.calls[0].0 == retained && everyone.context.engine.messages.calls[0].1 == .forEveryone)
        everyone.context.engine.messages.finish?()

        NagramiXMessageArchiveSettings.current.showDeletedMessages = false
        let native = ChatControllerImpl(archive: archive)
        let nativePlan = archive.postDeletionPlan(transaction: transaction, messageIds: retained, localCandidates: [])
        precondition(nativePlan.keepVisibleUntilDeletionIds.isEmpty)
        native.confirm(plan: nativePlan, type: .forLocalPeer)
        precondition(native.nativeFallbacks == [retained] && native.overlays.isEmpty)
        print("PASS retained round, voice and text during Undo, mixed deletion, duplicate tap, Undo/commit, everyone and archive disabled")
    }
}
