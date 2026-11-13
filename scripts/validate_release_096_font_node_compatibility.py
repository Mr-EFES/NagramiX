#!/usr/bin/env python3
"""Verify actual imported Texture initializer and preserve font screen behavior."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_quick_format import manifest
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from app_font_selection_runtime import UI
from app_font_selection_apple import check as apple_check,navigation_check,access_check
from font_preview_apply_native import check as node_check
import font_preview_apply_runtime as preview
import app_font_selection_runtime as fonts

ROOT=Path(__file__).resolve().parents[1];STAGE='release_096_font_node_compatibility'


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert plan['required_previous_stage']=='release_096_transcription_compatibility' and set(plan['inputs'])=={UI} and len(plan['guards'])==5 and not plan['copies']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
 before=(ROOT/'ios'/plan['previous'][UI]).read_text();after=(a.source/UI).read_text()
 old='super.init(viewBlock: { button }, didLoadBlock: nil)';new='super.init(viewBlock: { button }, didLoad: nil)'
 assert before.count(old)==1 and after==before.replace(old,new,1),'Unrelated font/preview/apply/layout/license changes'
 snapshot=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='font-node-abi-') as d:
  folder=Path(d);refusals=guard_checks(a.source,STAGE,plan,folder/'guards')
  node=node_check(a.source,a.swiftc,folder);code=preview.fixture(a.source)
  runs=execute(a.swiftc,folder,'font-preview-final63',code)
  runs+=execute(a.swiftc,folder,'font-resolver-final63',fonts.fixture(a.source))
  for name,mutated,label in preview.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
  navigation=navigation_check(a.source,a.swiftc,folder);access=access_check(a.source,a.swiftc,folder)
  apple=apple_check(a.source,a.swiftc,folder);run([a.swiftc,'-frontend','-parse',a.source/UI])
 assert snapshot==manifest(a.source)
 report={'stage':STAGE,'loader_refusals':len(refusals),'executions':runs,'node':node,'navigation':navigation,'public_access':access,'complete_screen_uikit':apple,'source_unchanged_by_checks':True,'contract':'Exactly one imported initializer label. Same designated two-argument Objective-C initializer, button/frame/navigation visibility, draft/apply/preview/current cards/catalogue/licenses/status/theme unchanged. Historical52/63 source/runtime bytes exact; native checks now use final64 lifecycle fix only for known SHA. This historical label patch alone did not fix device208 dynamic constructor redispatch. Original207 label must be rejected.','full_application_sdk':'pending','device':'pending'}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
