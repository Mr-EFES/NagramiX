import Foundation

// Selection widgets, signals and DB scheduling are boundaries. The selection
// mutations, search callbacks, title switch, peer-store helper and send barrier
// are extracted from production by the validator.
typealias PeerId=Int
extension Int { var namespace: Int32 { 0 } }
enum Namespaces { enum Peer { static let CloudUser: Int32=0 } }
struct User { var id: Int }
struct Channel { var id: Int; var isForumOrMonoForum=false }
enum EnginePeer {
    typealias Id=Int
    case user(User),channel(Channel),community(Int),secretChat(Int)
    var id:Int { switch self { case let .user(p):return p.id;case let .channel(p):return p.id;case let .community(id),let .secretChat(id):return id } }
    func _asPeer()->Any { self }
    init(_ value: Any) { self=value as! EnginePeer }
}
enum ContactListPeerId: Hashable { case peer(Int) }
enum ContactListPeer: Equatable {
    case peer(peer:EnginePeer,isGlobal:Bool,participantCount:Int?)
    var id:ContactListPeerId { switch self { case let .peer(p,_,_):return .peer(p.id) } }
    static func ==(a:Self,b:Self)->Bool { a.id==b.id }
}
// PRODUCTION_CONTACT_STATE
struct ListState {
    var editing=false
    var selectedPeerIds=Set<Int>()
    var selectedPeerMap:[Int:EnginePeer]=[:]
    var foundPeers:[(EnginePeer,EnginePeer?)]=[]
    var nagramiXCopyThreadIds:[Int:Int64]=[:]
}
final class Contacts {
    var multipleSelection=false
    var nagramiXSelectionLimit:Int?=nil
    var state:ContactListNodeGroupSelectionState?
    func updateSelectionState(_ transform:(ContactListNodeGroupSelectionState?)->ContactListNodeGroupSelectionState?) { state=transform(state) }
    var selectedPeers:[ContactListPeer] {
        guard let state else {return []}
        return state.selectedPeerIndices.sorted{$0.value<$1.value}.compactMap{state.selectedPeerMap[$0.key]}
    }
}
final class Chats {
    var state=ListState()
    var currentState:ListState {state}
    var selectionLimit=1000
    func updateState(_ transform:(ListState)->ListState) {state=transform(state)}
}
final class Container { let currentItemNode=Chats();var nagramiXPreserveCopyRecipients=false }
final class SelectionController {var multipleSelectionLimit:Int?}
enum SendMode: Equatable {case generic,silent,schedule,whenOnline}
typealias SendRequest=([EnginePeer],[Int:EnginePeer],NSAttributedString,SendMode,Int?,Int?)->Void
struct InputState {var inputText=NSAttributedString(string:"")}
struct InterfaceState {var composeInputState=InputState();var forwardOptionsState:Int?=nil}
struct PresentationInterfaceState {var interfaceState=InterfaceState()}
final class SendPanel {
    var enabled=false
    var sendMessage:((SendMode,Int?)->Void)?
    func updateSendButtonEnabled(_ value:Bool,animated:Bool){enabled=value}
}
final class SendRequestBridge {
    var multiplePeersSelected:SendRequest?
    func connect(_ node:SelectionNode) {
        node.requestSend = // PRODUCTION_SEND_REQUEST_BRIDGE
    }
}
final class SelectionNode {
    var contactListActive=false
    let controller:SelectionController?=SelectionController()
    let contactListNode:Contacts?=Contacts()
    let mainContainerNode:Container?=Container()
    let chatListNode:Chats?=nil
    let textInputPanelNode:SendPanel?=SendPanel()
    let forwardedMessageIds:[Int]=[]
    var presentationInterfaceState=PresentationInterfaceState()
    var requestSend:SendRequest?
    func installSendButton() {
        textInputPanelNode!.sendMessage = // PRODUCTION_SEND_BUTTON_CALLBACK
    }
    // PRODUCTION_SELECTION_PROPERTIES
    // PRODUCTION_SELECT_RECIPIENT
    // PRODUCTION_SELECTED_PROPERTIES
    func beginSelection() {
        // PRODUCTION_BEGIN_SELECTION
        if contactListActive {contactListNode?.state=ContactListNodeGroupSelectionState()}
        else {mainContainerNode?.currentItemNode.state.editing=true}
    }
    func switchTab(_ active:Bool) {
        if nagramiXCopySelection,nagramiXCopySelectionStarted {nagramiXCopyRecipients=nagramiXActiveSelectedPeers}
        contactListActive=active
        nagramiXRestoreCopyRecipients()
    }
    var ids:Set<Int> {Set(selectedPeers.0.map{$0.id})}
    func selectChatSearch(_ peer:EnginePeer) {
        let strongSelf=self
        let chatPeer:EnginePeer?=nil
        let threadId:Int64?=nil
        var updated=false
        var ignoredSelectionContainer=false
        var count=0
        // PRODUCTION_CHAT_SEARCH_SELECTION
        textInputPanelNode?.updateSendButtonEnabled(count>0,animated:true)
        _=(updated,ignoredSelectionContainer)
    }
    func selectContactSearch(_ peer:ContactListPeer) {
        let strongSelf=self
        var updated=false
        var count=0
        // PRODUCTION_CONTACT_SEARCH_SELECTION
        _=updated
        textInputPanelNode?.updateSendButtonEnabled(count>0,animated:true)
    }
}
struct PresentationStrings {
    var values:[String:String]
    var nagramiXForwardWithAuthor:String {values["NagramiX.Context.ForwardWithAuthor"]!}
    var nagramiXForwardWithoutAuthor:String {values["NagramiX.Context.ForwardWithoutAuthor"]!}
    var nagramiXBroadcastMessages:String {values["NagramiX.Context.BroadcastMessages"]!}
}
// PRODUCTION_TRANSFER_MODE
func selectsCopy(_ transferMode:NagramiXMessageTransferMode)->Bool {
    // PRODUCTION_COPY_PICKER_PREDICATE
}
func selectionLimit(_ transferMode:NagramiXMessageTransferMode)->Int? {
    // PRODUCTION_PICKER_LIMIT
}

