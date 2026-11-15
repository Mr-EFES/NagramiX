#!/usr/bin/env python3
"""YouTube background playback: explicit ownership, early policy and actual media state."""
import argparse,json,tempfile
from pathlib import Path
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from system_web_picture_in_picture_runtime import WEB,CONTENT
from youtube_background_continuity_runtime import fixture
from youtube_background_continuity_apple import check as apple_check
from youtube_background_continuity_js import check as js_check
STAGE='youtube_background_continuity'


def contracts(source,plan):
    assert plan['required_previous_stage']=='pip_transition_coordinator'
    assert set(plan['inputs'])=={WEB,CONTENT} and len(plan['guards'])==16 and not plan['copies'] and not plan['deletions']
    before=(OVERLAY/plan['previous'][WEB]).read_text();after=(source/WEB).read_text()
    # Retain the actual player/decoder and all existing PiP entry/stop/restore behavior.
    old=block(before,'private final class NagramiXWebSystemPictureInPicture:');new=block(after,'private final class NagramiXWebSystemPictureInPicture:')
    for marker in ['    func begin()', '    func stop()']:
        assert block(old,marker)==block(new,marker),marker
    for marker in ['    func play()', '    func pause()', '    func seek(timestamp:']:
        assert block(block(before,'final class WebEmbedPlayerNode:'),marker)==block(block(after,'final class WebEmbedPlayerNode:'),marker),marker
    content=(source/CONTENT).read_text()
    assert 'self.playerNode.isYouTube && NagramiXTabSettings.backgroundVideoPlaybackEnabled' in block(content,'    func play()')
    assert 'DispatchQueue.main.asyncAfter(deadline: .now() + 5.0)' in block(content,'    func play()')
    return {'scope':'Two existing web-player files; native/audio/recording/settings/NowPlaying/Gallery/BUILD unchanged by SHA and full manifest.',
      'existing_webkit_player_retained':True,'background_independent_of_pip_switch':True,'document_start_policy_seeded':True,
      'manual_pause_interruption_and_background_off_preserved':True,'bounded_explicit_start_handoff':True,
      'no_new_strings_resources_dependencies_or_stream_extraction':True}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=checked_plan(STAGE);assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    contract=contracts(a.source,plan);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='youtube-background-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');api=apple_check(a.source,a.swiftc,root/'apple')
        code=fixture(a.source);runs=execute(a.swiftc,root,'youtube-background',code)
        variants=[
          ('no-background-handoff','self.playerNode.isYouTube && NagramiXTabSettings.backgroundVideoPlaybackEnabled','false && NagramiXTabSettings.backgroundVideoPlaybackEnabled','initial play survives background'),
          ('stale-iframe-pause','case .paused where actual && self.nagramiXSystemPiP.preservesYouTubePlayback:','case .paused where false:','stale iframe pause cannot drop'),
          ('lost-native-pause','case .playing where !actual || !self.nagramiXSystemPiP.playbackAllowed:','case .playing where false:','stale iframe playing cannot undo'),
          ('stale-acquisition','guard let self, self.nagramiXAudioGeneration == generation, self.nagramiXHasManagedAudio else { return }','guard let self, self.nagramiXHasManagedAudio else { return }','stale acquisition cannot start'),
          ('foreign-token','body["token"] as? String == self.token','body["token"] is String','foreign token cannot change playback'),
          ('no-background-payload','"backgroundEnabled": self.youtube && self.background','"backgroundEnabled": false','background lease is independent'),
          ('no-handoff-expiry','guard let self, self.nagramiXPlaybackHandoffGeneration == generation else { return }','guard let self, self.nagramiXPlaybackHandoffGeneration != generation else { return }','startup handoff expires'),
        ]
        for name,old,new,why in variants:
            assert code.count(old)==1,(name,code.count(old));runs+=execute(a.swiftc,root,name,code.replace(old,new,1),why)
        dom=js_check(a.source,root/'dom')
        for path in plan['inputs']:run([a.swiftc,'-frontend','-parse',a.source/path])
    assert before==manifest(a.source)
    report={'stage':91,'name':STAGE,'contracts':contract,'loader_refusals':len(refused),'executions':runs,'javascript':dom,'apple_api':api,'source_unchanged_by_checks':True,
      'scope':'Entire production frame/script helper, actual MediaPlayerStatus definitions, mapping, changed explicit play/pause/owner and managed session statements, actual notification handlers. DOM, WK, timers, implementation and SignalKit/audio-session hosts are explicit adapters.',
      'full_application_sdk':'not_run','live_youtube':'not_run','physical_iphone':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
