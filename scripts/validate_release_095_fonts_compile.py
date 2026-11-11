#!/usr/bin/env python3
"""Проверить фактический native API экрана шрифтов после SDK199."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import run
from app_font_selection_runtime import UI
from app_font_selection_apple import navigation_check,access_check,check as apple_check

ROOT=Path(__file__).resolve().parents[1]
STAGE='release_095_fonts_compile'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
 plan=checked_plan(STAGE)
 assert plan['required_previous_stage']=='temporary_expiration_semantics'
 assert set(plan['inputs'])=={UI} and len(plan['guards'])==7 and len(plan['native_guards'])==2
 assert not plan['copies'] and not plan['deletions']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
 before=(ROOT/'ios'/plan['previous'][UI]).read_text();after=(a.source/UI).read_text()
 old='self.navigationBar?.updatePresentationData(NavigationBarPresentationData(presentationData: value))'
 new='self.navigationBar?.updatePresentationData(NavigationBarPresentationData(presentationData: value), transition: .immediate)'
 assert before.count(old)==1 and after==before.replace(old,new),'Unexpected font screen changes'
 initial=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='nagramix-font-sdk199-') as temporary:
  folder=Path(temporary)
  refusals=guard_checks(a.source,STAGE,plan,folder/'guards')
  navigation=navigation_check(a.source,a.swiftc,folder)
  access=access_check(a.source,a.swiftc,folder)
  apple=apple_check(a.source,a.swiftc,folder)
  run([a.swiftc,'-frontend','-parse',a.source/UI])
 assert manifest(a.source)==initial
 report={'stage':STAGE,'replacements':1,'guards':7,'native_guard_origins':plan['native_guards'],'loader_refusals':len(refusals),'native_navigation_contract':navigation,'public_override_contract':access,'apple_uikit_precheck':apple,'swift_parse':1,'source_files':len(initial),'source_unchanged_by_checks':True,'whole_app_sdk':'pending','device':'pending'}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
