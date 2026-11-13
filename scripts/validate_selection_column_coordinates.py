#!/usr/bin/env python3
"""Проверить визуально левую полосу выделения в обоих backend истории."""
import argparse
import json
from pathlib import Path
import tempfile
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_quick_format import manifest,block
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from selection_column_coordinates_runtime import fixture,HISTORY,HELPER
from selection_column_coordinates_apple import check as apple_check

ROOT=Path(__file__).resolve().parents[1]
STAGE='selection_column_coordinates'


def negatives(code):
    for name,old,new,diagnostic in [
        ('two-finger-regression','self.minimumNumberOfTouches = 1','self.minimumNumberOfTouches = 2','single touch only; native two-finger separate'),
        ('mirror-unrotated','self.rotated ? self.listView.view.bounds.maxX - location.x : location.x','true ? self.listView.view.bounds.maxX - location.x : location.x','host coordinates convert into list coordinates'),
        ('stale-frame-width','self.listView.view.bounds.maxX - location.x','self.frame.width - location.x','column follows current bounds after resize'),
        ('double-flip-vertical','let columnLocation = CGPoint(x: columnX, y: location.y)','let columnLocation = CGPoint(x: columnX, y: self.frame.height - location.y)','existing vertical safe area stays in list coordinates'),
        ('icon-height-only','NagramiXMessageSelectionColumn.contains(columnLocation,','location.y < 180 && NagramiXMessageSelectionColumn.contains(columnLocation,','visual left checkbox column starts selection'),
    ]:
        assert code.count(old)==1,(name,code.count(old))
        yield name,code.replace(old,new,1),diagnostic


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='recording_start_recovery'
    assert set(plan['inputs'])=={HISTORY} and not plan['copies']
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/name)==h,name
    previous=(ROOT/'ios'/plan['previous'][HISTORY]).read_text();current=(a.source/HISTORY).read_text()
    marker='private func nagramiXBindSingleSelection()'
    old=block(previous,marker);new=block(current,marker)
    assert previous.replace(old,new,1)==current,'Only the initial column coordinate check changes'
    assert 'self.transform = CATransform3DMakeRotation(CGFloat(Double.pi)' in current
    state=manifest(a.source);code=fixture(a.source)
    # The Linux fixture maps only the Objective-C selector spelling to its
    # explicit boundary; the real UIKit preflight retains the native selector.
    selector='#selector(self.nagramiXSingleSelectionPan(_:))'
    old_runtime=old.replace(selector,'"single-selection"')
    new_runtime=new.replace(selector,'"single-selection"')
    assert code.count(new_runtime)==1
    with tempfile.TemporaryDirectory(prefix='selection-column-check-') as d:
        folder=Path(d);refusals=guard_checks(a.source,STAGE,plan,folder/'guards')
        runs=execute(a.swiftc,folder,'left-selection-column',code)
        runs+=execute(a.swiftc,folder,'original096-right-selection-column',code.replace(new_runtime,old_runtime,1),'visual left checkbox column starts selection')
        for name,mutated,diagnostic in negatives(code):runs+=execute(a.swiftc,folder,name,mutated,diagnostic)
        apple=apple_check(a.source,a.swiftc,folder)
        run([a.swiftc,'-frontend','-parse',a.source/HISTORY])
    assert state==manifest(a.source)
    report={'stage':STAGE,'loader_refusals':len(refusals),'executions':runs,'unchanged_previous_selection_assertions':4841,'visual_coordinate_assertions':1134,
            'only_runtime_change':'Horizontal touch-down column mapping in rotated history; original row hit testing/range/selection baseline/reversal/edge scrolling/recognizer and entire helper unchanged.',
            'geometry_cases':'rotated and unrotated histories; same-view Legacy and nested scroll host CoreList;320/390/744pt;safe insets0/20/44pt;ancestor offsets,scroll bounds origin,tall rows,downward drag,reverse,current bounds after resize',
            'apple_uikit':apple,'source_unchanged_by_checks':True,'full_application_sdk':'pending','device':'pending',
            'boundary':'Actual complete production helper/recognizer/binding/history hooks run with an independent affine view hierarchy adapter for UIKit conversion. Prior4841 checks retained, plus visual-left/right and actual range drag. Physical UIKit gesture arbitration and rendering are not exercised on Linux.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
