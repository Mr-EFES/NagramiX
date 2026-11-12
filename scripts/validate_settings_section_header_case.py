#!/usr/bin/env python3
"""Проверить оформление заголовков категорий без изменения настроек и переводов."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import run
from settings_header_contract import SETTINGS,check

ROOT=Path(__file__).resolve().parents[1];STAGE='settings_section_header_case'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='wide_panel_consistency' and set(plan['inputs'])=={SETTINGS} and len(plan['guards'])==3
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
    current=(a.source/SETTINGS).read_text();before=(ROOT/'ios'/plan['previous'][SETTINGS]).read_text();restored=current
    expressions=['presentationData.strings.Settings_Appearance',*[f'presentationData.strings.nagramiXUILocalized("{key}")' for key in ['РАСШИФРОВКА ГОЛОСОВЫХ','ПЕРЕВОДЧИК','КАЧЕСТВЕННЫЕ КРУЖКИ']]]
    for expression in expressions:
        old='text: '+expression+'.uppercased(), sectionId: self.section)';new='text: '+expression+', sectionId: self.section)'
        assert restored.count(old)==1,expression;restored=restored.replace(old,new,1)
    assert restored==before,'Изменены другие строки, настройки, геометрия или обработчики'
    contract=check(current)
    # The old concrete regression must also be rejected by the shared lint.
    try:check(before)
    except ValueError as e:
        assert 'заголовок категории' in str(e)
    else:raise AssertionError('Прежнее оформление категории принято')
    initial=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='settings-section-header-case-') as d:
        refused=guard_checks(a.source,STAGE,plan,Path(d)/'guards')
        run([a.swiftc,'-frontend','-parse',a.source/SETTINGS])
    assert manifest(a.source)==initial
    report={'stage':STAGE,'inputs':1,'guards':3,'loader_refusals':len(refused),'contract':contract,'only_changes':'Четыре заголовка получают .uppercased() после локализации. Переводы, ключи, настройки, обработчики и оформление остального экрана побайтно прежние.','old_screenshot_regression_rejected':True,'source_files':len(initial),'swift_parse':1,'source_unchanged_by_checks':True,'whole_app_sdk':'not_run','device':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
