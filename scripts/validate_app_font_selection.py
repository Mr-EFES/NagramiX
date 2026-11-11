#!/usr/bin/env python3
"""Проверить выбор шрифтов, UIKit API, точные ресурсы и неизменность прежних функций."""
import argparse,hashlib,json,re,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from validate_app_language_localization import strings
import app_font_selection_runtime as runtime
from app_font_selection_apple import check as apple_check
from app_font_resources import validate_fonts
ROOT=Path(__file__).resolve().parents[1];STAGE='app_font_selection'

def source_contract(source,plan):
 assert plan['required_previous_stage']=='transcription_account_defaults'
 assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(source/n)==h,n
 for n,item in plan['copies'].items():assert digest(source/n)==item['sha256'],n
 assert len(plan['outputs'])==75 and len(plan['copies'])==27
 font=(source/runtime.FONT).read_text();before=(ROOT/'ios'/plan['previous'][runtime.FONT]).read_text()
 wrapper=block(font,'    public static func with(')
 native=block(font,'    private static func nagramiXNativeWith(')
 old=block(before,'    public static func with(')
 assert native[native.index('{'):]==old[old.index('{'):],'Native factory body changed'
 restored=font.replace(wrapper+'\n\n','',1).replace(native,old,1)
 for name in ['regular','medium','semibold','bold','light','semiboldItalic','mediumItalic','italic']:
  current=block(restored,'    public static func '+name+'(');original=block(before,'    public static func '+name+'(')
  lines=current.splitlines();assert 'NagramiXFontManager.font' in lines[1]
  assert '\n'.join([lines[0]]+lines[2:])==original,name
  restored=restored.replace(current,original,1)
 for name in ['monospace','semiboldMonospace','italicMonospace','semiboldItalicMonospace']:
  current=block(restored,'    public static func '+name+'(');original=block(before,'    public static func '+name+'(')
  assert original.splitlines()[1].strip() in current and 'withNativeFonts' in current
  restored=restored.replace(current,original,1)
 assert restored==before,'Unexpected font factory changes'
 model=(source/runtime.MODEL).read_text();manager=(source/runtime.MANAGER).read_text();ui=(source/runtime.UI).read_text()
 assert 'guard selection != nil || settings.enabled' in manager and 'method_getTypeEncoding' in manager and 'strcmp(firstEncoding, secondEncoding) == 0' in manager
 assert 'Thread.current.threadDictionary' in manager and 'defer {' in manager
 assert 'private static let initialized: Void' in manager and '.process, nil)' in manager
 assert 'URLSession' not in manager and 'UIDocumentPicker' not in ui
 for text in ['case camera','case monospace']:assert text in font
 for text in ['self.specimen.numberOfLines = 1','constant: 20','constant: -20','constant: 14','constant: -14','self.name.numberOfLines = 0','self.detail.numberOfLines = 0','isAccessibilityCategory','self.specimenWidth.isActive = !stacked','[.button, .selected]']:
  assert text in ui,text
 root=(source/'submodules/SettingsUI/Sources/NagramiXSettingsController.swift').read_text()
 for text in ['.fontsHeader: return 6000','.fontsEnabled: return 6001','.fontsOptions: return 6002','NagramiXFontSettings.current.enabled ? [.fontsOptions','NagramiXFontsController(context: context)','UIImage(systemName: "textformat")']:
  assert text in root,text
 assert 'case .fontsHeader, .fontsEnabled, .fontsOptions,' in block(root,'    var category:')
 presentation=(source/'submodules/TelegramPresentationData/Sources/PresentationData.swift').read_text()
 assert 'NagramiXFontManager.settingsSignal()' in presentation and 'theme: themeValue.withUpdated(chat: themeValue.chat)' in presentation
 assert 'init(enabled: Bool = true, fontId: String = "system")' in model
 loc=json.loads((ROOT/'ios/app_font_selection/localization.json').read_text());codes={x['code'] for x in json.loads((ROOT/'ios/app_language_localization/languages.json').read_text())['languages']}
 assert set(loc['translations'])==codes and len(loc['keys'])==12
 for code in codes:
  n='submodules/NagramiXCore/Resources/'+code+'.lproj/Localizable.strings'
  original=strings(ROOT/'ios'/plan['previous'][n]);actual=strings(source/n)
  assert actual=={**original,**dict(zip(loc['keys'],loc['translations'][code]))},code
 assert len(strings(source/'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings'))==647
 assets=json.loads((ROOT/'ios/app_font_selection/fonts.json').read_text());assert len(assets['fonts'])==20 and len(assets['licenses'])==4
 for item in assets['fonts']:
  path=source/'submodules/Display/Resources/NagramiXFonts'/item['file'];data=path.read_bytes()
  assert hashlib.sha256(data).hexdigest()==item['sha256'] and len(data)==item['bytes']
  assert data[:4] in [b'\x00\x01\x00\x00',b'OTTO']
 for name,h in assets['licenses'].items():
  data=(source/'submodules/Display/Resources/NagramiXFonts'/name).read_bytes();assert hashlib.sha256(data).hexdigest()==h
  assert b'Copyright' in data or b'Apache License' in data
 assert plan['native_inputs'][runtime.FONT]=='e53d8ae64da88e4b48b7c430496cd3d74d279ee0'
 # Concrete methods/labels of the native ownership boundary, never invented members.
 view=(source/'submodules/Display/Source/ViewController.swift').read_text();assert 'public func push(_ controller: ViewController)' in view
 assert 'public func withUpdated(chat: PresentationThemeChat)' in (source/'submodules/TelegramPresentationData/Sources/PresentationTheme.swift').read_text()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
 plan=checked_plan(STAGE);source_contract(a.source,plan);initial=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='app-font-selection-') as temporary:
  folder=Path(temporary);rejected=guard_checks(a.source,STAGE,plan,folder/'guards')
  code=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'font-selection',code)
  for name,mutated,label in runtime.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
  parsed=[n for n in [*plan['outputs'],*plan['copies']] if n.endswith('.swift')]
  for n in parsed:run([a.swiftc,'-frontend','-parse',a.source/n])
  apple=apple_check(a.source,a.swiftc,folder)
 assert manifest(a.source)==initial
 font_resources=validate_fonts(a.source,json.loads((ROOT/'ios/app_font_selection/fonts.json').read_text()))
 report={'stage':STAGE,'replacements':len(plan['outputs']),'guards':len(plan['guards']),'copies':len(plan['copies']),'font_faces':20,'font_resources':font_resources,'licenses':4,'languages':71,'keys_per_catalog':647,'loader_refusals':len(rejected),'executions':runs,'parsed_swift':len(parsed),'source_unchanged':True,'apple_uikit_precheck':apple,'apple_sdk_build':'not_run','device':'pending','boundary':'Actual complete Font factory, settings and resolver run with explicit UIKit/CoreText/resource adapters on Linux. Objective-C selector installation and UIKit rendering require Apple; the early Apple precheck compiles complete production bodies against real UIKit SDK before the native build. Real font bytes, names, licenses and glyphs are separately inspected; native full modules, live relayout and device pixels remain pending.'}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='executions'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
