#!/usr/bin/env python3
"""Validate bidirectional archive capture, real media copies and checkbox gates."""
import argparse
import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from validate_quick_format import block, manifest
from validate_archive_persistence import models, harness, WRITER

ROOT=Path(__file__).resolve().parents[1]
A='submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
M='submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift'
S='submodules/TelegramCore/Sources/State/ApplyUpdateMessage.swift'


def production(before,after):
    source=(after/A).read_text()
    settings=block(source,'private struct NagramiXMessageArchiveSettings ')
    media=(after/M).read_text().replace('import Postbox','').replace('import SwiftSignalKit','')
    names=['private static func key(','private static func makeRecord(message: StoreMessage,','private static func makeRecord(message: Message,','private func mediaRequests(','public func captureSent(','public func captureIncoming(','public func captureTemporaryBeforeViewing(','public func archiveTemporaryExpiration(','public func markTemporaryExpired(','public func archiveServerDeletion(messageIds:','public func deletedMessage(','public func snapshotForExpiredMessage(','public func containsArchivedMessage(','public func deletedMessages(','private func renderDeletedRecord(','public func cacheResourcesToRemove(']
    methods='\n'.join(block(source,name) for name in names)
    legacy=block((before/A).read_text(),'private static func makeRecord(message: StoreMessage,').replace('makeRecord(','legacyMakeRecord(',1)
    # Metadata IO below is a harness boundary. The unchanged real native
    # persistence coordinator and archive integration execute as separate suites.
    return settings+'\n'+models(source)+'\n'+media+'''
private final class ArchiveHarness {
    let accountPeerId=PeerId(Int32(1))
    let queue=Queue()
    let mediaBox:MediaBox
    let mediaStore:NagramiXArchivedMediaStore
    let path:String
    let state=Atomic<NagramiXMessageArchiveState>(value:NagramiXMessageArchiveState())
    let renderVersion=Atomic<UInt32>(value:0)
    var mutationState:NagramiXMessageArchiveState { state.with{$0} }
    var writes=0
    init(_ base:String,mediaBox:MediaBox) {
        self.mediaBox=mediaBox
        self.path=base+"/archive.json"
        try! FileManager.default.createDirectory(atPath:base,withIntermediateDirectories:true)
        self.mediaStore=NagramiXArchivedMediaStore(mediaBox:mediaBox,queue:queue,basePath:base,changed:{})
        if let data=try? Data(contentsOf:URL(fileURLWithPath:path)),let restored=try? JSONDecoder().decode(NagramiXMessageArchiveState.self,from:data){_=state.swap(restored)}
        mediaStore.load()
    }
    func refresh() {
        let s=NagramiXMessageArchiveSettings.current
        mediaStore.configure(enabled:s.showDeletedMessages,temporaryEnabled:s.saveTemporaryMessages)
    }
    private func persist(_ state:NagramiXMessageArchiveState) {
        try! JSONEncoder().encode(state).write(to:URL(fileURLWithPath:path),options:.atomic)
        _=self.state.swap(state);writes += 1
    }
    private func publishUpdate() {}
    private static func encodedRootObject(_ object:PostboxCoding)->Data { Codec.encode(object) }
    private static func decodedRootObject(_ data:Data)->PostboxCoding? { Codec.values[data] }
    private func localMedia(_ media:Media)->Media {
        if let file=media as? TelegramMediaFile{return TelegramMediaFile(mediaStore.localResource(for:file.resource),kind:file.kind)}
        if let image=media as? TelegramMediaImage,let first=image.representations.first{return TelegramMediaImage(mediaStore.localResource(for:first.resource))}
        return media
    }
    func hasSnapshot(_ id:MessageId)->Bool {state.with{$0.records[Self.key(id)] != nil}}
    func wasIncoming(_ id:MessageId)->Bool? {state.with{$0.records[Self.key(id)]?.incoming}}
    func legacyAccepts(_ message:StoreMessage,peers:[PeerId:Peer])->Bool {Self.legacyMakeRecord(message:message,peers:peers) != nil}
''' + methods+'\n'+legacy+'\n}\n'