enum NoError {}
final class Signal<T,E> {
    let subscribe:(@escaping(T)->Void)->Void
    init(_ subscribe:@escaping(@escaping(T)->Void)->Void) {self.subscribe=subscribe}
    @discardableResult func start(next:@escaping(T)->Void)->Int {subscribe(next);return 0}
    static func single(_ value:T)->Self {Self{$0(value)}}
}
precedencegroup PipeRight {
    associativity: left
    higherThan: DefaultPrecedence
}
infix operator |> : PipeRight
func |> <A,B>(value:A,transform:(A)->B)->B {transform(value)}
func take<T,E>(_ count:Int)->(Signal<T,E>)->Signal<T,E> {
    {source in Signal {out in var remaining=count;source.subscribe{value in if remaining>0 {remaining-=1;out(value)}}}}
}
func mapToSignal<T,U,E>(_ transform:@escaping(T)->Signal<U,E>)->(Signal<T,E>)->Signal<U,E> {{source in Signal{out in source.subscribe{transform($0).subscribe(out)}}}}
func combineLatest<T,E>(_ signals:[Signal<T,E>])->Signal<[T],E> {
    Signal {out in
        var values:[T?]=Array(repeating:nil,count:signals.count)
        for (i,signal) in signals.enumerated() {signal.subscribe{value in values[i]=value;if values.allSatisfy({$0 != nil}) {out(values.map{$0!})}}}
    }
}
enum GroupId {case root,archive}
enum Inclusion {case notIncluded;case ifHasMessagesOrOneOf(groupId:GroupId,pinningIndex:Int?,minTimestamp:Int?)}
struct MigrationReference {var peerId:Int}
final class TelegramGroup {var migrationReference:MigrationReference?}
final class Postbox {
    var peers:[Int:EnginePeer]=[:]
    var inclusions:[Int:Inclusion]=[:]
    var pending:[()->Void]=[]
    func transaction<T>(_ body:@escaping(Transaction)->T)->Signal<T,NoError> {
        Signal{out in self.pending.append {let value=body(Transaction(self));out(value)}}
    }
    func flushOne() {if !pending.isEmpty {pending.removeFirst()()}}
    func flushAll() {while !pending.isEmpty {flushOne()}}
}
final class Transaction {
    let db:Postbox
    init(_ db:Postbox){self.db=db}
    func getPeer(_ id:Int)->Any? {db.peers[id]}
    func getPeerChatListInclusion(_ id:Int)->Inclusion {db.inclusions[id] ?? .notIncluded}
    func updatePeerChatListInclusion(_ id:Int,inclusion:Inclusion) {db.inclusions[id]=inclusion}
}
func updatePeersCustom(transaction:Transaction,peers:[Any],update:(Any?,Any)->Any) {
    for value in peers {let p=value as! EnginePeer;transaction.db.peers[p.id]=update(transaction.getPeer(p.id),p) as? EnginePeer}
}
// PRODUCTION_STORE_PEER
enum TelegramEngine {enum EngineData {enum Item {enum Peer {
    struct SendPaidMessageStars {let id:Int}
    struct RenderedPeer {let id:Int}
}}}}
struct EngineDataMap {let peers:[TelegramEngine.EngineData.Item.Peer.SendPaidMessageStars];init(_ peers:[TelegramEngine.EngineData.Item.Peer.SendPaidMessageStars]){self.peers=peers}}
struct EngineDataList {let peers:[TelegramEngine.EngineData.Item.Peer.RenderedPeer];init(_ peers:[TelegramEngine.EngineData.Item.Peer.RenderedPeer]){self.peers=peers}}
final class DataEngine {
    let db:Postbox
    var queries=0
    var missingQueries=0
    init(_ db:Postbox){self.db=db}
    func get(_ stars:EngineDataMap,_ peers:EngineDataList)->Signal<Int,NoError> {
        queries+=1
        if peers.peers.contains(where:{db.peers[$0.id]==nil}) {missingQueries+=1}
        return .single(peers.peers.count)
    }
}
final class Account {let postbox:Postbox;init(_ db:Postbox){postbox=db}}
final class PeersEngine {
    let account:Account
    init(_ db:Postbox){account=Account(db)}
    // PRODUCTION_ENGINE_STORE_WRAPPER
}
final class Engine {let data:DataEngine;let peers:PeersEngine;init(_ db:Postbox){data=DataEngine(db);peers=PeersEngine(db)}}
final class Context {let account:Account;let engine:Engine;init(_ db:Postbox){account=Account(db);engine=Engine(db)}}
func prepareRecipients(_ peers:[EnginePeer],peerMap:[Int:EnginePeer],context:Context,done:@escaping(Int)->Void) {
    // PRODUCTION_PEERS_TO_STORE
    let _ = (
    // PRODUCTION_PEER_BARRIER
    ).start(next:done)
}
func includeQueuedChat(_ transaction:Transaction,peerId:Int) {
    // PRODUCTION_CHAT_INCLUSION
}

