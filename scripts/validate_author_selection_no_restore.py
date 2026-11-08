#!/usr/bin/env python3
"""Проверить read-only выбор автора, пагинацию и отложенное подтверждение."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
STAGE = 'author_selection_no_restore'
PLAN = json.loads((OVERLAY / (STAGE + '_patches.json')).read_text())
CORE = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXAuthorSelection.swift'
UI = 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(root):
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    text = (source / CORE).read_text()
    for forbidden in ['account.network', 'Api.', 'transaction.addMessages', 'updatePeers(', 'StoreMessage(', 'getMessagesLoadIfNecessary', 'import TelegramApi']:
        assert forbidden not in text, 'Selection must not load or restore history: ' + forbidden
    ui = author_body((source / UI).read_text())
    assert 'Array(Set(localIds + archivedIds))' in ui
    assert 'existingLocalIds + archivedIds.filter { currentArchivedIds.contains($0) }' in ui
    assert ui.count('self.presentationInterfaceState.subject == nil && NagramiXTabSettings.current.showDeletedMessages') == 2
    assert ui.count('self.nagramiXSelectAuthorGeneration == generation') == 4


def author_body(text):
    start = text.index('        }, selectMessagesByAuthor: { [weak self] authorId in')
    end = text.index('        }, updateForwardOptionsState:', start)
    return text[start:end].split('\n', 1)[1]


def guard_checks(source, folder):
    spec = importlib.util.spec_from_file_location(STAGE, OVERLAY / (STAGE + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    apply = getattr(module, 'apply_' + STAGE)
    count = 0

    def seed(label):
        root = folder / label
        for name, origin in {**PLAN['previous'], **PLAN['guard_sources']}.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OVERLAY / origin, p)
        return root

    def reject(root, overlay=OVERLAY):
        nonlocal count
        old = snapshot(root)
        try:
            apply(root, overlay)
        except (SystemExit, OSError, KeyError):
            pass
        else:
            raise AssertionError('Unsafe application accepted')
        assert snapshot(root) == old, 'Failed validation made a partial write'
        count += 1

    valid = seed('valid')
    apply(valid, OVERLAY)
    assert all((valid / n).read_bytes() == (source / n).read_bytes() for n in PLAN['outputs'])
    reject(valid)
    for name in {**PLAN['inputs'], **PLAN['guards']}:
        for mutation in ['drift', 'missing']:
            root = seed(str(count))
            p = root / name
            if mutation == 'missing':
                p.unlink()
            else:
                p.write_bytes(p.read_bytes() + b'\n// drift\n')
            reject(root)
    variants = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        plan = copy.deepcopy(PLAN)
        plan[field][next(iter(plan[field]))] = '0' * 64
        variants.append(plan)
    for field in ['previous', 'replacements']:
        plan = copy.deepcopy(PLAN)
        plan[field][CORE] = '../outside.swift'
        variants.append(plan)
    for field in ['target_pin', 'overlay_base_pin']:
        plan = copy.deepcopy(PLAN)
        plan[field] = '0' * 40
        variants.append(plan)
    plan = copy.deepcopy(PLAN)
    plan['copies'] = {'new.swift': {'source': PLAN['replacements'][CORE], 'sha256': PLAN['outputs'][CORE]}}
    variants.append(plan)
    for plan in variants:
        overlay = folder / ('overlay-' + str(count))
        for name in PLAN['templates']:
            p = overlay / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OVERLAY / name, p)
        (overlay / (STAGE + '_patches.json')).write_text(json.dumps(plan))
        reject(seed(str(count)), overlay)
    return count


HEADER = 'import Foundation\n\nenum NoError {}\nenum SignalResult<V, E> { case value(V); case error(E) }\nfinal class Disposable { let action: () -> Void; init(_ action: @escaping () -> Void = {}) { self.action = action }; func dispose() { action() } }\nfinal class MetaDisposable { var value: Disposable?; func set(_ value: Disposable?) { self.value?.dispose(); self.value = value } }\npublic final class Signal<V, E> {\n    let run: () -> SignalResult<V, E>\n    var onDispose: (() -> Void)?\n    init(_ run: @escaping () -> SignalResult<V, E>) { self.run = run }\n    static func single(_ v: V) -> Signal<V, E> { Signal { .value(v) } }\n    static func fail(_ e: E) -> Signal<V, E> { Signal { .error(e) } }\n    func start(next: @escaping (V) -> Void, error: ((E) -> Void)? = nil) -> Disposable {\n        switch self.run() { case let .value(v): next(v); case let .error(e): error?(e) }\n        return Disposable { self.onDispose?() }\n    }\n}\ninfix operator |> : AdditionPrecedence\nfunc |> <T,U>(v: T, f: (T)->U) -> U { f(v) }\nfunc castError<V,E>(_ type: E.Type) -> (Signal<V,NoError>)->Signal<V,E> { { s in Signal<V,E> { switch s.run() { case let .value(v): return .value(v); case .error: fatalError() } } } }\nfunc mapToSignal<A,B,E>(_ f: @escaping (A)->Signal<B,E>) -> (Signal<A,E>)->Signal<B,E> { { s in Signal<B,E> { switch s.run() { case let .value(v): return f(v).run(); case let .error(e): return .error(e) } } } }\nfunc deliverOnMainQueue<V,E>(_ signal: Signal<V,E>) -> Signal<V,E> { signal }\nfunc afterDisposed<V,E>(_ f: @escaping () -> Void) -> (Signal<V,E>)->Signal<V,E> { { s in s.onDispose = f; return s } }\nfinal class Queue { static func mainQueue() -> Queue { Queue() }; func async(_ f: () -> Void) { f() } }\npublic struct PeerId: Hashable, Comparable { let raw: Int64; init(_ raw: Int64) { self.raw=raw }; public static func <(l: Self,r: Self)->Bool { l.raw < r.raw } }\npublic struct MessageId: Hashable, Comparable {\n    let peerId: PeerId; let namespace: Int32; let id: Int32\n    public static func <(l: Self,r: Self)->Bool { if l.peerId != r.peerId { return l.peerId < r.peerId }; if l.namespace != r.namespace { return l.namespace < r.namespace }; return l.id < r.id }\n}\nstruct MessageIndex: Comparable {\n    let id: MessageId; let timestamp: Int32\n    public static func <(l: Self,r: Self)->Bool { if l.timestamp != r.timestamp { return l.timestamp < r.timestamp }; return l.id < r.id }\n    static func upperBound(peerId: PeerId, namespace: Int32) -> Self { Self(id: MessageId(peerId: peerId,namespace: namespace,id: Int32.max),timestamp: Int32.max) }\n    static func lowerBound(peerId: PeerId, namespace: Int32) -> Self { Self(id: MessageId(peerId: peerId,namespace: namespace,id: Int32.min),timestamp: Int32.min) }\n}\nclass Peer { let id: PeerId; init(_ id: PeerId) { self.id=id } }\nfinal class TelegramChannel: Peer {}\nstruct MigrationReference { let maxMessageId: MessageId }\nfinal class CachedChannelData { let migrationReference: MigrationReference?; init(_ p: PeerId?) { migrationReference=p.map { MigrationReference(maxMessageId: MessageId(peerId:$0,namespace:0,id:1)) } } }\nstruct Message { let id: MessageId; let index: MessageIndex; let author: Peer?; let threadId: Int64? }\nenum Namespaces { enum Message { static let Cloud: Int32=0, Local: Int32=1, SecretIncoming: Int32=2, EphemeralLocal: Int32=3, ScheduledCloud: Int32=4, QuickReplyCloud: Int32=5 } }\nfinal class Transaction {\n    var peers: [PeerId:Peer]=[:]; var messages: [MessageId:Message]=[:]; var cached: [PeerId:CachedChannelData]=[:]\n    var pageCalls=0; var fetchedMessages=0; var stalled=false\n    func getPeer(_ id: PeerId)->Peer? { peers[id] }\n    func getPeerCachedData(peerId: PeerId)->Any? { cached[peerId] }\n    func getMessage(_ id: MessageId)->Message? { messages[id] }\n    func page(peerId: PeerId, namespace: Int32, threadId: Int64?, from: MessageIndex, to: MessageIndex, limit: Int)->[Message] {\n        pageCalls += 1\n        if stalled { return Array(messages.values.sorted {$0.index > $1.index}.prefix(1)) }\n        let result=Array(messages.values.filter { m in m.id.peerId==peerId && m.id.namespace==namespace && (threadId==nil || m.threadId==threadId) && m.index < from && m.index > to }.sorted {$0.index > $1.index}.prefix(limit))\n        fetchedMessages += result.count\n        return result\n    }\n    func getMessages(peerId: PeerId, namespace: Int32, from: MessageIndex, includeFrom: Bool, to: MessageIndex, limit: Int)->[Message] { assert(!includeFrom); return page(peerId:peerId,namespace:namespace,threadId:nil,from:from,to:to,limit:limit) }\n    func getMessagesWithThreadId(peerId: PeerId, namespace: Int32, threadId: Int64, from: MessageIndex, includeFrom: Bool, to: MessageIndex, limit: Int)->[Message] { assert(!includeFrom); return page(peerId:peerId,namespace:namespace,threadId:threadId,from:from,to:to,limit:limit) }\n}\nfinal class Postbox {\n    let value: Transaction; var transactions=0; var beforeTransaction: ((Int,Transaction)->Void)?\n    init(_ value: Transaction) { self.value=value }\n    func transaction<T>(_ f: @escaping (Transaction)->T)->Signal<T,NoError> { Signal { self.transactions += 1; self.beforeTransaction?(self.transactions,self.value); return .value(f(self.value)) } }\n}\nstruct TabValues { var showDeletedMessages=false }\nenum NagramiXTabSettings { static var current=TabValues() }\nfinal class Archive {\n    var values: [Message]=[]\n    func deletedMessages(peerId: PeerId, threadId: Int64?, minIndex: MessageIndex?, maxIndex: MessageIndex?, limit: Int)->[Message] { guard NagramiXTabSettings.current.showDeletedMessages else { return [] }; return values.filter { $0.id.peerId==peerId && (threadId==nil || $0.threadId==threadId) } }\n}\npublic final class Account { let postbox: Postbox; let nagramiXMessageArchive=Archive(); init(_ t: Transaction) { postbox=Postbox(t) } }\nstruct Theme {}\nstruct Strings { let nagramiXAuthorSelectionEmpty="empty", nagramiXAuthorSelectionFailed="failed", Common_OK="OK" }\nstruct PresentationData { var theme=Theme(); var strings=Strings() }\nfinal class PresentationDataHolder { var value=PresentationData(); func with<T>(_ f: (PresentationData)->T)->T { f(value) } }\nfinal class SharedContext { let currentPresentationData=PresentationDataHolder() }\nfinal class Context { let account: Account; let sharedContext=SharedContext(); init(_ account: Account) { self.account=account } }\nstruct ChatLocation { var peerId: PeerId?; var threadId: Int64? }\nstruct InterfaceState { var selected: [MessageId]=[]; func withUpdatedSelectedMessages(_ ids: [MessageId])->Self { var next=self;next.selected=ids;return next } }\nstruct PresentationState {\n    var subject: String?; var interfaceState=InterfaceState()\n    func updatedInterfaceState(_ f:(InterfaceState)->InterfaceState)->Self { var next=self; next.interfaceState=f(next.interfaceState);return next }\n    func updatedShowCommands(_ value: Bool)->Self { self }\n}\nenum OverlayType { case loading(cancelled: ()->Void) }\nfinal class OverlayStatusController { let type: OverlayType; var dismissed=false; init(theme: Theme,type: OverlayType) { self.type=type }; func dismiss() { dismissed=true } }\nenum WindowPosition { case root }; enum PresentationLocation { case window(WindowPosition) }; enum PresentationAnimation { case modalSheet }\nstruct ViewControllerPresentationArguments { init(presentationAnimation: PresentationAnimation) {} }\nenum AlertActionType { case defaultAction }\nstruct TextAlertAction { init(type: AlertActionType,title: String,action: ()->Void) {} }\nfinal class Alert { let text: String;init(_ text:String) { self.text=text } }\nfunc textAlertController(context: Context,updatedPresentationData: Int?,title: String?,text:String,actions:[TextAlertAction])->Alert { Alert(text) }\nfinal class Controller {\n    let context: Context\n    var isNodeLoaded=true; var nagramiXIsSelectingAuthorMessages=false; var nagramiXSelectAuthorGeneration: UInt64=0\n    let nagramiXSelectAuthorDisposable=MetaDisposable();var nagramiXSelectedAuthorMessageIds: Set<MessageId>?\n    var chatLocation: ChatLocation;var presentationData=PresentationData();var updatedPresentationData: Int?\n    var presentationInterfaceState=PresentationState();var pendingDiscard: (() -> Void)?;var deferDiscard=false\n    var presented:[AnyObject]=[];var updates=0\n    init(_ account: Account,_ peer: PeerId,threadId: Int64?=nil) { self.context=Context(account);self.chatLocation=ChatLocation(peerId:peer,threadId:threadId) }\n    func present(_ controller: AnyObject,in location: PresentationLocation,with arguments: ViewControllerPresentationArguments?=nil) { presented.append(controller) }\n    func presentVoiceMessageDiscardAlert(action: @escaping ()->Void,alertAction: ()->Void,delay: Bool)->Bool { if deferDiscard {pendingDiscard=action} else {action()};return true }\n    func updateChatPresentationInterfaceState(animated: Bool,interactive:Bool,_ f:(PresentationState)->PresentationState) { updates += 1;presentationInterfaceState=f(presentationInterfaceState) }\n// ACTUAL_UI_METHOD\n}\n'

TESTS = 'var count=0\nfunc check(_ value: @autoclosure ()->Bool,_ label:String) { count += 1; if !value() { print("FAIL "+label); exit(91) } }\nlet p=PeerId(10), q=PeerId(20), author=PeerId(30), other=PeerId(40)\nfunc msg(_ id:Int32,peer:PeerId=p,ns:Int32=0,authorId:PeerId=author,thread:Int64?=nil)->Message { let mid=MessageId(peerId:peer,namespace:ns,id:id);return Message(id:mid,index:MessageIndex(id:mid,timestamp:id),author:Peer(authorId),threadId:thread) }\nfunc make(_ messages:[Message],channel:Bool=false)->Account { let t=Transaction();t.peers[p]=channel ? TelegramChannel(p) : Peer(p);t.peers[q]=Peer(q);t.peers[author]=Peer(author);for m in messages {t.messages[m.id]=m};return Account(t) }\nfunc selected(_ a: Account,peer:PeerId=p,thread:Int64?=nil)->[MessageId] { switch nagramiXMessagesByAuthor(account:a,peerId:peer,authorId:author,threadId:thread).run() { case let .value(ids):return ids;case .error:return [] } }\nfunc snapshot(_ a:Account)->[MessageId] { a.postbox.value.messages.keys.sorted() }\nlet many=(1...650).map { msg(Int32($0)) };let a=make(many)\nlet before=snapshot(a);check(selected(a)==many.map {$0.id}.sorted(),"complete pagination over 650 messages");check(snapshot(a)==before,"selection performs no history writes");check(a.postbox.value.pageCalls>=7,"all namespaces and older pages read")\nlet intervening=(1...450).map { msg(Int32($0),authorId:$0>200 ? other : author) };let b=make(intervening)\ncheck(selected(b)==intervening.filter {$0.author?.id==author}.map {$0.id}.sorted(),"page of another author does not stop older traversal")\nlet namespaces=(0...5).map { msg(1,ns:Int32($0)) };let c=make(namespaces)\ncheck(selected(c)==namespaces.filter {$0.id.namespace<4}.map {$0.id}.sorted(),"cloud local secret ephemeral only")\nlet scoped=[msg(1),msg(2,authorId:other),msg(3,peer:q),msg(4,thread:77),msg(5,thread:88)]\nlet d=make(scoped);check(selected(d)==[scoped[0].id,scoped[3].id,scoped[4].id].sorted(),"real sender and current peer only");check(selected(d,thread:77)==[scoped[3].id],"thread exact")\nlet migrated=make([msg(1),msg(2,peer:q)],channel:true);migrated.postbox.value.cached[p]=CachedChannelData(q)\ncheck(Set(selected(migrated))==Set([msg(1).id,msg(2,peer:q).id]),"migrated group existing history included")\nlet regular=make([msg(1),msg(2,peer:q)]);regular.postbox.value.cached[p]=CachedChannelData(q)\ncheck(selected(regular)==[msg(1).id],"nonchannel does not import migration peer")\nlet e=make([msg(1)]);let lazy=nagramiXMessagesByAuthor(account:e,peerId:p,authorId:author,threadId:nil)\ncheck(e.postbox.transactions==0,"subscription is lazy");e.postbox.value.messages.removeAll();switch lazy.run() {case let .value(v):check(v.isEmpty,"deletion before subscription not restored");case .error:check(false,"deleted peer remains available")}\nlet f=make([msg(1),msg(2)]);f.postbox.beforeTransaction={ n,t in if n>2 && t.pageCalls>=4 { t.messages.removeValue(forKey:msg(1).id) } }\ncheck(selected(f)==[msg(2).id],"deletion during pagination excluded by final existence check")\nlet g=make([msg(1)]);g.postbox.value.stalled=true\nswitch nagramiXMessagesByAuthor(account:g,peerId:p,authorId:author,threadId:nil).run() {case .error(.stalled):check(true,"nonprogressing index rejected");default:check(false,"nonprogressing index rejected")}\nlet missing=make([]);missing.postbox.value.peers.removeValue(forKey:p)\nswitch nagramiXMessagesByAuthor(account:missing,peerId:p,authorId:author,threadId:nil).run() {case .error(.unavailable):check(true,"missing peer fails without partial result");default:check(false,"missing peer fails")}\nlet repeated=make([msg(1)]);check(selected(repeated)==selected(repeated),"repeat subscription independent");repeated.postbox.value.messages.removeAll();check(selected(repeated).isEmpty,"repeat after deletion remains empty")\nNagramiXTabSettings.current.showDeletedMessages=false\nlet u=make([msg(1),msg(2,authorId:other)]);u.nagramiXMessageArchive.values=[msg(3)]\nlet ui=Controller(u,p);ui.selectAuthor(author)\ncheck(ui.nagramiXSelectedAuthorMessageIds==Set([msg(1).id]),"UI off selects existing sender only");check(ui.updates==1,"UI applies exactly one selection");check(!ui.nagramiXIsSelectingAuthorMessages,"UI releases selection admission")\nNagramiXTabSettings.current.showDeletedMessages=true\nlet u2=make([msg(1)]);u2.nagramiXMessageArchive.values=[msg(3),msg(4,authorId:other),msg(5,peer:q)]\nlet ui2=Controller(u2,p);ui2.selectAuthor(author)\ncheck(ui2.nagramiXSelectedAuthorMessageIds==Set([msg(1).id,msg(3).id]),"UI on selects only current author archive");check(snapshot(u2)==[msg(1).id],"archive selection never inserts history")\nlet ui3=Controller(u2,p);ui3.presentationInterfaceState.subject="scheduled";ui3.selectAuthor(author)\ncheck(ui3.nagramiXSelectedAuthorMessageIds==Set([msg(1).id]),"auxiliary history does not reveal archive")\nlet u4=make([msg(1)]);u4.nagramiXMessageArchive.values=[msg(3)]\nlet ui4=Controller(u4,p);ui4.deferDiscard=true;ui4.selectAuthor(author)\ncheck(ui4.updates==0 && ui4.pendingDiscard != nil,"discard confirmation precedes selection")\nNagramiXTabSettings.current.showDeletedMessages=false;ui4.pendingDiscard?()\ncheck(ui4.nagramiXSelectedAuthorMessageIds==Set([msg(1).id]),"archive off during confirmation excluded")\nNagramiXTabSettings.current.showDeletedMessages=true\nlet u5=make([msg(1)]);u5.nagramiXMessageArchive.values=[msg(3)]\nlet ui5=Controller(u5,p);ui5.deferDiscard=true;ui5.selectAuthor(author);u5.postbox.value.messages.removeAll();u5.nagramiXMessageArchive.values.removeAll();ui5.pendingDiscard?()\ncheck(ui5.updates==0,"delete local and archive during confirmation stays deleted");check(snapshot(u5).isEmpty,"confirmation cannot restore deleted IDs")\nlet u6=make([msg(1)]);u6.nagramiXMessageArchive.values=[msg(3)]\nlet ui6=Controller(u6,p);ui6.deferDiscard=true;ui6.selectAuthor(author);u6.nagramiXMessageArchive.values.append(msg(7));ui6.pendingDiscard?()\ncheck(ui6.nagramiXSelectedAuthorMessageIds==Set([msg(1).id,msg(3).id]),"new archive IDs not added to pending snapshot")\nlet ui7=Controller(make([msg(1)]),p);ui7.deferDiscard=true;ui7.selectAuthor(author);ui7.chatLocation.peerId=q;ui7.pendingDiscard?();check(ui7.updates==0,"changed chat rejects stale intent")\nlet ui8=Controller(make([msg(1)]),p);ui8.deferDiscard=true;ui8.selectAuthor(author);ui8.nagramiXSelectAuthorGeneration &+= 1;ui8.pendingDiscard?();check(ui8.updates==0,"new generation rejects stale intent")\nlet ui9=Controller(make([msg(1)]),p);ui9.deferDiscard=true;ui9.selectAuthor(author);ui9.chatLocation.threadId=77;ui9.pendingDiscard?();check(ui9.updates==0,"changed thread rejects stale intent")\nlet ui10=Controller(make([msg(1)]),p);ui10.isNodeLoaded=false;ui10.selectAuthor(author);check(ui10.updates==0 && ui10.presented.isEmpty,"unloaded UI does not select")\nlet ui11=Controller(make([msg(1)]),p);ui11.nagramiXIsSelectingAuthorMessages=true;ui11.selectAuthor(author);check(ui11.presented.isEmpty,"concurrent selection refused")\nlet ui12=Controller(make([]),p);ui12.selectAuthor(author);check(ui12.updates==0 && ui12.presented.contains {$0 is Alert},"empty result uses alert without selection")\nfinal class WeakControllerBox { weak var value: Controller?; init(_ value: Controller) {self.value=value} }\nvar transient: Controller?=Controller(make([msg(1)]),p);transient!.deferDiscard=true;transient!.selectAuthor(author)\nlet weakController=WeakControllerBox(transient!);let pendingAction=transient!.pendingDiscard;transient=nil\ncheck(weakController.value==nil,"deferred selection does not retain departed controller");pendingAction?()\nprint("PASS author selection production checks: \\(count)")\n'


def fixture(core, body):
    # Preserve the original weak-self entry closure and its whole production body.
    method = '    func selectAuthor(_ authorId: PeerId) {\n        let action: (PeerId) -> Void = { [weak self] authorId in\n' + body + '\n        }\n        action(authorId)\n    }\n'
    core = '\n'.join(line for line in core.splitlines() if not line.startswith('import '))
    return HEADER.replace('// ACTUAL_UI_METHOD', method) + '\n' + core + '\n' + TESTS


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def execute(source, swiftc, folder):
    core = (source / CORE).read_text()
    body = author_body((source / UI).read_text())
    mutations = []
    def core_mutation(label, old, new):
        assert old in core, label
        mutations.append((label, core.replace(old, new), body))
    core_mutation('author-page-gap', 'return messages.map { $0.index }.min()', 'return messages.filter { $0.author?.id == authorId }.map { $0.index }.min()')
    core_mutation('missing-older-pages', 'return collectLocal(peer: peer, namespaceIndex: namespaceIndex, from: next)', 'return .single(Void())')
    core_mutation('missing-local-namespaces', 'let localNamespaces = [Namespaces.Message.Cloud, Namespaces.Message.Local, Namespaces.Message.SecretIncoming, Namespaces.Message.EphemeralLocal]', 'let localNamespaces = [Namespaces.Message.Cloud]')
    mutations.append(('other-author-selection', core.replace('message.id.peerId == peer.id && message.author?.id == authorId', 'message.id.peerId == peer.id').replace('transaction.getMessage($0)?.author?.id == authorId', 'transaction.getMessage($0) != nil'), body))
    core_mutation('late-deletion-restored-id', 'return selectedIds.filter { transaction.getMessage($0)?.author?.id == authorId }.sorted()', 'return selectedIds.sorted()')
    core_mutation('scheduled-history-leak', 'Namespaces.Message.EphemeralLocal]', 'Namespaces.Message.EphemeralLocal, Namespaces.Message.ScheduledCloud]')
    core_mutation('migration-ignored', 'if let previousPeer {\n                return collectLocal(peer: previousPeer)\n            }', 'if let previousPeer {\n                _ = previousPeer\n            }')
    mutations.append(('stale-archive-selection', core, body.replace('currentArchivedIds.contains($0)', 'currentArchivedIds.contains($0) || archivedIds.contains($0)')))
    mutations.append(('local-recheck-removed', core, body.replace('return localIds.filter { transaction.getMessage($0)?.author?.id == authorId }', 'return localIds')))
    mutations.append(('chat-guard-removed', core, body.replace('self.chatLocation.peerId == peerId', 'true')))
    mutations.append(('generation-guard-removed', core, body.replace('self.nagramiXSelectAuthorGeneration == generation', 'self.nagramiXSelectAuthorGeneration >= generation')))
    runs = []
    negatives = []
    cache = folder / 'module-cache'
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        for label, current_core, current_body in [('production', core, body)] + mutations:
            path = folder / (mode + '-' + label + '.swift')
            binary = path.with_suffix('')
            path.write_text(fixture(current_core, current_body))
            command = [swiftc, '-warnings-as-errors', '-module-cache-path', str(cache), *flags, str(path), '-o', str(binary)]
            compiled = subprocess.run(command, capture_output=True, text=True)
            assert compiled.returncode == 0, label + '\n' + compiled.stdout + compiled.stderr
            executed = subprocess.run([str(binary)], capture_output=True, text=True, preexec_fn=no_core)
            if label == 'production':
                assert executed.returncode == 0 and 'PASS author selection production checks: 34' in executed.stdout, executed.stdout + executed.stderr
                runs.append({'mode': mode, 'checks': 34})
            else:
                assert executed.returncode == 91 and executed.stdout.startswith('FAIL '), label + ': semantic regression did not fail with expected assertion: ' + executed.stdout + executed.stderr
                negatives.append({'mode': mode, 'variant': label, 'assertion': executed.stdout.strip()})
    for i, name in enumerate(PLAN['outputs']):
        path = folder / ('parse-' + str(i) + '.swift')
        path.write_bytes((source / name).read_bytes())
        subprocess.run([swiftc, '-frontend', '-parse', str(path)], check=True, capture_output=True, text=True)
    return runs, negatives


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-author-read-only-') as tmp:
        folder = Path(tmp)
        rejected = guard_checks(args.source, folder / 'guards')
        runs, negatives = execute(args.source, args.swiftc, folder)
    report = {'production_runs': runs, 'semantic_negative_runs': len(negatives), 'negative_variants': negatives, 'fail_closed': rejected, 'swift_parse_files': 2, 'outputs': PLAN['outputs'], 'source_scope': 'exact two author-selection outputs and thirteen dependencies', 'boundaries': 'Postbox queue/signal scheduling, UIKit presentation, AVKit and network are adapters; complete production local helper and author UI closure bodies execute', 'new_ui_strings': 0, 'apple_sdk': 'pending', 'physical_iphone': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
