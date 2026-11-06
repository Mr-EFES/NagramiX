#!/usr/bin/env python3
"""Проверить единые copy-действия, их названия и получателей из поиска."""
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
from validate_localization_standard import catalog_contract, source_contract

ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
STAGE='transfer_consistency'
PLAN=json.loads((OVERLAY/(STAGE+'_patches.json')).read_text())
F,N,L,M=PLAN['inputs']
CONTACT='submodules/ContactListUI/Sources/ContactListNode.swift'
STORE='submodules/TelegramCore/Sources/Utils/StoredMessageFromSearchPeer.swift'
ENGINE='submodules/TelegramCore/Sources/TelegramEngine/Peers/TelegramEnginePeers.swift'
ENQUEUE='submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source):
    for name,digest in {**PLAN['outputs'],**PLAN['guards']}.items():
        assert sha((source/name).read_bytes())==digest,name
    for name,digest in PLAN['templates'].items():
        assert sha((OVERLAY/name).read_bytes())==digest,name
    f=(source/F).read_text()
    assert 'title: selectionTitle' in f
    assert 'multipleSelectionLimit: transferMode.singleRecipient ? 1 : nil' in f
    assert 'if transferMode.copiesAsNew {\n                    // Assign nil as well:' in f
    assert 'if transferMode.copiesAsNew && !nagramiXOwnViewOnceCopy {' in f
    assert 'nagramiXTransferTitle: selectionTitle)' in f
    assert f.index('context.engine.peers.ensurePeerIsLocallyAvailable(peer:')<f.index('peerIds.map(TelegramEngine.EngineData.Item.Peer.SendPaidMessageStars')
    before=(OVERLAY/PLAN['previous'][F]).read_text()
    # Both actions retain the exact existing preparer, per-recipient copies,
    # source eligibility and commit-time OFF gate, payments and topic routing.
    start='                        switch transferMode {'
    end='                        strongController.dismiss()'
    assert f[f.index(start):f.index(end,f.index(start))]==before[before.index(start):before.index(end,before.index(start))]
    for marker in ['if nagramiXOwnViewOnceCopy {\n                        let allowsMode:','if let batch = nagramiXRecipientCopies {\n                                    // All recipients']:
        assert block(f,marker)==block(before,marker)
    assert 'forward(copies)' not in (source/M).read_text()
    assert 'interfaceInteraction.forwardMessages(copies)' in (source/M).read_text()
    assert 'transferMode: .copyToSingleRecipient, nagramiXTransferTitle: strongSelf.presentationData.strings.nagramiXForwardWithAuthor)' in (source/L).read_text()
    pipeline=(OVERLAY/'apply_overlay.py').read_text()
    assert pipeline.index('    apply_editor_attachment_delivery(')<pipeline.index('    apply_transfer_consistency(')
    assert catalog_contract(source)==(71,613)
    source_contract(source)


def guard_checks(source,temp):
    spec=importlib.util.spec_from_file_location(STAGE,OVERLAY/(STAGE+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    apply=getattr(module,'apply_'+STAGE)
    rejected=[]
    def seed(label):
        tree=temp/label
        for name in {**PLAN['inputs'],**PLAN['guards']}:
            p=tree/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((OVERLAY/PLAN['previous'][name] if name in PLAN['previous'] else source/name).read_bytes())
        return tree
    def reject(tree,label,overlay=OVERLAY):
        before=manifest(tree)
        try:apply(tree,overlay)
        except (SystemExit,OSError):pass
        else:raise AssertionError('Invalid input accepted: '+label)
        assert manifest(tree)==before,'Partial write: '+label
        rejected.append(label)
    valid=seed('valid');apply(valid,OVERLAY)
    assert all((valid/n).read_bytes()==(source/n).read_bytes() for n in PLAN['outputs'])
    reject(valid,'repeat')
    for i,n in enumerate({**PLAN['inputs'],**PLAN['guards']}):
        for kind in ['missing','drift']:
            tree=seed(str(i)+'-'+kind)
            if kind=='missing':(tree/n).unlink()
            else:(tree/n).write_bytes(b'drift')
            reject(tree,kind+' '+n)
    variants=[]
    for field in ['inputs','outputs','guards','templates']:
        bad=copy.deepcopy(PLAN);bad[field][next(iter(bad[field]))]='0'*64;variants.append((field,bad))
    for field in ['previous','replacements']:
        bad=copy.deepcopy(PLAN);bad[field][F]='../outside.swift';variants.append((field,bad))
    bad=copy.deepcopy(PLAN);bad['outputs'].clear();variants.append(('inconsistent',bad))
    for label,bad in variants:
        overlay=temp/('overlay-'+label)
        for name in PLAN['templates']:
            p=overlay/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OVERLAY/name).read_bytes())
        (overlay/(STAGE+'_patches.json')).write_text(json.dumps(bad))
        reject(seed('source-'+label),label,overlay)
    for i,n in enumerate([F,next(iter(PLAN['guards']))]):
        tree=seed('symlink-'+str(i));p=tree/n;outside=temp/('outside-'+str(i))
        outside.write_bytes(p.read_bytes());p.unlink();p.symlink_to(outside);reject(tree,'external symlink '+n)
    return rejected


