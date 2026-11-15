#!/usr/bin/env python3
"""Проверить SD/HQ/MAX, подключение UIKit context и актуальный пресет редактора."""
import argparse,json,tempfile,subprocess,sys
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from round_editor_quality_runtime import badge_fixture
from round_quality_summary_runtime import route_fixture
import round_quality_badge_runtime as rt

STAGE='round_quality_preset_badge'


def contracts(source):
    plan=checked_plan(STAGE)
    assert set(plan['inputs'])=={rt.C,rt.S} and len(plan['guards'])==11 and not plan['copies'] and not plan['deletions']
    assert plan['required_previous_stage']=='round_quality_title_layout'
    before=lambda n:(OVERLAY/plan['previous'][n]).read_text()
    component=(source/rt.C).read_text();screen=(source/rt.S).read_text()
    old=before(rt.C)
    marker='func nagramiXRoundVideoQualityImage('
    old=old.replace(block(old,marker),block(component,marker),1)
    old=old.replace('// The round export side is a pixel value, not a legacy video-preset index.\n','// Fixed technical glyph codes chosen for the quality icon, like HD or 4K.\n'+block(component,'func nagramiXRoundVideoQualityCode(')+'\n\n',1)
    assert component==old.replace('key: "nagramix-round-quality-\\(side)"','key: "nagramix-round-quality-badge-\\(side)"',1),'Other toolbar rendering changed'
    old='roundVideoQualitySide: self.nagramiXIsRoundVideo ? Int(chatMediaEditorVideoFileDimensions(values: self.mediaEditor.values, duration: self.subject.duration).width) : nil'
    new='roundVideoQualitySide: self.nagramiXIsRoundVideo ? (self.mediaEditor.values.nagramiXRoundTuning?.first ?? 480) : nil'
    assert before(rt.S).count(old)==1 and screen==before(rt.S).replace(old,new,1),'Unrelated editor behavior changed'
    native=(source/'submodules/Display/Source/GenerateImage.swift').read_text()
    assert 'UIGraphicsPushContext' not in block(native,'public func generateImage(_ size: CGSize, opaque:')
    assert 'UIGraphicsPushContext' not in block(native,'    public func withContext(')
    assert 'context.scaleBy(x: 1.0, y: -1.0)' in block(native,'    public func withContext(')
    return {'only_two_ui_files':True,'other_four_tools_and_native_quality_verbatim':True,'settings_export_capture_sheet_camera_unchanged':True,'display_generator_does_not_push_uikit_context':True,'native_generator_uses_rotated_coordinates':True,'fixed_technical_icon_codes':'SD/HQ/MAX; существующие подписи и VoiceOver локализованы как прежде'}


def apple_check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    component=(source/rt.C).read_text()
    drawing='\n'.join(block(component,n) for n in ['func nagramiXRoundVideoQualityCode(', 'func nagramiXRoundVideoQualityImage('])
    code='''import UIKit
import CoreGraphics
enum Font {static func semibold(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size,weight:.semibold)}}
func generateImage(_ size:CGSize,rotatedContext:(CGSize,CGContext)->Void)->UIImage? {
 let format=UIGraphicsImageRendererFormat();format.scale=1
 return UIGraphicsImageRenderer(size:size,format:format).image{rotatedContext(size,$0.cgContext)}
}
'''+drawing
    path=folder/'badge-real-uikit.swift';path.write_text(code)
    result=subprocess.run([str(swiftc),'-frontend','-parse',str(path)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    report={'probe_parse':'passed','uikit_api':'not_run','reason':'Linux без UIKit/iPhoneOS SDK','pixel_verification':'not_run'}
    if sys.platform!='darwin':return report
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    result=subprocess.run([str(swiftc),'-typecheck','-parse-as-library','-swift-version','5','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),str(path)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    return {'probe_parse':'passed','uikit_api':'passed','target':'arm64-apple-ios15.0','scope':'Actual code mapper and entire drawing helper, real NSString/UIFont/UIKit context/CoreGraphics API. Display image factory and Font are explicit hosts. Not full editor linkage or pixel execution.','pixel_verification':'not_run'}


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    contract=contracts(source);code=rt.fixture(source)
    positive=execute(swiftc,folder,'round-preset-badge',code)
    toolbar=execute(swiftc,folder,'round-badge-existing-toolbar',badge_fixture(source))
    route=route_fixture(source)
    marker='@main struct RoundQualitySummaryRouteTests'
    prefix,tests=route.split(marker,1)
    # Старый сценарий86 предшествует ограничению битрейта88. Меняются только
    # его входные/ожидаемые тестовые значения, все production-тела и assertions прежние.
    tests=tests.replace('1_600_000','1_200_000').replace('2_000_000','1_300_000')
    routing=execute(swiftc,folder,'round-badge-existing-routing',prefix+marker+tests)
    negatives=[]
    for name,old,new,why in [
        ('missing-uikit-context','        UIGraphicsPushContext(context)\n        defer { UIGraphicsPopContext() }\n','','glyph is drawn into returned bitmap'),
        ('leaked-uikit-context','        defer { UIGraphicsPopContext() }','        // simulated missing pop','outer UIKit context is restored'),
        ('wrong-maximum-code','case 640: return "MAX"','case 640: return "SD"','glyph is drawn into returned bitmap'),
        ('off-uses-maximum','self.mediaEditor.values.nagramiXRoundTuning?.first ?? 480','self.mediaEditor.values.nagramiXRoundTuning?.first ?? 640','badge uses current preset and OFF uses standard'),
    ]:
        assert code.count(old)==1,(name,code.count(old))
        negatives+=execute(swiftc,folder,name,code.replace(old,new,1),why)
    return {'contracts':contract,'executions':positive,'existing_toolbar_executions':toolbar,'existing_routing_executions':routing,'routing_test_data':'Только входные/ожидаемые битрейты старого сценария86 приведены к действующим ступеням88: 1.6→1.2 и2.0→1.3 Мбит/с; assertions и production-тела сохранены.','semantic_negatives':negatives,'apple_api':apple_check(source,swiftc,folder/'apple'),'boundary':'Actual image renderer/cache branch and real model/helper/live-toolbar snapshot execute. UIKit stack, bitmap text drawing and font metrics are explicit recording adapters; actual pixel rendering is not verified.','full_application_sdk':'not_run','physical_iphone':'pending'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    before=manifest(a.source);plan=checked_plan(STAGE)
    with tempfile.TemporaryDirectory(prefix='nagramix-round-badge-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');result=check(a.source,a.swiftc,root/'runtime')
        for n in plan['inputs']:
            v=subprocess.run([str(a.swiftc),'-frontend','-parse',str(a.source/n)],capture_output=True,text=True,timeout=120)
            assert v.returncode==0,v.stdout+v.stderr
    assert manifest(a.source)==before
    report={'stage':96,'name':STAGE,'runtime_paths':list(plan['inputs']),'guards':11,'loader_refusals':len(refused),'checks':result,'source_unchanged_by_checks':True,'new_localization_keys':0,'full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
