#!/usr/bin/env python3
"""Единые floating glass меню DNS/эффекта/скачивания, без download footer."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from unified_glass_menus_apple import check as apple_check,modules_check
import unified_glass_menus_runtime as runtime
STAGE='unified_glass_menus'

def contracts(source,plan):
 assert plan['required_previous_stage']=='font_license_compact' and set(plan['inputs'])=={runtime.O,runtime.S,runtime.P,runtime.G,runtime.N}
 assert len(plan['guards'])==11 and not plan['copies'] and not plan['deletions'] and not plan['native_inputs']
 current=lambda name:(source/name).read_text()
 before=lambda name:(OVERLAY/plan['previous'][name]).read_text()
 s=before(runtime.S).replace('footnote: "", bottomAttached: true, selected:','footnote: "", floatingGlass: true, selected:',1).replace('selectedId: current.mode.rawValue, footnote: presentationData.strings.nagramiXDownloadModeFootnote, bottomAttached: true, selected:','selectedId: current.mode == .maximum ? NagramiXDownloadAcceleration.maximum.rawValue : NagramiXDownloadAcceleration.medium.rawValue, footnote: "", floatingGlass: true, selected:',1)
 assert s==current(runtime.S),'Only the two specified parameter menu calls may change in settings'
 p=before(runtime.P);q=current(runtime.P);start='    selectDnsImpl = {';end='    selectTimeoutImpl = {'
 assert p[:p.index(start)]==q[:q.index(start)] and p[p.index(end):]==q[q.index(end):],'Unrelated proxy/network/custom-editor logic changed'
 n=before(runtime.N);added='''        if !self.allowInputInset, !self.nagramiXUsesBottomAttachedLayout, self.itemGroupsContainerNode.groupNodes.count == 1, self.itemGroupsContainerNode.groupNodes[0].nagramiXFloatingGlass {
            return UIEdgeInsets(top: containerInsets.top, left: 16.0, bottom: 18.0, right: 16.0)
        }
''';assert current(runtime.N)==n.replace('        return self.nagramiXUsesBottomAttachedLayout ?',added+'        return self.nagramiXUsesBottomAttachedLayout ?',1),'Native presentation/gesture code changed beyond opt-in margins'
 assert 'footnote: "", floatingGlass: true' in block(q,start)
 assert 'nagramiXDownloadModeFootnote' not in block(current(runtime.S),'        openDownloadAccelerationMode: {')
 assert 'func nagramiXOptionSheet(' in current(runtime.O) and 'floatingGlass: Bool = false' in current(runtime.O)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 contracts(a.source,plan);state=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='unified-glass-menus-') as d:
  temp=Path(d);refused=guard_checks(a.source,STAGE,plan,temp/'guards');modules=modules_check(a.source,a.swiftc,temp/'modules');apple=apple_check(a.source,a.swiftc,temp/'apple');text=runtime.fixture(a.source);runs=execute(a.swiftc,temp,'unified-glass-menus',text)
  variants=[
   ('download-footer-returns','footnote: "", floatingGlass: true, selected: { id in\n                guard let mode','footnote: "Annotation", floatingGlass: true, selected: { id in\n                guard let mode','download contains exactly header and two options without footer'),
   ('duplicate-commit','guard let controller, !finished else { return }\n            finished = true','guard let controller else { return }\n            finished = true','download choice commits and dismisses exactly once'),
   ('lost-custom-route','if provider == .customDoh && current.customDohUrl.isEmpty','if provider == .customDoh && !current.customDohUrl.isEmpty','empty custom DoH opens existing editor once without premature provider write'),
   ('lost-opt-in','return !self.itemNodes.isEmpty && self.itemNodes.allSatisfy','return self.itemNodes.isEmpty && self.itemNodes.allSatisfy','native glass styling is opt-in and preserves default corners'),
   ('floating-margins','left: 16.0, bottom: 18.0, right: 16.0','left: 10.0, bottom: 10.0, right: 10.0','floating menus share native safe margins without changing other sheets'),
   ('lost-theme','self.backgroundEffectView.overrideUserInterfaceStyle = self.theme.backgroundType == .light ? .light : .dark','self.backgroundEffectView.overrideUserInterfaceStyle = self.theme.backgroundType == .light ? .dark : .light','glass uses application theme rather than phone theme'),
  ]
  for name,old,new,why in variants:
   assert text.count(old)==1,(name,text.count(old));runs+=execute(a.swiftc,temp,name,text.replace(old,new,1),why)
  for path in plan['inputs']:run([a.swiftc,'-frontend','-parse',a.source/path])
 assert manifest(a.source)==state
 report={'stage':84,'name':STAGE,'inputs':5,'guards':11,'loader_refusals':len(refused),'executions':runs,'actual_module_import':modules,'apple_api':apple,'source_unchanged_by_checks':True,
 'request':'Выбран второй floating glass эскиз, download footer и его отступ/линия удалены. Только Среднее/Максимум и две исходные подписи.',
 'scope':'Shared option factory flags default false; only DNS, typing effect and download callers opt in. Native Display marker protocol gates shared glass material/rim/corners and safe margins. Existing dismissal/scroll/animations/key handling preserved. All providers/presets/persisted IDs and enabled rechecks remain. Custom DoH editor routing retained. No dependencies, UI strings or resources added.',
 'boundaries':'Complete actual factory/node/native group and all caller closures execute against explicit UIKit/Texture/measurement/presentation/settings host adapters. Genuine public marker export/import compiles across Swift modules. Future first macOS/iOS15 gate compiles complete UI/group against real UIKit/UIGlassEffect/symbol palettes with app/Texture adapters. No full app or phone pixels locally.',
 'full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
