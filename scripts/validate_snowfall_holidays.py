#!/usr/bin/env python3
"""Check forced holiday overlay, civil calendar, live lifecycle and saved manual state."""
import argparse,json,tempfile
from pathlib import Path
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from validate_quick_format import manifest,block
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix,historical_source
import snowfall_holidays_runtime as runtime
from snowfall_holidays_apple import check as api_check
ROOT=Path(__file__).resolve().parents[1];STAGE='snowfall_holidays'


def contract(source,plan):
    assert plan['required_previous_stage']=='snowfall' and len(plan['inputs'])==2 and len(plan['guards'])==16
    assert set(plan['copies'])=={runtime.POLICY,runtime.SCHEDULE}
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards'],**{n:v['sha256'] for n,v in plan['copies'].items()}}.items():assert digest(source/n)==h,n
    previous=lambda n:(ROOT/'ios'/plan['previous'][n]).read_text()
    ui=(source/runtime.UI).read_text();old=previous(runtime.UI)
    helper=block(ui,'private func nagramiXSnowSettingsSignal(')
    text=ui.replace(helper+'\n\n','',1).replace('nagramiXTranscriptionSettingsSignal(), nagramiXSnowSettingsSignal())','nagramiXTranscriptionSettingsSignal())',1).replace('let (settings, privacy, _, _, _) = settingsAndPrivacy','let (settings, privacy, _, _) = settingsAndPrivacy',1)
    assert text==old,'Unrelated settings rows/layout/callbacks changed'
    settings=(source/runtime.SETTINGS).read_text();before=previous(runtime.SETTINGS)
    for marker in ['public struct NagramiXSnowConfiguration:', 'public static func read(in defaults:', 'public static func normalizedDensity(']:assert block(settings,marker)==block(before,marker),'Storage/defaults changed: '+marker
    a=block(settings,'public static func update(').replace('        self.published = self.effectiveLocked(at: Date(), timeZone: .autoupdatingCurrent)\n','',1)
    assert a==block(before,'public static func update('),'Manual storage semantics changed'
    assert 'RunLoop.main.add(timer, forMode: .common)' in (source/runtime.SCHEDULE).read_text()
    assert 'repeats: false' in (source/runtime.SCHEDULE).read_text()
    from settings_header_contract import check
    headers=check(ui)
    return {'manual_storage':'Exact previous defaults/schema/normalization/update, except separate published effective state','policy':'Temporary forced ON/75, preserves saved manual state and inChats','dates':'Local Dec25, Jan7, Dec31–Jan1, Jan13–14, first Chinese New Year civil day determined in Asia/Shanghai','clock':'Next local-midnight one-shot; day/timezone/significant-clock/foreground refresh; inactive timer invalidated','ui':'Native five-input combineLatest observes effective changes; every old row/ID/layout unchanged','rendering':'Exact guarded emitter/geometry/lifecycle/LowPower/ReduceMotion unchanged','localization':'No new strings; 71 languages ×668 keys retained','headers':headers}


def predecessor_contract(source):
    # The workflow validates56 before applying57. Its exact prefix must stay56
    # when the stage registry grows; accepting the latest prefix would hide drift.
    from validate_snowfall import contract as snow_contract
    snow=checked_plan('snowfall')
    with historical_source(source,before_stage=STAGE) as prior:
        snow_contract(prior,snow)
    try:snow_contract(source,snow)
    except AssertionError:pass
    else:raise AssertionError('Stage56 validator accepted stage57 source')
    return {'stage56_exact_boundary':'passed','stage57_rejected_by_stage56':'passed'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE);c=contract(a.source,plan);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='snowfall-holidays-check-') as d:
        folder=Path(d);refusals=guard_checks(a.source,STAGE,plan,folder/'guards');code=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'snowfall-holidays',code)
        for name,mutated,label in runtime.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
        api=api_check(a.source,a.swiftc,folder,public_api=True);apple=api_check(a.source,a.swiftc,folder)
        for n in [runtime.SETTINGS,runtime.POLICY,runtime.SCHEDULE,runtime.UI]:run([a.swiftc,'-frontend','-parse',a.source/n])
    assert before==manifest(a.source)
    report={'stage':STAGE,'source_contract':c,'loader_refusals':len(refusals),'executions':runs,'public_core_api':api,'apple_sdk_precheck':apple,'source_unchanged_by_checks':True,'whole_app_sdk':'not_run','device':'pending','boundary':'Actual complete production helpers, real Foundation calendars/Timers, native SignalKit and unchanged Snow view with explicit OS-clock/UIKit/CA/queue adapters. Not physical rendering or an Apple SDK build.'}
    report['predecessor_stage_contract']=predecessor_contract(a.source)
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
