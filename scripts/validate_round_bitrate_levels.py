#!/usr/bin/env python3
"""Четыре уровня кружков: UI, сохранение, старые snapshot и фактический экспорт."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import round_bitrate_levels_runtime as runtime
from round_bitrate_levels_apple import check as apple_check
STAGE='round_bitrate_levels'

def contracts(source,plan):
    assert plan['required_previous_stage']=='font_apply_glass' and len(plan['inputs'])==76 and len(plan['guards'])==12 and not plan['copies'] and not plan['deletions']
    assert (source/runtime.M).read_bytes()==(source/runtime.C).read_bytes(),'capture and editor must share identical limits'
    before=lambda n:(OVERLAY/plan['previous'][n]).read_text()
    after=lambda n:(source/n).read_text()
    model=after(runtime.M);addition=block(model,'    public enum BitRateLevel:')+'\n'+block(model,'    public var bitRateLevel:')+'\n\n'
    assert model==before(runtime.M).replace('case .maximum: return 1_500_000','case .maximum: return 1_300_000',1).replace('maximumBitRate = 2_000_000','maximumBitRate = 1_300_000',1).replace('    public var enabled: Bool',addition+'    public var enabled: Bool',1),'unrelated settings behavior changed'
    u=after(runtime.U);old=before(runtime.U);helper=block(u,'func nagramiXRoundQualitySubtitle(')
    expected=old.replace(block(old,'private func nagramiXRoundBitRateText(')+'\n\n','',1).replace(block(old,'private final class NagramiXRoundBitRateCell:'),helper+'\n\n'+block(u,'private final class NagramiXRoundBitRateCell:'),1)
    oldline=next(l for l in expected.splitlines() if 'nagramiXRoundBitRateText(value.bitRate' in l)
    newline=next(l for l in u.splitlines() if 'cell.detailTextLabel?.text = nagramiXRoundQualitySubtitle(' in l)
    assert u==expected.replace(oldline,newline,1),'unrelated quality selection/cinematic/save behavior changed'
    core=after(runtime.G);a=core.index('    /// Opt-in for discrete controls.');b=core.index('    private let glassThumbView',a)
    assert core[:a]+core[b:]==before(runtime.G),'shared glass appearance or other slider semantics changed'
    v=after(runtime.V);a=next(l for l in before(runtime.V).splitlines() if 'let rate = tuning.count == 4' in l);b='        // Accept older deferred snapshots while enforcing the current round-video ceiling.\n'+next(l for l in v.splitlines() if 'let rate = min(1_300_000,' in l)
    assert v==before(runtime.V).replace(a,b,1),'unrelated media export changed'
    from validate_app_language_localization import strings
    for n in plan['inputs']:
        if n.endswith('.strings'):
            old=strings(OVERLAY/plan['previous'][n]);new=strings(source/n)
            assert len(new)==len(old)+5 and all(new[k]==value for k,value in old.items()),n
    return {'camera_model_matches':True,'only_requested_runtime_behavior_changed':True,'old_catalog_keys_preserved':True,'native_sender_guards_unchanged':True}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    contract=contracts(a.source,plan);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='round-bitrate-levels-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');apple=apple_check(a.source,a.swiftc,root/'apple')
        domain=runtime.fixture(a.source);ui=runtime.ui_fixture(a.source)
        runs=execute(a.swiftc,root,'round-bitrate-model-export',domain)+execute(a.swiftc,root,'round-bitrate-control',ui)
        # These semantic regressions must be caught by behavior, not accepted
        # because a UI label or model constant looks correct.
        for name,code,old,new,why in [
            ('uncapped-prepared-job',domain,'let rate = min(1_300_000, tuning.count','let rate = min(2_000_000, tuning.count','legacy prepared job cannot exceed new ceiling'),
            ('wrong-ceiling',domain,'maximumBitRate = 1_300_000','maximumBitRate = 2_000_000','extreme and legacy values stay on four levels'),
            ('stuck-voiceover',ui,'self.adjustAccessibilityValue(by: step)','self.adjustAccessibilityValue(by: step * 0.1)','VoiceOver increments exactly one step'),
            ('wrong-visible-stop',ui,'let step = Int(min(3, max(0, self.slider.value.rounded())))','let step = Int(min(2, max(0, self.slider.value.rounded())))','VoiceOver increments exactly one step')]:
            assert old in code
            negative=code.replace(old,new,1).replace('exit(91)','exit(96)')
            runs+=execute(a.swiftc,root,name,negative,why)
        for n in plan['inputs']:
            if n.endswith('.swift'):run([a.swiftc,'-frontend','-parse',a.source/n])
    assert before==manifest(a.source)
    report={'stage':88,'name':STAGE,'contracts':contract,'loader_refusals':len(refused),'executions':runs,'apple_api':apple,'boundaries':'Actual models, immutable editor/copy, export branch and localization use real Foundation. Full actual glass control and bitrate cell execute with explicit UIKit/AutoLayout/presentation/target-dispatch adapters; layout rendering is not simulated. Apple probe uses actual UIKit with real public modules before future app compilation.','source_unchanged_by_checks':True,'full_application_sdk':'not_run','physical_iphone':'pending','server_round_message_verification':'not_run'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
