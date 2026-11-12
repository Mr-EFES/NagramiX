#!/usr/bin/env python3
"""Verify nullable native RPC descriptions without changing transcription routes."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_quick_format import manifest
from validate_local_copy_delivery import execute,run
from validate_premium_temporary_transcription_native_api import check as native_api
from transcription_compatibility_apple import check as header_check,TRANSPORT
import transcription_compatibility_runtime as runtime

ROOT=Path(__file__).resolve().parents[1];STAGE='release_096_transcription_compatibility'


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert plan['required_previous_stage']=='release_096_calendar_compatibility' and set(plan['inputs'])=={TRANSPORT} and len(plan['guards'])==4 and not plan['copies']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
 before=(ROOT/'ios'/plan['previous'][TRANSPORT]).read_text();after=(a.source/TRANSPORT).read_text()
 old='let description = error.errorDescription';new=old+' ?? ""'
 assert before.count(old)==1 and after==before.replace(old,new,1),'Unrelated route/lifetime/RPC/storage changes'
 snapshot=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='transcription-nullability-') as d:
  folder=Path(d);refusals=guard_checks(a.source,STAGE,plan,folder/'guards')
  header=header_check(a.source,a.swiftc,folder/'native-header');native=native_api(a.source,a.swiftc,folder/'native-rpc')
  code=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'nullable-premium-asr',code)
  for name,mutated,label in runtime.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
  run([a.swiftc,'-frontend','-parse',a.source/TRANSPORT])
 assert snapshot==manifest(a.source)
 report={'stage':STAGE,'loader_refusals':len(refusals),'executions':runs,'native_error_header':header,'native_rpc':native,'source_unchanged_by_checks':True,'contract':'Exactly one nil-coalescing expression. Original-ID guards, temporary voice/round lifetime, selected provider, server classification and RPC shape unchanged. Unknown/nil description maps to existing network error. No force unwrap.','full_application_sdk':'pending','device':'pending'}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
