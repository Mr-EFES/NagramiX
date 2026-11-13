#!/usr/bin/env python3
"""Verify approved photo, channel-envelope and transcription-master contracts before SDK."""
import argparse,json,tempfile,shutil,hashlib
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import execute,run
from feature_contract_consistency_apple import check as apple_check
import feature_photo_policy_runtime as photo
import feature_transcription_master_runtime as transcription
import feature_wide_post_envelope_runtime as wide
import original_video_mode_runtime as original

STAGE='feature_contract_consistency'
ROOT=Path(__file__).resolve().parents[1]
BASE='submodules/TelegramUI/Components/Chat/'
SEND='submodules/TelegramUI/Components/ChatMediaSend/Sources/'


def contracts(source,plan):
    assert plan['required_previous_stage']=='original_video_mode'
    assert len(plan['inputs'])==14 and len(plan['guards'])==43 and not plan['copies'] and not plan['deletions']
    assert len(plan['native_inputs'])==3
    # Every changed file is a declared input; full earlier plans/snapshots stay immutable.
    assert set(plan['outputs'])==set(plan['inputs'])
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(source/n)==h,n
    messages=(source/(SEND+'ChatMediaSendMessages.swift')).read_text()
    item_media=block(messages,'private func chatMediaSendItemMedia(')
    assert 'let photoQuality = item.options.nagramiXPhotoQuality' in item_media
    assert item_media.count('photoQuality: photoQuality')==4
    assert 'quality: photoQuality, forceHd: forceHd' in messages
    assert 'photoQuality: item.options.nagramiXPhotoQuality' in (source/(SEND+'ChatMediaSendRender.swift')).read_text()
    assert 'photoQuality: item.options.nagramiXPhotoQuality' in (source/(SEND+'ChatMediaSendLivePhoto.swift')).read_text()
    assert 'forceHd: forceHd || settings.outgoingPhotoHD, photoQuality: settings.outgoingPhotoQuality' in (source/(SEND+'ChatMediaSendSingleItem.swift')).read_text()
    legacy=(source/'submodules/LegacyMediaPickerUI/Sources/LegacyMediaPickers.swift').read_text()
    assert 'let outgoingPhotoQuality = Float(mediaSettings.jpegQuality)' in legacy
    assert 'let outgoingPhotoHD = mediaSettings.outgoingPhotoHD' in legacy
    # Video conversion, export, timing and payment/grouping internals are not rewritten.
    before=(ROOT/'ios'/plan['previous'][SEND+'ChatMediaSendMessages.swift']).read_text()
    assert block(messages,'        if isVideo {')==block(before,'        if isVideo {')
    old=(ROOT/'ios'/plan['previous'][photo.MEDIA]).read_text()
    assert 'return Double(Self.normalizedPercentage(self.photoQuality)) / 100.0' in old
    for kind in ['Sticker','AnimatedSticker']:
        path=BASE+'ChatMessage'+kind+'ItemNode/Sources/ChatMessage'+kind+'ItemNode.swift'
        code=(source/path).read_text()
        assert 'nagramiXIsWideChannelPost(item: item, enabled: NagramiXTabSettings.current.wideChannelPosts)' in code
        assert 'wideColumn?.width ?? imageSize.width' in code
        assert 'wideColumn?.width ?? (params.width - totalInset)' in code
        assert 'strongSelf.updateNagramiXWidePostContainer(item: item, parent: strongSelf.contextSourceNode.contentNode, frame: wideFrame)' in code
        assert 'self.updateNagramiXWidePostAbsoluteRect(rect, within: containerSize)' in code
        assert 'wideColumn?.minX ?? imageFrame.minX' in code
        assert '.BubbleIncoming : .FreeIncoming' in code
        assert '(self.nagramiXWidePostFrame ?? self.imageNode.frame).contains(location)' in code
        assert 'column.maxX - imageFrame.width' in code
    build=(source/(BASE+'ChatMessageItemView/BUILD')).read_text()
    assert '"//submodules/ChatMessageBackground"' in build and '"//submodules/WallpaperBackgroundNode"' in build
    native=(source/wide.BACKGROUND).read_text()
    assert 'public override init()' in native
    assert 'public func setType(type: ChatMessageBackgroundType, highlighted: Bool, graphics: PrincipalThemeEssentialGraphics, maskMode: Bool, hasWallpaper: Bool, transition: ContainedViewLayoutTransition, backgroundNode: WallpaperBackgroundNode?)' in native
    assert 'public func setType(type: ChatMessageBackgroundType, theme: ChatPresentationThemeData, essentialGraphics: PrincipalThemeEssentialGraphics, maskMode inputMaskMode: Bool, backgroundNode: WallpaperBackgroundNode?)' in native
    for path in [transcription.FILE,transcription.ROUND]:
        code=(source/path).read_text();tap=block(code,'    private func transcribe()')
        assert tap.index('guard NagramiXTranscriptionRuntime.requestsEnabled')<tap.index('let temporary =')
        assert 'displayTranscribe = displayTranscribe &&' in code
        assert 'NotificationCenter.default.removeObserver(observer)' in code
        assert 'self.transcribeDisposable?.dispose()' in block(code,'        self.nagramiXTranscriptionSettingsObserver = NotificationCenter.default.addObserver(')
    assert 'guard NagramiXTranscriptionRuntime.requestsEnabled else { return .complete() }' in (source/transcription.FILE).read_text()
    runtime=(source/transcription.RUNTIME).read_text()
    assert 'guard self.requestsEnabled else { completion(.failure(.disabled)); return }' in runtime
    # The original-ID versus uploaded-audio transport and temporary identity rules are unchanged.
    old=(ROOT/'ios'/plan['previous'][transcription.RUNTIME]).read_text()
    for signature in ['    private static func contextTelegramTranscribe(', '    public static func canUseTelegram(', '    private static func canUseTelegramFile(', '    public static func transcribe(context:']:
        assert block(runtime,signature)==block(old,signature),signature


