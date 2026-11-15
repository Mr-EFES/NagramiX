#!/usr/bin/env python3
"""Проверить цельное название качества, галочку у разрешения и узкий экран."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_quick_format import manifest,block
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from round_quality_compact_apple import check as apple_check
from round_quality_compact_runtime import fixture as existing_domain_fixture
import round_quality_title_runtime as rt
STAGE='round_quality_title_layout'


def contracts(source):
    plan=checked_plan(STAGE);before=(OVERLAY/plan['previous'][rt.U]).read_text();after=(source/rt.U).read_text()
    assert set(plan['inputs'])=={rt.U} and len(plan['guards'])==12 and not plan['copies'] and not plan['deletions']
    assert plan['required_previous_stage']=='sticker_status_spacing'
    for marker in ['func nagramiXRoundQualityTitle(', 'func nagramiXRoundQualitySubtitle(', 'private final class NagramiXRoundBitRateCell:', 'private struct NagramiXRoundSegmentOption', '    init(context:', '    private func supports(', '    private func shouldShowCinematic(', '    private func options(', '    private func refreshVisibleRows(', '    private func commit(', '    private func updateBitRate(', '    private func select(']:
        assert block(before,marker)==block(after,marker),'Unrelated behavior changed: '+marker
    assert 'adjustsFontSizeToFitWidth' not in after and 'minimumScaleFactor' not in after
    assert (source/rt.M).read_bytes()==(source/'submodules/Camera/Sources/NagramiXRoundVideoSettings.swift').read_bytes()
    old=block(before,'    func tableView(_ tableView: UITableView, cellForRowAt')
    current=block(after,'    func tableView(_ tableView: UITableView, cellForRowAt')
    assert old.replace('count: count)','count: count, qualityLayout: section == .quality)',1)==current
    return {'single_app_file':True,'preset_model_and_camera_copy_unchanged':True,'all_options_and_selection_commit_verbatim':True,'bitrate_cell_and_cinematic_gates_verbatim':True,'quality_factory_flag_scoped':True,'font_sizes_and_localized_names_unchanged':True}


def lifecycle_fixture(source):
    method=block((source/rt.U).read_text(),'    override func containerLayoutUpdated(')
    return '''import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
struct Insets {var top:CGFloat=0,bottom:CGFloat=0}
struct ContainerViewLayout {let size:CGSize;let intrinsicInsets=Insets()}
enum ContainedViewLayoutTransition {case immediate}
struct Navigation {let navigationFrame=CGRect(x:0,y:0,width:0,height:44)}
enum UIView {static func performWithoutAnimation(_ body:()->Void){body()}}
class Table {
 var frame=CGRect.zero;var bounds:CGRect{CGRect(origin:.zero,size:frame.size)}
 var contentInset=Insets(),scrollIndicatorInsets=Insets(),reloads=0
 func reloadData(){reloads+=1}
}
class Controller {func containerLayoutUpdated(_ layout:ContainerViewLayout,transition:ContainedViewLayoutTransition){};func navigationLayout(layout:ContainerViewLayout)->Navigation{Navigation()}}
class Page:Controller {let table=Table()
'''+method+'''
}
@main enum ResizeChecks {static func main(){
 let page=Page()
 for (size,count) in [(CGSize(width:390,height:844),1),(CGSize(width:390,height:700),1),(CGSize(width:320,height:700),2),(CGSize(width:768,height:390),3),(CGSize(width:768,height:400),3)] {
  page.containerLayoutUpdated(ContainerViewLayout(size:size),transition:.immediate)
  guard page.table.reloads==count && page.table.frame.size==size && page.table.contentInset.top==44 else{print("FAIL: quality width reload lifecycle");exit(96)}
 }
 print("PASS 5 quality width reload checks")
}}
'''


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    contract=contracts(source)
    code=rt.fixture(source)
    runs=execute(swiftc,folder,'round-quality-title',code)
    lifecycle=lifecycle_fixture(source);resize=execute(swiftc,folder,'round-quality-width-change',lifecycle)
    domain=execute(swiftc,folder,'round-quality-existing-routing',existing_domain_fixture(source))
    negatives=[]
    for name,old,new,diagnostic in [
      ('quality-name-wraps','label.numberOfLines = checkOnDetailLine ? 1 : 0','label.numberOfLines = 0','quality names and resolutions never wrap'),
      ('check-takes-title-width','labels.trailingAnchor.constraint(equalTo: self.trailingAnchor, constant: -8)','labels.trailingAnchor.constraint(equalTo: self.checkView.leadingAnchor, constant: -4)','quality title uses full width'),
      ('check-centered-on-button','self.checkView.centerYAnchor.constraint(equalTo: self.detailLabel.centerYAnchor)','self.checkView.centerYAnchor.constraint(equalTo: self.centerYAnchor)','check belongs to resolution row'),
      ('narrow-row-stays-horizontal','return rowWidth < requiredWidth','return rowWidth < requiredWidth && false','narrow widths reflow before clipping'),
      ('title-font-shrinks','Font.regular(presentationData.listsFontSize.itemListBaseFontSize)','Font.regular(presentationData.listsFontSize.itemListBaseFontSize * 0.8)','quality preserves original font sizes'),
    ]:
        assert code.count(old)==1,(name,code.count(old))
        negatives+=execute(swiftc,folder,name,code.replace(old,new,1),diagnostic)
    old='if previousWidth != layout.size.width'
    assert lifecycle.count(old)==1
    negatives+=execute(swiftc,folder,'reload-on-every-layout',lifecycle.replace(old,'if previousWidth >= 0',1),'quality width reload lifecycle')
    apple=apple_check(source,swiftc,folder/'apple')
    return {'contracts':contract,'executions':runs,'resize_executions':resize,'existing_routing_executions':domain,'semantic_negatives':negatives,'apple_api':apple,'boundary':'Entire actual button/cell/constraints and width helper execute with explicit recording UIKit/font/presentation edges. Actual page width lifecycle and complete existing option/selection/commit methods execute separately. This does not solve UIKit AutoLayout or render pixels. The complete final page is typechecked with genuine UIKit before future app SDK on macOS.','full_application_sdk':'not_run','physical_iphone':'pending'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    before=manifest(a.source);plan=checked_plan(STAGE)
    with tempfile.TemporaryDirectory(prefix='nagramix-round-title-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');result=check(a.source,a.swiftc,root/'runtime')
        run([a.swiftc,'-frontend','-parse',a.source/rt.U])
    assert manifest(a.source)==before
    report={'stage':95,'name':STAGE,'runtime_paths':[rt.U],'guards':12,'loader_refusals':len(refused),'checks':result,'source_unchanged_by_checks':True,'scope':'Only quality names get full segment width, one line at original font, and check on resolution line. Measured-width fallback uses vertical quality options if three columns cannot fit; width changes trigger remeasurement. Other settings groups and all stored values/availability/camera/export remain unchanged.','full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
