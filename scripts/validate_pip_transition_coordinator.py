#!/usr/bin/env python3
"""Единые PiP переходы, готовность, превью и откат; фон YouTube неизменён."""
import argparse,json,tempfile
from pathlib import Path
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from validate_pip_swipe_handoff import U,G,N
from pip_transition_coordinator_runtime import entry_fixture,poster_fixture,native_fixture
from pip_transition_coordinator_apple import check as apple_check
STAGE='pip_transition_coordinator'

def contracts(source,plan):
    assert plan['required_previous_stage']=='round_quality_compact_page' and set(plan['inputs'])=={U,G,N} and len(plan['guards'])==19 and not plan['copies'] and not plan['deletions']
    u=(source/U).read_text();g=(source/G).read_text()
    previous=lambda n:(OVERLAY/plan['previous'][n]).read_text()
    # Policy, decoder, audio and transport do not change in this first part.
    for marker in ['    private func nagramiXUpdateBackgroundVideoPlayback()', 'private func nagramiXCanOfferWebPictureInPicture(', '    private func nagramiXAwaitNativePiPPresentation(']:
        assert block(u,marker)==block(previous(U),marker),marker
    assert 'snapshotView(' not in block(g,'    func nagramiXPrepareNativePiPBackdrop()')
    assert 'nagramiXPreparePiPPreviewFallback' not in g
    assert 'self.nagramiXRequestPictureInPicture()' in block(u,'    @objc func pictureInPictureButtonPressed()')
    assert 'self.nagramiXRequestPictureInPicture()' in block(u,'    override func maybePerformActionForSwipeDismiss()')
    assert 'getVideoLayer() != nil' not in block(u,'    override var usesNativePictureInPictureSwipe:')
    # Only the two owner/lock guards change in the existing scroll delegate.
    before=previous(N);after=(source/N).read_text()
    expected=before.replace('if let owner, self.nagramiXNativePictureInPictureItem !== owner { return }','if let owner, let locked = self.nagramiXNativePictureInPictureItem, locked !== owner { return }',1).replace('guard wasLocked else { return }','guard wasLocked || (owner != nil && owner === self.pager.centralItemNode()) else { return }',1)
    assert after==expected,'unrelated gesture changed'
    return {'existing_players_retained':True,'source_only_poster_no_screen_snapshot':True,'shared_button_swipe_path':True,'native_web_restore_waits_for_stop':True,'source_dimensions_not_fixed_16_9':True,'youtube_background_js_audio_and_decoder_guarded_unchanged':True,'no_new_strings_resources_dependencies':True}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    contract=contracts(a.source,plan);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='pip-coordinator-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');api=apple_check(a.source,a.swiftc,root/'apple')
        code=entry_fixture(a.source);poster=poster_fixture(a.source);native=native_fixture(a.source)
        runs=execute(a.swiftc,root,'pip-coordinator-entry',code)+execute(a.swiftc,root,'pip-coordinator-poster',poster)+execute(a.swiftc,root,'pip-coordinator-native',native)
        variants=[('missing-unlocked-rollback',code,'guard wasLocked || (owner != nil && owner === self.pager.centralItemNode()) else { return }','guard wasLocked else { return }'),('early-web-cover-removal',code,'self.nagramiXSystemWebPiPWasRestored = true','self.nagramiXSystemWebPiPWasRestored = true\n            (controller as? GalleryController)?.nagramiXFinishNativePiPBackdrop(animated: false)'),('stale-source-entry',code,'self.videoNode === self.nagramiXPiPEntryVideoNode,','self.videoNode != nil,'),('wrong-web-scale',code,'self.item?.content is WebEmbedVideoContent ? 1.0 : 2.0','self.item?.content is WebEmbedVideoContent ? 2.0 : 2.0'),('cropped-poster',poster,'let scale = min(bounds.width / size.width, bounds.height / size.height)','let scale = max(bounds.width / size.width, bounds.height / size.height)'),('waiting-keeps-wrong-aspect',code,' && self.nagramiXPiPVisualState.phase != .waiting && !(afterPiPStop',' && !(afterPiPStop'),('duplicate-native-didstart',native,'guard self.isStarting else { return }','if self.isStarting {}')]
        for name,body,old,new in variants:
            assert body.count(old)==1,(name,body.count(old));runs+=execute(a.swiftc,root,name,body.replace(old,new,1),'PiP ')
        for path in plan['inputs']:run([a.swiftc,'-frontend','-parse',a.source/path])
    assert before==manifest(a.source)
    report={'stage':90,'name':STAGE,'contracts':contract,'loader_refusals':len(refused),'executions':runs,'apple_api':api,'source_unchanged_by_checks':True,'scope':'Production gallery entry/commit/restore/rollback/size and poster functions plus changed native cancellation/delegate guards. Explicit AVKit, DOM, timers, navigation/attachment, signals and image adapters do not emulate live decoding or pixels.','youtube_background_fix':'deferred_by_user','full_application_sdk':'not_run','physical_iphone':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