def negatives(name,code):
    cases={
      'photo':[
       ('maximum-ignored','self.highQualityPhotos ? 100 : Self.normalizedPercentage(self.photoQuality)','Self.normalizedPercentage(self.photoQuality)','maximum overrides stored manual quality'),
       ('edited-fixed60','Float(min(100, max(0, photoQuality))) / 100.0','0.6 + Float(photoQuality) * 0.0','edited photo encoder honors snapshot'),
       ('quality-not-persisted','quality: photoQuality, forceHd: forceHd','quality: nil, forceHd: forceHd','persisted resource survives preference changes'),
       ('hd-ignored','global.forceHd = global.forceHd || settings.outgoingPhotoHD','global.forceHd = global.forceHd && settings.outgoingPhotoHD','HD follows max or explicit editor selection'),
      ],
      'wide':[
       ('master-ignored','guard enabled, case .peer','guard !enabled, case .peer','only eligible broadcast history receives envelope'),
       ('selection-width-not-reserved','- max(0.0, selectionInset)','- 0.0','selection translation stays within right safe edge'),
       ('background-left-after-off','self.nagramiXWidePostBackground?.removeFromSupernode()','_ = self.nagramiXWidePostBackground','OFF fully restores native artwork-only row'),
      ],
      'transcription':[
       ('native-master-ignored','NagramiXTranscriptionSettings.current.enabled }','true }','file tap blocks all new requests when master OFF'),
       ('pending-is-cached','!text.isPending && text.error == nil && !text.text.isEmpty','!text.text.isEmpty','ready transcript requires actual completed text'),
       ('native-ui-not-cancelled','self.transcribeDisposable?.dispose()','_ = self.transcribeDisposable','OFF disposes native and local UI operations'),
       ('context-not-cancelled','for job in jobs.values { job.dispose() }','_ = jobs','OFF clears outliving context operation'),
      ]}
    for label,old,new,diagnostic in cases[name]:
        assert old in code,(name,label)
        yield label,code.replace(old,new),diagnostic


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=checked_plan(STAGE);contracts(a.source,plan)
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    initial=manifest(a.source);runs=[]
    with tempfile.TemporaryDirectory(prefix='nagramix-feature-contracts-') as temp:
        folder=Path(temp);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
        for name,module in [('photo',photo),('wide',wide),('transcription',transcription)]:
            code=module.fixture(a.source);runs+=execute(a.swiftc,folder,name,code)
            for label,mutated,diagnostic in negatives(name,code):runs+=execute(a.swiftc,folder,name+'-'+label,mutated,diagnostic)
        runs+=execute(a.swiftc,folder,'original-video-preserved',original.fixture(a.source))
        api=apple_check(a.source,a.swiftc,folder/'api')
        for n in plan['outputs']:
            if n.endswith('.swift'):run([a.swiftc,'-frontend','-parse',a.source/n])
    assert manifest(a.source)==initial
    report={'stage':STAGE,'source_files':len(initial),'source_unchanged_by_checks':True,'outputs':len(plan['outputs']),'guards':len(plan['guards']),'loader_refusals':len(refused),'executions':runs,'actual_api':api,'boundary':'Actual production settings, photo snapshots/builders, native video branch, channel envelope eligibility/geometry/background methods, ASR entry/display gates/observers/context cancellation; native graph/codec/engine/theme are explicit adapters. No live encoding, network, AV capture or iPhone pixel claim.','full_application_sdk':'pending','device':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
