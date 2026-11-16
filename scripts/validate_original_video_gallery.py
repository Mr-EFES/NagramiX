#!/usr/bin/env python3
"""Проверить исходные байты видео через gallery prep/native resource path без fallback в сжатие/документ."""
import argparse,json,subprocess,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from original_video_gallery_apple import check as api_check
import original_video_gallery_runtime as rt
STAGE='original_video_gallery'


def contracts(source):
    p=checked_plan(STAGE);assert p['required_previous_stage']=='font_toggle_alignment'
    assert set(p['inputs'])=={rt.HELPER,rt.LEGACY} and len(p['guards'])==38 and not p['copies'] and not p['deletions']
    before=(OVERLAY/p['previous'][rt.LEGACY]).read_text();after=(source/rt.LEGACY).read_text();restored=after
    for marker in ['public func nagramiXOriginalVideoFile(', 'private func nagramiXPrepareOriginalVideoValue(']:
        restored=restored.replace(block(after,marker),block(before,marker),1)
    assert restored==before,'Unrelated legacy sender changed'
    assert block(before,'private func nagramiXOriginalVideoSupportsStreaming(')==block(after,'private func nagramiXOriginalVideoSupportsStreaming(')
    old=block(before,'private func nagramiXPrepareOriginalVideoValue(')
    new=block(after,'private func nagramiXPrepareOriginalVideoValue(')
    old=old.replace('case let .asset(asset) = data, let photoAsset = asset.backingAsset, let thumbnail,','case let .asset(asset) = data, let photoAsset = asset.backingAsset,',1)
    old=old.replace('!asFile, !asAnimation, stickers.isEmpty, item.timer == nil, item.price == nil,\n          !photoAsset.mediaSubtypes.contains(.videoHighFrameRate)','!asFile, !asAnimation, stickers.isEmpty, item.timer == nil, item.price == nil',1)
    old=old.replace('    if let adjustments {\n','''    if let adjustments {
        let preservesWholeDuration = photoAsset.duration.isFinite && photoAsset.duration > 0.0
            && abs(adjustments.trimStartValue) < 0.001 && abs(adjustments.trimEndValue - photoAsset.duration) < 0.001
''',1).replace('abs(adjustments.cropRotation) < 0.0001, !adjustments.trimApplied(),','abs(adjustments.cropRotation) < 0.0001, (!adjustments.trimApplied() || preservesWholeDuration),',1)
    old=old.replace('stickers.isEmpty, item.timer == nil, item.price == nil else','stickers.isEmpty, (item.timer == nil || item.timer == 0), item.price == nil else',1)
    assert new==old,'Legacy explicit send-as-file and substantive edit rules changed'
    helper=(source/rt.HELPER).read_text()
    assert 'guard enabled else { return .single((items, global)) }' in helper
    assert 'case .videoHighFrameRate' not in helper and 'guard !asset.mediaSubtypes.contains(.videoHighFrameRate)' not in helper
    assert 'public func withUpdatedVideoTrimRange(_ videoTrimRange: Range<Double>?) -> MediaEditorValues' in (source/'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift').read_text()
    return {'runtime_files':2,'off_and_native_compression_implementation_unchanged':True,'settings_default_key_ui_callback_and_saved_values_unchanged':True,'original_resource_before_fullsize_derivative':True,'optional_thumbnail_and_hfr_do_not_request_compression':True,'full_duration_trim_is_not_a_content_edit':True,'real_edits_file_intent_camera_round_paid_rules_preserved':True,'pin_chunk_write_stream_parser_and_native_upload_unchanged':True}


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True);contract=contracts(source);code=rt.fixture(source)
    positive=execute(swiftc,folder,'original-gallery-pipeline',code)
    negative=[]
    for name,old,new,why in [
        ('thumbnail-gate','          item.stickers.isEmpty,','          item.thumbnail != nil, item.stickers.isEmpty,','ON retains original playable video'),
        ('hfr-gate','        return nagramiXOriginalVideoFile(account: context.account, asset: asset, thumbnail: item.thumbnail, cover: item.coverImage)',
         '''        if asset.mediaSubtypes.contains(.videoHighFrameRate) { return .single(NagramiXOriginalVideoPreparation(item: item, isOriginalDocument: false)) }
        return nagramiXOriginalVideoFile(account: context.account, asset: asset, thumbnail: item.thumbnail, cover: item.coverImage)''','ON retains original playable video'),
        ('derived-resource','resources.first(where: { $0.type == .video }) ?? resources.first(where: { $0.type == .fullSizeVideo })','resources.first(where: { $0.type == .fullSizeVideo }) ?? resources.first(where: { $0.type == .video })','original byte length remains unchanged'),
        ('missing-video-metadata','                attributes.append(.Video(duration: duration, size: dimensions, flags: flags, preloadSize: nil, coverTime: nil, videoCodec: nil))','                _ = (flags, duration)','ON retains original playable video'),
        ('ignored-off','guard enabled else { return .single((items, global)) }','guard enabled || !enabled else { return .single((items, global)) }','OFF enters standard Telegram compress route'),
        ('full-trim-as-edit','comparisonValues = values.withUpdatedVideoTrimRange(nil)','comparisonValues = values','full-duration trim does not trigger recompression'),
        ('legacy-full-trim-as-edit','(!adjustments.trimApplied() || preservesWholeDuration)','(!adjustments.trimApplied() && (preservesWholeDuration || !preservesWholeDuration))','legacy full clip keeps original mode'),
        ('lossy-on-error','''            // A failed original export is reported by the existing skipped-item
            // outcome; it must not silently change into a compressed upload.
            return .single(NagramiXOriginalVideoPreparation(item: nagramiXOriginalVideoFailedItem(item), isOriginalDocument: false))''','''            return .single(NagramiXOriginalVideoPreparation(item: item, isOriginalDocument: false))''','failed original never silently recompresses'),
    ]:
        assert code.count(old)==1,(name,code.count(old));negative+=execute(swiftc,folder,name,code.replace(old,new,1),why)
    return {'contracts':contract,'executions':positive,'semantic_negatives':negative,'apple_api':api_check(source,swiftc,folder/'apple'),'boundary':'Actual SignalKit, whole Photos resource exporter/FileHandle writes/streaming parser/pin, modern original preparation/context wrapper and native library-video/prebuilt branches execute together. Photos/UIKit, account/cache/model IO and compressed encoder are explicit adapters. Tests assert OFF selects actual .compress resource; no Linux encoder-size or live Telegram delivery claim. Five genuine synthetic movies include H.264/HEVC 60fps.','full_application_sdk':'not_run','physical_iphone':'pending','server_byte_roundtrip':'pending','new_localization_keys':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    original=manifest(a.source);plan=checked_plan(STAGE)
    with tempfile.TemporaryDirectory(prefix='nagramix-original-gallery-') as d:
        folder=Path(d);refused=guard_checks(a.source,STAGE,plan,folder/'guards');result=check(a.source,a.swiftc,folder/'runtime')
        for n in plan['inputs']:
            value=subprocess.run([str(a.swiftc),'-frontend','-parse',str(a.source/n)],capture_output=True,text=True,timeout=120);assert value.returncode==0,value.stdout+value.stderr
    assert manifest(a.source)==original
    report={'stage':100,'name':STAGE,'runtime_paths':list(plan['inputs']),'guards':len(plan['guards']),'loader_refusals':len(refused),'checks':result,'source_unchanged_by_checks':True,'full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