def routing_fixture(source):
    n=(source/N).read_text();f=(source/F).read_text()
    fixture=(ROOT/'scripts/tests/NagramiXTransferConsistencyBoundary.swift').read_text()
    contact=block((source/CONTACT).read_text(),'public struct ContactListNodeGroupSelectionState:').replace('public ','')
    start=n.index('    var nagramiXCopySelection = false')
    props=n[start:n.index(' = ([], [:])',start)+len(' = ([], [:])')].replace('private ','')
    select=block(n,'    func nagramiXSelectCopyRecipient(')
    select=select[:select.index('        // Copy mode deliberately')]+'''        self.textInputPanelNode?.updateSendButtonEnabled(!self.selectedPeers.0.isEmpty, animated: true)
    }'''
    start=n.index('    private var selectedPeers:')
    selected=n[start:n.index('    func beginSelection()',start)].replace('private ','')
    begin=block(n,'    func beginSelection()')
    begin=begin[begin.index('        if self.nagramiXCopySelection {'):begin.index('        guard let controller')]
    # Actual search state callbacks, without UIKit search presentation.
    search=n.index('openPeer: { [weak self] peer, chatPeer, threadId, _ in')
    chats=block(n[search:],'                        chatListNode?.updateState { state in')
    chats=chats.replace('chatListNode?.updateState','self.mainContainerNode?.currentItemNode.updateState')
    search=n.index('contentNode: ContactsSearchContainerNode(')
    contacts=block(n[search:],'                    strongSelf.contactListNode?.updateSelectionState { state -> ContactListNodeGroupSelectionState? in')
    copies=block(f,'                if transferMode.copiesAsNew {\n                    // Assign nil as well:')
    predicate=copies[copies.index('if ')+3:copies.index(' {')]
    line=next(line for line in f.splitlines() if 'multipleSelection: !transferMode.singleRecipient' in line)
    limit=line.split('multipleSelectionLimit: ',1)[1].split(', forwardedMessageIds:',1)[0]
    start=f.index('                let peerIds = peers.map')
    peers=f[start:f.index('                let beginSend:',start)]
    start=f.index('combineLatest(recipientsToStore.values.map')
    barrier=f[start:f.index('                |> deliverOnMainQueue).start',start)]
    include=block((source/ENQUEUE).read_text(),'            if peerId.namespace == Namespaces.Peer.CloudUser {\n                if case .notIncluded')
    for marker,body in [
        ('CONTACT_STATE',contact),('SELECTION_PROPERTIES',props),('SELECT_RECIPIENT',select),('SELECTED_PROPERTIES',selected),('BEGIN_SELECTION',begin),
        ('CHAT_SEARCH_SELECTION',chats),('CONTACT_SEARCH_SELECTION',contacts),('TRANSFER_MODE',block(f,'enum NagramiXMessageTransferMode:')),
        ('COPY_PICKER_PREDICATE','return '+predicate),('PICKER_LIMIT','return '+limit),('PEERS_TO_STORE',peers),('PEER_BARRIER',barrier),
        ('STORE_PEER',block((source/STORE).read_text(),'public func _internal_storedMessageFromSearchPeer(').replace('public ','')),('CHAT_INCLUSION',include),
        ('ENGINE_STORE_WRAPPER',block((source/ENGINE).read_text(),'        public func ensurePeerIsLocallyAvailable(').replace('public ','')),
    ]:
        assert '// PRODUCTION_'+marker in fixture,marker
        fixture=fixture.replace('// PRODUCTION_'+marker,body)
    return fixture


