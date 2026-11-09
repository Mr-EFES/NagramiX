#!/usr/bin/env python3
"""Проверить восстановление медиассылки копии перед загрузкой, без Apple SDK."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import tempfile
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

ROOT=Path(__file__).resolve().parents[1]
STAGE='copy_reference_recovery'
CORE='submodules/TelegramCore/Sources/'
MANAGER=CORE+'State/PendingMessageManager.swift'
COPIER=CORE+'Utils/NagramiXOutgoingCopy.swift'
UPLOAD=CORE+'PendingMessages/PendingMessageUploadedContent.swift'

MANAGER_BEFORE=r'''import Foundation
struct MessageId: Hashable { let value:Int }
protocol Media {}
struct TelegramMediaImage:Media {}
struct TelegramMediaFile:Media {}
struct TelegramMediaPoll:Media {}
struct OtherMedia:Media {}
protocol Attribute {}
struct OutgoingContentInfoFlags:OptionSet { let rawValue:Int; static let nagramiXCopy=Self(rawValue:2) }
struct OutgoingContentInfoMessageAttribute:Attribute { let flags:OutgoingContentInfoFlags }
struct ForwardSourceInfoAttribute:Attribute {}
enum PartialMediaReference { case message(Int), standalone }
struct OutgoingMessageInfoAttribute:Attribute { let partialReference:PartialMediaReference? }
struct Message { let id:MessageId; let media:[Media]; let attributes:[Attribute] }
final class PendingMessageContext { var forcedReuploadOnce=false;var nagramiXRefreshCopyReferences=false }
final class ManagerProbe {
 var messageContexts:[MessageId:PendingMessageContext]=[:]
 var sending:[[MessageId]]=[]
 func beginSendingMessages(_ ids:[MessageId]) { sending.append(ids) }
'''
MANAGER_AFTER=r'''

 func retry(_ messages:[Message],_ error:String,_ indices:[Int]?=nil)->Bool {
 nagramiXRefreshCopiedMediaReferencesIfNeeded(messages:messages,error:error,indices:indices)
 }
}
var checks=0
func check(_ condition:@autoclosure()->Bool,_ label:String){precondition(condition(),label);checks+=1}
@main enum Tests {static func main(){
 func message(_ id:Int,_ copy:Bool=true,_ partial:PartialMediaReference? = .message(42),_ media:Media=TelegramMediaPoll(),_ forward:Bool=false)->Message {
 var attributes:[Attribute]=[OutgoingMessageInfoAttribute(partialReference:partial)]
 if copy {attributes.append(OutgoingContentInfoMessageAttribute(flags:[.nagramiXCopy]))}
 if forward {attributes.append(ForwardSourceInfoAttribute())}
 return Message(id:MessageId(value:id),media:[media],attributes:attributes)
 }
 func manager(_ messages:[Message])->ManagerProbe {let m=ManagerProbe();for message in messages {m.messageContexts[message.id]=PendingMessageContext()};return m}
 for media:Media in [TelegramMediaPoll(),TelegramMediaImage(),TelegramMediaFile()] {
 for error in ["FILE_REFERENCE_EXPIRED","FILEREF_INVALID","FILE_REFERENCE_0_EXPIRED"] {
 let msg=message(1,true,.message(42),media);let m=manager([msg])
 check(m.retry([msg],error),"first rejected cloud reference refreshes")
 check(m.sending==[[msg.id]],"same pending ID restarted")
 check(!m.messageContexts[msg.id]!.forcedReuploadOnce,"byte retry budget remains available")
 check(m.messageContexts[msg.id]!.nagramiXRefreshCopyReferences,"upload wrapper receives refresh phase")
 check(!m.retry([msg],error),"second rejection cannot refresh forever")
 check(m.sending.count==1,"no duplicate restart")
 }}
 for error in ["MEDIA_INVALID","CHAT_FORWARDS_RESTRICTED","CHAT_WRITE_FORBIDDEN","SLOWMODE_WAIT_10","NETWORK_ERROR"] {
 let msg=message(1);let m=manager([msg]);check(!m.retry([msg],error),"unrelated error preserves existing policy");check(m.sending.isEmpty,"unrelated error does not enqueue")
 }
 let cases=[message(1,false),message(1,true,nil),message(1,true,.standalone),message(1,true,.message(2),OtherMedia()),message(1,true,.message(2),TelegramMediaPoll(),true)]
 for msg in cases {let m=manager([msg]);check(!m.retry([msg],"FILE_REFERENCE_EXPIRED"),"native/local/missing provenance do not opt in");check(m.sending.isEmpty,"ineligible record untouched")}
 let a=message(1),b=message(2);let m=manager([a,b]);check(m.retry([a,b],"FILE_REFERENCE_1_EXPIRED",[1]),"album index identifies failing record")
 check(m.sending==[[a.id,b.id]],"whole album re-enters native send gate")
 check(!m.messageContexts[a.id]!.nagramiXRefreshCopyReferences && m.messageContexts[b.id]!.nagramiXRefreshCopyReferences,"unrelated album item untouched")
 for indices:[Int] in [[],[-1],[2],[0,0],[0,2]] {let m=manager([a,b]);check(!m.retry([a,b],"FILE_REFERENCE_EXPIRED",indices),"invalid album selection refused");check(m.sending.isEmpty && !m.messageContexts[a.id]!.nagramiXRefreshCopyReferences,"failed group validation is atomic")}
 let atomic=manager([a,b]);atomic.messageContexts[b.id]!.forcedReuploadOnce=true
 check(!atomic.retry([a,b],"FILE_REFERENCE_EXPIRED"),"exhausted retry budget refused")
 check(!atomic.messageContexts[a.id]!.nagramiXRefreshCopyReferences,"no partial state mutation")
 let missing=manager([a]);check(!missing.retry([a,b],"FILE_REFERENCE_EXPIRED"),"missing context rejected")
 print("Copy retry state checks: \(checks)")
}}
'''

def manager_fixture(source):
    return MANAGER_BEFORE+block((source/MANAGER).read_text(),'    private func nagramiXRefreshCopiedMediaReferencesIfNeeded(')+MANAGER_AFTER

def index_fixture(source):
    text=(source/MANAGER).read_text()
    start=text.index('                                var selectiveIndices: [Int]?')
    end=text.index('                                if strongSelf.nagramiXRefreshCopiedMediaReferencesIfNeeded',start)
    return '''import Foundation
func indices(_ errorText:String,_ count:Int)->[Int]? {
    let messages=Array(repeating:0,count:count)
'''+text[start:end]+'''
    return selectiveIndices
}
@main enum IndexTests { static func main() {
    precondition(indices("FILE_REFERENCE_EXPIRED",2)==nil)
    precondition(indices("FILE_REFERENCE__EXPIRED",2)==nil)
    precondition(indices("FILE_REFERENCE_0_EXPIRED",2)==[0])
    precondition(indices("FILE_REFERENCE_1_EXPIRED",2)==[1])
    precondition(indices("FILE_REFERENCE_2_EXPIRED",2)==nil)
    precondition(indices("FILE_REFERENCE_-1_EXPIRED",2)==nil)
    precondition(indices("FILE_REFERENCE_x_EXPIRED",2)==nil)
    precondition(indices("FILE_REFERENCE_999999999999999999999999999999_EXPIRED",2)==nil)
    precondition(indices("FILE_REFERENCE_0_EXPIRED",0)==nil)
    print("Native album error parser checks: 9")
}}
'''

def execute(swiftc,root,name,text,expected=0,diagnostic=None):
    swift=root/(name+'.swift');swift.write_text(text);runs=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        binary=root/(name+'-'+mode)
        result=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-module-cache-path',str(root/'cache'),*flags,str(swift),'-o',str(binary)],capture_output=True,text=True)
        assert result.returncode==0,result.stdout+result.stderr
        result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
        assert result.returncode==expected,result.stdout+result.stderr
        assert diagnostic is None or diagnostic in result.stderr,result.stdout+result.stderr
        runs.append({'name':name,'mode':mode,'exit_code':result.returncode,'output':(result.stdout+result.stderr).strip()});binary.unlink()
    return runs

def contract(source):
    plan=checked_plan(STAGE)
    for name,sha in {**plan['outputs'],**plan['guards']}.items(): assert digest(source/name)==sha,name
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    manager=(source/MANAGER).read_text()
    assert manager.count('.nagramiXRefreshCopiedMediaReferencesIfNeeded(messages: ')==2
    assert 'message: message, nagramiXRefreshCopyReferences: messageContext.nagramiXRefreshCopyReferences)' in manager
    old=(ROOT/'ios'/plan['previous'][MANAGER]).read_text()
    for marker in ['    private func applyAcknowledgedMessage(', '    private func applySentMessage(']:
        assert block(old,marker)==block(manager,marker),marker
    copier=(source/COPIER).read_text()
    assert 'mediaReference = .message(message: MessageReference(message), media: copy)' in copier
    for marker in ['private func nagramiXCopyPollAsNew(', 'public final class NagramiXRecipientCopyBatch', 'public func nagramiXPrepareRecipientCopies(', 'public func nagramiXRetryCopiedMessages(']:
        assert block(copier,marker)==block((ROOT/'ios'/plan['previous'][COPIER]).read_text(),marker),marker
    assert 'value >= 0, value < messages.count' in manager
    return plan

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);parser.add_argument('--swiftc',required=True,type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    plan=contract(args.source)
    from copy_reference_recovery_runtime import fixtures
    from temporary_notice_recovery_runtime import fixture, assert_temporary_contract, semantic_negatives
    assert_temporary_contract(args.source)
    with tempfile.TemporaryDirectory(prefix='copy-reference-recovery-') as d:
        root=Path(d);rejected=guard_checks(args.source,STAGE,plan,root/'guards')
        runs=execute(args.swiftc,root,'manager',manager_fixture(args.source))
        runs+=execute(args.swiftc,root,'album-parser',index_fixture(args.source))
        for name,text in fixtures(args.source).items():runs+=execute(args.swiftc,root,name,text)
        notice=fixture(args.source)
        runs+=execute(args.swiftc,root,'temporary-notice',notice)
        for name,code,diagnostic in semantic_negatives(notice):runs+=execute(args.swiftc,root,name,code,97,diagnostic)
        for name in plan['outputs']:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/name)],check=True)
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),'fail_closed':len(rejected),'executions':runs,'apple_sdk':'pending','device':'pending','boundary':'Real production helpers and SignalKit with native network/Postbox/UI adapters; no real Telegram RPC or UIKit rendering'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
