#!/usr/bin/env python3
"""Проверить связь редактора круглого видео с качественными кружками."""
import argparse,json,tempfile,copy,importlib.util,hashlib
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import execute,run
import round_editor_quality_runtime as runtime
from round_editor_quality_apple import check as api_check

ROOT=Path(__file__).resolve().parents[1];STAGE='round_editor_quality'


def contracts(source,plan):
    assert plan['required_previous_stage']=='transcription_cached_read'
    assert len(plan['outputs'])==7 and len(plan['guards'])==21
    assert not plan['copies'] and not plan['deletions']
    assert not plan['native_inputs']
    historical=json.loads((ROOT/'ios/round_video_editor_patches.json').read_text())
    assert plan['inputs'][runtime.GALLERY]==historical['guards'][runtime.GALLERY], 'Inherited known native guard must stay exact'
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(source/n)==h,n
    before=(ROOT/'ios'/plan['previous'][runtime.VALUES]).read_text();after=(source/runtime.VALUES).read_text()
    method=block(after,'    public func withUpdatedNagramiXRoundTuning(')
    assert after.replace('\n\n'+method,'',1)==before,'Native encoder/settings/JSON/copy paths must remain exact outside the one new copy method'
    copy=block(before,'    public func makeCopy()')
    assert method==copy.replace('makeCopy()','withUpdatedNagramiXRoundTuning(_ tuning: [Int]?)').replace('nagramiXRoundTuning: self.nagramiXRoundTuning)','nagramiXRoundTuning: tuning)')
    video=(source/runtime.VIDEO).read_text();gallery=(source/runtime.GALLERY).read_text();component=(source/runtime.COMPONENT).read_text()
    assert 'import NagramiXMediaSettings\n' in video
    assert '"//submodules/NagramiXMediaSettings:NagramiXMediaSettings",' in (source/(runtime.SCREEN[:-8]+'BUILD')).read_text()
    assert 'initialValues = chatMediaEditorRoundVideoValues(initialValues, settings: .current)' in gallery
    assert 'if subject.isVideo && !item.isAnimation {' in gallery
    assert 'values: initialValues, hasHistogram:' in gallery
    assert 'roundVideoQualitySide: self.nagramiXIsRoundVideo ? Int(chatMediaEditorVideoFileDimensions(values: self.mediaEditor.values, duration: self.subject.duration).width) : nil' in (source/(runtime.SCREEN+'ChatMediaEditorScreen.swift')).read_text()
    assert 'case let .roundVideoQuality(side):' in component and 'nagramiXRoundVideoQualityImage(side: side, color: color)' in component
    assert 'NagramiXRoundVideoSettings.update(' not in video and 'UserDefaults.standard.set' not in video
    single=(source/'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendSingleItem.swift').read_text()
    messages=(source/'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendMessages.swift').read_text()
    assert 'let configuration = recommendedVideoExportConfiguration(values: values, duration: duration, frameRate: 30.0)' in single
    assert 'let finalDimensions = chatMediaEditorVideoFileDimensions(values: values, duration: duration)' in messages


def inherited_origin_negative(source,plan,folder):
    spec=importlib.util.spec_from_file_location(STAGE,ROOT/'ios'/ (STAGE+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    tree=folder/'inherited-native-source';overlay=folder/'inherited-native-overlay';overlay.mkdir()
    for n in set(plan['inputs'])|set(plan['guards']):
        f=tree/n;f.parent.mkdir(parents=True,exist_ok=True)
        data=(ROOT/'ios'/plan['previous'][n]).read_bytes() if n in plan['inputs'] else (source/n).read_bytes()
        f.write_bytes(data)
    for n in plan['templates']:
        f=overlay/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((ROOT/'ios'/n).read_bytes())
    changed=copy.deepcopy(plan);n=runtime.GALLERY;data=(tree/n).read_bytes()+b'\n';h=hashlib.sha256(data).hexdigest()
    (tree/n).write_bytes(data);(overlay/changed['previous'][n]).write_bytes(data);changed['inputs'][n]=h;changed['templates'][changed['previous'][n]]=h
    (overlay/(STAGE+'_patches.json')).write_text(json.dumps(changed))
    before=manifest(tree)
    try:module.apply_round_editor_quality(tree,overlay)
    except SystemExit as error:assert 'native input origin' in str(error),str(error)
    else:raise AssertionError('Inherited native input accepted after changing matching source/template/SHA')
    assert manifest(tree)==before
    return 'inherited-native-blob-drift'


def mutate(code,old,new):
    assert code.count(old)>=1,old
    return code.replace(old,new)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=checked_plan(STAGE);contracts(a.source,plan);assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    initial=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-round-editor-quality-') as temp:
        folder=Path(temp);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
        refused.append(inherited_origin_negative(a.source,plan,folder))
        policy=runtime.fixture(a.source);editor=runtime.ui_fixture(a.source);badge=runtime.badge_fixture(a.source)
        runs=execute(a.swiftc,folder,'quality-policy',policy)
        runs+=execute(a.swiftc,folder,'quality-editor',editor)
        runs+=execute(a.swiftc,folder,'quality-badge',badge)
        old_video=(ROOT/'ios'/plan['previous'][runtime.VIDEO]).read_text();new_video=(a.source/runtime.VIDEO).read_text()
        original=editor.replace(runtime.clean(block(new_video,'    func nagramiXToggleRoundVideo(')),runtime.clean(block(old_video,'    func nagramiXToggleRoundVideo(')),1)
        assert original!=editor
        variants=[
            ('original72-reset-480',original,'actual round toggle attaches high-quality settings instead of native 480'),
            ('master-ignored',mutate(policy,', settings.enabled else { return values }',' else { return values }'),'master OFF retains native default'),
            ('codec-reset',mutate(policy,'settings.codec.rawValue, settings.bitRate','0, settings.bitRate'),'editor snapshots selected side FPS codec'),
            ('bitrate-reset',mutate(policy,'settings.codec.rawValue, settings.bitRate','settings.codec.rawValue, settings.quality.bitRate'),'editor snapshots selected side FPS codec'),
            ('reopen-retunes',mutate(policy,'values.nagramiXRoundTuning == nil, ',''),'reopen keeps saved item snapshot'),
            ('stale-exit-tuning',mutate(editor,'.withUpdatedNagramiXRoundTuning(before?.nagramiXRoundTuning)',''),'exit round restores original tuning'),
            ('badge-stuck-480',mutate(badge,'roundVideoQualitySide ?? 480','480'),'round badge displays export side'),
            ('copy-drops-bitrate',mutate(policy,'nagramiXRoundTuning: tuning)','nagramiXRoundTuning: tuning.map { Array($0.prefix(3)) })'),'editor snapshots selected side FPS codec')]
        for name,code,error in variants:runs+=execute(a.swiftc,folder,name,code,error)
        for name in plan['outputs']:
            if name.endswith('.swift'):run([a.swiftc,'-frontend','-parse',a.source/name])
        api=api_check(a.source,a.swiftc,folder/'api')
    assert manifest(a.source)==initial
    report={'stage':STAGE,'source_files':len(initial),'source_unchanged_by_checks':True,'outputs':7,'guards':21,'loader_refusals':len(refused),'executions':runs,'actual_api':api,'boundary':'Actual 43-field immutable constructor/copy, editor snapshot, real toggle and per-item native crop methods, full recommendedVideoExportConfiguration and tuning JSON statements. Telegram graph/UI/AVFoundation writer are explicit adapters. Existing camera capture/recording, encoder implementation and ordinary send bodies unchanged; hardware/actual output file requires Apple SDK/iPhone.','full_application_sdk':'pending','device':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
