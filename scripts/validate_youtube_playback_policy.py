#!/usr/bin/env python3
"""Проверить устойчивые YouTube hints для того же системного PiP и фонового owner."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import run
from validate_private_temporary_transcription import execute
from system_web_picture_in_picture_runtime import script,WEB,AV
from system_web_picture_in_picture_apple import check as apple_check
import youtube_playback_policy_runtime as runtime
from youtube_playback_policy_js import check as js_check

ROOT=Path(__file__).resolve().parents[1];STAGE='youtube_playback_policy'


def source_contract(source,plan):
    assert plan['required_previous_stage']=='edit_result_consistency' and set(plan['inputs'])=={WEB} and len(plan['guards'])==19
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(source/n)==h,n
    before=(ROOT/'ios'/plan['previous'][WEB]).read_text();after=(source/WEB).read_text()
    for marker in ['    var status:','    func enterNativePictureInPicture()', '    func exitNativePictureInPicture()', '    private func dispatch(_ payload:', '    public func webpageToLoad(']:
        if marker in before:assert block(before,marker)==block(after,marker),marker
    assert before.count('WKWebView(')==after.count('WKWebView(')==1
    assert after.count('self.impl.setup(')==1 and 'import NagramiXCore\n' in after
    observer=block(after,'        self.nagramiXPolicyObserver = NotificationCenter.default.addObserver(')
    assert '[weak self]' in observer and 'self.impl is YoutubeEmbedImplementation' in observer and 'NagramiXTabSettings.videoPiPSwipeEnabled' in observer
    assert 'if let observer = self.nagramiXPolicyObserver { NotificationCenter.default.removeObserver(observer) }' in after
    build=(source/'submodules/TelegramUniversalVideoContent/BUILD').read_text();assert '"//submodules/NagramiXCore:NagramiXCore"' in build
    settings=(source/runtime.SETTINGS).read_text();assert 'UserDefaults.standard.object(forKey: Key.videoPiPSwipe) as? Bool ?? true' in settings
    gallery=(source/'submodules/GalleryUI/Sources/GalleryController.swift').read_text()
    config=block(gallery,'    static func with(appConfiguration: AppConfiguration)')
    assert config.index('if NagramiXTabSettings.videoPiPSwipeEnabled')<config.index('data["youtube_pip"]')
    policy=script(source)
    for forbidden in ['.play(','.pause(','.currentTime =','new Video','fetch(','XMLHttpRequest','createElement(\'video\'','setInterval(']:assert forbidden not in policy,forbidden
    assert 'webkitSetPresentationMode' in policy and 'MutationObserver' in policy and "document.addEventListener('visibilitychange', lifecycle, true)" in policy
    assert 'setMode(video, \'picture-in-picture\')' in policy
    # Most of the player stays exactly native. Reconstruct the one approved
    # settings hook and frame-policy change, preserving all playback commands.
    restored=after
    restored=restored.replace('import NagramiXCore\n','',1).replace('    private var nagramiXPolicyObserver: NSObjectProtocol?\n','',1)
    call='        self.nagramiXSystemPiP.setYouTubeOverride(self.impl is YoutubeEmbedImplementation, enabled: NagramiXTabSettings.videoPiPSwipeEnabled)\n'
    restored=restored.replace('\n'+call+observer+'\n','',1)
    restored=restored.replace('        if let observer = self.nagramiXPolicyObserver { NotificationCenter.default.removeObserver(observer) }\n','',1)
    current_bridge=block(restored,'private final class NagramiXWebSystemPictureInPicture:');old_bridge=block(before,'private final class NagramiXWebSystemPictureInPicture:')
    # Whole bridge runs in Swift fixtures and its DOM runs independently. Outside
    # this module-private bridge and the settings hookup every byte is native.
    restored=restored.replace(current_bridge,old_bridge,1)
    assert restored==before,'Unrelated web-player lifecycle/setup/controls changed'
    return {'one_existing_webview':True,'same_loaded_video':'native HTML-video WebKit presentation mode; no URL extraction or new player','server_youtube_pip_priority':'existing gate already overrides while ON; preserved exact bytes','native_avplayer_gallery_audio_permissions':'19 exact guards unchanged','settings':'existing key/default/explicit OFF and live observer; background flag unchanged','no_force_replay_or_polling':True}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE);contract=source_contract(a.source,plan);initial=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='youtube-playback-policy-') as d:
        folder=Path(d);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
        bridge=runtime.bridge_fixture(a.source);runs=execute(a.swiftc,folder,'youtube-bridge',bridge)
        for name,mutated,label in runtime.bridge_negatives(bridge):runs+=execute(a.swiftc,folder,name,mutated,label)
        hooks=runtime.hook_fixture(a.source);runs+=execute(a.swiftc,folder,'youtube-setting',hooks)
        for name,mutated,label in runtime.hook_negatives(hooks):runs+=execute(a.swiftc,folder,name,mutated,label)
        javascript=js_check(a.source,folder)
        from system_web_picture_in_picture_runtime import script as extract_script
        old=(ROOT/'ios'/plan['previous'][WEB]).read_text();marker='    private static let script = #"""\n';start=old.index(marker)+len(marker);end=old.index('\n"""#',start)
        previous=js_check(a.source,folder,old[start:end])
        apple=apple_check(a.source,a.swiftc,folder)
        run([a.swiftc,'-frontend','-parse',a.source/WEB])
    assert manifest(a.source)==initial
    report={'stage':STAGE,'inputs':1,'guards':19,'source_contract':contract,'loader_refusals':len(refused),'executions':runs,'javascript':javascript,'previous_policy_regression':previous,'apple_sdk_precheck':apple,'source_unchanged_by_checks':True,'live_youtube':'not_run','whole_app_sdk':'not_run','device':'pending','boundary':'Actual WK bridge, actual preference getter/observer and actual injected JS execute with explicit WK/DOM adapters. This does not guarantee PiP for a stream rejected by WebKit/iOS or unavailable at YouTube; no live stream, protected playback or lock-screen scheduling was tested.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='executions'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
