#!/usr/bin/env python3
"""Проверить исправление двух нативных строк ошибок вложений после SDK200."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import run
import native_string_references as native

ROOT=Path(__file__).resolve().parents[1];STAGE='release_095_composer_strings_compile'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert plan['required_previous_stage']=='release_095_fonts_compile'
 assert set(plan['inputs'])=={native.MENU} and len(plan['guards'])==6 and not plan['copies'] and not plan['deletions']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
 before=(ROOT/'ios'/plan['previous'][native.MENU]).read_text();after=(a.source/native.MENU).read_text()
 assert before.count('.strings.Common_UnknownError')==2
 assert after==before.replace('.strings.Common_UnknownError','.strings.Login_UnknownError')
 initial=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='nagramix-sdk200-native-') as temporary:
  folder=Path(temporary);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
  texts={str(p.relative_to(a.source)):p.read_text() for p in a.source.rglob('*.swift') if not p.is_symlink()}
  report=native.check(a.source,texts,a.swiftc,folder)
  run([a.swiftc,'-frontend','-parse',a.source/native.MENU])
 assert manifest(a.source)==initial
 report.update(stage=STAGE,replacements=1,string_reference_replacements=2,guards=6,loader_refusals=len(refused),source_files=len(initial),source_unchanged_by_checks=True,whole_app_sdk='pending',device='pending')
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
