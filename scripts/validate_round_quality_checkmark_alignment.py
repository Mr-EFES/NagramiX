#!/usr/bin/env python3
"""Проверить общий центр галочки качества и сохранность остальных настроек."""
import argparse,json,subprocess,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from round_quality_compact_apple import check as apple_check
STAGE='round_quality_checkmark_alignment'
PAGE='submodules/SettingsUI/Sources/NagramiXRoundQualityController.swift'


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    plan=checked_plan(STAGE)
    assert set(plan['inputs'])=={PAGE} and len(plan['guards'])==6 and len(plan['templates'])==8
    assert plan['required_previous_stage']=='original_video_gallery' and not plan['copies'] and not plan['deletions']
    before=(OVERLAY/plan['previous'][PAGE]).read_text();after=(source/PAGE).read_text()
    button='private final class NagramiXRoundSegmentButton:'
    restored=after.replace(block(after,button),block(before,button),1)
    restored=restored.replace('singleLineLabels: qualityLayout','checkOnDetailLine: qualityLayout',1)
    assert restored==before,'Changes outside the segment button and its private initializer argument'
    for marker in ['    override func layoutSubviews()', '    override var isHighlighted:', '    func update(', '    @objc private func tapped()']:
        assert block(block(before,button),marker)==block(block(after,button),marker),'Selection/appearance/accessibility changed: '+marker
    body=block(after,button)
    assert 'self.checkView.centerYAnchor.constraint(equalTo: self.centerYAnchor)' in body
    assert 'self.checkView.centerYAnchor.constraint(equalTo: self.detailLabel.centerYAnchor)' not in body
    assert 'labels.trailingAnchor.constraint(equalTo: self.checkView.leadingAnchor, constant: -4)' in body
    assert 'self.checkView.trailingAnchor.constraint(equalTo: self.trailingAnchor, constant: -8)' in body
    assert 'label.numberOfLines = singleLineLabels ? 1 : 0' in body
    assert 'self.detailLabel.intrinsicContentSize.width) + 36' in body
    assert 'adjustsFontSizeToFitWidth' not in body and 'minimumScaleFactor' not in body
    parsed=subprocess.run([str(swiftc),'-frontend','-parse',str(source/PAGE)],capture_output=True,text=True,timeout=120)
    assert parsed.returncode==0,parsed.stdout+parsed.stderr
    return {'single_runtime_file':True,'other_page_sections_and_selection_callbacks_verbatim':True,'source_parse':'passed','layout':'Shared trailing checkmark centered on the entire button. Unselected alpha reserves the same gutter. One-line quality labels; intrinsic width plus actual36pt insets preserves the existing narrow-width vertical fallback without reducing fonts.','apple_api':apple_check(source,swiftc,folder/'apple'),'new_ui_runtime_tests_added':False,'full_application_sdk':'not_run','pixel_verification':'not_run','physical_iphone':'pending'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    initial=manifest(a.source);plan=checked_plan(STAGE)
    with tempfile.TemporaryDirectory(prefix='nagramix-round-checkmark-') as d:
        folder=Path(d);refused=guard_checks(a.source,STAGE,plan,folder/'guards');result=check(a.source,a.swiftc,folder/'api')
    assert manifest(a.source)==initial
    report={'stage':101,'name':STAGE,'verification_kind':'source_contract_swift_parse_and_existing_apple_api_probe','runtime_paths':[PAGE],'guards':6,'loader_refusals':len(refused),'checks':result,'source_unchanged_by_checks':True,'new_localization_keys':0,'new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
