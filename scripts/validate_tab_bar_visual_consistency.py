#!/usr/bin/env python3
"""Проверить tint Контактов, атомарность панели и пустые фильтры Звонков."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from late_source_stages import verified_prefix, LATE_SOURCE_STAGES
from validate_private_temporary_transcription import execute, save_failed_fixture
from tab_visibility_runtime import BAR, NODE, COMPONENT, CONTACTS
from tab_bar_visual_runtime import fixture, ready_region, pieces
from call_filter_visual_runtime import CALLS, fixture as calls_fixture

STAGE = 'tab_bar_visual_consistency'


def contracts(source):
    plan = checked_plan(STAGE)
    assert set(plan['inputs']) == {BAR,NODE,COMPONENT,CONTACTS,CALLS}
    assert len(plan['guards']) == 7 and not plan['copies'] and not plan['deletions']
    assert plan['required_previous_stage'] == 'web_player_main_queue'
    for name, markers, extra in [
        (CONTACTS, ['    private func nagramiXUpdateTabItem('], []),
        (BAR, ['    override open func loadDisplayNode(', '    public func setControllers('], ['    private func nagramiXCompleteTabSelection(']),
        (NODE, ['        (self.view as? View)?.onLayout = {', '    func containerLayoutUpdated(', '    func updateTabBarItems(', '    func updateSelectedIndex('], []),
        (COMPONENT, ['        func update(component: TabBarComponent, availableSize:'], ['        private func nagramiXReconcileTabStructure(']),
        (CALLS, ['    func updateType(', '    func updateEmptyPlaceholder(', '    func updateLayout('], []),
    ]:
        text=(source/name).read_text(); old=(OVERLAY/plan['previous'][name]).read_text(); restored=text
        for marker in markers: restored=restored.replace(block(text,marker),block(old,marker),1)
        for marker in extra: restored=restored.replace(block(text,marker)+'\n\n','',1)
        if name==CALLS: restored=restored.replace('    private let emptyTextMeasureNode = ImmediateTextNode()\n','',1)
        assert restored==old, 'Unrelated change: '+name
    assert ready_region((source/BAR).read_text()) == ready_region((OVERLAY/plan['previous'][BAR]).read_text())
    return {'runtime_paths':5,'new_app_files':0,'new_strings':0,'new_dependencies':0,'unchanged_root_visibility_keys_defaults_and_geometry':True,'unchanged_image_ready_signal_region':True,'unchanged_call_queries_entries_pagination_and_start_call':True,'native_call_node_input_blob':plan['native_inputs'][CALLS]}


def apple_check(source, swiftc, folder):
    folder.mkdir(parents=True,exist_ok=True)
    # Bundle lookup/model data are IO hosts. New UIKit tint and gesture APIs are real.
    p=pieces(source)
    code='''import UIKit
private extension UIImage {
 convenience init?(bundleImageName:String){self.init(named:bundleImageName)}
}
private final class TabItem {var title:String?;var image:UIImage?;var selectedImage:UIImage?}
private enum ContextActionType {case none,always}
@MainActor private final class Contacts {
 var isTab=true;let tabBarItem=TabItem();var tabBarItemContextActionType=ContextActionType.none
 struct Data {struct Strings {let Contacts_Title=""};let strings=Strings()};let presentationData=Data()
'''+p['CONTACT']+'''
}
private struct TabBarComponent {
 struct Item{let id:AnyHashable};struct Search{}
 var items:[Item];var selectedId:AnyHashable?;var search:Search?
 var axis=0;var isCompact=false;var usesSystemLayout=true;var fillsAvailableWidth=false;var nagramiXWidePanelSnapshot=false
}
@MainActor private final class Host {
 var overrideSelectedItemId:AnyHashable?
 var selectionGestureState:AnyHashable?
 var pendingDoubleTapItem:(id:AnyHashable,previouslySelectedId:AnyHashable?,timer:Foundation.Timer)?
 var itemWithActiveContextGesture:AnyHashable?
 var tabSelectionRecognizer:UIGestureRecognizer?=UIPanGestureRecognizer()
'''+p['RECONCILE']+'\n}\n'
    path=folder/'TabBarVisualUIKit.swift';path.write_text(code)
    parse=subprocess.run([str(swiftc),'-frontend','-parse',str(path)],capture_output=True,text=True)
    assert parse.returncode==0,parse.stdout+parse.stderr
    result={'swift_parse':'passed','new_uikit_api':'not_run','full_application_sdk':'pending','device':'pending'}
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        r=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-typecheck','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),str(path)],capture_output=True,text=True,timeout=180)
        if r.returncode:save_failed_fixture(path,'tab-bar-visual-api','iphoneos','typecheck',r)
        assert r.returncode==0,r.stdout+r.stderr
        result['new_uikit_api']='passed; actual Contacts tint and reconcile body, real UIImage/UIGestureRecognizer/Timer; bundle/model hosts'
    return result


def check(source, swiftc, folder):
    folder.mkdir(parents=True,exist_ok=True)
    result={'contracts':contracts(source),'apple_api':apple_check(source,swiftc,folder/'apple')}
    tab=fixture(source);calls=calls_fixture(source)
    positive=execute(swiftc,folder,'tab-bar-visual',tab)+execute(swiftc,folder,'call-filter-visual',calls)
    variants=[
        ('untinted-contacts',tab,'?.withRenderingMode(.alwaysTemplate)','','Contacts icon must follow theme tint'),
        ('structural-spring',tab,'self.isChangingSelectedIndex = false\n        self.requestUpdate()','self.isChangingSelectedIndex = true\n        self.requestUpdate()','structural removal must not start selection spring'),
        ('stale-layout-params',tab,'self.containerLayoutUpdated(layoutResult.params.layout, toolbar: layoutResult.params.toolbar, transition: .immediate)','self.updateImpl(params: layoutResult.params, transition: .immediate)','layout must rebuild current item count'),
        ('cached-pending-update',tab,'if !needsUpdate, let layoutResult','if (!needsUpdate || needsUpdate), let layoutResult','ordinary selection keeps native spring'),
        ('stale-ready-index',tab,'guard let index = self.controllers.firstIndex(where: { $0 === controller }) else { return }','let index = 0','ready callback resolves moved tab identity'),
        ('stale-lens-override',tab,'self.overrideSelectedItemId = nil','self.overrideSelectedItemId = AnyHashable(0)','removed selection and drag coordinates cleared in same pass'),
        ('morph-removed-tabs',tab,'transition = .immediate','transition = .spring','structural change cannot interpolate old item geometry'),
        ('pending-double-tap',tab,'self.pendingDoubleTapItem?.timer.invalidate()','// omitted','removed gesture context and pending double tap cancelled'),
        ('uncancelled-gesture',tab,'self.tabSelectionRecognizer?.isEnabled = false','// omitted','structural change cancels old gesture before new frames'),
        ('flash-new-call-row',calls,'// Keep the applied empty state until the new list transaction completes.','self.emptyStatePromise.set(.single(false))','switch filter must not expose synthetic new-call row'),
        ('moving-duck',calls,'emptyAnimationSpacing + emptyTextHeight + emptyTextSpacing + emptyButtonSize.height','emptyAnimationSpacing + emptyTextSize.height + emptyTextSpacing + emptyButtonSize.height','all and missed reserve same duck position'),
        ('repeat-empty-fades',calls,'if previousAlpha != alpha {','if true {','same empty state must not restart fade'),
        ('ignore-filter-value',calls,'        if !isHidden {\n            let emptyText: String','        if !isHidden {\n            let type = self.currentLocationAndType.scope\n            let emptyText: String','placeholder honors supplied filter'),
    ]
    negatives=[]
    for name,code,old,new,reason in variants:
        assert old in code,name
        negatives+=execute(swiftc,folder,name,code.replace(old,new),reason)
    for name in checked_plan(STAGE)['inputs']:
        r=subprocess.run([str(swiftc),'-frontend','-parse',str(source/name)],capture_output=True,text=True)
        assert r.returncode==0,r.stdout+r.stderr
    result.update(executions=positive,semantic_negatives=negatives,boundary='Actual tint/model commit/cache invalidation/reconcile/ready identity and Calls updateType/empty/layout bodies. UIKit/navigation/unchanged ready/image pipeline/text measurement/list IO are explicit hosts; no pixel, AVKit or device claim.',full_application_sdk='not_run',physical_iphone='pending')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='tab-bar-visual-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,checked_plan(STAGE),root/'guards');r=check(a.source,a.swiftc,root/'runtime')
    assert manifest(a.source)==before
    r.update(stage=STAGE,loader_refusals=refused)
    if a.report:a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
