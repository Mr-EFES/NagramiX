#!/usr/bin/env python3
"""Проверить явное удаление временной копии без преждевременного purge до Undo."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
FILE = 'submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift'
ARCHIVE = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'


def verify(source, baseline=None):
    text=(source/FILE).read_text()
    plan_path=OVERLAY/'temporary_message_interaction_patches.json'
    if plan_path.exists():
        plan=json.loads(plan_path.read_text())
        assert hashlib.sha256((source/FILE).read_bytes()).hexdigest()==plan['outputs'][FILE]
        old=(OVERLAY/plan['previous'][FILE]).read_text()
    else:
        assert baseline is not None
        old=(baseline/FILE).read_text()
    marker='    private func nagramiXBeginNativeDeleteMessagesWithUndo('
    assert block(text,marker)==block(old,marker), 'Ordinary native deletion was rewritten'
    scope=block(text,'    private var nagramiXArchivePostScope:')
    assert '!self.nagramiXReadHistoryDisabled' in scope
    assert 'NagramiXTabSettings.current.showDeletedMessages || temporaryEnabled' in scope
    assert 'peerId.namespace != Namespaces.Peer.SecretChat || temporaryEnabled' in scope
    assert 'case nil, .message: return true' in scope
    custom=block(text,'    private func nagramiXDeleteArchivedPostsWithUndo(')
    assert 'allowingLiveTemporaryMessageIds: plan.localMessageIds)' in custom
    assert 'local |> then(native)' in custom
    assert 'if plan.localMessageIds.isEmpty && (!NagramiXTabSettings.current.showDeletedMessages || self.chatLocation.peerId?.namespace == Namespaces.Peer.SecretChat)' in custom
    assert custom.index('let commit =') < custom.index('deleteArchivedPosts(') < custom.index('if immediate { commit(); return }')
    undo=custom[custom.index('if value == .undo'):]
    assert 'commit()' not in undo and 'deleteArchivedPosts' not in undo
    archive=(source/ARCHIVE).read_text()
    assert 'public func deleteArchivedPosts(messageIds: Set<MessageId>, allowingLiveTemporaryMessageIds: Set<MessageId> = [])' in archive
    # No other admin actions, restrictions, warnings or dialog variants change.
    a=old;b=text
    for marker in ['    private var nagramiXArchivePostScope:', '    private func nagramiXDeleteArchivedPostsWithUndo(']:
        a=a.replace(block(a,marker),'SCOPED_BLOCK',1)
        b=b.replace(block(b,marker),'SCOPED_BLOCK',1)
    assert a==b,'Unrelated admin/delete code changed'
    return text


def fixture(text,mode='current'):
    scope=block(text,'    private var nagramiXArchivePostScope:')
    custom=block(text,'    private func nagramiXDeleteArchivedPostsWithUndo(')
    native=block(text,'    private func nagramiXBeginNativeDeleteMessagesWithUndo(')
    if mode=='native-first': custom=custom.replace('local |> then(native)','native |> then(local)')
    elif mode=='intersection-only': custom=custom.replace('allowingLiveTemporaryMessageIds: plan.localMessageIds','allowingLiveTemporaryMessageIds: plan.localMessageIds.intersection(plan.nativeMessageIds)')
    elif mode=='early-purge': custom=custom.replace('if immediate { commit(); return }','commit(); if immediate { return }')
    elif mode=='no-native-ordinary':
        old=block(custom,'        if plan.localMessageIds.isEmpty && (!NagramiXTabSettings.current.showDeletedMessages || self.chatLocation.peerId?.namespace == Namespaces.Peer.SecretChat) {')
        custom=custom.replace(old,'',1)
    elif mode=='no-secret-scope': scope=scope.replace('peerId.namespace != Namespaces.Peer.SecretChat || temporaryEnabled','peerId.namespace != Namespaces.Peer.SecretChat')
    elif mode=='mutate-undo': custom=custom.replace('if value == .undo { self.chatDisplayNode.historyNode.ignoreMessageIds.subtract(messageIds); return true }','if value == .undo { commit(); self.chatDisplayNode.historyNode.ignoreMessageIds.subtract(messageIds); return true }')
    elif mode=='readonly-bypass': scope=scope.replace('!self.nagramiXReadHistoryDisabled, ','')
    return '''import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
// The three real UI scope/commit/undo methods execute. The Signal scheduler,
// Postbox/native delete, archive persistence and UIKit overlay are explicit adapters.
struct PeerId: Equatable { let namespace:Int;let value:Int }
enum Namespaces { enum Peer { static let SecretChat=2 } }
enum EngineMessage { typealias Id=Int64 }
enum ChatLocation { case peer(PeerId), custom
    var peerId: PeerId? { if case let .peer(id)=self {return id};return nil }
}
enum Subject { case message, scheduledMessages, other }
struct PresentationState { var subject:Subject? }
struct Settings { var showDeletedMessages=false }
enum NagramiXTabSettings { static var current=Settings() }
var temporaryEnabled=false
func nagramiXTemporaryMessagesEnabled()->Bool { temporaryEnabled }
enum InteractiveMessagesDeletionType { case forEveryone, forLocalPeer }
enum NoError: Error {}
final class Disposable {}
final class Signal<Value,ErrorType:Error> {
    let work:()->Void
    init(_ work:@escaping ()->Void) {self.work=work}
    static func complete()->Signal { Signal({}) }
    @discardableResult func startStandalone(completed:@escaping ()->Void={}) -> Disposable {work();completed();return Disposable()}
}
infix operator |> : AdditionPrecedence
func |> <A,B>(_ value:A,_ f:(A)->B)->B { f(value) }
func then(_ next:Signal<Void,NoError>)->(Signal<Void,NoError>)->Signal<Void,NoError> { return { first in Signal { first.work();next.work() } } }
func deliverOnMainQueue(_ value:Signal<Void,NoError>)->Signal<Void,NoError> { value }
final class State {
    var live:Set<Int64>=[]
    var records:Set<Int64>=[]
    var tombstones:Set<Int64>=[]
    var events:[String]=[]
    var allowed:Set<Int64>=[]
    var temporaryApprovalRequired:Set<Int64>=[]
}
final class Archive {
    let state:State
    init(_ state:State) {self.state=state}
    func deleteArchivedPosts(messageIds:Set<Int64>,allowingLiveTemporaryMessageIds:Set<Int64>=[])->Signal<Void,NoError> {
        return Signal { self.state.events.append("local");self.state.allowed=allowingLiveTemporaryMessageIds
            let approved=messageIds.subtracting(self.state.temporaryApprovalRequired).union(messageIds.intersection(allowingLiveTemporaryMessageIds))
            self.state.records.subtract(approved);self.state.tombstones.formUnion(approved)
        }
    }
}
final class Messages {
    let state:State
    init(_ state:State) {self.state=state}
    func deleteMessagesInteractively(messageIds:[Int64],type:InteractiveMessagesDeletionType)->Signal<Void,NoError> {
        return Signal { self.state.events.append("native")
            for id in messageIds where !self.state.tombstones.contains(id) { self.state.records.insert(id) }
            self.state.live.subtract(messageIds)
        }
    }
}
final class Account { let peerId=PeerId(namespace:0,value:1);let nagramiXMessageArchive:Archive;init(_ s:State){nagramiXMessageArchive=Archive(s)} }
final class Engine { let messages:Messages;init(_ s:State){messages=Messages(s)} }
struct Strings { func Chat_MessagesDeletedToast_Text(_ count:Int32)->String {String(count)} }
struct PresentationData { let strings=Strings() }
struct CurrentData { func with<T>(_ f:(PresentationData)->T)->T {f(PresentationData())} }
struct SharedContext { let currentPresentationData=CurrentData() }
final class Context { let account:Account;let engine:Engine;let sharedContext=SharedContext();init(_ s:State){account=Account(s);engine=Engine(s)} }
final class History { var ignoreMessageIds:Set<Int64>=[] }
final class DisplayNode { let historyNode=History() }
enum UndoAction { case commit, undo, other }
enum OverlayContent { case removedChat(context:Context,title:NSAttributedString,text:String?) }
enum Position { case top }
enum PresentationLocation { case current }
final class UndoOverlayController {
    let action:(UndoAction)->Bool
    init(presentationData:PresentationData,content:OverlayContent,elevatedLayout:Bool,position:Position,action:@escaping (UndoAction)->Bool) {self.action=action}
}
struct NagramiXArchivePostDeletionPlan {let nativeMessageIds:Set<Int64>;let localMessageIds:Set<Int64>}
final class ChatControllerImpl {
    let context:Context
    var nagramiXReadHistoryDisabled=false
    var chatLocation=ChatLocation.peer(PeerId(namespace:0,value:7))
    var presentationInterfaceState=PresentationState(subject:nil)
    var isNodeLoaded=true
    let chatDisplayNode=DisplayNode()
    let presentationData=PresentationData()
    var overlay:UndoOverlayController?
    init(_ state:State) {context=Context(state)}
    func present(_ overlay:UndoOverlayController,in location:PresentationLocation) {self.overlay=overlay}
'''+scope+'\n'+custom+'\n'+native+'''
    var scope:Bool {nagramiXArchivePostScope}
    func delete(_ plan:NagramiXArchivePostDeletionPlan,_ type:InteractiveMessagesDeletionType) {nagramiXDeleteArchivedPostsWithUndo(plan:plan,type:type)}
}
var checks=0
func check(_ value:@autoclosure ()->Bool,_ label:String) {if !value(){FileHandle.standardError.write(Data(("delete UI regression: "+label+"\\n").utf8));exit(91)};checks += 1}
@main struct Main {
    static func main() {
        let state=State(),controller=ChatControllerImpl(State())
        NagramiXTabSettings.current.showDeletedMessages=false;temporaryEnabled=false
        check(!controller.scope,"all off native scope")
        temporaryEnabled=true
        check(controller.scope,"TEMP-only scope")
        controller.chatLocation = .peer(PeerId(namespace:2,value:9))
        check(controller.scope,"TEMP secret scope")
        temporaryEnabled=false;NagramiXTabSettings.current.showDeletedMessages=true
        check(!controller.scope,"ordinary deleted feature keeps secret excluded")
        temporaryEnabled=true;controller.nagramiXReadHistoryDisabled=true
        check(!controller.scope,"readonly never mutates")
        controller.nagramiXReadHistoryDisabled=false;controller.presentationInterfaceState.subject = .scheduledMessages
        check(!controller.scope,"scheduled stays native")
        controller.presentationInterfaceState.subject = .message
        check(controller.scope,"ordinary message subject accepted")
        NagramiXTabSettings.current.showDeletedMessages=false;temporaryEnabled=true
        state.live=[42];state.records=[42]
        state.temporaryApprovalRequired=[42]
        let c=ChatControllerImpl(state)
        c.chatDisplayNode.historyNode.ignoreMessageIds=[901]
        let plan=NagramiXArchivePostDeletionPlan(nativeMessageIds:[42],localMessageIds:[42])
        c.delete(plan,.forLocalPeer)
        check(state.events.isEmpty && state.records==[42] && state.tombstones.isEmpty,"no mutation before Undo choice")
        check(c.chatDisplayNode.historyNode.ignoreMessageIds==[901,42],"hide selected row only while Undo pending")
        check(c.overlay?.action(.undo)==true,"Undo accepted")
        check(state.events.isEmpty && state.live==[42] && state.records==[42],"Undo rolls back before purge and native")
        check(c.chatDisplayNode.historyNode.ignoreMessageIds==[901],"Undo preserves unrelated ignore owners")
        c.delete(plan,.forLocalPeer)
        check(c.overlay?.action(.commit)==true,"commit accepted")
        check(state.events==["local","native"],"purge precedes native capture")
        check(state.allowed==[42],"only frozen local IDs approved")
        check(state.records.isEmpty && state.tombstones==[42] && state.live.isEmpty,"no resurrection after explicit live delete")
        check(c.chatDisplayNode.historyNode.ignoreMessageIds==[901],"commit restores owned row visibility")
        let immediate=State();immediate.live=[8];immediate.records=[8]
        let d=ChatControllerImpl(immediate)
        d.delete(NagramiXArchivePostDeletionPlan(nativeMessageIds:[8],localMessageIds:[8]),.forEveryone)
        check(d.overlay==nil && immediate.events==["local","native"],"global delete uses immediate native timing")
        check(immediate.records.isEmpty,"immediate temp copy purged")
        let retained=State();retained.records=[11];retained.temporaryApprovalRequired=[11]
        let retainedController=ChatControllerImpl(retained)
        retainedController.delete(NagramiXArchivePostDeletionPlan(nativeMessageIds:[],localMessageIds:[11]),.forEveryone)
        check(retained.allowed==[11],"retained temporary with no native row remains explicitly approved")
        check(retained.records.isEmpty && retained.events==["local"],"unexpired retained-only snapshot purges without native delete")
        let ordinary=State();ordinary.live=[3]
        let e=ChatControllerImpl(ordinary)
        e.delete(NagramiXArchivePostDeletionPlan(nativeMessageIds:[3],localMessageIds:[]),.forEveryone)
        check(ordinary.events==["native"],"ordinary TEMP-only uses exact native path")
        check(ordinary.allowed.isEmpty && ordinary.tombstones.isEmpty,"ordinary native has no local purge")
        NagramiXTabSettings.current.showDeletedMessages=true
        let secretOrdinary=State();secretOrdinary.live=[13]
        let secretController=ChatControllerImpl(secretOrdinary)
        secretController.chatLocation = .peer(PeerId(namespace:2,value:9))
        secretController.delete(NagramiXArchivePostDeletionPlan(nativeMessageIds:[13],localMessageIds:[]),.forEveryone)
        check(secretOrdinary.events==["native"],"ordinary secret with both settings keeps native path")
        check(secretOrdinary.allowed.isEmpty,"ordinary secret never approves local purge")
        let first=State();first.live=[7]
        let f=ChatControllerImpl(first)
        f.delete(NagramiXArchivePostDeletionPlan(nativeMessageIds:[7],localMessageIds:[]),.forEveryone)
        check(first.records==[7] && first.tombstones.isEmpty,"deleted feature first click still retains")
        check(first.allowed.isEmpty,"first click never approves live purge")
        f.delete(NagramiXArchivePostDeletionPlan(nativeMessageIds:[],localMessageIds:[7]),.forEveryone)
        check(first.records.isEmpty && first.tombstones==[7],"deleted feature second click purges")
        check(first.events==["local","native","local"],"second stage needs no native deletion")
        print("PASS temporary delete UI checks: \\(checks)")
    }
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--baseline',type=Path)
    p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path)
    args=p.parse_args();text=verify(args.source,args.baseline)
    runs=[];negative=[]
    with tempfile.TemporaryDirectory(prefix='temporary-delete-ui-') as folder:
        root=Path(folder)
        for mode in ['current','native-first','intersection-only','early-purge','no-native-ordinary','no-secret-scope','mutate-undo','readonly-bypass']:
            source=root/(mode+'.swift');source.write_text(fixture(text,mode))
            for opt in [False,True]:
                binary=root/(mode+('-O' if opt else '-debug'))
                command=[str(args.swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(root/'cache')]
                if opt:command+=['-O']
                subprocess.run([*command,str(source),'-o',str(binary)],check=True)
                result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
                if mode=='current':
                    assert result.returncode==0,result.stdout+result.stderr;runs.append(result.stdout.strip())
                else:
                    assert result.returncode==91 and 'delete UI regression:' in result.stderr,(mode,result.stdout,result.stderr)
                    negative.append({'mode':mode,'optimized':opt,'diagnostic':result.stderr.strip()})
        subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/FILE)],check=True)
    report={'production_runs':runs,'semantic_negatives':negative,'source_sha256':hashlib.sha256((args.source/FILE).read_bytes()).hexdigest(),'parse_files':1,'boundary':'Actual UI scope, commit/Undo and unchanged native delete methods execute; cold Signals, UIKit overlay, native Postbox delete and archive persistence are adapters. Core deletion plan/tombstone behavior is tested separately.','sdk':'not run','device':'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
