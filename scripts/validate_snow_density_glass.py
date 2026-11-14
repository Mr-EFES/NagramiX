#!/usr/bin/env python3
"""Утверждённая геометрия строки плотности и прозрачный стеклянный бегунок."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from snow_density_glass_apple import check as apple_check
import snow_density_glass_runtime as runtime

STAGE='snow_density_glass'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
 plan=checked_plan(STAGE);assert plan['required_previous_stage']=='rich_file_padding' and set(plan['inputs'])=={runtime.ITEM}
 assert len(plan['guards'])==12 and not plan['copies'] and not plan['deletions'] and not plan['native_inputs']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 current=(a.source/runtime.ITEM).read_text();before=(OVERLAY/plan['previous'][runtime.ITEM]).read_text()
 for marker in ['    private func commitValue(', '    func asyncLayout(', '    @objc private func sliderValueChanged(']:
  original=block(before,marker)
  if 'commitValue(' in marker:original=original.replace('NagramiXSnowSettings.normalizedDensity(Int(sliderView.value.rounded()))','sliderView.density')
  assert block(current,marker)==original,marker
 switch=(a.source/runtime.SWITCH).read_text();assert 'var leftInset = 16.0 + params.leftInset' in switch and 'switchSize.width - 15.0' in switch
 theme=(a.source/'submodules/TelegramPresentationData/Sources/PresentationTheme.swift').read_text();assert 'public let overallDarkAppearance: Bool' in theme
 assert 'sliderView.minimumValue = 0.0' in current and 'sliderView.maximumValue = 90.0' in current
 assert 'PresentationResourcesItemList.knobImage(item.theme)' not in current
 assert 'UIGlassEffect(style: .clear)' in current and 'if #available(iOS 26.0, *)' in current
 state=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='snow-density-glass-') as d:
  temp=Path(d);refused=guard_checks(a.source,STAGE,plan,temp/'guards');apple=apple_check(a.source,a.swiftc,temp/'apple')
  text=runtime.fixture(a.source);runs=execute(a.swiftc,temp,'snow-density-glass',text)
  variants=[
   ('old-left-padding','self.left = leftInset + 16.0','self.left = leftInset + 24.0','density title shares native switch left edge'),
   ('old-right-padding','width - rightInset - 15.0','width - rightInset - 24.0','density value shares native switch right edge'),
   ('legacy-positive-minimum','sliderView.minimumValue = 0.0','sliderView.minimumValue = 10.0','zero-based legacy adapter retains correct positions'),
   ('thumb-overflow','static let thumbInset: CGFloat = thumbDiameter * 0.5 - 7.0','static let thumbInset: CGFloat = 0.0','minimum thumb stays within shared left edge'),
   ('opaque-thumb','format.opaque = false','format.opaque = true','native knob image is clear rather than white'),
   ('opaque-glass','alpha: 0.025','alpha: 1.0','glass center stays transparent in both themes'),
   ('drag-reset','if !self.isInteracting { sliderView.density = item.value }','if true { sliderView.density = item.value }','external layout cannot reset held slider'),
   ('wrong-voiceover-step','self.value + 5.0','self.value + 10.0','VoiceOver increment is five percent'),
   ('system-theme-leak','self.effectView?.overrideUserInterfaceStyle = isDark ? .dark : .light','self.effectView?.overrideUserInterfaceStyle = .unspecified','native glass follows the app theme'),
  ]
  for name,old,new,why in variants:
   assert text.count(old)==1,(name,text.count(old));runs+=execute(a.swiftc,temp,name,text.replace(old,new,1),why)
  run([a.swiftc,'-frontend','-parse',a.source/runtime.ITEM])
 assert manifest(a.source)==state
 report={'stage':STAGE,'inputs':1,'guards':12,'loader_refusals':len(refused),'executions':runs,'apple_api':apple,'source_unchanged_by_checks':True,
  'root_cause':'Density used 24pt side insets instead of native switch 16pt left/15pt right. Opaque standard knob. Positive-minimum Legacy expression also shifts native thumb geometry.',
  'change':'Shared content bounds, 28pt clear native iOS26+ glass/transparent fallback, rim/sheen; glass stays on original Legacy knob view, does not intercept touches. Local 0...90 adapter exposes/stores 10...100 with original step/commit/holiday policy. Full-width track and safe thumb endpoints.',
  'boundaries':'Complete actual node/geometry/glass/control/normalizer execute with explicit UIKit/Legacy dispatch/List/theme/text measurement adapters. Real Legacy positive-minimum geometry expression executes. Apple preflight typechecks entire actual node/classes against original ObjC header and real UIKit at iOS15 on macOS; Linux not_run. Physical pixels/gesture competition pending.',
  'full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
