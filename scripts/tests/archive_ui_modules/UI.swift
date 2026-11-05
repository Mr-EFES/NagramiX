import TelegramCore
import NagramiXCore
import SwiftSignalKit
import AccountContext

// UIKit/engine scheduling are boundaries. Production helper bodies and their
// signatures are inserted unchanged, in a client with no Postbox import.
private enum Subject { case message, pinned }
private protocol ContextControllerProtocol {}
private final class UIView {}
private enum ContextMenuActionResult { case dismiss }
private struct Location { var peerId: EnginePeer.Id? { fatalError("interface only") } }
private struct Interface { var subject: Subject? { fatalError("interface only") } }
private final class History {
    func messageGroupInCurrentHistoryView(_ id: EngineMessage.Id) -> [EngineRawMessage]? { fatalError("interface only") }
}
private final class Display { var historyNode: History { fatalError("interface only") } }
private final class Account {
    var peerId: EnginePeer.Id { fatalError("interface only") }
    var nagramiXMessageArchive: NagramiXMessageArchive { fatalError("interface only") }
}
private final class Messages {
    func nagramiXArchivePostDeletionPlan(messageIds: Set<EngineMessage.Id>, localCandidates: Set<EngineMessage.Id>) -> Signal<NagramiXArchivePostDeletionPlan, NoError> { fatalError("interface only") }
}
private final class Engine { var messages: Messages { fatalError("interface only") } }
private final class Shared {
    func chatAvailableMessageActions(engine: Engine, accountPeerId: EnginePeer.Id, messageIds: Set<EngineMessage.Id>, keepUpdated: Bool) -> Signal<ChatAvailableMessageActions, NoError> { fatalError("interface only") }
}
private final class Context {
    var account: Account { fatalError("interface only") }
    var engine: Engine { fatalError("interface only") }
    var sharedContext: Shared { fatalError("interface only") }
}
private final class Controller {
    var isNodeLoaded: Bool { false }
    var nagramiXReadHistoryDisabled: Bool { false }
    var chatLocation: Location { fatalError("interface only") }
    var presentationInterfaceState: Interface { fatalError("interface only") }
    var context: Context { fatalError("interface only") }
    var chatDisplayNode: Display { fatalError("interface only") }
    // ACTUAL_METHODS
}
// ACTUAL_POST
