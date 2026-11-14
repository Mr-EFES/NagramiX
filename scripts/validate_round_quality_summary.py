#!/usr/bin/env python3
"""Проверить пятую кнопку кружка, текущие параметры и точный экспорт."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import round_quality_summary_runtime as runtime
from round_quality_summary_apple import check as apple_check
STAGE='round_quality_summary'

def contracts(source,plan):
 assert plan['required_previous_stage']=='translation_account_defaults' and len(plan['inputs'])==76 and len(plan['guards'])==13 and set(plan['copies'])=={runtime.N}
 assert not plan['deletions'] and not plan['native_inputs']
 before=lambda n:(OVERLAY/plan['previous'][n]).read_text()
 after=lambda n:(source/n).read_text()
 q=after(runtime.Q);a='    private func nagramiXPresentRoundQuality()';b=block(q,a);assert 'self.captureCurrentValues()' in b and 'self.saveCurrentItemEdits()' in b
 assert all(gate in b for gate in ['self.activeTool == nil','!self.isSending','!self.isInvalidated','!controller.isDismissing','self.endCaptionEditing()'])
 old=before(runtime.Q);expected=old.replace('''        guard self.showsQualityTab, !self.nagramiXIsRoundVideo else {
            return
        }
        if self.subject.isVideo {''','''        guard self.showsQualityTab else { return }
        if self.nagramiXIsRoundVideo {
            self.nagramiXPresentRoundQuality()
            return
        }
        if self.subject.isVideo {''',1)
 assert q==expected.replace('    private func openQuality() {',b+'\n\n    private func openQuality() {',1),'Unrelated photo/video quality code changed'
 current=after(runtime.G);capture=block(current,'    func captureCurrentValues()');assert 'chatMediaEditorRoundVideoValues(self.mediaEditor.values, settings: .current)' in capture
 old=before(runtime.G);assert current==old.replace(block(old,'    func captureCurrentValues()'),capture,1),'Unrelated gallery/send/selection changed'
 toolbar=block(after(runtime.S),'        private func updateToolbar(');assert 'chatMediaEditorRoundVideoValues(self.mediaEditor.values, settings: .current)' in toolbar and 'chatMediaEditorVideoFileDimensions(values: self.mediaEditor.values' in toolbar
 old=before(runtime.S);assert after(runtime.S)==old.replace(block(old,'        private func updateToolbar('),toolbar,1),'Unrelated main editor behavior changed'
 assert after(runtime.T)==before(runtime.T).replace('isDisabled: disabledTabs.contains(tab) || (roundVideoSelected && tab == .qualityTab)','isDisabled: isVideo && roundVideoSelected && tab == .qualityTab ? false : disabledTabs.contains(tab)',1),'Other tabs or controls changed'
 assert after(runtime.V)==before(runtime.V).replace('// Capture export settings once for this editor item; deferred export uses its JSON snapshot.','// Resolve settings in the live editor; prepared/deferred exports retain their JSON snapshot.',1).replace(block(before(runtime.V),'func chatMediaEditorRoundVideoValues('),block(after(runtime.V),'func chatMediaEditorRoundVideoValues('),1),'Crop/toggle/camera code changed'
 # Native encoding and deferred JSON resources are frozen guards, not new reads of shared settings.
 assert 'NagramiXRoundVideoSettings.current' not in (source/runtime.old.VALUES).read_text()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 contracts(a.source,plan);state=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='round-quality-summary-') as d:
  root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');apple=apple_check(a.source,a.swiftc,root/'apple')
  domain=runtime.fixture(a.source);ui=runtime.ui_fixture(a.source);route=runtime.route_fixture(a.source);runs=execute(a.swiftc,root,'round-quality-values',domain)+execute(a.swiftc,root,'round-quality-sheet',ui)+execute(a.swiftc,root,'round-quality-route',route)
  # Existing helper and export fixtures use exit91 diagnostics; convert just the assertion adapter exit code for mutant expectations.
  domain=domain.replace('exit(91)','exit(96)')
  variants=[
   ('stale-profile',domain,'guard values.qualityPreset == .videoMessage else','guard values.qualityPreset == .videoMessage, values.nagramiXRoundTuning == nil else','live editor takes all four current settings'),
   ('off-leaks-custom',domain,': nil\n    guard values.nagramiXRoundTuning',': values.nagramiXRoundTuning\n    guard values.nagramiXRoundTuning','OFF clears previous custom tuning in live editor'),
   ('lost-bitrate',domain,'settings.codec.rawValue, settings.bitRate','settings.codec.rawValue, 1_000_000','live editor takes all four current settings'),
   ('summary-wrong-fps',domain,'"\\(tuning[1]) кадров/с"','"30 кадров/с"','summary uses selected FPS'),
   ('dismiss-twice',ui,'guard let sheet, !finished else','guard let sheet, (finished || !finished) else','close commits dismissal exactly once'),
   ('text-overlap',ui,'contentWidth - 16 - titleWidth','contentWidth + 20','key and value columns never overlap'),
   ('round-button-disabled',route,'isVideo && roundVideoSelected && tab == .qualityTab ? false','isVideo && roundVideoSelected && tab == .qualityTab ? true','round quality control enabled for inspection'),
   ('missing-glass',ui,'var nagramiXUsesFloatingGlass: Bool { true }','var nagramiXUsesFloatingGlass: Bool { false }','all summary nodes opt into shared native glass'),
  ]
  for name,text,old,new,why in variants:
   assert text.count(old)==1,(name,text.count(old));runs+=execute(a.swiftc,root,name,text.replace(old,new,1),why)
  for path in [n for n in plan['inputs'] if n.endswith('.swift')]+list(plan['copies']):run([a.swiftc,'-frontend','-parse',a.source/path])
 assert manifest(a.source)==state
 report={'stage':86,'name':STAGE,'inputs':76,'swift_inputs':5,'localized_resources':71,'new_helpers':1,'new_localization_keys':5,'guards':13,'loader_refusals':len(refused),'executions':runs,'apple_api':apple,'source_unchanged_by_checks':True,'scope':'Пятая кнопка доступна только как сводка круглого видео. Live editor/capture разрешают текущие four settings; OFF убирает custom tuning. Prepared deferred exports/кодеки/камера/звук/обычные фото и видео/выбор не изменены. Все5полей сводки соответствуют snapshot экспорта; read-only native glass sheet с X, RTL, переносами, темой и доступностью.','boundaries':'Actual constructor/copy/helper/recommended export/JSON and complete actual rows/factory/item/node execute. Telegram graph, encoded writer, presentation/strings/UIKit/Texture are explicit adapters. Apple genuine UIKit gate mandatory in future preflight, locally not_run.','full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
