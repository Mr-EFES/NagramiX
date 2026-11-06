// Name formatting, archive lookup and editor widgets are boundaries. The
// author/entity map and deleted-message reply branch are extracted from UI.
struct TemporaryStrings { var User_DeletedAccount="Удалённый аккаунт" }
struct TemporaryPresentation { var strings=TemporaryStrings(); var nameDisplayOrder=0; var dateTimeFormat=0 }
extension EnginePeer {
    init(_ user:TestUser) { self = .user(user) }
    func displayTitle(strings:TemporaryStrings,displayOrder:Int)->String { if case let .user(user)=self {return user.name}; return strings.User_DeletedAccount }
}
extension EngineMessage { init(_ message:Message) { self = .raw(message) } }
func authoredTemporaryCopies(_ copyMessagesToForward:[Message])->[Message] {
    let chatPresentationInterfaceState=TemporaryPresentation()
    // PRODUCTION_AUTHOR_MAP
    return copies
}
final class TemporaryArchive { var deleted=true;func isLocallyDeletedMessage(id:MessageId)->Bool {deleted} }
struct TemporaryReplyAccount { let nagramiXMessageArchive=TemporaryArchive();var peerId=PeerId() }
struct TemporaryReplyContext { let account=TemporaryReplyAccount();let currentContentSettings=Atomic(value:ContentSettings()) }
struct ChatTextInputState { let inputText:NSAttributedString;let selectionRange:Range<Int> }
enum TemporaryInputMode { case text }
final class TemporaryInteraction {
    var state=ChatTextInputState(inputText:NSAttributedString(string:"Answer"),selectionRange:0..<0)
    func updateTextInputStateAndMode(_ f:(ChatTextInputState,TemporaryInputMode)->(ChatTextInputState,TemporaryInputMode)) {state=f(state,.text).0}
}
func descriptionStringForMessage(contentSettings:ContentSettings,message:EngineMessage,strings:TemporaryStrings,nameDisplayOrder:Int,dateTimeFormat:Int,accountPeerId:PeerId)->(NSAttributedString,Int) {(NSAttributedString(string:"Media"),0)}
final class TemporaryDismiss {func dismiss() {}}
final class TemporaryReplyHarness {
    let context=TemporaryReplyContext();let interfaceInteraction=TemporaryInteraction();var usedServerReply=false
    func reply(_ messages:[Message]) {
        let chatPresentationInterfaceState=TemporaryPresentation()
        let c:TemporaryDismiss?=TemporaryDismiss()
        // PRODUCTION_REPLY_BRANCH
        usedServerReply=true
    }
}
