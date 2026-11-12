#!/usr/bin/env python3
"""Validate Atmosphere controls, native placement and Snow lifecycle before SDK."""
import argparse,ast,json,tempfile
from pathlib import Path
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from validate_quick_format import manifest
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_app_language_localization import strings
import snowfall_runtime as runtime
from snowfall_apple import check as api_check
ROOT=Path(__file__).resolve().parents[1];STAGE='snowfall'


def contract(source,plan):
    assert plan['required_previous_stage']=='input_effects' and len(plan['inputs'])==75 and len(plan['guards'])==12
    assert set(plan['copies'])=={runtime.SETTINGS,runtime.VIEW,runtime.DENSITY}
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards'],**{n:v['sha256'] for n,v in plan['copies'].items()}}.items():assert digest(source/n)==h,n
    def previous(n):return (ROOT/'ios'/plan['previous'][n]).read_text()
    text=(source/runtime.LIST).read_text()
    additions=['    private let nagramiXSnowView = NagramiXSnowView(scope: .header)\n','            self.nagramiXSnowView.bind(to: navigationBarComponentView, above: navigationBarComponentView.edgeEffectBackgroundView)\n','    deinit {\n        let snow = self.nagramiXSnowView\n        Queue.mainQueue().async { snow.setVisible(false); snow.removeFromSuperview() }\n    }\n\n    func nagramiXSetSnowVisible(_ visible: Bool) { self.nagramiXSnowView.setVisible(visible) }\n\n']
    for a in additions:assert text.count(a)==1;text=text.replace(a,'',1)
    assert text==previous(runtime.LIST),'Unrelated list layout/scroll changed'
    text=(source/runtime.CONTROLLER).read_text()
    for value in ['true','false']:
        a='        self.chatListDisplayNode.nagramiXSetSnowVisible('+value+')\n';assert text.count(a)==1;text=text.replace(a,'',1)
    assert text==previous(runtime.CONTROLLER),'Unrelated controller logic changed'
    text=(source/runtime.CHAT).read_text()
    for a in ['    private let nagramiXSnowView = NagramiXSnowView(scope: .messages)\n','        let snow = self.nagramiXSnowView\n        Queue.mainQueue().async { snow.setVisible(false); snow.removeFromSuperview() }\n','        self.nagramiXSnowView.setVisible(isInFocus)\n','        self.nagramiXSnowView.bind(to: self.backgroundNode.view)\n']:
        assert text.count(a)==1;text=text.replace(a,'',1)
    assert text==previous(runtime.CHAT),'History, wallpaper or keyboard logic changed'
    bar=(source/'submodules/TelegramUI/Components/ChatListHeaderComponent/Sources/ChatListNavigationBar.swift').read_text();assert 'public var edgeEffectBackgroundView: UIView' in bar
    for name in ['submodules/ChatListUI/BUILD','submodules/TelegramUI/BUILD']:assert '"//submodules/NagramiXCore:NagramiXCore"' in (source/name).read_text()
    core=(source/'submodules/NagramiXCore/BUILD').read_text();assert 'ChatListUI' not in core and 'TelegramUI:' not in core and '"Sources/**/*.swift"' in core
    ui=(source/runtime.UI).read_text();assert 'case atmosphere = 40' in ui
    assert 'case .otherCallsHeader: return 500' in ui, 'Calls heading must follow all optional Atmosphere rows'
    assert all('case .'+n+': return '+str(v) in ui for n,v in [('snowHeader',496),('snowEnabled',497),('snowInChats',498),('snowDensity',499)])
    from settings_header_contract import check
    headers=check(ui)
    for a in ['guard NagramiXSnowSettings.current.enabled else { return }','nagramiXSnowEntries(NagramiXSnowSettings.current)']:assert a in ui
    density=(source/runtime.DENSITY).read_text();assert 'self.titleLabel.numberOfLines = 0' in density and 'sliderView.minimumValue = 10.0' in density and 'stacked ?' in density
    assert 'NagramiXSnowSettings.normalizedDensity' in density
    view=(source/runtime.VIEW).read_text()
    for a in ['lightning','bolt','CADisplayLink','Timer(','UIApplication.shared','ghostgram']:assert a not in view,a
    loc=json.loads((ROOT/'ios/snowfall/localization.json').read_text());codes={x['code'] for x in json.loads((ROOT/'ios/app_language_localization/languages.json').read_text())['languages']}
    assert set(loc['translations'])==codes and len(loc['keys'])==4
    for code in codes:
        n='submodules/NagramiXCore/Resources/'+code+'.lproj/Localizable.strings';before=strings(ROOT/'ios'/plan['previous'][n]);after=strings(source/n)
        assert len(before)==664 and len(loc['translations'][code])==4 and after=={**before,**dict(zip(loc['keys'],loc['translations'][code]))}
    assert loc['translations']['ru']==['Атмосфера','Снегопад','Показывать в чатах','Плотность']
    return {'native_paths':'Exact native list/chat/controller code after removing only Snow hooks','placement':'Above list header background below controls; child of wallpaper view, behind history; existing view/controller frames unchanged','controls':'Only master while OFF; in-chats and density appear while ON; no preview','defaults':'OFF, in-chats ON, density100%; independent persistence; density10–100 step5','section_ids':'40 reserves existing input-effect sections','headers':headers,'locales':71,'keys':668,'legacy_percentage_item':'exact guard unchanged'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE);c=contract(a.source,plan);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='snowfall-check-') as d:
        folder=Path(d);refusals=guard_checks(a.source,STAGE,plan,folder/'guards');code=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'snowfall',code)
        for name,mutated,label in runtime.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
        api=api_check(a.source,a.swiftc,folder,public_api=True);apple=api_check(a.source,a.swiftc,folder)
        for n in [runtime.UI,runtime.CHAT,runtime.LIST,runtime.CONTROLLER,runtime.SETTINGS,runtime.VIEW,runtime.DENSITY]:run([a.swiftc,'-frontend','-parse',a.source/n])
    assert before==manifest(a.source)
    report={'stage':STAGE,'source_contract':c,'loader_refusals':len(refusals),'executions':runs,'public_core_api':api,'apple_sdk_precheck':apple,'source_unchanged_by_checks':True,'whole_app_sdk':'not_run','device':'pending','boundary':'Actual settings, Snow UIView/CA code, section enum and conditional entries with explicit UIKit/emitter adapters. Real public module plus consumer. No physical pixel rendering, particle smoothness or native font metrics tested.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
