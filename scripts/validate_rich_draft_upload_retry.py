#!/usr/bin/env python3
"""Проверить общий rich uploader и черновик настоящими операторами SignalKit."""
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
ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
STAGE='rich_draft_upload_retry'
PLAN=json.loads((OVERLAY/(STAGE+'_patches.json')).read_text())
F=next(iter(PLAN['inputs']))
SK='submodules/SSignalKit/SwiftSignalKit/Source/'
UPLOAD='submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift'
EDIT='submodules/TelegramCore/Sources/PendingMessages/RequestEditMessage.swift'
def sha(data):return hashlib.sha256(data).hexdigest()

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


def verify(source):
    for name,digest in {**PLAN['outputs'],**PLAN['guards']}.items():
        assert sha((source/name).read_bytes())==digest,name
    for name,digest in PLAN['templates'].items():
        assert sha((OVERLAY/name).read_bytes())==digest,name
    before=(OVERLAY/PLAN['previous'][F]).read_text()
    after=(source/F).read_text()
    addition='        // Keep the persisted draft/operation alive until its complete rich payload\n        // uploads. Retry is cancellable when the draft changes or the account stops.\n        |> retry(0.2, maxDelay: 5.0, onQueue: Queue.concurrentDefaultQueue())\n'
    assert after.count(addition)==1 and after.replace(addition,'')==before
    assert after.index('|> retry(0.2,')<after.index('|> mapToSignal { apiRichMessage -> Signal<Void, NoError>')
    calls={}
    for path in (source/'submodules').rglob('*.swift'):
        count=path.read_text().count('uploadedRichMessage(')
        if count:calls[str(path.relative_to(source))]=count
    assert calls=={UPLOAD:1,EDIT:1,F:1},calls
    retry=block((source/(SK+'Signal_Catch.swift')).read_text(),'public func retry<T, E>(_ delayIncrement:')
    assert 'Signal<T, NoError>' in retry and 'shouldRetry.swap(false)' in retry
    native_map=block((source/(SK+'Signal_Meta.swift')).read_text(),'public func mapToSignal<T, R, E>(')
    assert '(Signal<T, E>) -> Signal<R, E>' in native_map
    assert '"//submodules/SSignalKit/SwiftSignalKit:SwiftSignalKit"' in (source/'submodules/TelegramCore/BUILD').read_text()
    assert '"Source/**/*.swift"' in (source/'submodules/SSignalKit/SwiftSignalKit/BUILD').read_text()
    pipeline=(OVERLAY/'apply_overlay.py').read_text()
    assert pipeline.index('    apply_pip_transition_geometry(')<pipeline.index('    apply_rich_draft_upload_retry(')


