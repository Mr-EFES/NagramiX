#!/usr/bin/env python3
"""Проверить сохранение всех частей исходного поста при отправке из редактора."""
import argparse,copy,hashlib,importlib.util,json,os,resource,subprocess,tempfile
from pathlib import Path
from validate_quick_format import block,manifest
from validate_copy_delivery import payload_fixture,temporary_fixture
ROOT=Path(__file__).resolve().parents[1];OVERLAY=ROOT/'ios';STAGE='repost_copy_integrity'
PLAN=json.loads((OVERLAY/(STAGE+'_patches.json')).read_text())
CORE='submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift'
UI='submodules/TelegramUI/Sources/ChatControllerNode.swift'
ARGS='messages, account: account, hideCaptions: hideCaptions, forceLocalMedia: forceLocalMedia, accountPeerId: accountPeerId, mediaCopy: mediaCopy'
def sha(data):return hashlib.sha256(data).hexdigest()
def previous(name):return (OVERLAY/PLAN['previous'][name]).read_text()
def assembly(text,old=False):
    marker='                    let archivedMessages = forwardMessageIds.sorted()' if old else '                    let orderedForwardIds = forwardMessageIds.sorted()'
    a=text.index(marker);b=text.index('\n                }\n                \n                let doSend:',a)
    return text[a:b]
def routing(text,old=False):
    marker='                var targetThreadId: Int64?' if old else '                let nagramiXForwardPaymentRequired ='
    a=text.index(marker,text.index('                let doSend:'))
    b=text.index('\n            }\n        }\n    }\n    \n    func animateIn',a)
    return text[a:b]
def confirmation(text):
    a=text.index('                nagramiXSubmitComposerForwardMessages(messageCount:')
    b=text.index('}, send: sendPreparedForward)',a)+len('}, send: sendPreparedForward)')
    return text[a:b]
def verify(source):
    for n,d in {**PLAN['outputs'],**PLAN['guards']}.items():assert sha((source/n).read_bytes())==d,n
    for n,d in PLAN['templates'].items():assert sha((OVERLAY/n).read_bytes())==d,n
    before=previous(CORE);after=(source/CORE).read_text()
    old=block(before,'public func nagramiXCopyMessagesAsNew(')
    wrapper=block(after,'public func nagramiXCopyMessagesAsNew(')
    mapped=block(after,'public func nagramiXCopyMessagesAsNewBySource(')
    builder=block(after,'private func nagramiXBuildCopiedMessages(')
    first=after.index(wrapper);end=after.index(builder)+len(builder)
    assert after[:first]==before[:before.index(old)] and after[end:]==before[before.index(old)+len(old):],'Unrelated core changes'
    old_signature=old[:old.index(' {')];signature=builder[:builder.index(' {')]
    restored=builder.replace(signature,old_signature,1)
    restored=restored.replace('    var sourceRanges: [Range<Int>] = []\n','',1)
    tracking='        let outputStart = result.count\n        // Paid bundles and separate round captions can expand one input. The\n        // range is recorded at iteration exit, including the paid continue path.\n        defer { sourceRanges.append(outputStart ..< result.count) }\n'
    assert tracking in restored
    restored=restored.replace(tracking,'',1).replace('    return (result, sourceRanges)\n}','    return result\n}')
    assert restored==old,'Flat copy/media/temporary policy changed beyond source ranges'
    assert wrapper==old_signature+' {\n    return nagramiXBuildCopiedMessages('+ARGS+')?.messages\n}'
    assert 'Set(messages.map { $0.id }).count == messages.count' in mapped
    node=(source/UI).read_text();old_node=previous(UI);new_ui=assembly(node);old_ui=assembly(old_node,True)
    helper=block(node,'private func nagramiXSubmitComposerForwardMessages(')
    restored_node=node.replace('// Native payment confirmation must see the final output cardinality. This\n// composer helper is main-queue confined, including native Stars callbacks.\n'+helper+'\n\n','',1)
    new_payment=block(node,'                        if let _ = self.chatPresentationInterfaceState.sendPaidMessageStars,')
    old_payment=block(old_node,'                        if let _ = self.chatPresentationInterfaceState.sendPaidMessageStars {')
    assert 'forwardMessageIds?.isEmpty != false' in new_payment and 'forwardedCount' not in new_payment
    restored_node=restored_node.replace(new_payment,old_payment,1).replace('                var nagramiXForwardCopyStaging: NagramiXArchivedMediaCopy?\n','',1)
    restored_node=restored_node.replace(new_ui,old_ui,1)
    new_send=block(node,'                let doSend: (Int64?, Bool)')
    old_send=block(old_node,'                let doSend: (Int64?)')
    restored_send=new_send.replace('(Int64?, Bool) -> Void = { [weak self] overrideThreadId, confirmedPostpone in','(Int64?) -> Void = { [weak self] overrideThreadId in',1)
    restored_send=restored_send.replace('                    nagramiXForwardCopyStaging?.commit()\n','',1).replace('confirmedPostpone','postpone')
    assert restored_send==old_send,'Unrelated enqueue/composer behavior changed'
    restored_node=restored_node.replace(new_send,old_send,1)
    send_route=block(node,'                let sendPreparedForward: (Bool)')
    a=send_route.index('                    var targetThreadId: Int64?');b=send_route.rfind('\n                }')
    unwrapped='\n'.join(line[4:] if line.strip() else line for line in send_route[a:b].splitlines())
    unwrapped=unwrapped.replace('doSend(targetThreadId, confirmedPostpone)','doSend(targetThreadId)').replace('doSend(nil, confirmedPostpone)','doSend(nil)')
    assert unwrapped==routing(old_node,True),'Native topic/navigation routing changed'
    restored_node=restored_node.replace(routing(node),routing(old_node,True),1)
    assert restored_node==old_node,'Unrelated composer/send/keyboard changes'
    assert new_ui.count('nagramiXCopyMessagesAsNewBySource(')==1 and 'zip(' not in new_ui
    assert 'messages.append(contentsOf: copies.map { $0.withUpdatedThreadId(replyThreadId) })' in new_ui
    assert 'mediaCopy: staging)' in new_ui and 'nagramiXForwardCopyStaging?.commit()' in new_send
    assert 'messageCount: messages.count' in confirmation(node)
    assert 'self.sendMessages(messages, silentPosting, scheduleTime, repeatPeriod, messages.count > 1, confirmedPostpone)' in new_send
    assert 'self.chatLocation == nagramiXPreparedForwardLocation' in send_route
    assert 'self.chatPresentationInterfaceState.interfaceState == nagramiXPreparedForwardState' in send_route
    assert 'self.chatPresentationInterfaceState.sendPaidMessageStars == nagramiXPreparedForwardFee' in send_route
    post=json.loads((OVERLAY/'upstream_13_2_post_patches.json').read_text());assert not set(PLAN['outputs'])&set(post['outputs'])
    pipeline=(OVERLAY/'apply_overlay.py').read_text();assert pipeline.index('    apply_native_pip_baseline(')<pipeline.index('    apply_repost_copy_integrity(')
    workflow=(ROOT/'.github/workflows/build-unsigned-ipa.yml').read_text();assert workflow.index('python3 scripts/validate_repost_copy_integrity.py')<workflow.index('python3 scripts/validate_native_pip_baseline.py')

