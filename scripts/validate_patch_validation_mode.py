#!/usr/bin/env python3
"""Проверить быстрый путь сборки и явный запуск широких исторических тестов."""
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def check(text):
    start=text.index('      - name: Применить overlay NagramiX\n')
    assert re.search(r'^          python3 scripts/validate_release_095_apple_preflight\.py --swiftc ',text[:start],re.M), 'Complete fixture preflight must run before overlay'
    end=text.index('      - name: Восстановить кеш Bazel\n',start)
    source=text[start:end]
    option=re.search(r'^      extended_patch_tests:\n(.*?)(?=^      \w+:)',text,re.M|re.S).group(1)
    assert 'type: boolean' in option and 'default: false' in option
    assert 'NAGRAMIX_EXTENDED_PATCH_TESTS: ${{ inputs.extended_patch_tests }}' in source
    begin=source.index('          # BEGIN optional historical regressions\n')
    finish=source.index('          # END optional historical regressions\n',begin)+len('          # END optional historical regressions\n')
    helper='\n'.join(line[10:] for line in source[begin:finish].splitlines())+'\n'
    mandatory=['validate_late_source_stages.py','validate_custom_member_references.py','validate_upstream_13_2_release.py','validate_localization_standard.py','validate_release_092_settings_compile.py','validate_round_native_playback.py','validate_poll_copy_transport.py']
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
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
