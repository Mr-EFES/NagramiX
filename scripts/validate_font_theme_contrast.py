#!/usr/bin/env python3
"""Проверить цвета шрифтов, фактические native типы и UIKit API до SDK."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import execute,run
from app_font_selection_apple import check as apple_check,navigation_check,access_check
from font_theme_contrast_apple import icon_check,member_check,SETTINGS
import font_theme_contrast_runtime as runtime

ROOT=Path(__file__).resolve().parents[1];STAGE='font_theme_contrast'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert plan['required_previous_stage']=='wide_channel_post_consistency'
 assert set(plan['inputs'])=={runtime.UI,SETTINGS} and len(plan['guards'])==11 and not plan['copies'] and not plan['deletions']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
 before={n:(ROOT/'ios'/plan['previous'][n]).read_text() for n in plan['inputs']}
 ui=(a.source/runtime.UI).read_text();settings=(a.source/SETTINGS).read_text()
 for line in ['        self.statusBar.statusBarStyle = self.presentation.theme.rootController.statusBarStyle.style\n','        self.statusBar.statusBarStyle = presentation.theme.rootController.statusBarStyle.style\n']:
  assert ui.count(line)==1;ui=ui.replace(line,'',1)
 assert ui==before[runtime.UI],'Unrelated changes in fonts, layout or strings'
 helper=block(settings,'private func nagramiXFontSettingsIcon(')+'\n\n'
 restored=settings.replace(helper,'',1).replace('nagramiXFontSettingsIcon(color: presentationData.theme.list.itemPrimaryTextColor)','UIImage(systemName: "textformat")?.withTintColor(presentationData.theme.list.itemAccentColor, renderingMode: .alwaysOriginal)',1)
 assert restored==before[SETTINGS],'Unrelated settings, defaults or preference changes'
 # Both existing initialization and current presentation updates reach refresh.
 original=before[runtime.UI]
 assert 'self.presentation = value' in original and 'self.refresh()' in original and 'deliverOnMainQueue' in original
 initial=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='font-theme-contrast-') as temporary:
  folder=Path(temporary);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
  text=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'font-theme',text)
  for name,mutated,why in runtime.negatives(text):runs+=execute(a.swiftc,folder,name,mutated,why)
  navigation=navigation_check(a.source,a.swiftc,folder);access=access_check(a.source,a.swiftc,folder)
  apple=apple_check(a.source,a.swiftc,folder);icon=icon_check(a.source,a.swiftc,folder)
  members=member_check(a.source,a.swiftc,folder)
  for n in plan['inputs']:run([a.swiftc,'-frontend','-parse',a.source/n])
 assert manifest(a.source)==initial
 report={'stage':STAGE,'inputs':2,'guards':11,'loader_refusals':len(refused),'source_files':len(initial),'source_unchanged_by_checks':True,'executions':runs,'native_navigation_contract':navigation,'public_override_contract':access,'apple_uikit_precheck':apple,'icon_real_uikit_precheck':icon,'boundary':'Actual native status enum cases and theme style mapping; actual font-screen assignments and actual settings icon expression/helper. UIImage/renderer are explicit call-recording adapters on Linux, no glyph pixels or ASImageNode renderer simulation. Complete actual font UI plus icon helper typechecked against real UIKit on Apple.','whole_app_sdk':'not_run','device':'pending'}
 report['actual_adapter_member_probe']=members
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
