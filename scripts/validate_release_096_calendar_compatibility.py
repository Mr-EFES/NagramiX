#!/usr/bin/env python3
"""Проверить iOS15-совместимый календарь без изменения праздничного расписания."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_quick_format import manifest
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from snowfall_holidays_runtime import POLICY
from snowfall_holidays_apple import check as api_check
import calendar_compatibility_runtime as runtime

ROOT=Path(__file__).resolve().parents[1];STAGE='release_096_calendar_compatibility'


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert plan['required_previous_stage']=='single_touch_message_selection' and set(plan['inputs'])=={POLICY} and len(plan['guards'])==4 and not plan['copies']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
 before=(ROOT/'ios'/plan['previous'][POLICY]).read_text();after=(a.source/POLICY).read_text()
 old='let lunar = chinese.dateComponents([.month, .day, .isLeapMonth], from: noon)';new='let lunar = chinese.dateComponents(in: referenceZone, from: noon)'
 assert before.count(old)==1 and after==before.replace(old,new,1),'Unrelated policy/date/storage changes'
 snapshot=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='calendar-ios15-check-') as d:
  folder=Path(d);refusals=guard_checks(a.source,STAGE,plan,folder/'guards');code=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'calendar-ios15',code)
  for name,mutated,label in runtime.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
  public=api_check(a.source,a.swiftc,folder,public_api=True);apple=api_check(a.source,a.swiftc,folder)
  run([a.swiftc,'-frontend','-parse',a.source/POLICY])
 assert snapshot==manifest(a.source)
 report={'stage':STAGE,'loader_refusals':len(refusals),'executions':runs,'public_core_api':public,'apple_sdk_precheck':apple,'source_unchanged_by_checks':True,'contract':'Exactly one calendar query replacement; public API, dates, density75, storage, timezones, timers, settings, inChats and emitter remain exact. Bulk legacy components retain leap-month flag. Historical57 SHA/runtime stays exact; native SDK checks final61 policy at iOS15.','boundary':'Complete holiday/settings/scheduler/native SignalKit/emitter code with explicit OS clock and UIKit/CA I/O.5857modern-vs-legacy cases plus6933holiday cases per mode; original unsupported API must fail on real Apple iOS15 SDK. Full application/device pending.','full_application_sdk':'not_run','device':'pending'}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
