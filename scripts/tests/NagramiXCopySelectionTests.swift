@main struct CopySelectionTests {
    static func main() {
        var checks=0
        func check(_ value:@autoclosure()->Bool,_ label:String){if !value(){fatalError("Copy selection regression: "+label)};checks+=1}
        let a=EnginePeer.user(User(id:10)), b=EnginePeer.user(User(id:20)), c=EnginePeer.user(User(id:30))
        for contacts in [false,true] {
            for single in [false,true] {
                let node=SelectionNode();node.nagramiXCopySelection=true;node.contactListActive=contacts
                node.controller!.multipleSelectionLimit=single ? 1:nil
                node.beginSelection()
                node.nagramiXSelectCopyRecipient(a,threadId:nil)
                if contacts {check(node.contactListNode!.state!.foundPeers.isEmpty,"existing contact not promoted")}
                else {check(node.mainContainerNode!.currentItemNode.state.foundPeers.isEmpty,"existing chat not promoted")}
                node.nagramiXSelectCopyRecipient(b,threadId:nil)
                check(node.ids == (single ? [20]:[10,20]),"single selection replaces, broadcast accumulates")
                node.nagramiXRecordFoundCopyRecipient(c)
                check(node.nagramiXCopyFoundAnchors[c.id] == (single ? [20]:[10,20]),"search freezes selected anchors")
                node.nagramiXSelectCopyRecipient(c,threadId:77)
                check(node.ids == (single ? [30]:[10,20,30]),"found recipient selected")
                node.switchTab(!contacts)
                check(node.ids == (single ? [30]:[10,20,30]),"recipients survive switching tabs")
                check(node.nagramiXCopyThreads[30] == 77,"search topic retained")
                node.switchTab(contacts)
                check(node.nagramiXCopyFoundPeers.map{$0.id} == [30],"existing recipients never become search results")
            }
        }
        for contacts in [false,true] {
            let node=SelectionNode();node.nagramiXCopySelection=true;node.contactListActive=contacts;node.controller!.multipleSelectionLimit=1;node.beginSelection()
            node.nagramiXSelectCopyRecipient(a,threadId:nil)
            if contacts {node.selectContactSearch(.peer(peer:b,isGlobal:true,participantCount:nil))}
            else {node.selectChatSearch(b)}
            check(node.ids == [20],"actual search callback replaces single selection")
            check(node.nagramiXCopyFoundAnchors[20] == [10],"actual search callback freezes prior recipients")
        }
        let existing=(0..<5).map { ChatListNodeEntry.peer(id:$0,order:100-$0,thread:nil) }
        let search=EnginePeer.user(User(id:50))
        var state=ListState();state.nagramiXCopyMode=2
        var result=existing+[ChatListNodeEntry.peer(id:50,order:200,thread:nil)]
        state.nagramiXCopySearchAnchors[50]=[1,3]
        let sorted=arrange(result,state:state,found:[(search,nil)],native:existing)
        check(sorted == [0,1,2,3,50,4],"search row inserted after previously selected rows")
        state.selectedPeerIds=[0,1,3,4]
        check(arrange(result,state:state,found:[(search,nil)],native:existing) == sorted,"later selections do not move search row")
        state.nagramiXCopySearchAnchors[50]=[]
        check(arrange(result,state:state,found:[(search,nil)],native:existing) == [50,0,1,2,3,4],"first search stays at top")
        check(arrange(existing,state:state,found:[(a,nil)],native:existing) == [0,1,2,3,4],"searching a native row does not move it")
        result=[.peer(id:30,order:3,thread:101),.peer(id:30,order:2,thread:102),.peer(id:30,order:1,thread:103)]
        check(arrange(result,state:state,found:[],native:result) == [30,30,30],"same-peer forum topics keep distinct identities without a dictionary trap")
        let contact = ContactListPeer.peer(peer:search,isGlobal:true,participantCount:nil)
        var contacts = ContactListNodeGroupSelectionState().withFoundPeers([contact])
        contacts.nagramiXCopyMode=2;contacts.nagramiXCopySearchAnchors[.peer(50)]=[.peer(1),.peer(3)]
        var contactRows:[ContactListNodeEntry] = [.row(50),.row(0),.row(1),.row(2),.row(3),.row(4)]
        nagramiXArrangeCopyContacts(&contactRows,state:contacts,nativePeerIds:Set((0..<5).map { .peer($0) }))
        let contactIds=contactRows.compactMap { item -> Int? in if case let .peer(_,peer,_,_,_,_,_,_,_,_,_,_,_,_,_,_)=item,case let .peer(value,_,_)=peer{return value.id};return nil }
        check(contactIds == [0,1,2,3,50,4],"Contacts tab shares frozen-anchor ordering")
        var duplicateRows:[ContactListNodeEntry] = [.row(50),.row(50),.header(7),.row(0)]
        nagramiXArrangeCopyContacts(&duplicateRows,state:contacts,nativePeerIds:[.peer(0)])
        check(duplicateRows.count==4,"story/contact rows for the same peer are not collapsed")
        print("Copy selection/order checks: \(checks)")
    }
}
