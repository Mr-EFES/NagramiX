#!/usr/bin/env python3
"""Проверить высоту скрытого времени стикеров и новый cold default OFF."""
import argparse,json,os,subprocess,sys,tempfile,uuid
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_quick_format import manifest,block
from validate_private_temporary_transcription import execute
import sticker_status_spacing_runtime as rt
STAGE='sticker_status_spacing'


def command(args,env=None):
    p=subprocess.run([str(x) for x in args],env=env,capture_output=True,text=True,timeout=180)
    assert p.returncode==0,p.stdout+p.stderr
    return p


def cold_fixture(source):
    model=(source/rt.M).read_text().replace('UserDefaults.standard','StickerStorage.defaults')
    return 'import Foundation\n'+model+r'''
enum StickerStorage {
 static let suite=ProcessInfo.processInfo.environment["NAGRAMIX_STICKER_SUITE"] ?? UUID().uuidString
 static let defaults=UserDefaults(suiteName:suite)!
}
@main enum ColdStickerChecks {
 static func main(){
  func check(_ value:Bool,_ message:String){if !value{print("FAIL: "+message);exit(96)}}
  let args=CommandLine.arguments
  let action=args.count>1 ? args[1]:"fresh"
  let defaults=StickerStorage.defaults
  if action=="cleanup" {defaults.removePersistentDomain(forName:StickerStorage.suite);_ = defaults.synchronize();return}
  check(!NagramiXMediaSettings.default.showStickerTime,"fresh sticker default OFF")
  if action=="fresh" {
   check(defaults.object(forKey:"nagramix.stickers.showTime")==nil,"isolated fresh key absent")
   check(!NagramiXMediaSettings.current.showStickerTime,"absent key defaults OFF")
  } else if action=="write" {
   var value=NagramiXMediaSettings.current;value.showStickerTime=args[2]=="true"
   NagramiXMediaSettings.update(value);_ = defaults.synchronize()
   check(NagramiXMediaSettings.current.showStickerTime==value.showStickerTime,"explicit ON/OFF stores exactly")
  } else if action=="other" {
   var value=NagramiXMediaSettings.current;value.photoQuality=42
   NagramiXMediaSettings.update(value);_ = defaults.synchronize()
   check(NagramiXMediaSettings.current.photoQuality==42 && NagramiXMediaSettings.current.showStickerTime,"other preference update preserves saved ON")
  } else {
   check(NagramiXMediaSettings.current.showStickerTime==(args[2]=="true"),"cold process preserves explicit ON/OFF")
  }
  check(NagramiXMediaSettings.current.highQualityPhotos && !NagramiXMediaSettings.current.originalVideos && NagramiXMediaSettings.current.roundVideo,"unrelated defaults retained")
  print("PASS sticker cold settings "+action)
 }
}
'''


