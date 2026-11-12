#!/usr/bin/env python3
"""Проверить быстрый путь сборки и явный запуск широких исторических тестов."""
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def check(text):
    assert text.index('uses: actions/setup-node@v4') < text.index('python3 scripts/validate_release_095_apple_preflight.py')
    start=text.index('      - name: Применить overlay NagramiX\n')
    assert re.search(r'^          python3 scripts/validate_release_095_apple_preflight\.py --swiftc ',text[:start],re.M), 'Complete fixture preflight must run before overlay'
    assert re.search(r'^          python3 scripts/validate_native_string_references\.py --canonical --swiftc ',text[:start],re.M), 'Native generated strings SDK check must run before overlay'
    assert re.search(r'^          python3 scripts/validate_premium_temporary_transcription_native_api\.py --source Telegram-iOS ',text[:start],re.M), 'Actual native file ASR API probe must run before overlay'
    end=text.index('      - name: Восстановить кеш Bazel\n',start)
    source=text[start:end]
    option=re.search(r'^      extended_patch_tests:\n(.*?)(?=^      \w+:)',text,re.M|re.S).group(1)
    assert 'type: boolean' in option and 'default: false' in option
    assert 'NAGRAMIX_EXTENDED_PATCH_TESTS: ${{ inputs.extended_patch_tests }}' in source
    begin=source.index('          # BEGIN optional historical regressions\n')
    finish=source.index('          # END optional historical regressions\n',begin)+len('          # END optional historical regressions\n')
    helper='\n'.join(line[10:] for line in source[begin:finish].splitlines())+'\n'
    mandatory=['validate_late_source_stages.py','validate_custom_member_references.py','validate_upstream_13_2_release.py','validate_localization_standard.py','validate_release_092_settings_compile.py','validate_round_native_playback.py','validate_poll_copy_transport.py','validate_release_095_fonts_compile.py','validate_release_095_composer_strings_compile.py']
    mandatory.append('validate_wide_channel_post_consistency.py')
    mandatory.append('validate_font_theme_contrast.py')
    mandatory.append('validate_system_web_picture_in_picture.py')
    mandatory.append('validate_wide_panel_consistency.py')
    mandatory.append('validate_settings_section_header_case.py')
    mandatory.append('validate_premium_temporary_transcription.py')
    mandatory.append('validate_font_preview_apply.py')
    mandatory.append('validate_edit_result_consistency.py')
    mandatory.append('validate_youtube_playback_policy.py')
    mandatory.append('validate_input_effects.py')
    mandatory.append('validate_snowfall.py')
    mandatory.append('validate_snowfall_holidays.py')
    mandatory.append('validate_composer_copy_integrity.py')
    mandatory.append('validate_single_touch_message_selection.py')
    for name in mandatory:
        assert re.search(r'^          python3 scripts/'+re.escape(name)+r'\b',source,re.M),name
        assert 'nagramix_extended_check python3 scripts/'+name not in source,name
    assert re.search(r'^          python3 Telegram-iOS/build-system/Make/PostboxImportCheck.py Telegram-iOS$',source,re.M)
    assert '--final-upstream-13-2' in source and '--allow-incomplete' not in source
    assert re.search(r'^          python3 ios/apply_overlay.py ',source,re.M)
    applications=re.findall(r'^          PYTHONPATH=ios python3 -c .*apply_\w+.*$',source,re.M)
    assert len(applications)>=32 and not any('nagramix_extended_check' in line for line in applications)
    wrapped=re.findall(r'^          nagramix_extended_check python3 scripts/(validate_\w+\.py)',source,re.M)
    assert len(wrapped)>100
    runs=[]
    for flag,body,expected in [
        ('false','nagramix_extended_check bash -c "exit 17"',0),
        ('true','nagramix_extended_check bash -c "exit 17"',17),
        ('true','nagramix_extended_check true',0),
        ('invalid','nagramix_extended_check true',64),
    ]:
        script='set -euo pipefail\nNAGRAMIX_EXTENDED_PATCH_TESTS='+flag+'\n'+helper+body+'\n'
        result=subprocess.run(['bash','-c',script],capture_output=True,text=True)
        assert result.returncode==expected,(flag,result.returncode,result.stderr)
        runs.append({'extended':flag,'exit_code':result.returncode})
    # Syntax-check the real whole step, including all heredocs and continuations.
    script=source[source.index('        run: |\n')+len('        run: |\n'):]
    script='\n'.join(line[10:] if line.startswith('          ') else line for line in script.splitlines())+'\n'
    result=subprocess.run(['bash','-n'],input=script,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    return {'optional_historical_calls':len(wrapped),'unconditional_apply_calls':len(applications),'mandatory_final_checks':mandatory+['PostboxImportCheck.py'],'complete_fixture_preflight_before_overlay':'mandatory','bash_syntax':'passed','runtime_cases':runs}


def main():
    text=(ROOT/'.github/workflows/build-unsigned-ipa.yml').read_text();report=check(text)
    # Mandatory integrity cannot accidentally be moved behind the optional flag.
    changed=text.replace('          python3 scripts/validate_late_source_stages.py','          nagramix_extended_check python3 scripts/validate_late_source_stages.py',1)
    try:check(changed)
    except AssertionError:pass
    else:raise AssertionError('Optional final integrity gate accepted')
    changed=text.replace('          python3 scripts/validate_release_095_apple_preflight.py','          nagramix_extended_check python3 scripts/validate_release_095_apple_preflight.py',1)
    try:check(changed)
    except AssertionError:pass
    else:raise AssertionError('Optional early complete fixture gate accepted')
    changed=text.replace('          python3 scripts/validate_release_095_fonts_compile.py','          nagramix_extended_check python3 scripts/validate_release_095_fonts_compile.py',1)
    try:check(changed)
    except AssertionError:pass
    else:raise AssertionError('Optional final native font API gate accepted')
    for script in ['validate_release_095_composer_strings_compile.py','validate_native_string_references.py','validate_wide_channel_post_consistency.py','validate_font_theme_contrast.py','validate_system_web_picture_in_picture.py','validate_wide_panel_consistency.py','validate_settings_section_header_case.py','validate_premium_temporary_transcription.py','validate_font_preview_apply.py','validate_edit_result_consistency.py','validate_youtube_playback_policy.py','validate_input_effects.py','validate_snowfall.py','validate_snowfall_holidays.py','validate_composer_copy_integrity.py','validate_single_touch_message_selection.py']:
        changed=text.replace('          python3 scripts/'+script,'          nagramix_extended_check python3 scripts/'+script)
        try:check(changed)
        except AssertionError:pass
        else:raise AssertionError('Optional native generated strings gate accepted')
    changed=text.replace('          python3 scripts/validate_premium_temporary_transcription_native_api.py','          nagramix_extended_check python3 scripts/validate_premium_temporary_transcription_native_api.py',1)
    try:check(changed)
    except AssertionError:pass
    else:raise AssertionError('Optional early native file ASR API probe accepted')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
