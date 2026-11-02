import Foundation
enum EngineMessage { typealias Id = MessageId }
struct InlineRow { var nagramiXInlineParentIndex: Int? }
struct RowResult { var enabled:Bool; var selectable:Bool; var opened:[Int]; var threads:[Int64?]; var toggled:[Int] }
final class RowInteraction {
 var opened:[Int]=[], threads:[Int64?]=[], toggled:[Int]=[]
 func peerSelected(_ p:EnginePeer,_ a:Int?,_ t:Int64?,_ b:Int?,_ c:Bool) {opened.append(p.id);threads.append(t)}
 func togglePeerSelected(_ p:EnginePeer,_ t:Int64?) {toggled.append(p.id)}
}
enum TreeMode { case peers(ChatListNodePeersFilter,Bool,Int,Int,Int,Int,Int) }
enum TreeLocation { case chatList(Int), forum(peerId:Int) }
struct Rendered { var peerId:Int }
struct Thread { var id:Int64 }
enum ChatListNodeEntry {
 struct PeerEntryData {
  var index:Int; var peer:Rendered; var threadInfo:Thread?; var selected=false
  var nagramiXInlineParentIndex:Int?; var nagramiXInlineOrder=0; var nagramiXInlineExpanded=false
 }
 case PeerEntry(PeerEntryData), HeaderEntry
}
struct EngineChatList { var rows:[ChatListNodeEntry] }
func chatListNodeEntriesForView(view:EngineChatList,state:SelectionState,savedMessagesPeer:Int?,foundPeers:[Int],hideArchivedFolderByDefault:Bool,displayArchiveIntro:Bool,mode:TreeMode,chatListLocation:TreeLocation,contacts:[Int],accountPeerId:Int,isMainTab:Bool)->([ChatListNodeEntry],Bool) {(view.rows,false)}
final class TopicHost {
 var mode=TreeMode.peers(.nagramiXCopyDestinations,false,0,0,0,0,0)
 var location=TreeLocation.chatList(0)
 var currentState=SelectionState()
 var peerSelected:((EnginePeer,Int64?,Bool,Bool,Int?)->Void)?
 func updateState(_ f:(SelectionState)->SelectionState) {currentState=f(currentState)}
 init() {
  peerSelected = { [weak self] peer, thread, _, _, _ in
   self?.currentState.selectedPeerIds.insert(peer.id)
   self?.currentState.selectedPeerMap[peer.id]=peer
   self?.currentState.nagramiXCopyThreadIds[peer.id]=thread
  }
 }
}
@main struct InlineTests {
 static func main() {
  Tests.main()
  let forum=EnginePeer.channel(Channel(id:40,isForum:true))
  let other=EnginePeer.channel(Channel(id:50,isForum:true))
  let person=EnginePeer.user(10)
  var checks=0
  func check(_ value:Bool) { checks+=1;precondition(value) }
  for row in [inlineRowInsert,inlineRowUpdate] {
   let parent=row(forum,true,false,nil,.nagramiXCopyDestinations,true)
   check(!parent.selectable && parent.opened == [40] && parent.toggled.isEmpty)
   let child=row(forum,true,false,9,.nagramiXCopyDestinations,true)
   check(child.selectable && child.toggled == [40] && child.opened.isEmpty)
   check(!row(forum,true,false,9,.nagramiXCopyDestinations,false).enabled)
   check(row(person,true,false,nil,.nagramiXCopyDestinations,true).toggled == [10])
  }
  let host=TopicHost();host.currentState.selectedPeerIds=[10]
  host.tap(forum,threadId:9);check(host.currentState.selectedPeerIds == [10,40])
  host.tap(other,threadId:9);check(host.currentState.nagramiXCopyThreadIds == [40:9,50:9])
  host.tap(forum,threadId:10);check(host.currentState.nagramiXCopyThreadIds == [40:10,50:9])
  func parent(_ id:Int,_ index:Int)->ChatListNodeEntry {.PeerEntry(.init(index:index,peer:Rendered(peerId:id)))}
  func topic(_ id:Int,_ thread:Int64)->ChatListNodeEntry {.PeerEntry(.init(index:100,peer:Rendered(peerId:id),threadInfo:Thread(id:thread)))}
  let source=[parent(10,1),parent(40,2),parent(50,3)]
  let lists=[40:EngineChatList(rows:[.HeaderEntry,topic(40,9),topic(40,10)]),50:EngineChatList(rows:[topic(50,9)])]
  let tree=makeTree(source,lists:lists,state:host.currentState)
  check(tree.count == 6)
  for i in tree.indices { for j in tree.indices where i < j {
   check(inlineLess(tree[i],tree[j]) && !inlineLess(tree[j],tree[i]))
  } }
  var selected:[String]=[]
  for entry in tree {
   guard case let .PeerEntry(data)=entry else {continue}
   if let thread=data.threadInfo {
    check(data.nagramiXInlineParentIndex == (data.peer.peerId == 40 ? 2:3))
    check(data.nagramiXInlineOrder < 0)
    if data.selected {selected.append("\(data.peer.peerId):\(thread.id)")}
   }
  }
  check(selected == ["40:10","50:9"])
  check(makeTree(source,lists:[:],state:host.currentState).count == 3)
  check(host.currentState.selectedPeerIds == [10,40,50]) // collapse never deselects
  host.tap(forum,threadId:10)
  check(host.currentState.selectedPeerIds == [10,50] && host.currentState.nagramiXCopyThreadIds[40] == nil)
  check(makeTree(source,lists:lists,state:host.currentState).filter { if case let .PeerEntry(d)=$0 {return d.selected};return false }.count == 1)
  let first=Folder(),second=Folder(),container=FolderContainer()
  first.listNode.currentState=host.currentState;container.currentItemNodeValue=first;container.nagramiXPreserveCopyRecipients=true
  container.activate(second);check(second.listNode.currentState.nagramiXCopyThreadIds == [50:9])
  print("PASS \(checks) actual inline tree/row/toggle/folder checks; UIKit/network are boundaries")
 }
}