@main struct TransferConsistencyTests {
    static func main() throws {
        var checks=0
        func check(_ ok:@autoclosure()->Bool,_ label:String){if !ok(){fatalError("Transfer consistency regression: "+label)};checks+=1}
        let a=EnginePeer.user(User(id:10)),b=EnginePeer.user(User(id:20)),forum=EnginePeer.channel(Channel(id:30,isForumOrMonoForum:true))
        for isContacts in [false,true] {
            for single in [false,true] {
                let node=SelectionNode(),bridge=SendRequestBridge()
                node.nagramiXCopySelection=true;node.contactListActive=isContacts
                node.controller!.multipleSelectionLimit=single ? 1:nil
                node.beginSelection();node.installSendButton();bridge.connect(node)
                var sends=0
                let caption=NSAttributedString(string:"Видео и текст 😀",attributes:[NSAttributedString.Key("bold"):true])
                node.presentationInterfaceState.interfaceState.composeInputState.inputText=caption
                node.presentationInterfaceState.interfaceState.forwardOptionsState=7
                bridge.multiplePeersSelected={peers,map,text,mode,options,effect in
                    check(Set(peers.map{$0.id})==(single ? [10]:[10,20]),"send button passes every chosen recipient")
                    check(Set(map.keys)==Set(peers.map{$0.id}),"send bridge keeps all peer records")
                    check(text.isEqual(to:caption) && options==7 && effect==9,"send button preserves text/entities and options")
                    check([SendMode.generic,.silent,.schedule,.whenOnline].contains(mode),"native send mode reaches transfer callback")
                    sends+=1
                }
                node.textInputPanelNode!.sendMessage?(.generic,9)
                check(sends==0,"empty selection cannot send")
                node.nagramiXSelectCopyRecipient(a,threadId:nil)
                if !single {node.nagramiXSelectCopyRecipient(b,threadId:nil)}
                check(node.textInputPanelNode!.enabled,"send button enabled with chosen recipients")
                for mode in [SendMode.generic,.silent,.schedule,.whenOnline] {node.textInputPanelNode!.sendMessage?(mode,9)}
                check(sends==4,"each tap reaches the real transfer callback exactly once")
            }
        }
        for startContacts in [false,true] {
            let node=SelectionNode();node.nagramiXCopySelection=true;node.contactListActive=startContacts;node.beginSelection()
            node.nagramiXSelectCopyRecipient(a,threadId:nil)
            check(node.ids==[10],"single picked recipient is selected")
            if startContacts {check(node.contactListNode!.state!.foundPeers.contains{$0.id == .peer(10)},"picked contact is visible")}
            else {check(node.mainContainerNode!.currentItemNode.state.foundPeers.contains{$0.0.id==10},"picked chat is visible")}
            node.nagramiXSelectCopyRecipient(a,threadId:nil)
            check(node.ids==[10],"repeated selection does not remove or duplicate recipient")
            node.switchTab(!startContacts)
            check(node.ids==[10],"selection survives tabs")
            if !startContacts {check(node.contactListNode!.state!.foundPeers.contains{$0.id == .peer(10)},"contact remains visible after tab switch")}
            else {check(node.mainContainerNode!.currentItemNode.state.foundPeers.contains{$0.0.id==10},"chat remains visible after tab switch")}
            node.nagramiXSelectCopyRecipient(b,threadId:nil)
            node.switchTab(startContacts)
            node.nagramiXSelectCopyRecipient(forum,threadId:77)
            check(node.ids==[10,20,30],"broadcast preserves all contacts and selected topic")
            node.switchTab(false)
            check(node.mainContainerNode!.currentItemNode.state.nagramiXCopyThreadIds[30]==77,"topic remains explicit")
        }
        let chat=SelectionNode();chat.nagramiXCopySelection=true;chat.beginSelection();chat.selectChatSearch(a)
        check(chat.ids==[10] && chat.mainContainerNode!.currentItemNode.state.foundPeers.contains{$0.0.id==10},"search result enters the visible chat selector")
        chat.selectChatSearch(a);check(chat.ids.isEmpty,"search selection can be toggled off")
        let contacts=SelectionNode();contacts.nagramiXCopySelection=true;contacts.contactListActive=true;contacts.beginSelection();contacts.selectContactSearch(.peer(peer:a,isGlobal:true,participantCount:nil))
        check(contacts.ids==[10] && contacts.contactListNode!.state!.foundPeers.contains{$0.id == .peer(10)},"search result enters the visible contacts selector")
        for isContacts in [false,true] {
            let single=SelectionNode();single.nagramiXCopySelection=true;single.controller!.multipleSelectionLimit=1;single.contactListActive=isContacts;single.beginSelection();single.nagramiXSelectCopyRecipient(a,threadId:nil);single.nagramiXSelectCopyRecipient(b,threadId:nil)
            check(single.ids==[10],"single-forward callback cannot add a second recipient")
            if isContacts {single.selectContactSearch(.peer(peer:b,isGlobal:true,participantCount:nil))} else {single.selectChatSearch(b)}
            check(single.ids==[10],"single-forward search cannot add a second recipient")
            single.switchTab(!isContacts);check(single.ids==[10],"single limit survives tab changes")
        }
        let catalogs=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))) as! [[String:Any]]
        for catalog in catalogs {
            let values=catalog["values"] as! [String:String],strings=PresentationStrings(values:values)
            let expected=[values["NagramiX.Context.ForwardWithAuthor"]!,values["NagramiX.Context.ForwardWithoutAuthor"]!,values["NagramiX.Context.BroadcastMessages"]!]
            check(NagramiXMessageTransferMode.forwardWithSource.selectionTitle(strings:strings)==expected[0],"localized Repost title")
            check(NagramiXMessageTransferMode.forwardWithoutSource.selectionTitle(strings:strings)==expected[1],"localized Forward title")
            check(NagramiXMessageTransferMode.copyToSingleRecipient.selectionTitle(strings:strings)==expected[1],"local single copy keeps Forward title")
            check(NagramiXMessageTransferMode.copyAsNew.selectionTitle(strings:strings)==expected[2],"localized Broadcast title")
        }
        for mode in [NagramiXMessageTransferMode.forwardWithSource,.forwardWithoutSource,.copyAsNew,.copyToSingleRecipient] {
            check(selectsCopy(mode)==mode.copiesAsNew,"both copy modes use the same batch picker")
            check(selectionLimit(mode)==(mode.singleRecipient ? 1:nil),"only Forward is limited to one recipient")
        }
        let db=Postbox(),context=Context(db)
        var completed=0
        prepareRecipients([a,b],peerMap:[30:forum],context:context){completed=$0}
        check(context.engine.data.queries==0 && completed==0,"lookup/send waits for peer-store commit")
        check(db.pending.count==3,"all chosen and associated peer-map values are persisted")
        db.flushOne();check(context.engine.data.queries==0,"one persisted peer cannot release the whole send")
        db.flushAll()
        check(context.engine.data.queries==1 && context.engine.data.missingQueries==0 && completed==2,"lookup starts once with complete recipient records")
        check(Set(db.peers.keys)==[10,20,30],"no search recipient is omitted")
        includeQueuedChat(Transaction(db),peerId:10)
        if case .ifHasMessagesOrOneOf(groupId:.root,_,_)=db.inclusions[10] {checks+=1} else {fatalError("Transfer consistency regression: new chat not included immediately")}
        db.inclusions[20] = .ifHasMessagesOrOneOf(groupId:.archive,pinningIndex:4,minTimestamp:nil)
        includeQueuedChat(Transaction(db),peerId:20)
        if case .ifHasMessagesOrOneOf(groupId:.archive,pinningIndex:4,_)=db.inclusions[20] {checks+=1} else {fatalError("existing archived chat changed")}
        print("Transfer consistency checks: \(checks)")
    }
}
