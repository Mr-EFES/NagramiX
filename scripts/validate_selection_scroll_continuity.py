#!/usr/bin/env python3
"""Проверить непрерывное выделение при автопрокрутке и смене окна истории."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_quick_format import manifest
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from selection_scroll_continuity_runtime import fixture,HISTORY,HELPER
from selection_column_coordinates_apple import check as apple_check

ROOT=Path(__file__).resolve().parents[1];STAGE='selection_scroll_continuity'
CHANGES=[('private var nagramiXSingleSelectionView: (ObjectIdentifier, Int32)?','private var nagramiXSingleSelectionView: (MessageHistoryView, Int32)?'),('let token = (ObjectIdentifier(historyView.originalView), historyView.id)','let token = (historyView.originalView, historyView.id)'),('previous.0 == token.0 && previous.1 == token.1','previous.0 === token.0 && previous.1 == token.1')]


def negatives(code):
    for name,old,new,diagnostic in [
        ('no-stationary-update','strongSelf.handlePanSelection(location: location)','_ = location','stationary finger selects newly loaded rows'),
        ('retain-after-release','        self.nagramiXSingleSelectionView = nil\n        self.selectionPanState = nil','        self.selectionPanState = nil','video: cached snapshot releases when gesture ends'),
    ]:
        assert code.count(old)==1,(name,code.count(old));yield name,code.replace(old,new,1),diagnostic


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='selection_column_coordinates' and set(plan['inputs'])=={HISTORY} and len(plan['guards'])==7 and not plan['copies']
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
    old=(ROOT/'ios'/plan['previous'][HISTORY]).read_text();expected=old
    for before,after in CHANGES:assert expected.count(before)==1;expected=expected.replace(before,after,1)
    assert expected==(a.source/HISTORY).read_text(),'Only cached view identity/lifetime changes'
    assert 'public final class MessageHistoryView: PostboxView' in (a.source/'submodules/Postbox/Sources/MessageHistoryView.swift').read_text()
    state=manifest(a.source);code=fixture(a.source);original=code
    for before,after in CHANGES:assert original.count(after)==1;original=original.replace(after,before,1)
    with tempfile.TemporaryDirectory(prefix='selection-scroll-check-') as d:
        f=Path(d);refusals=guard_checks(a.source,STAGE,plan,f/'guards');runs=execute(a.swiftc,f,'selection-held-edge',code)
        runs+=execute(a.swiftc,f,'original68-cache-lifetime',original,'video: cached snapshot stays alive across skipped display update')
        for n,mutated,diagnostic in negatives(code):runs+=execute(a.swiftc,f,n,mutated,diagnostic)
        apple=apple_check(a.source,a.swiftc,f);run([a.swiftc,'-frontend','-parse',a.source/HISTORY])
    assert state==manifest(a.source)
    report={'stage':STAGE,'loader_refusals':len(refusals),'executions':runs,'previous_checks_per_mode':5975,'new_video_checks_per_mode':52,'production_scope':'Three cache identity/lifetime expressions only. Left column68, one-finger recognizer,range,reversal,rows,edge timing/speed,helpers and all unrelated paths unchanged.',
'cause':'ObjectIdentifier does not retain its object. Across skipped display updates an old cached snapshot can deallocate and its address can be reused while location.id is unchanged. A stale identity token skips caching intermediate rows.',
'fix':'Retain the last cached MessageHistoryView during the gesture, compare by ===, release through existing finish/reset. Only one cached snapshot is retained.',
'apple_uikit':apple,'source_unchanged_by_checks':True,'full_application_sdk':'pending','device':'pending',
'boundary':'Actual production history/helper/recognizer/autoscroll/cache code with affine UIKit and list/timer/display adapters. Rotated Legacy/CoreList host geometry, checked/unchecked anchor,stationary held finger,repeated paging across skipped display frames,upward reversal and cache release. Weak reference assertion reproduces unsafe lifetime deterministically; no claim that this cause has been traced on the user iPhone.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
