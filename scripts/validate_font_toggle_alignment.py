#!/usr/bin/env python3
"""Проверить единственное удаление icon-аргумента строки «Шрифты» и guarded source."""
import argparse,json,subprocess,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
STAGE='font_toggle_alignment'
SETTINGS='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    initial=manifest(a.source);plan=checked_plan(STAGE)
    assert set(plan['inputs'])=={SETTINGS} and len(plan['guards'])==6 and len(plan['templates'])==8
    assert plan['required_previous_stage']=='file_caption_edit' and not plan['copies'] and not plan['deletions']
    before=(OVERLAY/plan['previous'][SETTINGS]).read_text();after=(a.source/SETTINGS).read_text()
    removed='icon: nagramiXFontSettingsIcon(color: presentationData.theme.list.itemPrimaryTextColor), '
    assert before.count(removed)==1 and before.replace(removed,'',1)==after,'Only the font-row icon argument may change'
    with tempfile.TemporaryDirectory(prefix='nagramix-font-toggle-') as d:
        refused=guard_checks(a.source,STAGE,plan,Path(d)/'guards')
        parsed=subprocess.run([str(a.swiftc),'-frontend','-parse',str(a.source/SETTINGS)],capture_output=True,text=True,timeout=120)
        assert parsed.returncode==0,parsed.stdout+parsed.stderr
    assert manifest(a.source)==initial
    report={'stage':99,'name':STAGE,'verification_kind':'source_contract_and_swift_parse','runtime_paths':[SETTINGS],'guards':6,'loader_refusals':len(refused),'source_delta':'Удалён только icon-аргумент в fontsEnabled. Остальные байты Settings controller и общие switch/disclosure компоненты прежние.','layout_evidence':'Штатный ItemListSwitchItem использует icon=nil по умолчанию, общий Font.regular и leftInset16pt. У непустого icon добавлялись43pt; тот же leftInset задаёт начало разделителя. Подпись и разделитель теперь используют стандартный путь без icon.','new_localization_keys':0,'source_unchanged_by_checks':True,'ui_runtime_tests_added':False,'full_application_sdk':'not_run','pixel_verification':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