def validate(args):
    plan=json.loads((ROOT/'ios/outgoing_archive_patches.json').read_text());a,b=manifest(args.before),manifest(args.after)
    assert a.keys()==b.keys()
    changed={n for n in a if a[n]!=b[n]};assert changed==set(plan['hashes']),changed
    assert all(a[n]==digest for n,digest in plan['hashes'].items())
    assert (args.before/M).read_bytes()==(args.after/M).read_bytes()
    # All previous persistence/retry/delete implementations stay byte-identical.
    for marker in ['private func persist(','private func didPersist(','public func retryPersistence(','public func clearAll(','public func removeLocal(']:
        assert block((args.before/A).read_text(),marker)==block((args.after/A).read_text(),marker),marker
    ack=(args.after/S).read_text()
    assert ack.count('?.captureSent(')==2
    single=ack.split('if let updatedMessage = updatedMessage, case let .Id(updatedId) = updatedMessage.id {',1)[1]
    assert single.lstrip().startswith('NagramiXMessageArchive.forPostbox(postbox)?.captureSent(updatedMessage, transaction: transaction)')
    group=ack.split('        for (message, _, updatedMessage) in mapping {\n            var archiveMessage:',1)[1]
    assert group.index('transaction.updateMessage(')<group.index('archiveMessage = finalMessage')<group.index('return .update(finalMessage)')<group.index('?.captureSent(archiveMessage, transaction: transaction)')
    spec=importlib.util.spec_from_file_location('outgoing_archive',ROOT/'ios/outgoing_archive.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    failures,runs=[],[]
    with tempfile.TemporaryDirectory(prefix='nagramix-outgoing-') as folder:
        folder=Path(folder)
        def seed(target):
            for n in plan['hashes']:
                (target/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.before/n,target/n)
        def reject(target,label,overlay=ROOT/'ios'):
            old=manifest(target)
            try:mod.apply_outgoing_archive(target,overlay)
            except SystemExit:pass
            else:raise AssertionError(label)
            assert manifest(target)==old,label
            failures.append(label)
        target=folder/'good';seed(target);mod.apply_outgoing_archive(target,ROOT/'ios')
        assert all((target/n).read_bytes()==(args.after/n).read_bytes() for n in changed);reject(target,'reapply')
        for n in plan['hashes']:
            for kind in ['missing','drift']:
                target=folder/(kind+str(len(failures)));seed(target)
                if kind=='missing':(target/n).unlink()
                else:(target/n).write_text((target/n).read_text()+'\n// drift')
                reject(target,kind+' '+n)
        for index in range(len(plan['patches'])):
            custom=json.loads(json.dumps(plan));custom['patches'][index][1]+=' bad anchor'
            overlay=folder/('overlay'+str(index));overlay.mkdir();(overlay/'outgoing_archive_patches.json').write_text(json.dumps(custom))
            target=folder/('anchor'+str(index));seed(target);reject(target,'anchor '+str(index),overlay)
        code=(ROOT/'scripts/tests/NagramiXOutgoingArchiveBoundary.swift').read_text()+'\n'+production(args.before,args.after)+'\n'+(ROOT/'scripts/tests/NagramiXOutgoingArchiveTests.swift').read_text()
        source=folder/'Tests.swift';source.write_text(code)
        archive_source=folder/'ArchiveStorage.swift';archive_source.write_text(harness((args.after/A).read_text()))
        for mode in ['debug','optimized']:
            suites={'outgoing':[source], 'persistence':[args.after/WRITER,ROOT/'scripts/tests/NagramiXArchivePersistenceTests.swift'], 'storage':[args.after/WRITER,ROOT/'scripts/tests/NagramiXArchiveStorageBoundary.swift',archive_source]}
            for name,sources in suites.items():
                binary=folder/(mode+name)
                command=[str(args.swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(folder/'cache'),*map(str,sources),'-o',str(binary)]
                if mode=='optimized':command.insert(1,'-O')
                subprocess.run(command,check=True)
                env=dict(os.environ,XDG_CONFIG_HOME=str(folder/(mode+'prefs')))
                runs.append(mode+' '+name+': '+subprocess.check_output([str(binary)],env=env,text=True,timeout=45).strip())
        subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.after/n) for n in sorted(changed) if n.endswith('.swift')]],check=True)
    for n in ['ios/outgoing_archive.py','ios/apply_features.py','scripts/validate_outgoing_archive.py']:ast.parse((ROOT/n).read_text())
    return dict(outputs=len(b),changed=sorted(changed),unchanged=len(b)-len(changed),guards=len(plan['hashes']),operations=len(plan['patches']),fail_closed=failures,runs=runs,UIKit_Engine_Postbox_network='boundaries; native media store and real filesystem executed',SDK_IPA='not started',device='pending')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']:parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args();result=validate(args);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
