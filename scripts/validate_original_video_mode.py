#!/usr/bin/env python3
"""Validate original ON / native compression OFF in modern Gallery sending."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_quick_format import manifest,block
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from original_video_mode_runtime import fixture,HELPER,RENDER,LEGACY,BASE
from original_video_mode_apple import check as apple_check
ROOT=Path(__file__).resolve().parents[1];STAGE='original_video_mode'


def negatives(code):
    for name,old,new,message in [
        ('always-original','enabled: originalVideos)','enabled: originalVideos || true)','ON original and OFF compression are distinct'),
        ('never-original','enabled: originalVideos)','enabled: originalVideos && false)','ON original and OFF compression are distinct'),
        ('lossy-error-fallback','result.source = .prebuilt(media: nil)','result.source = item.source','failed original export is skipped without compressed fallback'),
        ('discard-visual-edits','!chatMediaEditorValuesHaveVisualEdits(values)','true || !chatMediaEditorValuesHaveVisualEdits(values)','edited and special videos retain native conversion'),
        ('late-mode-read','result.source = .prebuilt(media: file)','result.source = NagramiXMediaSettings.current.originalVideos ? .prebuilt(media: file) : item.source','mode snapshot survives setting change during export'),
    ]:
        assert code.count(old)==1,(name,code.count(old));yield name,code.replace(old,new,1),message


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='selection_scroll_continuity' and len(plan['inputs'])==3 and len(plan['guards'])==24 and set(plan['copies'])=={HELPER}
    assert plan['native_inputs']=={'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendRender.swift':'dae033d53acacb1d6b96c10ffb8ab9f13f91b621'}
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards'],**{n:v['sha256'] for n,v in plan['copies'].items()}}.items():assert digest(a.source/n)==h,n
    old=(ROOT/'ios'/plan['previous'][LEGACY]).read_text();new=(a.source/LEGACY).read_text()
    assert old.replace('private func nagramiXOriginalVideoFile(account:','public func nagramiXOriginalVideoFile(account:',1)==new,'Original export body/bytes/cleanup unchanged'
    assert '"//submodules/NagramiXMediaSettings:NagramiXMediaSettings"' in (a.source/(BASE+'BUILD')).read_text()
    state=manifest(a.source);code=fixture(a.source);current=block((a.source/RENDER).read_text(),'public func chatMediaSendMessages(context:').replace('public ','');previous=block((ROOT/'ios'/plan['previous'][RENDER]).read_text(),'public func chatMediaSendMessages(context:').replace('public ','');assert code.count(current)==1
    with tempfile.TemporaryDirectory(prefix='original-video-mode-') as d:
        f=Path(d);refusals=guard_checks(a.source,STAGE,plan,f/'guards');runs=execute(a.swiftc,f,'original-video-mode',code)
        runs+=execute(a.swiftc,f,'original69-mode-ignored',code.replace(current,previous,1),'ON original and OFF compression are distinct')
        for n,mutated,message in negatives(code):runs+=execute(a.swiftc,f,n,mutated,message)
        apple=apple_check(a.source,a.swiftc,f/'native-api')
        for n in [HELPER,RENDER,LEGACY]:run([a.swiftc,'-frontend','-parse',a.source/n])
    assert state==manifest(a.source)
    report={'stage':STAGE,'loader_refusals':len(refusals),'executions':runs,'production_checks_per_positive_mode':41,'actual_settings_and_native_api':apple,
'boundary':'Actual new original preparation, context send wrapper, existing item/options/visual-edit checks, unchanged native library-video compress branch and real SwiftSignalKit core/map/catch/switch/take/then/combine/bounded lanes execute with explicit Photos/exporter/media/renderer adapters. Original export implementation byte-identical except public visibility. Tests prove routing and lifecycle; no claim of real Photos bytes, transcoding size, server roundtrip or iPhone behavior.',
'stock_OFF':'No Photos original lookup/export; original inputs/global options go into exact existing native .compress(adjustments/nil) path. No forced bitrate/preset/default change.',
'new_sdk_actions_ipa_started':False,'full_application_sdk':'pending','device':'pending','source_unchanged_by_checks':True}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
