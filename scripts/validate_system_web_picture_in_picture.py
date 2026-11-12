#!/usr/bin/env python3
"""Проверить системный PiP/фон web и AVPlayer без второго плеера до SDK."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import execute,run
import system_web_picture_in_picture_runtime as runtime
import system_web_picture_in_picture_gallery_runtime as gallery
from system_web_picture_in_picture_js import check as js_check
from system_web_picture_in_picture_apple import check as apple_check

ROOT=Path(__file__).resolve().parents[1];STAGE='system_web_picture_in_picture'


def contracts(source,plan):
 assert plan['required_previous_stage']=='font_theme_contrast'
 assert len(plan['inputs'])==8 and len(plan['guards'])==22 and not plan['copies'] and not plan['deletions']
 assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(source/n)==h,n
 before={n:(ROOT/'ios'/plan['previous'][n]).read_text() for n in plan['inputs']}
 after={n:(source/n).read_text() for n in plan['inputs']}
 g=after[runtime.GALLERY];old=before[runtime.GALLERY]
 for marker in ['private final class NativePictureInPictureContentImpl:','private func nagramiXCanOfferWebPictureInPicture(','private func nagramiXUsesEmbeddedPictureInPicture(']:
  assert block(old,marker)==block(g,marker),'Native sample-buffer player and permission rules must stay unchanged'
 entry=block(g,'    private func nagramiXBeginWebPictureInPicture()')
 assert 'OverlayUniversalVideoNode' not in entry and 'expandIntoCustomPiP' not in entry and 'setOverlayVideoNode' not in entry
 assert entry.count('videoNode.enterNativePictureInPicture()')==1
 assert 'if active {' in entry and entry.index('if active {')<entry.index('self.beginCustomDismiss(.pip)')
 assert 'self.nagramiXFinishSystemWebPiP(stop: true)' in block(g,'    override func centralityUpdated(')
 assert 'self.nagramiXFinishSystemWebPiP(stop: true)' in block(g,'    override func visibilityUpdated(')
 assert 'else if nagramiXUsesEmbeddedPictureInPicture(item)' in block(g,'    private func nagramiXUpdateBackgroundVideoPlayback()')
 assert 'isPictureInPicture: self.nagramiXWebPiPTransitionStarted' in g
 for n in [runtime.AV,runtime.BASE+'PlatformVideoContent.swift']:
  assert before[n].count('AVPlayer(')==after[n].count('AVPlayer(')==1
  assert 'NagramiXAVPlayerPictureInPicture(player: self.player, layer: layer)' in after[n]
 assert before[runtime.WEB].count('WKWebView(')==after[runtime.WEB].count('WKWebView(')==1
 assert 'configuration.allowsPictureInPictureMediaPlayback = true' in after[runtime.WEB]
 assert 'UIApplication.shared' not in after[runtime.AV] and 'UIApplication.shared' not in after[runtime.CONTENT]
 assert 'minimum_os_version = "15.0"' in (source/'Telegram/BUILD').read_text()
 build=after['submodules/TelegramUniversalVideoContent/BUILD']
 assert build==before['submodules/TelegramUniversalVideoContent/BUILD'].replace('    deps = [\n','    deps = [\n        "//submodules/NagramiXCore:NagramiXCore",\n',1)
 assert '"//submodules/TelegramUniversalVideoContent' not in (source/'submodules/NagramiXCore/BUILD').read_text()
 # Check preference keys/defaults and the original YouTube override through
 # the exact unchanged guarded setting implementation, no migration/reset.
 settings=(source/'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift').read_text()
 assert 'UserDefaults.standard.object(forKey: Key.backgroundVideoPlayback) as? Bool ?? true' in settings
 assert 'UserDefaults.standard.object(forKey: Key.videoPiPSwipe) as? Bool ?? true' in settings
 return before


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE);contracts(a.source,plan)
 initial=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='system-web-pip-') as temporary:
  folder=Path(temporary);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
  bridge=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'system-web-bridges',bridge)
  for name,text,why in runtime.negatives(bridge):runs+=execute(a.swiftc,folder,name,text,why)
  life=gallery.fixture(a.source);runs+=execute(a.swiftc,folder,'system-web-gallery',life)
  for name,text,why in gallery.negatives(life):runs+=execute(a.swiftc,folder,name,text,why)
  javascript=js_check(a.source,folder);apple=apple_check(a.source,a.swiftc,folder)
  for n in plan['outputs']:
   if n.endswith('.swift'):run([a.swiftc,'-frontend','-parse',a.source/n])
 assert manifest(a.source)==initial
 report={'stage':STAGE,'inputs':8,'guards':22,'loader_refusals':len(refused),'source_files':len(initial),'source_unchanged_by_checks':True,'executions':runs,'javascript':javascript,'apple_real_sdk_precheck':apple,'boundary':'Actual AVKit/WK bridge, managed audio and global keep-session policy; actual gallery begin/restore/finish, original visual-state/attachment acknowledgement; actual all-frame JavaScript. Explicit nominal framework/DOM and layout adapters on Linux; source controls remain single-owner. No device pixels, lock-screen scheduling or live YouTube transport tested here.','whole_app_sdk':'not_run','device':'pending'}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
