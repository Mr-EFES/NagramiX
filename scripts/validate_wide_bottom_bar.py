#!/usr/bin/env python3
"""Проверить сохранение ширины нижней панели без изменения других режимов."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
NODE='submodules/TabBarUI/Sources/TabBarContollerNode.swift'
COMP='submodules/TelegramUI/Components/TabBarComponent/Sources/TabBarComponent.swift'
CORE='submodules/NagramiXCore/Sources/NagramiXTabSettings.swift'
UI='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'
STR='submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift'
ITEMS='submodules/TelegramUI/Components/TabBarLayout/Sources/TabBarItemsLayout.swift'
KEY='NagramiX.Settings.Tabs.WideBar'
sha=lambda b:hashlib.sha256(b).hexdigest()

def plan(stage):
    return json.loads((OVERLAY/(stage+'_patches.json')).read_text())

def block(text,marker):
    start=text.index(marker);opening=text.index('{',start);level=1;end=opening+1
    while level:
        if text[end]=='{':level+=1
        elif text[end]=='}':level-=1
        end+=1
    return text[start:end]

def verify(source,stage):
    p=plan(stage)
    assert p['target_pin']=='24638bc69bd083981b178dd1e7f921eebbf7fc46'
    assert p['overlay_base_pin']=='279f89e4d4f63f17227bf877dc3d8990f22ecd58'
    assert all(p['inputs'].keys()==p[k].keys() for k in ('outputs','previous','replacements'))
    assert not p['copies'] and not p['deletions']
    for n,h in p['templates'].items():assert sha((OVERLAY/n).read_bytes())==h,n
    for n,h in {**p['outputs'],**p['guards']}.items():assert sha((source/n).read_bytes())==h,n
    for n,h in p['inputs'].items():assert sha((OVERLAY/p['previous'][n]).read_bytes())==h,n
    return p

def apply(source,overlay,stage):
    spec=importlib.util.spec_from_file_location(stage,overlay/(stage+'.py'))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    getattr(mod,'apply_'+stage)(source,overlay)

def before_fixture(target,p):
    for n,h in {**p['inputs'],**p['guards']}.items():
        if n in p['previous']:data=(OVERLAY/p['previous'][n]).read_bytes()
        else:
            candidates=[OVERLAY/f for f,v in p['templates'].items() if v==h]
            assert candidates,n
            data=candidates[0].read_bytes()
        path=target/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

def guard_checks(stage,folder):
    p=plan(stage);baseline=folder/'baseline';before_fixture(baseline,p)
    accepted=folder/'accepted';shutil.copytree(baseline,accepted)
    apply(accepted,OVERLAY,stage);verify(accepted,stage)
    rejected=0
    names=list(p['inputs']);guards=list(p['guards'])
    cases=['input-first','input-last','input-missing','guard-first','guard-last','guard-missing',
           'template-after','template-before','unsafe-path','pin','prior-stage','replay','output-shape','copy-collision']
    for case in cases:
        root=folder/case;source=root/'source';overlay=root/'ios'
        shutil.copytree(accepted if case=='replay' else baseline,source)
        overlay.mkdir(parents=True)
        q=json.loads(json.dumps(p))
        shutil.copy2(OVERLAY/(stage+'.py'),overlay/(stage+'.py'))
        for n in p['templates']:
            t=overlay/n;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes((OVERLAY/n).read_bytes())
        if case.startswith('input-'):
            n=names[-1] if case=='input-last' else names[0]
            if case=='input-missing':(source/n).unlink()
            else:(source/n).write_bytes((source/n).read_bytes()+b'\n// drift\n')
        elif case.startswith('guard-'):
            n=guards[-1] if case=='guard-last' else guards[0]
            if case=='guard-missing':(source/n).unlink()
            else:(source/n).write_bytes((source/n).read_bytes()+b'\n// drift\n')
        elif case.startswith('template-'):
            n=p['previous' if case=='template-before' else 'replacements'][names[0]]
            (overlay/n).write_bytes((overlay/n).read_bytes()+b'\n// drift\n')
        elif case=='unsafe-path':
            n=names[0]
            for k in ('inputs','outputs','previous','replacements'):q[k]['../escape']=q[k].pop(n)
        elif case=='pin':q['target_pin']='0'*40
        elif case=='prior-stage':q['required_previous_stage']='wrong_stage'
        elif case=='output-shape':q['outputs'].pop(names[0])
        elif case=='copy-collision':q['copies'][names[0]]={'source':p['replacements'][names[0]],'sha256':p['outputs'][names[0]]}
        (overlay/(stage+'_patches.json')).write_text(json.dumps(q))
        snapshot={str(f.relative_to(source)):f.read_bytes() for f in source.rglob('*') if f.is_file()}
        try:apply(source,overlay,stage)
        except (SystemExit,AssertionError):rejected+=1
        else:raise AssertionError('Invalid stage input accepted: '+case)
        assert snapshot=={str(f.relative_to(source)):f.read_bytes() for f in source.rglob('*') if f.is_file()},case
    return rejected

def geometry_source(source,setting=False):
    node=(source/NODE).read_text();component=(source/COMP).read_text()
    helper=block(node,'private func nagramiXTabBarFillsAvailableWidth(')
    params=block(node,'    private struct Params: Equatable')
    items=(source/ITEMS).read_text().replace('import UIKit\n','').replace('import Display\n','')
    start=component.index('            let itemsLayout: TabBarItemsLayout')
    end=component.index('            let tabsSize = itemsLayout.size',start)
    layout=component[start:end]
    header='''import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
#if os(Linux)
import Glibc
#else
import Darwin
#endif
public let UIScreenScale: CGFloat = 3.0
func floorToScreenPixels(_ value: CGFloat) -> CGFloat { floor(value * UIScreenScale) / UIScreenScale }
struct ContainerViewLayout: Equatable { let size: CGSize }
struct Toolbar: Equatable {}
enum ViewController { struct TabBarSearchState: Equatable {} }
struct ComponentAdapter { let axis: TabBarAxis; let isCompact: Bool; let fillsAvailableWidth: Bool }
var count = 0
func check(_ value: Bool, _ label: String) { if !value { print("FAIL " + label); exit(91) }; count += 1 }
'''
    api='''
func renderedLayout(axis: TabBarAxis, compact: Bool, system: Bool, titles: [CGFloat], availableLength: CGFloat, search hasSearch: Bool, fill: Bool) -> TabBarItemsLayout {
    let component = ComponentAdapter(axis: axis, isCompact: compact, fillsAvailableWidth: fill)
    let search: Bool? = hasSearch ? true : nil
    let isSystemLayout = system
    let titleWidths = titles
LAYOUT
    return itemsLayout
}
func fills(_ count: Int, _ search: Bool, _ side: Bool, _ compact: Bool, _ landscape: Bool, _ enabled: Bool) -> Bool {
    nagramiXTabBarFillsAvailableWidth(itemCount: count, showSearchButton: search, hasSidePlacement: side, isCompact: compact, isWide: landscapeSETTING)
}
private func parameters(_ enabled: Bool) -> Params {
    Params(layout: ContainerViewLayout(size: CGSize(width:393,height:852)), toolbar:nil, isTabBarHidden:false, currentControllerSearchState:nil, nagramiXShowSearchButton:falseSETTING_INIT, nagramiXHasGlobalSearch:true, nagramiXIsGlobalSearchController:false, itemCount:2)
}
'''.replace('LAYOUT',layout).replace('SETTING_INIT',', nagramiXWideTabBar: enabled' if setting else '').replace('SETTING',', wideTabBar: enabled' if setting else '')
    tests='''
for countValue in 0...5 {
    for hasSearch in [false,true] { for side in [false,true] { for compact in [false,true] { for landscape in [false,true] { for enabled in [false,true] {
        let expected = countValue == 2 && !hasSearch && !side && !compact && !landscapeENABLED
        check(fills(countValue,hasSearch,side,compact,landscape,enabled) == expected,"gate-matrix")
    } } } } }
}
for width: CGFloat in [280,320,360,393,430,500,680] {
    let fit = renderedLayout(axis:.horizontal, compact:false, system:true, titles:[32,59], availableLength:width, search:false, fill:fills(2,false,false,false,false,true))
    check(abs(fit.size.width-width)<0.001,"wide-width")
    check(fit.size.height==62,"native-height")
    check(fit.itemFrames.count==2 && fit.itemFrames[0].minX==4,"native-insets")
    check(fit.itemFrames.allSatisfy { $0.width>0 && $0.minX>=0 && $0.maxX<=width },"valid-frames")
    for titles: [CGFloat] in [[32],[32,59,80],[32,59,80,32]] {
        let value=renderedLayout(axis:.horizontal,compact:false,system:true,titles:titles,availableLength:width,search:false,fill:fills(titles.count,false,false,false,false,true))
        check(value==tabBarSystemItemsLayout(fittedItemWidths:titles,availableLength:width,hasAccessory:false),"native-extra-tabs")
    }
    let search=renderedLayout(axis:.horizontal,compact:false,system:true,titles:[32,59],availableLength:width,search:true,fill:fills(2,true,false,false,false,true))
    check(search==tabBarSystemItemsLayout(fittedItemWidths:[32,59],availableLength:width,hasAccessory:true),"native-search")
    let compact=renderedLayout(axis:.horizontal,compact:true,system:false,titles:[32,59],availableLength:width,search:false,fill:fills(2,false,false,true,false,true))
    check(compact==tabBarItemsLayout(axis:.horizontal,isCompact:true,unboundItemWidths:[52,79],availableLength:width),"native-compact")
    let vertical=renderedLayout(axis:.vertical,compact:false,system:false,titles:[32,59],availableLength:width,search:false,fill:fills(2,false,true,false,false,true))
    check(vertical==tabBarItemsLayout(axis:.vertical,isCompact:false,unboundItemWidths:[52,79],availableLength:width),"native-side")
    let landscape=renderedLayout(axis:.horizontal,compact:false,system:false,titles:[32,59],availableLength:width,search:false,fill:fills(2,false,false,false,true,true))
    check(landscape==tabBarItemsLayout(axis:.horizontal,isCompact:false,unboundItemWidths:[52,79],availableLength:width),"native-landscape")
    let off=renderedLayout(axis:.horizontal,compact:false,system:true,titles:[32,59],availableLength:width,search:false,fill:fills(2,false,false,false,false,false))
    OFF_CHECK
}
check(parameters(true)==parameters(true),"same-params")
PARAMS_CHECK
print("PASS wide geometry checks: \\(count)")
'''.replace('ENABLED',' && enabled' if setting else '').replace('OFF_CHECK','check(off==tabBarSystemItemsLayout(fittedItemWidths:[32,59],availableLength:width,hasAccessory:false),"off-native-layout")' if setting else 'check(abs(off.size.width-width)<0.001,"default-wide-layout")').replace('PARAMS_CHECK','check(parameters(true) != parameters(false),"wide-change-invalidates-layout")' if setting else '')
    return header+items+'\n'+helper+'\n'+params+'\n'+api+tests

def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def run_geometry(source,swiftc,temp,setting=False):
    code=geometry_source(source,setting)
    variants=[('missing-fill','component.fillsAvailableWidth','false','wide-width'),
              ('ignore-search','!showSearchButton','true','gate-matrix'),
              ('ignore-extra-tabs','itemCount == 2','itemCount >= 2','gate-matrix')]
    if setting:variants += [('ignore-off','return wideTabBar &&','return true &&','gate-matrix'),('stale-cache','self.nagramiXWideTabBar = nagramiXWideTabBar','self.nagramiXWideTabBar = true','wide-change-invalidates-layout')]
    report=[];negatives=0
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        path=temp/(mode+'.swift');path.write_text(code);binary=temp/mode
        subprocess.run([swiftc,'-module-cache-path',str(temp/'module-cache'),'-warnings-as-errors',*flags,str(path),'-o',str(binary)],check=True,capture_output=True,text=True)
        result=subprocess.run([str(binary)],check=True,capture_output=True,text=True,preexec_fn=no_core)
        report.append(result.stdout.strip())
        for name,old,new,label in variants:
            assert old in code,name
            changed=code.replace(old,new,1)
            variant=temp/(mode+'-'+name+'.swift');variant.write_text(changed);bad=temp/(mode+'-'+name)
            subprocess.run([swiftc,'-module-cache-path',str(temp/'module-cache'),'-warnings-as-errors',*flags,str(variant),'-o',str(bad)],check=True,capture_output=True,text=True)
            result=subprocess.run([str(bad)],capture_output=True,text=True,preexec_fn=no_core)
            assert result.returncode==91 and 'FAIL '+label in result.stdout,(name,result.returncode,result.stdout)
            negatives+=1
    return report,negatives

def source_contract(source,setting=False):
    component=(source/COMP).read_text();node=(source/NODE).read_text()
    assert 'fillsAvailableWidth: Bool = false' in component
    assert 'if lhs.fillsAvailableWidth != rhs.fillsAvailableWidth' in component
    assert 'self.fillsAvailableWidth = fillsAvailableWidth' in component
    assert 'fillsAvailableWidth: nagramiXTabBarFillsAvailableWidth(' in node
    # Freeze all unrelated component code: only this added public argument and native layout admission differ.
    p=plan('wide_bottom_bar');before=(OVERLAY/p['previous'][COMP]).read_text()
    expected=(OVERLAY/p['replacements'][COMP]).read_text()
    assert component==expected
    assert before.count('hasAccessory: search != nil)')==1
    if setting:
        assert 'nagramiXWideTabBar: NagramiXTabSettings.current.wideTabBar' in node
        root=(source/'submodules/TelegramUI/Sources/TelegramRootController.swift').read_text()
        assert 'addObserver(forName: NagramiXTabSettings.changedNotification' in root
        assert 'rootTabController.updateLayout(transition: .immediate)' in root

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc');parser.add_argument('--report',type=Path)
    args=parser.parse_args();stage='wide_bottom_bar';verify(args.source,stage);source_contract(args.source)
    with tempfile.TemporaryDirectory(prefix='wide-bottom-') as folder:
        temp=Path(folder);guard=guard_checks(stage,temp/'guards')
        runs,negative=run_geometry(args.source,args.swiftc,temp) if args.swiftc else ([],0)
        if args.swiftc:
            for n in plan(stage)['outputs']:subprocess.run([args.swiftc,'-frontend','-parse',str(args.source/n)],check=True)
    result={'stage':stage,'geometry_runs':runs,'semantic_negative_runs':negative,'fail_closed':guard,'outputs':plan(stage)['outputs'],'apple_sdk':'not run','physical_device':'pending'}
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