def guard_checks(source,temp):
    spec=importlib.util.spec_from_file_location(STAGE,OVERLAY/(STAGE+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    apply=module.apply_repost_copy_integrity;rejected=[]
    def seed(label):
        tree=temp/label
        for n in {**PLAN['inputs'],**PLAN['guards']}:
            p=tree/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OVERLAY/PLAN['previous'][n] if n in PLAN['previous'] else source/n).read_bytes())
        return tree
    def reject(tree,label,overlay=OVERLAY):
        before=manifest(tree)
        try:apply(tree,overlay)
        except (SystemExit,OSError):pass
        else:raise AssertionError('Invalid input accepted: '+label)
        assert manifest(tree)==before,'Partial write: '+label
        rejected.append(label)
    valid=seed('valid');apply(valid,OVERLAY)
    for n in PLAN['outputs']:assert (valid/n).read_bytes()==(source/n).read_bytes(),n
    reject(valid,'repeat')
    for i,n in enumerate({**PLAN['inputs'],**PLAN['guards']}):
        for kind in ['missing','drift']:
            tree=seed(str(i)+kind)
            if kind=='missing':(tree/n).unlink()
            else:(tree/n).write_bytes(b'drift')
            reject(tree,kind+' '+n)
    f=next(iter(PLAN['inputs']));variants=[]
    for field in ['inputs','outputs','guards','templates']:
        bad=copy.deepcopy(PLAN);bad[field][next(iter(bad[field]))]='0'*64;variants.append((field,bad))
    for field in ['previous','replacements']:
        bad=copy.deepcopy(PLAN);bad[field][f]='../outside.swift';variants.append((field,bad))
    bad=copy.deepcopy(PLAN);bad['outputs'].clear();variants.append(('inconsistent',bad))
    for label,bad in variants:
        overlay=temp/('overlay-'+label)
        for n in PLAN['templates']:
            p=overlay/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OVERLAY/n).read_bytes())
        (overlay/(STAGE+'_patches.json')).write_text(json.dumps(bad));reject(seed('source-'+label),label,overlay)
    for i,n in enumerate([f,next(iter(PLAN['guards']))]):
        tree=seed('symlink-'+str(i));p=tree/n;external=temp/('outside-'+str(i));external.write_bytes(p.read_bytes());p.unlink();p.symlink_to(external);reject(tree,'external symlink '+n)
    return rejected


def runtime(source):
    base=payload_fixture(source).split('@main struct CopyDeliveryTests')[0]
    assert base.count('final class Account {')==1 and base.count('struct EnqueueMessage {')==1
    base=base.replace('final class Account {','final class Account {\n    let nagramiXMessageArchive=SourceArchive()',1)
    base=base.replace('struct EnqueueMessage {','struct EnqueueMessage {\n    var nativeForwardSource: MessageId? = nil',1)
    part=assembly((source/UI).read_text())
    node=(source/UI).read_text();helper=block(node,'private func nagramiXSubmitComposerForwardMessages(')
    boundary=(ROOT/'scripts/tests/NagramiXRepostCopyIntegrityBoundary.swift').read_text().replace('// PRODUCTION_COMPOSER_ASSEMBLY',part).replace('// PRODUCTION_COMPOSER_CONFIRMATION',confirmation(node))
    return base+'\n'+helper+'\n'+boundary+'\n'+(ROOT/'scripts/tests/NagramiXRepostCopyIntegrityTests.swift').read_text()

