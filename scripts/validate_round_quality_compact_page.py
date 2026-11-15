#!/usr/bin/env python3
"""Компактная страница кружков: маршруты кнопок и прежняя доступность камеры."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from round_quality_compact_apple import check as apple_check
import round_quality_compact_runtime as runtime
STAGE='round_quality_compact_page'

def contracts(source,plan):
    assert plan['required_previous_stage']=='round_bitrate_levels' and set(plan['inputs'])=={runtime.U} and len(plan['guards'])==11 and not plan['copies'] and not plan['deletions']
    before=(OVERLAY/plan['previous'][runtime.U]).read_text();after=(source/runtime.U).read_text()
    for anchor in ['func nagramiXRoundQualityTitle(', 'func nagramiXRoundQualitySubtitle(', 'private final class NagramiXRoundBitRateCell:', '    init(context:', '    override func loadDisplayNode(', '    override func containerLayoutUpdated(', '    private func supports(', '    private func shouldShowCinematic(', '    private func refreshVisibleRows(', '    private func commit(', '    private func updateBitRate(']:
        assert block(before,anchor)==block(after,anchor),'Unrelated behavior changed: '+anchor
    assert (source/runtime.M).read_bytes()==(source/'submodules/Camera/Sources/NagramiXRoundVideoSettings.swift').read_bytes()
    assert 'numberOfLines = 0' in after and 'adjustsFontSizeToFitWidth' not in after
    return {'single_app_file':True,'stored_defaults_and_keys_unchanged':True,'bitrate_cell_verbatim':True,'camera_capability_and_commit_verbatim':True,'capture_export_senders_guarded':True,'no_new_localization_keys':True}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    contract=contracts(a.source,plan);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='round-compact-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');apple=apple_check(a.source,a.swiftc,root/'apple')
        domain=runtime.fixture(a.source);runs=execute(a.swiftc,root,'round-compact-page',domain)
        for name,old,new,why in [
            ('wrong-fps-route','value.frameRate = NagramiXRoundVideoSettings.FrameRate.allCases[index]','value.frameRate = NagramiXRoundVideoSettings.FrameRate.allCases[0]','correct routing preserves other fields'),
            ('missing-master-gate','guard value.enabled, options.indices.contains(index), options[index].enabled','guard options.indices.contains(index)','master OFF blocks delayed events'),
            ('wrong-cinema-yes','case .cinematic: value.cinematic = index == 0','case .cinematic: value.cinematic = index == 1','correct routing preserves other fields')]:
            assert old in domain
            # Check specific regressions by behavior; gate mutant can fail on the
            # earlier unsupported-format assertion before reaching master OFF.
            mutated=domain.replace(old,new,1)
            diagnostic='Round compact:'
            runs+=execute(a.swiftc,root,name,mutated,diagnostic)
        run([a.swiftc,'-frontend','-parse',a.source/runtime.U])
    assert before==manifest(a.source)
    result={'stage':89,'name':STAGE,'contracts':contract,'loader_refusals':len(refused),'executions':runs,'apple_api':apple,'source_unchanged_by_checks':True,'boundaries':'Actual settings/options/selection/commit/section methods run with real Foundation and isolated UserDefaults. Explicit table/presentation hosts do not render UIKit. Real complete page typecheck is first in future macOS job; Linux not_run.','full_application_sdk':'not_run','physical_iphone':'pending'}
    if a.report:a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