def runtime(source):
    parts=[(ROOT/'scripts/tests/NagramiXRichDraftRetryBoundary.swift').read_text()]
    for file in ['Atomic','Disposable','Subscriber']:
        parts.append((source/(SK+file+'.swift')).read_text())
    signal=(source/(SK+'Signal.swift')).read_text()
    parts.append(signal[:signal.index('@available(iOS 13.0')])
    meta=(source/(SK+'Signal_Meta.swift')).read_text()
    parts.extend(block(meta,m) for m in ['private final class SignalQueueState', 'public func switchToLatest<', 'public func mapToSignal<T, R, E>('])
    catch=(source/(SK+'Signal_Catch.swift')).read_text()
    parts.extend(block(catch,m) for m in ['public func `catch`<', 'private func recursiveFunction(', 'public func retry<T, E>(_ delayIncrement:'])
    parts.append(block((source/(SK+'Signal_Take.swift')).read_text(),'public func take<T, E>(_ count:'))
    parts.append(block((source/(SK+'Signal_Mapping.swift')).read_text(),'public func mapError<T, E, R>('))
    parts.append(block((source/UPLOAD).read_text(),'func uploadedRichMessage('))
    draft=(source/F).read_text()
    start=draft.index('        return uploadedRichMessage(')
    end=draft.index('\n    } else {\n        return .complete()',start)
    parts.append('''func synchronizeDraft(network: Network, richText: RichTextMessageAttribute?) -> Signal<Void,NoError> {
    let postbox=Postbox(), auxiliaryMethods=AccountAuxiliaryMethods(), messageMediaPreuploadManager=MessageMediaPreuploadManager()
    let peerId=PeerId()
    let flags: Int32=(1 << 0) | (1 << 3) | (1 << 8)
    let replyTo: Api.InputReplyTo? = .init(id: 5)
    let inputPeer=Api.InputPeer(id: 7)
    let savedMessage="plain"
    let savedEntities=[Api.MessageEntity(id: 3)]
    let suggestedPost: Int?=9
'''+draft[start:end]+'\n}')
    edit=(source/EDIT).read_text()
    start=edit.index('    return uploadedRichMessage(')
    end=edit.index('\n    |> mapToSignal { resolvedRichMessage',start)
    parts.append('''struct StateManager { let auxiliaryMethods=AccountAuxiliaryMethods() }
struct EditMessageId { let peerId=PeerId() }
func resolveEdit(network: Network, richText: RichTextMessageAttribute?) -> Signal<Api.InputRichMessage?,RequestEditMessageInternalError> {
    let postbox=Postbox(), stateManager=StateManager(), messageMediaPreuploadManager=MessageMediaPreuploadManager()
    let forceReupload=false, messageId=EditMessageId()
'''+edit[start:end]+'\n}')
    parts.append((ROOT/'scripts/tests/NagramiXRichDraftRetryTests.swift').read_text())
    return '\n'.join(parts)


def execute(source,swiftc,temp):
    code=runtime(source)
    variants={'current':code,
      'original-compile-error':code.replace('        |> retry(0.2, maxDelay: 5.0, onQueue: Queue.concurrentDefaultQueue())\n',''),
      'bare-fallback':code.replace('        |> retry(0.2, maxDelay: 5.0, onQueue: Queue.concurrentDefaultQueue())','        |> `catch` { _ -> Signal<Api.InputRichMessage?, NoError> in return .single(nil) }'),
      'lost-cancellation':code.replace('let currentShouldRetry = shouldRetry.with { value in\n                    return value\n                }','let currentShouldRetry = true'),
    }
    assert all(text!=code for name,text in variants.items() if name!='current')
    runs=[]
    for label,text in variants.items():
        file=temp/(label+'.swift');file.write_text(text)
        for optimized in [False,True]:
            name=label+('-O' if optimized else '-debug');binary=temp/name
            built=subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),str(file),'-o',str(binary)],capture_output=True,text=True)
            if label=='original-compile-error':
                assert built.returncode!=0 and ('conflicting arguments to generic parameter' in built.stderr or 'cannot convert' in built.stderr),built.stdout+built.stderr
                status='original Signal<Void, NoError>/PendingMessageUploadError mismatch rejected'
            else:
                assert built.returncode==0,built.stdout+built.stderr
                result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
                if label=='current':
                    assert result.returncode==0,result.stdout+result.stderr
                    status=result.stdout.strip()
                else:
                    assert result.returncode!=0 and 'Rich draft retry regression:' in result.stderr,result.stdout+result.stderr
                    status='regression reproduced and rejected'
            runs.append(name+': '+status);print(runs[-1],flush=True)
    return runs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-rich-draft-retry-') as folder:
        temp=Path(folder);rejected=guard_checks(args.source,temp/'guards')
        work=temp/'runtime';work.mkdir()
        runs=execute(args.source,args.swiftc,work) if args.swiftc else []
        if args.swiftc:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/F)],check=True)
    report={'replacements':len(PLAN['outputs']),'guards':len(PLAN['guards']),'fail_closed':len(rejected),'executions':runs,'sdk':'not rerun','device':'pending','boundaries':'Pinned real Signal/Subscriber/Atomic/Disposable/Meta/retry/catch/take/mapError implementation, production rich uploader and both complete consumer boundary chains. Scheduling and Telegram network/postbox/API values are test boundaries.'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