def execute(source,swiftc,temp):
    code=runtime(source);mapped=block(code,'func nagramiXCopyMessagesAsNewBySource(')
    signature=mapped[:mapped.index(' {')]
    one_by_one=signature+' {\n    guard Set(messages.map { $0.id }).count == messages.count else { return nil }\n    var output: [EngineMessage.Id: [EnqueueMessage]] = [:]\n    for message in messages {\n        guard let value = nagramiXCopyMessagesAsNew([message], account: account, hideCaptions: hideCaptions, forceLocalMedia: forceLocalMedia, accountPeerId: accountPeerId, mediaCopy: mediaCopy) else { return nil }\n        output[message.id] = value\n    }\n    return output\n}'
    new_ui=assembly((source/UI).read_text());old_ui=assembly(previous(UI),True)
    variants={'current':code,'legacy-flat':payload_fixture(source),'legacy-temporary':temporary_fixture(source),
      'legacy-zip-assembly':code.replace(new_ui,old_ui+'\n        nagramiXForwardCopyStaging = nil'),
      'one-builder-per-source':code.replace(mapped,one_by_one),
      'range-recorded-too-early':code.replace('defer { sourceRanges.append(outputStart ..< result.count) }','sourceRanges.append(outputStart ..< result.count)'),
      'reversed-parts':code.replace('copies.map { $0.withUpdatedThreadId(replyThreadId) }','copies.reversed().map { $0.withUpdatedThreadId(replyThreadId) }'),
      'first-part-topic-only':code.replace('copies.map { $0.withUpdatedThreadId(replyThreadId) }','copies.enumerated().map { $0.offset == 0 ? $0.element.withUpdatedThreadId(replyThreadId) : $0.element }'),
      'native-protection-guard-lost':code.replace('guard self.chatPresentationInterfaceState.interfaceState.forwardOptionsState?.hideNames == true,','guard true,'),
      'truncated-source-range':code.replace('Array(batch.messages[range])','Array(batch.messages[range].prefix(1))'),
      'duplicate-source-accepted':code.replace('guard Set(messages.map { $0.id }).count == messages.count,','guard true,'),
      'source-count-payment':code.replace('messageCount: messages.count, requiresPayment:', 'messageCount: 1, requiresPayment:'),
      'early-copy-commit':code.replace('nagramiXForwardCopyStaging = staging','staging.commit(); nagramiXForwardCopyStaging = staging'),
      'repeated-payment-submit':code.replace('guard !submitted else { return }','if submitted { submitted = false }'),
    }
    positive={'current','legacy-flat','legacy-temporary'}
    assert all(v!=code for n,v in variants.items() if n not in positive)
    results=[]
    for label,content in variants.items():
        path=temp/(label+'.swift');path.write_text(content)
        for optimized in [False,True]:
            name=label+('-O' if optimized else '-debug');exe=temp/name;private_temp=temp/(name+'-files');private_temp.mkdir()
            compile=subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),str(path),'-o',str(exe)],capture_output=True,text=True)
            assert compile.returncode==0,compile.stdout+compile.stderr
            run=subprocess.run([str(exe)],env={**os.environ,'TMPDIR':str(private_temp)},capture_output=True,text=True,timeout=30,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if label in positive:assert run.returncode==0,run.stdout+run.stderr;status=run.stdout.strip()
            else:assert run.returncode!=0 and 'Repost integrity regression:' in run.stderr,run.stdout+run.stderr;status='regression reproduced and rejected'
            results.append(name+': '+status);print(results[-1],flush=True)
    return results

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path);p.add_argument('--report',type=Path);a=p.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(a, Path(__file__), 'pip_playback_commands'):
        return
    if delegate_icon_stage_if_applied(a, Path(__file__), 'round_caption_transport'):
        return
    verify(a.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-repost-copy-check-') as folder:
        temp=Path(folder);rejected=guard_checks(a.source,temp/'guards');run=temp/'runtime';run.mkdir();results=execute(a.source,a.swiftc,run) if a.swiftc else []
        if a.swiftc:
            for n in PLAN['outputs']:subprocess.run([str(a.swiftc),'-frontend','-parse',str(a.source/n)],check=True)
    report={'replacements':len(PLAN['outputs']),'guards':len(PLAN['guards']),'fail_closed':len(rejected),'executions':results,'scope':'R1 only; R2 caption flags and R3 native playback unchanged','sdk':'not authorized or run','device':'pending','boundaries':'Current production flat/source-indexed copier, real Foundation staging bytes and complete composer assembly block. Postbox/composer widgets are explicit boundaries; no UIKit, Telegram RPC or physical device execution.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
