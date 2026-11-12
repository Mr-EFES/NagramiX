#!/usr/bin/env python3
"""Проверить единую широкую панель, сохранение OFF и guarded late stage."""
import argparse,ast,hashlib,json,re,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import execute,run
from wide_panel_consistency_core import check as core_check
import wide_panel_consistency_runtime as runtime

ROOT=Path(__file__).resolve().parents[1];STAGE='wide_panel_consistency'

def source_contract(source,plan):
    core=(source/runtime.CORE).read_text()
    old=(ROOT/'ios'/plan['previous'][runtime.CORE]).read_text()
    restored=core.replace(block(core,'    public static var wideTabBarEnabled: Bool')+'\n\n','',1).replace('wideTabBar: self.wideTabBarEnabled','wideTabBar: defaults.object(forKey: Key.wideTabBar) as? Bool ?? true',1)
    assert restored==old,'Other defaults or settings changed'
    attachment=(source/runtime.ATTACH).read_text()
    assert attachment.count('glassTabBarFrame(layout: layout, buttonCount: buttons.count, widePanel: NagramiXTabSettings.wideTabBarEnabled)')==2
    assert 'actualButtonSize.width = itemWidth' in attachment and 'self.itemSizes[type.key] = actualButtonSize' in attachment
    assert 'itemSize.width / 2.0 - contentOffset' in attachment and 'lensSelection = (selectionFrame.minX, selectionFrame.width)' in attachment
    assert 'self.scrollNode.view.setContentOffset(.zero, animated: false)' in attachment
    assert 'let shouldCollapseTabRow = buttons.count == 1 || hideButtons' in attachment
    for name in [runtime.COMP,runtime.SELECT]:
        text=(source/name).read_text();assert 'private let nagramiXWidePanelSnapshot = NagramiXTabSettings.wideTabBarEnabled' in text
        assert 'lhs.nagramiXWidePanelSnapshot != rhs.nagramiXWidePanelSnapshot' in text
        assert 'self.nagramiXLastWidePanel = NagramiXTabSettings.wideTabBarEnabled' in text
        assert 'removeObserver(observer)' in text
    # Every new import has a direct Bazel dependency, no new dependency cycle.
    for name in [runtime.ATTACH,runtime.COMP,runtime.SELECT]:
        directory=(source/name).parent.parent
        assert '"//submodules/NagramiXCore:NagramiXCore"' in (directory/'BUILD').read_text()
    def deps(label):
        package,_,target=label.removeprefix('//').partition(':')
        target=target or package.rsplit('/',1)[-1]
        build=source/package/'BUILD'
        if not build.is_file():return []
        tree=ast.parse(build.read_text())
        for call in ast.walk(tree):
            if not isinstance(call,ast.Call):continue
            keywords={k.arg:k.value for k in call.keywords}
            name=keywords.get('name')
            if not isinstance(name,ast.Constant) or name.value!=target:continue
            dependency=keywords.get('deps')
            if dependency is None:return []
            labels=[v.value for v in ast.walk(dependency) if isinstance(v,ast.Constant) and isinstance(v.value,str)]
            return [v if v.startswith('//') else '//'+package+v for v in labels if v.startswith('//') or v.startswith(':')]
        return []
    forbidden={'//'+str(Path(n).parent.parent)+':'+Path(n).parent.parent.name for n in [runtime.ATTACH,runtime.COMP,runtime.SELECT]}
    seen=set();queue=['//submodules/NagramiXCore:NagramiXCore']
    while queue:
        n=queue.pop()
        if n in seen:continue
        seen.add(n);assert n not in forbidden,'Bazel dependency cycle: '+n
        queue.extend(deps(n))
    return {'direct_import_dependencies':3,'core_reachable_dependency_labels':len(seen),'cycle_check':'passed','shared_panels':3,'existing_key':'nagramix.tabs.wideBar','stable_id':165}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='system_web_picture_in_picture' and len(plan['inputs'])==8 and len(plan['guards'])==13
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
    contract=source_contract(a.source,plan);initial=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='wide-panel-consistency-') as temp:
        folder=Path(temp);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
        text=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'wide-panels',text)
        for name,mutated,label in runtime.negatives(text):runs+=execute(a.swiftc,folder,name,mutated,label)
        core=core_check(a.source,a.swiftc,folder)
        for n in plan['inputs']:
            if n.endswith('.swift'):run([a.swiftc,'-frontend','-parse',a.source/n])
    assert manifest(a.source)==initial
    report={'stage':STAGE,'inputs':8,'guards':13,'loader_refusals':len(refused),'source_files':len(initial),'source_unchanged_by_checks':True,'contract':contract,'executions':runs,'actual_core_executions':core,'boundary':'Actual attachment frame/slot arithmetic, root policy, native TabBarItemsLayout, shared selector frame loop and shared weak observer with actual ComponentState body. Explicit adapters provide measured title widths, container safe insets and ComponentTransition enum. Full actual Core and all 13 Foundation media sources compile and execute. No UIKit pixels or whole module compilation is claimed.','whole_app_sdk':'not_run','device':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
