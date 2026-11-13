#!/usr/bin/env python3
"""Verify cached text cannot retry recognition with the master OFF."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import execute,run
import transcription_cached_read_runtime as runtime
import feature_transcription_master_runtime as master

ROOT=Path(__file__).resolve().parents[1];STAGE='transcription_cached_read'


class BeforeSource:
    def __init__(self,source,plan):self.source=source;self.plan=plan
    def __truediv__(self,name):
        return ROOT/'ios'/self.plan['previous'][name] if name in self.plan['previous'] else self.source/name


def contracts(source,plan):
    assert plan['required_previous_stage']=='feature_contract_consistency'
    assert set(plan['inputs'])=={master.FILE,master.ROUND} and len(plan['guards'])==8
    assert not plan['copies'] and not plan['deletions'] and not plan['native_inputs']
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(source/n)==h,n
    for path in plan['inputs']:
        before=(ROOT/'ios'/plan['previous'][path]).read_text();after=(source/path).read_text()
        old_tap=block(before,'    private func transcribe()');new_tap=block(after,'    private func transcribe()')
        new_prefix=block(new_tap,'        if !NagramiXTranscriptionRuntime.requestsEnabled {')
        old_prefix=next(l for l in old_tap.splitlines() if l.startswith('        guard NagramiXTranscriptionRuntime.requestsEnabled'))
        guard='            guard NagramiXTranscriptionRuntime.requestsEnabled else { return }\n'
        assert new_tap.count(guard)==1
        restored=after.replace(new_prefix,old_prefix,1).replace(guard,'',1)
        assert restored==before,'Changed code outside the cached-read gate: '+path
        assert 'self.isWaitingForCollapse = false' in new_prefix
        assert new_prefix.index('return')<new_tap.index('let temporary =')
        assert 'engine.' not in new_prefix and 'transcribeAudio(' not in new_prefix
        assert 'isWaitingForCollapse' in before,'Actual native waiting-state member required'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=checked_plan(STAGE);contracts(a.source,plan)
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    initial=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-cached-transcription-') as temp:
        folder=Path(temp);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
        code=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'cached-read',code)
        runs+=execute(a.swiftc,folder,'original71-native-retry',runtime.fixture(BeforeSource(a.source,plan)),'OFF reads forced cache without native retry')
        old='            guard NagramiXTranscriptionRuntime.requestsEnabled else { return }\n terminalRequests += 1'
        assert old in code
        runs+=execute(a.swiftc,folder,'no-final-master-check',code.replace(old,' terminalRequests += 1'),'final native gate rechecks a changed master before request')
        old='self.isWaitingForCollapse = false';assert old in code
        runs+=execute(a.swiftc,folder,'stale-collapse-state',code.replace(old,'self.isWaitingForCollapse = true'),'cached open resets waiting-for-collapse state')
        for n in plan['outputs']:run([a.swiftc,'-frontend','-parse',a.source/n])
    assert manifest(a.source)==initial
    report={'stage':STAGE,'source_files':len(initial),'source_unchanged_by_checks':True,'outputs':2,'guards':8,'loader_refusals':len(refused),'executions':runs,'boundary':'Actual master/cached UI prefixes and native shouldBeginTranscription decision; actual SignalKit cancellation, display and notification tests retained. Terminal RPC/recognition is an explicit counter boundary, no server or microphone accessed. Actual prior71 negative reproduces retry for ready forced transcript without a persisted message attribute.','full_application_sdk':'pending','device':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
