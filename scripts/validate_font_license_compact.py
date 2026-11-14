#!/usr/bin/env python3
"""Компактные лицензии шрифтов: выбранный эскиз2, исходный полный legal text."""
import argparse,json,tempfile,hashlib
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from font_license_compact_apple import check as apple_check
import font_license_compact_runtime as runtime
from font_license_compact_modules import check as modules_check
STAGE='font_license_compact'

def contracts(source,plan):
 assert plan['required_previous_stage']=='settings_glass_sliders' and set(plan['inputs'])=={runtime.UI}
 assert len(plan['guards'])==12 and not plan['copies'] and not plan['deletions'] and not plan['native_inputs']
 before=(OVERLAY/plan['previous'][runtime.UI]).read_text();after=(source/runtime.UI).read_text();marker='private final class NagramiXFontLicensesController:'
 assert before[:before.index(marker)]==after[:after.index(marker)].replace('import ItemListUI\n','',1),'Font picker/preview/apply changed'
 old=block(before,marker);new=block(after,marker)
 for exact in ['self.text.isEditable = false; self.text.isSelectable = true','self.presentationDisposable.set(', 'transition: .immediate)', 'self.statusBar.statusBarStyle = presentation.theme.rootController.statusBarStyle.style','let offset = self.text.contentOffset','self.text.contentOffset = offset','self.text.overrideUserInterfaceStyle = presentation.theme.overallDarkAppearance ? .dark : .light']:
  assert exact in old and exact in new,exact
 assert 'presentation.listsFontSize.itemListBaseHeaderFontSize' in new
 assert 'import ItemListUI\n' in after and '"//submodules/ItemListUI:ItemListUI"' in (source/'submodules/SettingsUI/BUILD').read_text()
 assert 'public let itemBlocksSeparatorColor: UIColor' in (source/'submodules/TelegramPresentationData/Sources/PresentationTheme.swift').read_text()
 whisper=(source/'submodules/NagramiXTranscription/Sources/Preferences.swift').read_text()
 assert 'cell.textLabel?.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize); cell.selectionStyle = .none' in whisper
 for _,name in runtime.DOCUMENTS:
  path=runtime.RESOURCE+name
  assert hashlib.sha256((source/path).read_bytes()).hexdigest()==plan['guards'][path]
 for name,expected in plan['guards'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==expected,name


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
 plan=checked_plan(STAGE);assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 contracts(a.source,plan);state=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='font-license-compact-') as d:
  temp=Path(d);refused=guard_checks(a.source,STAGE,plan,temp/'guards');apple=apple_check(a.source,a.swiftc,temp/'apple');modules=modules_check(a.source,a.swiftc,temp/'modules')
  text=runtime.fixture(a.source);runs=execute(a.swiftc,temp,'font-license-compact',text)
  variants=[
   ('old-large-font','let base = presentation.listsFontSize.itemListBaseHeaderFontSize','let base = max(16, presentation.listsFontSize.itemListBaseFontSize)','actual controller uses Whisper Vosk body size'),
   ('lost-legal-paragraph','NagramiXFontLicenseLayout.paragraphs(document.text).enumerated()','NagramiXFontLicenseLayout.paragraphs(document.text).enumerated().dropLast()','every original legal word copyright and notice remains in order'),
   ('double-blank-lines','string: paragraph + "\\n", attributes:','string: paragraph + "\\n\\n", attributes:','paragraph spacing is not doubled by empty lines'),
   ('wrong-alignment','style.alignment = .left','style.alignment = .justified','license text wraps without justification or truncation'),
   ('divider-left-edge','let left = self.textContainerInset.left','let left: CGFloat = 0.0','divider edges align exactly with text padding'),
   ('expensive-scroll','self.needsSeparatorLayout || self.separatorLayoutSize != self.bounds.size','self.needsSeparatorLayout || self.bounds.width > 0.0','scrolling does not relayout the full long license'),
   ('wrong-app-theme','presentation.theme.overallDarkAppearance ? .dark : .light','presentation.theme.overallDarkAppearance ? .light : .dark',"reader follows the application's light or dark theme"),
   ('wrong-unicode-anchor','range: NSRange(location: result.length, length: 1)','range: NSRange(location: result.string.count, length: 1)','separator anchors track original UTF16 paragraph boundaries'),
  ]
  for name,old,new,why in variants:
   assert text.count(old)==1,(name,text.count(old));runs+=execute(a.swiftc,temp,name,text.replace(old,new,1),why)
  run([a.swiftc,'-frontend','-parse',a.source/runtime.UI])
 assert manifest(a.source)==state
 report={'stage':83,'name':STAGE,'inputs':1,'copies':0,'guards':12,'loader_refusals':len(refused),'executions':runs,'apple_api':apple,'actual_module_import':modules,'source_unchanged_by_checks':True,
 'approved_reference':'Second displayed font license concept, exec-adebfec3-ce8d-49ab-8b30-b1761186a374.png; SHA256 c310c581b55e051389d9806b78e2faa94202a664524b025377266a00b925d838. Concept asset remains outside Git.',
 'scope':'Only font-license reader: exact Whisper/Vosk header-size body (13pt at regular scale), compact scaled paragraphs, aligned natural wrapping, small headings, noninteractive TextKit-positioned hairlines in one shared scroll surface. Complete original four legal documents/copyright/notice, font picker/apply and theme/navigation subscriptions retained.',
 'boundaries':'Complete actual controller/document formatter/TextView subclass run with explicit Linux UIKit, attributed-run storage, TextKit glyph metrics and app host adapters. Real Foundation string/UTF16 processing and actual legal resources execute. Future first macOS gate uses genuine UIKit/TextKit/NSAttributedString/iOS15; Linux not_run. No full app or physical rendering claim.',
 'full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