def cross_module(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    producer=rt.producer(source);consumer='import StatusProducer\n'+rt.consumer(source)
    provider=folder/'Producer.swift';caller=folder/'Caller.swift';provider.write_text(producer);caller.write_text(consumer)
    common=[swiftc,'-swift-version','5','-warnings-as-errors','-module-cache-path',folder/'cache']
    command(common+['-parse-as-library','-emit-module','-module-name','StatusProducer','-emit-module-path',folder/'StatusProducer.swiftmodule',provider])
    command(common+['-parse-as-library','-typecheck','-I',folder,caller])
    plan=checked_plan(STAGE);before=(OVERLAY/plan['previous'][rt.D]).read_text()
    old=block(block(before,'    public struct Arguments {'),'        public init(')
    current=block(block((source/rt.D).read_text(),'    public struct Arguments {'),'        public init(')
    assert producer.count(current)==1
    provider.write_text(producer.replace(current,old,1))
    command(common+['-parse-as-library','-emit-module','-module-name','StatusProducer','-emit-module-path',folder/'StatusProducer.swiftmodule',provider])
    negative=subprocess.run([str(x) for x in common+['-parse-as-library','-typecheck','-I',folder,caller]],capture_output=True,text=True,timeout=180)
    assert negative.returncode!=0 and "extra argument 'dateTextForHeight' in call" in negative.stderr,negative.stdout+negative.stderr
    result={'actual_arguments_and_display_signatures':'passed in a separate Swift module','old_initializer_negative':'rejected at both native caller expressions','apple_uikit':'not_run','boundary':'Whole actual Arguments/initializer and TextNodeLayoutArguments/public asyncLayout signature. Font/TextNode rendering, account/theme/reaction types are explicit adapters; no fake extra initializer parameter.'}
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        provider.write_text(producer)
        command(common+['-sdk',sdk,'-target','arm64-apple-ios15.0','-parse-as-library','-typecheck',provider])
        result['apple_uikit']='passed actual height block/arguments with real UIKit UIFont/UIColor/NSAttributedString/CoreText; TextNode rendering and model hosts remain adapters'
    return result


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    code=rt.fixture(source)
    runs=execute(swiftc,folder,'sticker-status-height',code)
    variants=[
      ('collapsed-height',code.replace('dateContentHeight = max(date.size.height, referenceDate.size.height)','dateContentHeight = max(date.size.height, referenceDate.size.height * 0)',1),'hidden time retains native status row height'),
      ('static-without-reference',code.replace('dateTextForHeight: mediaSettings.showStickerTime ? nil : dateText,','dateTextForHeight: nil,',1),'hidden time retains native status row height'),
      ('animated-without-reference',code.replace('dateTextForHeight: (mediaSettings.showStickerTime || telegramDice != nil) ? nil : dateText,','dateTextForHeight: nil,',1),'hidden time retains native status row height'),
      ('time-leaks',code.replace('dateText: mediaSettings.showStickerTime ? dateText : "",','dateText: dateText,',1),'only timestamp glyphs disappear'),
      ('dice-time-hidden',code.replace('(mediaSettings.showStickerTime || telegramDice != nil)','mediaSettings.showStickerTime'),'dice retain native time regardless of sticker toggle'),
    ]
    negatives=[]
    for name,text,diagnostic in variants:
        assert text!=code
        negatives+=execute(swiftc,folder,name,text,diagnostic)
    cold=cold_fixture(source);path=folder/'cold.swift';path.write_text(cold);cold_runs=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        binary=folder/('cold-'+mode)
        command([swiftc,'-swift-version','5','-parse-as-library','-warnings-as-errors','-module-cache-path',folder/'cache',*flags,path,'-o',binary])
        env=dict(os.environ,NAGRAMIX_STICKER_SUITE='nagramix.sticker.'+str(uuid.uuid4()),XDG_CONFIG_HOME=str(folder/'preferences'))
        try:
            for args in [['fresh'],['write','false'],['read','false'],['write','true'],['read','true'],['other'],['read','true'],['write','false'],['read','false']]:
                p=command([binary,*args],env=env);cold_runs.append({'mode':mode,'arguments':args,'exit_code':p.returncode,'output':p.stdout.strip()})
        finally:command([binary,'cleanup'],env=env)
    old_default='stickerSize: 100, showStickerTime: false)'
    assert cold.count(old_default)==1
    negatives+=execute(swiftc,folder,'original-default-on',cold.replace(old_default,'stickerSize: 100, showStickerTime: true)',1),'fresh sticker default OFF')
    api=cross_module(source,swiftc,folder/'cross-module')
    return {'executions':runs,'semantic_negatives':negatives,'cold_processes':cold_runs,'native_api':api,'full_application_sdk':'not_run','physical_iphone':'pending'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=checked_plan(STAGE);assert plan['required_previous_stage']=='doh_clear_input_lifecycle'
    assert set(plan['inputs'])=={rt.D,rt.S,rt.A,rt.M} and len(plan['guards'])==11 and not plan['copies'] and not plan['deletions']
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-sticker-spacing-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');result=check(a.source,a.swiftc,root/'runtime')
        for name in plan['inputs']:command([a.swiftc,'-frontend','-parse',a.source/name])
    assert manifest(a.source)==before
    report={'stage':94,'name':STAGE,'runtime_paths':list(plan['inputs']),'guards':11,'loader_refusals':len(refused),'checks':result,'source_unchanged_by_checks':True,'scope':'Hidden sticker time keeps zero visible text width and exact native reference line height. Static/animated/video stickers/large emoji use their existing renderers; dice keep native time. Fresh setting OFF; saved ON/OFF retained. Normal callers default nil. All other frame formulas, reaction layout, text/other media and playback remain unchanged.','boundary':'Source Swift checks and explicit typography/context/graphics adapters. Separate actual Arguments producer/consumer checks new public initializer parameter; future macOS gate typechecks actual height block with genuine UIKit. Full app SDK and iPhone are not verified.','full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
