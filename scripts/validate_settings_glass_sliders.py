#!/usr/bin/env python3
"""Общее стеклянное оформление всех NagramiX settings sliders без изменения значений."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from settings_glass_sliders_apple import check as apple_check
import settings_glass_sliders_runtime as runtime
STAGE='settings_glass_sliders'

def contracts(source,plan):
 assert plan['required_previous_stage']=='snow_density_glass' and set(plan['inputs'])=={runtime.S,runtime.P,runtime.R,runtime.A,runtime.T}
 assert set(plan['copies'])=={runtime.C,runtime.L} and len(plan['guards'])==11 and not plan['deletions'] and not plan['native_inputs']
 markers={runtime.S:['    private func commitValue(', '    func asyncLayout(', '    @objc private func sliderValueChanged('],runtime.P:['    private func commitValue(', '    func asyncLayout(', '    @objc private func sliderValueChanged('],runtime.R:['    func update(', '    @objc private func valueChanged(', '    @objc private func sliderTrackingEnded(', '    @objc private func sliderTapped('],runtime.A:['    @objc private func temperatureChanged(', '    @objc private func saveCredential('],runtime.T:['    @objc private func temperatureMoved(', '    private func renderTemperature(']}
 for path,items in markers.items():
  current=(source/path).read_text();before=(OVERLAY/plan['previous'][path]).read_text()
  for marker in items:assert block(current,marker)==block(before,marker),(path,marker)
 # All differences in the native consumer controllers are limited to decoration.
 for path in [runtime.R,runtime.A,runtime.T]:
  before=(OVERLAY/plan['previous'][path]).read_text();after=(source/path).read_text()
  if path==runtime.R:
   before=before.replace('private let slider = UISlider()','private let slider = NagramiXGlassSlider(frame: .zero)').replace('        self.slider.minimumTrackTintColor = presentationData.theme.list.itemAccentColor\n        self.slider.maximumTrackTintColor = presentationData.theme.list.itemSecondaryTextColor.withAlphaComponent(0.25)','        self.slider.updateAppearance(isDark: presentationData.theme.overallDarkAppearance, background: presentationData.theme.list.itemSecondaryTextColor.withAlphaComponent(0.25), foreground: presentationData.theme.list.itemAccentColor)')
  elif path==runtime.A:
   before=before.replace('let slider = UISlider(); slider.minimumValue = 0; slider.maximumValue = 1; slider.value = Float(self.selectedTemperature); slider.tintColor = self.presentationData.theme.list.itemAccentColor','let slider = NagramiXGlassSlider(frame: .zero); slider.minimumValue = 0; slider.maximumValue = 1; slider.value = Float(self.selectedTemperature)\n            slider.updateAppearance(isDark: self.presentationData.theme.overallDarkAppearance, background: self.presentationData.theme.list.itemSwitchColors.frameColor, foreground: self.presentationData.theme.list.itemAccentColor)')
  else:
   before=before.replace('let slider = UISlider()','let slider = NagramiXGlassSlider(frame: .zero)').replace('        slider.tintColor = self.presentationData.theme.list.itemAccentColor','        slider.updateAppearance(isDark: self.presentationData.theme.overallDarkAppearance, background: self.presentationData.theme.list.itemSwitchColors.frameColor, foreground: self.presentationData.theme.list.itemAccentColor)')
  assert before==after,'Consumer logic drift: '+path
 # No additional local settings slider can silently retain the old white knob.
 settings=(source/'submodules/SettingsUI/Sources/NagramiXSettingsController.swift').read_text()
 for case in ['inputEffectsParameter','photoQuality','stickerSize']:
  assert 'case let .'+case in settings
 assert (source/runtime.P).read_text().count('NagramiXLegacyGlassSliderView')==1
 for module in ['SettingsUI','TranslateUI','NagramiXTranscription','NagramiXCore']:
  for path in (source/'submodules'/module/'Sources').glob('NagramiX*.swift'):
   if path.name=='NagramiXGlassSlider.swift':continue
   assert 'UISlider()' not in path.read_text(),'Unstyled NagramiX slider: '+str(path)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
 plan=checked_plan(STAGE);assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 contracts(a.source,plan);state=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='settings-glass-sliders-') as d:
  temp=Path(d);refused=guard_checks(a.source,STAGE,plan,temp/'guards');apple=apple_check(a.source,a.swiftc,temp/'apple')
  text=runtime.fixture(a.source);runs=execute(a.swiftc,temp,'settings-glass-sliders',text)
  variants=[
   ('opaque-image','format.opaque = false','format.opaque = true','all native thumb states use the clear twenty-eight point image'),
   ('system-theme','self.effectView?.overrideUserInterfaceStyle = isDark ? .dark : .light','self.effectView?.overrideUserInterfaceStyle = .unspecified','glass uses application theme'),
   ('short-hit-area','height: max(44.0, size.height)','height: size.height','native controls keep a forty-four point height'),
   ('wrong-rtl','let isRTL = self.effectiveUserInterfaceLayoutDirection == .rightToLeft','let isRTL = self.effectiveUserInterfaceLayoutDirection == .leftToRight','right-to-left track fills from the correct edge'),
   ('lost-disabled-style','decoration.alpha = self.isEnabled ? 1.0 : 0.35','decoration.alpha = 1.0','disabled decoration remains disabled and dim'),
   ('percentage-reset','if !self.isInteracting { sliderView.value = CGFloat(item.value) }','if true { sliderView.value = CGFloat(item.value) }','held percentage is not reset or saved by layout'),
   ('wrong-temp-step','sender.value = (sender.value * 10).rounded() / 10','sender.value = (sender.value * 5).rounded() / 5','transcription retains tenths and current draft'),
  ]
  for name,old,new,why in variants:
   count=2 if name=='wrong-temp-step' else 1
   assert text.count(old)==count,(name,text.count(old));runs+=execute(a.swiftc,temp,name,text.replace(old,new),why)
  for path in [*plan['inputs'],*plan['copies']]:run([a.swiftc,'-frontend','-parse',a.source/path])
 assert manifest(a.source)==state
 report={'stage':82,'name':STAGE,'inputs':5,'copies':2,'guards':11,'loader_refusals':len(refused),'executions':runs,'apple_api':apple,'source_unchanged_by_checks':True,'consumer_handlers_and_saving_preserved':True,
 'scope':'Shared clear glass thumb and geometry in NagramiXCore; native UISlider adapter for round bitrate/ASR temperature/translation temperature; shared Legacy decoration for snow/percentage rows (photo quality, sticker size, typing effect parameters). Existing ranges, normalization, drag/commit handlers, saved settings and model eligibility preserved.',
 'boundaries':'Actual full controls/nodes/bitrate cell and ASR+translation temperature methods compile and execute with explicit Linux UIKit/List/theme/model/AutoLayout boundaries; native UISlider geometry is modeled. Future first Apple gate builds the real public Core module and all actual consumer bodies with real UIKit+iOS15+Legacy header. No app or physical iPhone verification locally.',
 'full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
