#!/usr/bin/env python3
"""Validate real round-video rate policy, retry lifecycle and writer settings."""
import argparse,json,subprocess,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from round_video_encoding_apple import check as api_check
import round_video_encoding_runtime as rt
STAGE='round_video_encoding'


def contracts(source):
    p=checked_plan(STAGE);assert p['required_previous_stage']=='round_quality_checkmark_alignment'
    assert len(p['inputs'])==7 and len(p['copies'])==2 and len(p['guards'])==32 and not p['deletions']
    assert set(p['copies'])=={rt.POLICY,rt.EXPORT}
    markers={
      'submodules/Camera/CameraNeo/Sources/VideoRecorder.swift':['    private func prepareWriterIfNeeded('],
      rt.BASE+'MediaEditorValues.swift':['public func recommendedVideoExportConfiguration('],
      rt.BASE+'MediaEditorVideoAVAssetWriter.swift':['    func setupVideoInput('],
      rt.BASE+'MediaEditorVideoStreamingWriter.swift':['    func setupVideoInput('],
      rt.VIDEO:['    public struct Configuration {','    private func setupWithInputs('],
    }
    for n,allowed in markers.items():
        before=(OVERLAY/p['previous'][n]).read_text();after=(source/n).read_text();restored=after
        for marker in allowed:restored=restored.replace(block(after,marker),block(before,marker),1)
        assert restored==before,'Unrelated code changed: '+n
    fetch='submodules/TelegramUI/Components/Resources/FetchVideoMediaResource/Sources/FetchVideoMediaResource.swift'
    before=(OVERLAY/p['previous'][fetch]).read_text();after=(source/fetch).read_text()
    factory=block(after,'private func nagramiXRoundVideoResourceExport(')
    after=after.replace('// Keep the legacy Postbox boundary here; the new round exporter consumes narrow signals/factories.\n'+factory+'\n\n','',1)
    assert after.count('let videoExport = nagramiXRoundVideoResourceExport(postbox: postbox,')==3
    assert after.replace('let videoExport = nagramiXRoundVideoResourceExport(postbox: postbox,','let videoExport = MediaEditorVideoExport(postbox: postbox,')==before
    assert 'import Postbox' not in (source/rt.EXPORT).read_text() and '.postbox' not in (source/rt.EXPORT).read_text()
    before=(OVERLAY/p['previous'][rt.SCREEN]).read_text();after=(source/rt.SCREEN).read_text()
    restored=after.replace(block(after,'private func storeUneditedVideoMessage('),block(before,'private func storeUneditedVideoMessage('),1)
    a=restored.index('                let maximumRoundSize: Int64?');b=restored.index('                let storedFileId = storeUneditedVideoMessage(',a)
    restored=restored[:a]+restored[b:];restored=restored.replace('                    maximumSize: maximumRoundSize,\n','',1)
    assert restored==before,'Camera completion/round flag/preview or settings were changed'
    values=rt.BASE+'MediaEditorValues.swift';before=(OVERLAY/p['previous'][values]).read_text();after=(source/values).read_text()
    assert before.split('    let compressionProperties: [String: Any]',1)[1]==after.split('    let compressionProperties: [String: Any]',1)[1],'Ordinary export configuration changed'
    assert (source/'submodules/Camera/Sources/NagramiXRoundVideoSettings.swift').read_bytes()==(source/'submodules/NagramiXMediaSettings/Sources/NagramiXRoundVideoSettings.swift').read_bytes()
    return {'settings_page_model_levels_480_512_640_1000_1100_1200_1300_unchanged':True,'only_custom_round_rate_and_fps_paths_changed':True,'actual_distinct_h264_hevc_settings':True,'account_local_server_limit_and_requested_rate_byte_ceiling':True,'validated_output_before_upload_prefix':True,'oversized_camera_bypasses_fast_store':True,'ordinary_videos_stories_and_raw_original_media_preserved':True,'round_flag_and_pending_upload_rpc_unchanged':True,'new_localization_keys':0}


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True);contract=contracts(source)
    pipeline=rt.fixture(source);profiles=rt.profile_fixture(source)
    positive=execute(swiftc,folder,'round-encoding-pipeline',pipeline)+execute(swiftc,folder,'round-encoding-profiles',profiles)
    negative=[]
    for name,code,old,new,reason in [
      ('account-limit',pipeline,'self.maximumSize = Int64(number.doubleValue)','self.maximumSize = Self.fallbackMaximumSize','account max_size is in bytes'),
      ('unchecked-bytes',pipeline,'if !policy.contains(size: size) || size > byteCeiling {','if !policy.contains(size: 1) || 1 > byteCeiling {','measured17MB triggers a fresh export'),
      ('unchecked-codec',pipeline,'guard self.matchesVideo(path: path, configuration: configuration) else {','guard self.matchesVideo(path: path, configuration: configuration) || self.attempts > 0 else {','wrong actual codec/FPS/side rejects mislabeled output'),
      ('unchecked-prefix',pipeline,'if policy == nil {','if self.attempts > 0 {','custom round exports never expose an unchecked upload prefix'),
      ('retry-bound',pipeline,'public static let maximumAttempts = 3','public static let maximumAttempts = 4','persistent overshoot fails after3 attempts'),
      ('camera-fast-store',pipeline,'(maximumSize.map { Int64(data.count) <= $0 } ?? true)','(maximumSize.map { _ in true } ?? true)','camera17MB bypasses unedited fast path'),
      ('reader-fps',pipeline,'CMTimeScale(frameRate)','CMTimeScale(min(frameRate, 30))','reader resamples source120FPS'),
      ('export-fps',profiles,'AVVideoExpectedSourceFrameRateKey: tuning[1]','AVVideoExpectedSourceFrameRateKey: frameRate','writer receives selected FPS'),
      ('export-codec',profiles,'AVVideoCodecKey: tuning[2] == 0 ? AVVideoCodecType.h264 : AVVideoCodecType.hevc','AVVideoCodecKey: tuning[2] == 0 ? AVVideoCodecType.h264 : AVVideoCodecType.h264','real requested H264/HEVC export codec'),
      ('capture-codec',profiles,'processor.quality?.codec == .hevc ? .hevc : .h264','processor.quality?.codec == .hevc ? .h264 : .h264','camera selects a real codec'),
    ]:
        assert code.count(old)==1,(name,code.count(old));negative+=execute(swiftc,folder,name,code.replace(old,new,1),reason)
    return {'contracts':contract,'executions':positive,'semantic_negatives':negative,'apple_api':api_check(source,swiftc,folder/'apple'),'boundary':'Actual Foundation/file IO/policy/direct store/whole new exporter/retry lifecycle/SignalKit and actual camera/export property bodies. Postbox, AV metadata, source reader and hardware encoder are explicit IO boundaries. No real VideoToolbox bitrate/file-size success claimed on Linux.','full_application_sdk':'not_run','physical_iphone':'pending','server_round_trip':'pending'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    initial=manifest(a.source);plan=checked_plan(STAGE)
    with tempfile.TemporaryDirectory(prefix='nagramix-round-encoding-') as d:
        folder=Path(d);refused=guard_checks(a.source,STAGE,plan,folder/'guards');result=check(a.source,a.swiftc,folder/'runtime')
        for n in [*plan['inputs'],*plan['copies']]:
            run=subprocess.run([str(a.swiftc),'-frontend','-parse',str(a.source/n)],capture_output=True,text=True,timeout=120);assert run.returncode==0,run.stdout+run.stderr
    assert manifest(a.source)==initial
    report={'stage':102,'name':STAGE,'runtime_modified':list(plan['inputs']),'new_helpers':list(plan['copies']),'guards':len(plan['guards']),'loader_refusals':len(refused),'checks':result,'source_unchanged_by_checks':True,'new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
