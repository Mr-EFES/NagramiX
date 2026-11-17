#!/usr/bin/env python3
"""Проверить независимость gallery profile и штатный decoder с выбранным FPS."""
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from late_source_stages import verified_prefix,LATE_SOURCE_STAGES
from validate_private_temporary_transcription import execute,save_failed_fixture
import gallery_round_export_runtime as rt
STAGE='gallery_round_export'


def apple_check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    text=(source/rt.R).read_text()
    code='import Foundation\nimport AVFoundation\nimport CoreMedia\n'+block(text,'final class NagramiXRoundVideoFrameReader')+'\n'
    path=folder/'GalleryRoundReaderAPI.swift';path.write_text(code)
    p=subprocess.run([str(swiftc),'-frontend','-parse',str(path)],capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
    report={'swift_parse':'passed','actual_avfoundation_reader_api':'not_run','application_sdk':'pending','physical_iphone':'pending'}
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        p=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-typecheck','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),str(path)],capture_output=True,text=True,timeout=180)
        if p.returncode:save_failed_fixture(path,'gallery-round-reader-api','iphoneos','typecheck',p)
        assert p.returncode==0,p.stdout+p.stderr
        report['actual_avfoundation_reader_api']='passed'
    return report


def contracts(source):
    plan=checked_plan(STAGE);assert len(plan['inputs'])==7 and len(plan['guards'])==8 and not plan['copies'] and not plan['deletions']
    assert plan['required_previous_stage']=='tab_bar_visual_consistency'
    for name in [rt.V,rt.G,rt.S]:
        current=(source/name).read_text()
        assert 'settings: .current' not in current
    helper=block((source/rt.V).read_text(),'func chatMediaEditorRoundVideoValues(')
    selection=block((source/rt.H).read_text(),'private final class NagramiXRoundQualitySelection')
    assert '.current' not in helper+selection and 'UserDefaults' not in helper+selection
    assert 'self.pageModel.currentItem.uniqueId == itemId' in block((source/rt.Q).read_text(),'    private func nagramiXPresentRoundQuality(')
    export=(source/rt.X).read_text()
    assert 'let videoOutput = AVAssetReaderTrackOutput(track: mainVideoTrack, outputSettings: outputSettings)' in export
    assert 'nagramiXRoundVideoReaderOutput' not in export
    assert 'reader.status == .completed && self.nagramiXRoundSampleReader?.failed == false' in export
    assert 'if self.nagramiXRoundSamplingFailed {' in export
    # Bounded size/metadata validation, retries, cancellation and upload boundary
    # remain the previously checked production implementation, byte for byte.
    text=(source/rt.R).read_text();before=(OVERLAY/plan['previous'][rt.R]).read_text()
    assert block(text,'public final class NagramiXRoundVideoExport')==block(before,'public final class NagramiXRoundVideoExport')
    assert block((source/rt.X).read_text(),'        var nagramiXIsCustomRoundVideo:')==block((OVERLAY/plan['previous'][rt.X]).read_text(),'        var nagramiXIsCustomRoundVideo:')
    return {'camera_settings_recording_page_and_upload_boundary_guarded':True,'gallery_profile_local_to_attachment':True,'bounded_export_validation_and_round_attribute_preserved':True,'new_strings_app_files_dependencies':0,'848x477_is_quality_estimate_not_confirmed_source_size':True,'exact_hardware_error_not_proven_by_screen_recording':True,'native_reader_replaces_added_video_composition_output':True}


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True);contract=contracts(source)
    profile=rt.model_fixture(source);reader=rt.reader_fixture(source)
    runs=execute(swiftc,folder,'gallery-round-profile',profile)+execute(swiftc,folder,'gallery-round-reader',reader)
    negatives=[]
    variants=[
        ('camera-default',profile,'let standard = [480, 30, 0, 1_000_000]','let standard = [640, 60, 1, 1_300_000]','gallery default is independent of camera preset'),
        ('overwrite-local-profile',profile,'let tuning = chatMediaEditorRoundVideoTuning(values.nagramiXRoundTuning)','let tuning = chatMediaEditorRoundVideoTuning(nil)','toolbar/capture refresh keeps local choice'),
        ('apply-once',profile,'guard !self.finished else { return }','if self.finished {}','Apply commits selected four-field profile exactly once'),
        ('cancel-applies',profile,'self.finished = true\n        self.sheet?.dismissAnimated()','self.finished = true\n        self.updated(self.tuning)\n        self.sheet?.dismissAnimated()','close cancels without applying'),
        ('ignore-fps',reader,'self.fps = CMTimeScale(frameRate)','self.fps = CMTimeScale(30)','selected FPS yields correct output frame count'),
        ('overrun-range',reader,'CMTimeCompare(self.target, self.end) < 0 else { return nil }','CMTimeCompare(self.target, CMTimeAdd(self.end, CMTime(value:1,timescale:self.fps))) < 0 else { return nil }','selected FPS yields correct output frame count'),
        ('wrong-source-frame',reader,'<= 0 {','< -999 {','drop/duplicate preserves source content and time'),
        ('truncate-native-eof',reader,'reader.status == .completed && self.nagramiXRoundSampleReader?.failed == false','reader.status == .completed && false','actual export guard preserves tail after native reader completes'),
    ]
    for name,code,old,new,reason in variants:
        assert old in code,name;negatives+=execute(swiftc,folder,name,code.replace(old,new),reason)
    for n in checked_plan(STAGE)['inputs']:
        p=subprocess.run([str(swiftc),'-frontend','-parse',str(source/n)],capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
    return {'contracts':contract,'executions':runs,'semantic_negatives':negatives,'apple_api':apple_check(source,swiftc,folder/'apple'),'boundary':'Actual43-field model/copies/export configuration, attachment helper, menu selection/cancel/apply and sample scheduling; explicit Telegram graph/UI/AV metadata/CoreMedia/encoder hosts. No real pixel/encoder/network/device claim.','full_application_sdk':'not_run','physical_iphone':'pending'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='gallery-round-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,checked_plan(STAGE),root/'guards');r=check(a.source,a.swiftc,root/'runtime')
    assert before==manifest(a.source);r.update(stage=STAGE,loader_refusals=refused)
    if a.report:a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
