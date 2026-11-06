#!/usr/bin/env python3
"""Проверить целостность постов, двухэтапное удаление и durable-очистку архива."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import tempfile
from validate_quick_format import block, manifest
from validate_archive_persistence import method
ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
PLAN=json.loads((OVERLAY/'archive_post_lifecycle_patches.json').read_text())
A='submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
B='submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift'
M='submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift'

def sha(data):return hashlib.sha256(data).hexdigest()

def verify(source):
    for name,digest in {**PLAN['outputs'],**PLAN['guards']}.items():assert sha((source/name).read_bytes())==digest,name
    for name,digest in PLAN['templates'].items():assert sha((OVERLAY/name).read_bytes())==digest,name
    old=(OVERLAY/PLAN['previous'][A]).read_text();new=(source/A).read_text()
    assert block(old,'private struct NagramiXMessageArchiveSettings')==block(new,'private struct NagramiXMessageArchiveSettings'), 'Core settings visibility must remain private'
    # Native/server deletion remains retaining; explicit UI purge is separate.
    for marker in ['public func removeLocal(', 'public func clear(peerId:', 'public func archiveServerDeletion(messageIds:', 'private func archiveHistoryDeletion(', 'public func transcriptionMessage(', 'public func updateTranscriptionAttributes(']:
        assert block(old,marker)==block(new,marker),marker
    controller=(source/B).read_text();before=(OVERLAY/PLAN['previous'][B]).read_text()
    native=block(controller,'private func nagramiXBeginNativeDeleteMessagesWithUndo(').replace('private func nagramiXBeginNativeDeleteMessagesWithUndo(', 'func beginDeleteMessagesWithUndo(',1)
    assert native==block(before,'func beginDeleteMessagesWithUndo('),'OFF native method changed'
    panel=(source/'submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift').read_text()
    assert 'if archiveOnlySelection {\n                self.deleteButton.isEnabled = true' in panel
    menus=(source/M).read_text()
    assert 'NagramiXMessageArchiveSettings' not in controller+menus, 'UI must use public NagramiXTabSettings'
    assert menus.count('nagramiXWholePostMessages(message, messages: messages)')==3
    load=(source/'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift').read_text()
    selected=load[load.index('        }, deleteSelectedMessages: {'):load.index('        }, reportSelectedMessages:')]
    assert selected.index('let localCandidates =')<selected.index('postbox.transaction')
    assert selected.count('nagramiXLocalCandidates: localCandidates')==2
    confirm=block(controller,'func presentDeleteMessageOptions(')
    assert confirm.index('engine.messages.nagramiXArchivePostDeletionPlan(')<confirm.index('engine.data.get(')
    assert confirm.count('nagramiXPlan: nagramiXPlan')==6
    assert '.postbox' not in controller, 'New UI file must use TelegramEngine'


def guard_checks(source,temp):
    spec=importlib.util.spec_from_file_location('archive_post_lifecycle',OVERLAY/'archive_post_lifecycle.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[]
    def seed(label):
        target=temp/label
        for name in {**PLAN['inputs'],**PLAN['guards']}:
            data=(OVERLAY/PLAN['previous'][name]).read_bytes() if name in PLAN['previous'] else (source/name).read_bytes()
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        return target
    def reject(target,label,overlay=OVERLAY):
        before=manifest(target)
        try:module.apply_archive_post_lifecycle(target,overlay)
        except (SystemExit,OSError):pass
        else:raise AssertionError('Invalid input accepted: '+label)
        assert manifest(target)==before,'Partial write: '+label
        rejected.append(label)
    valid=seed('valid');module.apply_archive_post_lifecycle(valid,OVERLAY)
    assert all((valid/name).read_bytes()==(source/name).read_bytes() for name in PLAN['outputs'])
    reject(valid,'repeat')
    for name in {**PLAN['inputs'],**PLAN['guards']}:
        for kind in ['missing','drift']:
            target=seed(str(len(rejected)));path=target/name
            if kind=='missing':path.unlink()
            else:path.write_bytes(path.read_bytes()+b'\n// drift\n')
            reject(target,kind+' '+name)
    mutations=[]
    for field in ['inputs','outputs','guards','templates']:
        bad=copy.deepcopy(PLAN);bad[field][next(iter(bad[field]))]='0'*64;mutations.append((field+'-SHA',bad))
    for field in ['previous','replacements']:
        bad=copy.deepcopy(PLAN);bad[field][A]='../outside.swift';mutations.append((field+'-traversal',bad))
    bad=copy.deepcopy(PLAN)
    for field in ['inputs','outputs','previous','replacements']:bad[field]['../outside.swift']=bad[field].pop(A)
    mutations.append(('source-traversal',bad))
    bad=copy.deepcopy(PLAN);bad['outputs'].pop(A);mutations.append(('inconsistent-keys',bad))
    for label,bad in mutations:
        overlay=temp/('overlay-'+label)
        for name in PLAN['templates']:
            path=overlay/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((OVERLAY/name).read_bytes())
        (overlay/'archive_post_lifecycle_patches.json').write_text(json.dumps(bad))
        reject(seed('source-'+label),label,overlay)
    for label,name in [('input-symlink',A),('guard-symlink',next(iter(PLAN['guards'])))]:
        target=seed(label);path=target/name;external=temp/(label+'.swift');external.write_bytes(path.read_bytes());path.unlink();path.symlink_to(external)
        reject(target,label)
    # A bad final template must be rejected before writing even the first file.
    overlay=temp/'overlay-last-template'
    for name in PLAN['templates']:
        path=overlay/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((OVERLAY/name).read_bytes())
    (overlay/'archive_post_lifecycle_patches.json').write_text(json.dumps(PLAN))
    (overlay/next(reversed(PLAN['replacements'].values()))).write_bytes(b'bad final template')
    reject(seed('last-template'),'last-output-template',overlay)
    return rejected

def runtime_source(native, mode='current'):
    root=ROOT
    a=(native/'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift').read_text()
    boundary=(root/'scripts/tests/NagramiXArchivePostsBoundary.swift').read_text()
    models=block(a,'public struct NagramiXMessageRevision:')+'\n'+a[a.index('private struct NagramiXArchivePostKey:'):a.index('private final class NagramiXWeakMessageArchive')]
    writer=(native/'submodules/TelegramCore/Sources/Utils/NagramiXArchivePersistence.swift').read_text()
    # Use the production coordinator and Foundation atomic JSON. UI status and retry
    # scheduling are explicit boundaries, not filesystem success shortcuts.
    props=a[a.index('    private let storageStatusValue ='):a.index('    private lazy var mediaStore =')]
    props=props.replace('SwiftSignalKit.Timer','BoundaryTimer')
    source=boundary+'\n'+models.replace('public ','')+'\n'+writer.replace('public ','')+'\n'
    source+='''
    final class BoundaryTimer {
        init(timeout:Double,repeat:Bool,completion:@escaping()->Void,queue:Queue){}
        func start(){};func invalidate(){}
    }
    final class ValuePromise<T> { var value:T;init(_ value:T,ignoreRepeated:Bool=false){self.value=value};func set(_ value:T){self.value=value};func get()->Signal<T,NoError>{Signal{ subscriber in subscriber.putNext(self.value);subscriber.putCompletion();return EmptyDisposable}} }
    private final class Archive {
        let path:String
        let queue=Queue()
        let mediaStore=MediaStore()
        let state=Atomic<NagramiXMessageArchiveState>(value:NagramiXMessageArchiveState())
        let renderVersion=Atomic<UInt32>(value:0)
        var revision=0
        init(path:String){self.path=path}
        static func forPostbox(_ postbox:BoundaryPostbox)->Archive? {postbox.archive}
        func publishUpdate(){revision+=1}
        func localMedia(_ media:Media)->Media{media}
        static func decodedRootObject(_ data:Data)->Any? {
            let text=String(data:data,encoding:.utf8)!
            if text.hasPrefix("peer:"){return Peer(PeerId(Int64(text.dropFirst(5))!))}
            return TelegramMediaFile(text)
        }
        func mediaRequests(_ record:NagramiXArchivedRecord)->[NagramiXArchiveMediaRequest]{record.content.media.map{NagramiXArchiveMediaRequest(name:String(data:$0,encoding:.utf8)!)}}
    '''+props+'\n'
    methods=['private func loadPersistedState()', 'private func persist(', 'private func didPersist(', 'private static func key(', 'public func postMessageIds(', 'public func localPostDeletionCandidates(', 'public func postDeletionPlan(', 'private func rejectPurgedCapture(', 'public func deleteArchivedPosts(', 'public func clearAll()', 'public func isLocallyDeletedMessage(', 'private func renderDeletedRecord(']
    for m in methods:
        original=method(a,m)
        if mode=='old-render' and m=='private func renderDeletedRecord(':original=method((OVERLAY/PLAN['previous'][A]).read_text(),m)
        if mode=='old-retention' and m=='public func deleteArchivedPosts(':
            original='''    func deleteArchivedPosts(messageIds: Set<MessageId>) -> Signal<Void, NoError> {
            return Signal { subscriber in self.removeLocal(messageIds: Array(messageIds)); subscriber.putCompletion(); return EmptyDisposable }
        }
    '''+method(a,'public func removeLocal(')+method(a,'public func archiveServerDeletion(messageIds:')
        source+=original.replace('public func','func')
    capture=method(a,'public func captureIncoming(')
    capture=capture[capture.index('        guard !self.purgedKeys.with'):].rsplit('\n    }',1)[0]
    source+='''
        func refresh(_ id:MessageId) {
            let record=NagramiXArchivedRecord(peerId:id.peerId.toInt64(),namespace:id.namespace,id:id.id,authorId:nil,timestamp:1,threadId:nil,groupingKey:nil,incoming:true,peerData:[:],content:NagramiXArchivedContent(text: "late refresh",entities:[],media:[]),contentTimestamp:1,revisions:[],deletedAt:nil)
            let settings=NagramiXMessageArchiveSettings.current
    '''+capture+'''
        }
        func restore(){_ = loadPersistedState()}
        var saved:NagramiXMessageArchiveState {state.with{$0}}
        func retry(){_ = persistence.retry()}
        func add(_ id:MessageId,group:Int64?,text:String,media:[String],deleted:Bool=false,thread:Int64?=nil,forward:NagramiXArchivedForwardInfo?=nil){
            var value=mutationState
            value.records[Self.key(id)]=NagramiXArchivedRecord(peerId:id.peerId.toInt64(),namespace:id.namespace,id:id.id,authorId:77,timestamp:id.id,threadId:thread,groupingKey:group,incoming:false,peerData:["77":Data("peer:77".utf8),"78":Data("peer:78".utf8)],content:NagramiXArchivedContent(text:text,entities:[MessageTextEntity(text:"entity")],media:media.map{Data($0.utf8)}),contentTimestamp:id.id,revisions:[],deletedAt:deleted ? 100 : nil,forwardInfo:forward)
            let requests=mediaRequests(value.records[Self.key(id)]!);let ticket=mediaStore.reserve(key:Self.key(id),requests:requests)
            persist(value);mediaStore.retain(key:Self.key(id),requests:requests,ticket:ticket)
        }
        func mark(_ ids:Set<MessageId>){var value=mutationState;for id in ids {value.records[Self.key(id)]?.deletedAt=100};persist(value)}
        func rendered(_ id:MessageId)->Message {renderDeletedRecord(saved.records[Self.key(id)]!)!}
        func reserveLate(_ id:MessageId)->Int64 {mediaStore.reserve(key:Self.key(id),requests:[NagramiXArchiveMediaRequest(name:"late")])}
        func rejectLate(_ id:MessageId,_ ticket:Int64)->Bool{rejectPurgedCapture(key:Self.key(id),ticket:ticket)}
        func purge(_ ids:Set<MessageId>){_ = deleteArchivedPosts(messageIds:ids).startStandalone()}
    }
    '''
    source+='\nextension Message {\n'+block((native/'submodules/Postbox/Sources/Message.swift').read_text(),'public func withUpdatedStableVersion(').replace('public func','func',1)+'\n}\n'
    source+='''
    private typealias NagramiXMessageArchive=Archive
    enum EngineMessage {typealias Id=MessageId}
    typealias EngineRawMessage=Message
    private typealias NagramiXTabSettings=NagramiXMessageArchiveSettings
    private final class BoundaryPostbox {
        var archive:Archive?
        let value:Transaction
        init(_ archive:Archive?,_ value:Transaction){self.archive=archive;self.value=value}
        func transaction<T>(_ transform:@escaping(Transaction)->T)->Signal<T,NoError> {
            Signal { subscriber in subscriber.putNext(transform(self.value));subscriber.putCompletion();return EmptyDisposable }
        }
    }
    private struct EngineAccount {let postbox:BoundaryPostbox}
    private final class EnginePlanner {
        let account:EngineAccount
        init(_ archive:Archive?,_ tx:Transaction){account=EngineAccount(postbox:BoundaryPostbox(archive,tx))}
    '''+block((native/'submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXLocalMessageData.swift').read_text(),'func nagramiXArchivePostDeletionPlan(')+'\n}\n'
    nativehelper=(native/'submodules/TelegramCore/Sources/Utils/MessageUtils.swift').read_text();source+='\n'+block(nativehelper,'func locallyRenderedMessage(message: StoreMessage, peers: [PeerId: Peer]')+'\n'
    ui=(root/'scripts/tests/NagramiXArchivePostsUIBoundary.swift').read_text()
    controller=(native/'submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift').read_text()
    functions='\n'.join(block(controller,m).replace('private func','func',1).replace('private var','var',1) for m in ['private var nagramiXArchivePostScope:', 'func nagramiXPostSelectionIds(', 'private func nagramiXDeleteArchivedPostsWithUndo('])
    ui=ui.replace('// Actual computed scope, selection helper and commit/undo method are inserted.',functions)
    context=(native/'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift').read_text()
    source+='\n'+block(context,'private func nagramiXWholePostMessages(')+'\n'+ui+'\n'+(root/'scripts/tests/NagramiXArchivePostsTests.swift').read_text()
    return source

def run_swift(source,swiftc,temp):
    runs=[]
    def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    for mode in ['current','old-render','old-retention']:
        suite=temp/(mode+'.swift');suite.write_text(runtime_source(source,mode))
        for optimized in [False,True]:
            label=mode+('-O' if optimized else '-debug');binary=temp/label
            command=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache')]
            if optimized:command.append('-O')
            subprocess.run([*command,str(suite),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,preexec_fn=no_core,timeout=30)
            if mode=='current':assert result.returncode==0,result.stdout+result.stderr;message=result.stdout.strip()
            else:
                expected='context payload includes only the focused complete post' if mode=='old-render' else 'only chosen post removed'
                assert result.returncode!=0 and 'archive post regression:' in result.stderr and expected in result.stderr,(result.stdout,result.stderr)
                message='Previous implementation rejected by regression checks'
            print(label+': '+message,flush=True);runs.append(label+': '+message)
    return runs

def check_public_ui_types(source, swiftc, temp):
    """Compile actual UI helpers across module boundaries, without importing Postbox."""
    fixtures=ROOT/'scripts/tests/archive_ui_modules'
    modules=temp/'ui-modules';modules.mkdir()
    common=[str(swiftc),'-warnings-as-errors','-module-cache-path',str(temp/'cache')]
    for name in ['Postbox','SwiftSignalKit','TelegramCore','NagramiXCore','AccountContext']:
        subprocess.run([*common,'-emit-module','-parse-as-library','-module-name',name,
                        '-I',str(modules),str(fixtures/(name+'.swift')),
                        '-emit-module-path',str(modules/(name+'.swiftmodule'))],check=True)
    admin=(source/B).read_text();menus=(source/M).read_text()
    assert 'import NagramiXCore' in admin and 'import NagramiXCore' in menus
    assert 'import AccountContext' in admin and 'import AccountContext' in menus
    functions='\n'.join(block(admin, marker) for marker in [
        'private var nagramiXArchivePostScope:', 'func nagramiXPostSelectionIds(',
        'private func nagramiXLocalDeletionCandidates(', 'func nagramiXDeletionActions('])
    signature=block(admin,'func presentDeleteMessageOptions(').split('{',1)[0]
    functions+='\n'+signature+'{ fatalError("signature-only interface check") }\n'
    whole=block(menus,'private func nagramiXWholePostMessages(')
    boundary=(fixtures/'UI.swift').read_text()
    results=[]
    for mode in ['current','bare-id','bare-message','private-settings']:
        methods=functions;post=whole
        if mode=='bare-id':methods=methods.replace('EngineMessage.Id','MessageId')
        elif mode=='bare-message':post=post.replace('EngineRawMessage','Message')
        elif mode=='private-settings':
            methods=methods.replace('NagramiXTabSettings','NagramiXMessageArchiveSettings')
            post=post.replace('NagramiXTabSettings','NagramiXMessageArchiveSettings')
        suite=modules/(mode+'.swift')
        suite.write_text(boundary.replace('// ACTUAL_METHODS',methods).replace('// ACTUAL_POST',post))
        result=subprocess.run([*common,'-typecheck','-I',str(modules),str(suite)],capture_output=True,text=True)
        if mode=='current':assert result.returncode==0,result.stderr
        else:
            symbol={'bare-id':'MessageId','bare-message':'Message','private-settings':'NagramiXMessageArchiveSettings'}[mode]
            assert result.returncode!=0 and 'error:' in result.stderr and ("'"+symbol+"'") in result.stderr,result.stderr
        results.append(mode+': '+('actual UI public interfaces typechecked' if mode=='current' else 'SDK visibility regression reproduced and rejected'))
    for item in results:print(item,flush=True)
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_transition_geometry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'transfer_consistency'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'editor_attachment_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_size'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_effect'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_visual_handoff'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_menu'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_visibility'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'temporary_media_actions'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'message_copy_availability'):
        return
    if delegate_icon_stage_if_applied(args,Path(__file__),'vosk_model_naming'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-archive-posts-') as folder:
        temp=Path(folder);rejected=guard_checks(args.source,temp)
        runs=(check_public_ui_types(args.source,args.swiftc,temp)+run_swift(args.source,args.swiftc,temp)) if args.swiftc else []
    if args.swiftc:
        for name in PLAN['outputs']:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/name)],check=True)
    result={'changed_files':len(PLAN['outputs']),'guards':len(PLAN['guards']),'fail_closed':rejected,'executions':runs,'sdk':'not run','device':'pending iPhone verification','boundaries':'Actual post planning/rendering/capture queue/purge/JSON persistence and UI selection/commit/Undo. Postbox codec, media IO, native engine submission, UIKit and signal scheduling are boundaries.'}
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
