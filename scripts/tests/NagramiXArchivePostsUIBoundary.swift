// UIKit/UndoOverlay and native engine submission boundaries. The actual
// selection helper and two-phase commit/undo method are inserted unchanged.
infix operator |> : AdditionPrecedence
func |> <A,B>(value:A, transform:(A)->B)->B {transform(value)}
func deliverOnMainQueue<T,E>(_ source:Signal<T,E>)->Signal<T,E>{source}
func then<T,E>(_ next:Signal<T,E>)->(Signal<T,E>)->Signal<T,E>{ { first in Signal{ subscriber in
    first.startStandalone(next:subscriber.putNext,completed:{_ = next.startStandalone(next:subscriber.putNext,completed:subscriber.putCompletion)})
}} }
enum InteractiveMessagesDeletionType {case forEveryone,forLocalPeer}
enum ChatControllerSubject {case message,pinnedMessages,scheduledMessages,messageOptions}
enum ChatLocation {case peer(PeerId);var peerId:PeerId? {switch self {case let .peer(id): return id}}}
private final class UIAccount {let peerId=PeerId(9);let nagramiXMessageArchive:Archive;init(_ archive:Archive){self.nagramiXMessageArchive=archive}}
private final class UIEngineMessages {
    let archive:Archive;var requests:[Set<MessageId>]=[]
    init(_ archive:Archive){self.archive=archive}
    func deleteMessagesInteractively(messageIds:[MessageId],type:InteractiveMessagesDeletionType)->Signal<Void,NoError>{Signal{subscriber in
        self.requests.append(Set(messageIds));self.archive.mark(Set(messageIds));subscriber.putCompletion();return EmptyDisposable
    }}
}
private final class UIEngine {let messages:UIEngineMessages;init(_ archive:Archive){messages=UIEngineMessages(archive)}}
struct UIStrings {func Chat_MessagesDeletedToast_Text(_ count:Int32)->String{"deleted \(count)"}}
struct UIPresentation {let strings=UIStrings()}
final class UISharedContext {let currentPresentationData=Atomic(value:UIPresentation())}
private final class UIContext {let account:UIAccount;let engine:UIEngine;let sharedContext=UISharedContext();init(_ archive:Archive){account=UIAccount(archive);engine=UIEngine(archive)}}
final class UIHistory {var ignoreMessageIds:Set<MessageId>=[];var groups:[MessageId:[Message]]=[:];func messageGroupInCurrentHistoryView(_ id:MessageId)->[Message]?{groups[id]}}
final class UIDisplay {let historyNode=UIHistory()}
struct UIInterface {var subject:ChatControllerSubject?}
enum UndoAction {case commit,undo}
enum UndoPosition {case top}
enum UIPlace {case current}
private enum UndoContent {case removedChat(context:UIContext,title:NSAttributedString,text:String?)}
private final class UndoOverlayController {
    let action:(UndoAction)->Bool
    init(presentationData:UIPresentation,content:UndoContent,elevatedLayout:Bool,position:UndoPosition,action:@escaping(UndoAction)->Bool){self.action=action}
}
private final class UIHost {
    let context:UIContext
    let presentationData=UIPresentation()
    let chatDisplayNode=UIDisplay()
    var presentationInterfaceState=UIInterface()
    var isNodeLoaded=true
    var nagramiXReadHistoryDisabled=false
    var chatLocation=ChatLocation.peer(PeerId(1))
    var undo:UndoOverlayController?
    init(_ archive:Archive){context=UIContext(archive)}
    func present(_ controller:UndoOverlayController,in place:UIPlace){undo=controller}
    // Actual computed scope, selection helper and commit/undo method are inserted.
}
