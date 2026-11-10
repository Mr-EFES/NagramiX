#!/usr/bin/env python3
"""Закрепить исправление SDK192: настоящий порядок аргументов настроек."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import run
from validate_settings_argument_bindings import SETTINGS,validate

ROOT=Path(__file__).resolve().parents[1]
STAGE='release_092_settings_compile'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert plan['required_previous_stage']=='content_interaction_consent' and set(plan['inputs'])=={SETTINGS}
 assert len(plan['guards'])==5 and not plan['copies'] and not plan['deletions']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,sha in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==sha,n
 before=(ROOT/'ios'/plan['previous'][SETTINGS]).read_text();after=(a.source/SETTINGS).read_text()
 old='        updateRoundVideo: { value in update { $0.media.roundVideo = value } },\n        updateBackgroundVideoPlayback: { value in update { $0.backgroundVideoPlayback = value } },'
 new='        updateBackgroundVideoPlayback: { value in update { $0.backgroundVideoPlayback = value } },\n        updateRoundVideo: { value in update { $0.media.roundVideo = value } },'
 assert before.count(old)==1 and after==before.replace(old,new)
 snapshot=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='nagramix-settings-192-') as d:
  root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');result=validate(after,a.swiftc,root)
  run([a.swiftc,'-frontend','-parse',a.source/SETTINGS])
 assert snapshot==manifest(a.source)
 run(['python3',a.source/'build-system/Make/PostboxImportCheck.py',a.source])
 result.update(stage=STAGE,outputs=plan['outputs'],guards=len(plan['guards']),loader_refusals=len(refused),source_files=len(snapshot),source_unchanged_by_checks=True,apple_sdk_retry='pending')
 if a.report:a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
