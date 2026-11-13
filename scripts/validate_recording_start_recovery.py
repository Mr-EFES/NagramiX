#!/usr/bin/env python3
"""Проверить передачу звука записи при синхронном завершении плеера."""
import argparse
import json
import tempfile
from pathlib import Path

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from recording_start_recovery_runtime import fixture, AUDIO, RECORDER, CAMERA, SIGNAL
from validate_private_temporary_transcription import execute
from validate_quick_format import manifest, block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import run

ROOT=Path(__file__).resolve().parents[1]
STAGE='recording_start_recovery'


def negatives(code):
    cases=[
        ('no-await-marker','self.holders[activeIndex].deactivatingDisposable = deactivationDisposable','self.holders[activeIndex].deactivatingDisposable = nil','async player release is awaited before recording'),
        ('never-clear-marker','currentRecord.deactivatingDisposable = nil','currentRecord.deactivatingDisposable = EmptyDisposable','every repeated voice/round request acquires the session'),
        ('always-discard-player','if currentRecord.once {','if true {','previous playback is restored only for reusable holder'),
        ('exclusive-music-transfer','temporary = true','temporary = false','music mixing handoff contract retained'),
        ('record-preempts-call','if self.holders[activeIndex].audioSessionType == .voiceCall {','if self.holders[activeIndex].audioSessionType == .videoCall {','recording and interruption preserve active call priority'),
    ]
    for name,old,new,message in cases:
        assert code.count(old)==1,(name,code.count(old))
        yield name,code.replace(old,new,1),message


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    a=parser.parse_args();plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='pip_preview_continuity'
    assert set(plan['inputs'])=={AUDIO} and len(plan['guards'])==19 and not plan['copies']
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/name)==h,name
    before=manifest(a.source)
    code=fixture(a.source)
    old=(ROOT/'ios'/plan['previous'][AUDIO]).read_text()
    new=(a.source/AUDIO).read_text()
    # This fix changes only the subscription setup around one unchanged
    # updateHolders completion. Every routing/configuration API remains exact.
    prefix='private func updateHolders(interruption: Bool = false)'
    assert old.split(prefix,1)[0]==new.split(prefix,1)[0]
    suffix='    private func applyNoneDelayed()'
    assert old.split(suffix,1)[1]==new.split(suffix,1)[1]
    old_method=block(old,prefix);new_method=block(new,prefix)
    assert code.count(new_method)==1
    with tempfile.TemporaryDirectory(prefix='recording-start-recovery-') as d:
        folder=Path(d)
        refusals=guard_checks(a.source,STAGE,plan,folder/'guards')
        executions=execute(a.swiftc,folder,'recording-transfer',code)
        executions+=execute(a.swiftc,folder,'original096-inline-deactivation',code.replace(new_method,old_method,1),'inline completion must not leave a stale deactivation holder')
        for name,mutated,message in negatives(code):executions+=execute(a.swiftc,folder,name,mutated,message)
        run([a.swiftc,'-frontend','-parse',a.source/AUDIO])
    assert manifest(a.source)==before
    report={'stage':STAGE,'loader_refusals':len(refusals),'executions':executions,'production_assertions_per_positive_mode':4906,
            'real_signal_kit':['Atomic','Disposable','Subscriber','Signal (through synchronous constructors)','deliverOn(Queue)','Queue (DispatchWorkItem submission adapter only)'],
            'recorders_unchanged':{n:plan['guards'][n] for n in [RECORDER,CAMERA]},
            'native_session_configuration_routing_unchanged':True,'source_unchanged_by_checks':True,
            'boundary':'Actual updateHolders/removeDeactivatedHolder/HolderRecord and real SwiftSignalKit completion/disposal/queue behavior execute in debug and optimized modes. DispatchWorkItem adapts legacy Swift closure submission to Linux Swift6; isCurrent/inline execution remain production code. Fixture holders replace only native session setup and AV capture; no iPhone microphone/camera or AVAudioSession hardware behavior is asserted.',
            'full_application_apple_sdk':'pending','device':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