def payload_fixture(source):
    from validate_editor_attachment_delivery import copy_fixture
    fixture=copy_fixture(source).split('@main struct EditorCopyTests',1)[0]
    tests=(ROOT/'scripts/tests/NagramiXTransferPayloadTests.swift').read_text()
    poll=block((ROOT/'scripts/tests/NagramiXCopyAvailabilityTests.swift').read_text(),'    static func poll(')
    tests=tests.replace('// PRODUCTION_POLL_FIXTURE',poll)
    return fixture+'\n'+tests


def run_swift(source,swiftc,temp):
    from validate_app_language_localization import strings
    fixture=routing_fixture(source)
    payload=payload_fixture(source)
    languages=json.loads((OVERLAY/'app_language_localization/languages.json').read_text())['languages']
    catalogs=[{'code':v['code'],'values':strings(source/('submodules/NagramiXCore/Resources/'+v['code']+'.lproj/Localizable.strings'))} for v in languages]
    catalog=temp/'catalogs.json';catalog.write_text(json.dumps(catalogs,ensure_ascii=False))
    # Mutations reproduce the previous behaviors; the production code is used
    # directly by every positive test, without a parallel selection algorithm.
    variants={
        'selection-and-storage':fixture,'payloads':payload,
        'old-single-draft':fixture.replace('return transferMode.copiesAsNew','return transferMode == .copyAsNew'),
        'missing-chat-found-row':fixture.replace('state.foundPeers.insert((peer, nil), at: 0)','state.foundPeers = Array(state.foundPeers)'),
        'missing-contact-found-row':fixture.replace('foundPeers.insert(.peer(peer: peer, isGlobal: false, participantCount: nil), at: 0)','foundPeers = Array(foundPeers)'),
        'search-hides-found-rows':fixture.replace('if !exists {','if !exists && !strongSelf.nagramiXCopySelection {'),
        'wrong-repost-title':fixture.replace('case .forwardWithSource: return strings.nagramiXForwardWithAuthor','case .forwardWithSource: return strings.nagramiXForwardWithoutAuthor'),
        'store-step-skipped':fixture.replace('context.engine.peers.ensurePeerIsLocallyAvailable(peer: peer)','Signal<EnginePeer, NoError>.single(peer)'),
        'single-limit-removed':fixture.replace('guard selected.isEmpty || selected.contains(where: { $0.id == peer.id }) else { return }','_ = selected'),
        'contact-topic-forgotten':fixture.replace('        self.nagramiXCopyThreads[peer.id] = threadId\n',''),
    }
    runs=[]
    for label,text in variants.items():
        path=temp/(label+'.swift');path.write_text(text)
        for optimized in [False,True]:
            binary=temp/(label+('-O' if optimized else '-debug'))
            subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),str(path),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary),str(catalog)],capture_output=True,text=True,timeout=30,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if label in ['selection-and-storage','payloads']:
                assert result.returncode==0,result.stdout+result.stderr
                status=result.stdout.strip()
            else:
                assert result.returncode!=0 and 'regression:' in result.stderr,label+result.stdout+result.stderr
                status='regression reproduced and rejected'
            runs.append(binary.name+': '+status);print(runs[-1],flush=True)
    return runs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_transition_geometry'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-transfer-consistency-') as folder:
        temp=Path(folder);rejected=guard_checks(args.source,temp/'guards')
        runtime=temp/'runtime';runtime.mkdir()
        runs=run_swift(args.source,args.swiftc,runtime) if args.swiftc else []
        if args.swiftc:
            for name in PLAN['outputs']:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/name)],check=True)
    report={'replacements':len(PLAN['outputs']),'guards':len(PLAN['guards']),'fail_closed':len(rejected),'executions':runs,'localization':'71 existing title catalogs, no new strings','sdk':'not run','device':'pending','boundaries':'Actual selection/search state mutations, native contact state, title switch, peer-store helper, pre-send persistence barrier and native chat-list inclusion block. Full copy builder, recipient batch and real local file staging tested. UIKit/DB scheduling/network/API are boundaries; enqueue is not proof of server delivery.'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
