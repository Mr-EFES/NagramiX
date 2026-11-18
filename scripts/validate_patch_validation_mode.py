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
    early=text.split('      - name: Проверить геометрию тестов на Apple Swift\n',1)[1].split('      - name:',1)[0]
    assert '          nagramix_pre_sdk_failed=0\n' in early
    early_checks=re.findall(r'^          python3 scripts/.*$',early,re.M)
    assert len(early_checks)==5 and all(line.endswith(' || nagramix_pre_sdk_failed=1') for line in early_checks)
    assert early.rstrip().endswith('test "$nagramix_pre_sdk_failed" -eq 0'), 'Any early failure must block overlay and SDK'
    assert 'pre-sdk-failed-checks.json' in text and 'nagramix-test-failures/' in text
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
    mandatory.append('validate_release_096_calendar_compatibility.py')
    mandatory.append('validate_release_096_transcription_compatibility.py')
    mandatory.append('validate_release_096_font_node_compatibility.py')
    mandatory.append('validate_font_apply_node_lifecycle.py')
    mandatory.append('validate_video_audio_continuity.py')
    mandatory.append('validate_pip_preview_continuity.py')
    mandatory.append('validate_recording_start_recovery.py')
    mandatory.append('validate_selection_column_coordinates.py')
    mandatory.append('validate_selection_scroll_continuity.py')
    mandatory.append('validate_original_video_mode.py')
    mandatory.append('validate_feature_contract_consistency.py')
    mandatory.append('validate_transcription_cached_read.py')
    mandatory.append('validate_round_editor_quality.py')
    mandatory.append('validate_doh_empty_action.py')
    mandatory.append('validate_archived_playlist_lifetime.py')
    mandatory.append('validate_story_avatar_visibility.py')
    mandatory.append('validate_original_video_media.py')
    mandatory.append('validate_named_link_preview.py')
    mandatory.append('validate_rich_file_padding.py')
    mandatory.append('validate_snow_density_glass.py')
    mandatory.append('validate_settings_glass_sliders.py')
    mandatory.append('validate_font_license_compact.py')
    mandatory.append('validate_unified_glass_menus.py')
    mandatory.append('validate_translation_account_defaults.py')
    mandatory.append('validate_round_quality_summary.py')
    mandatory.append('validate_font_apply_glass.py')
    mandatory.append('validate_round_bitrate_levels.py')
    mandatory.append('validate_round_quality_compact_page.py')
    mandatory.append('validate_pip_transition_coordinator.py')
    mandatory.append('validate_youtube_background_continuity.py')
    mandatory.append('validate_release_098_compile_compatibility.py')
    mandatory.append('validate_doh_clear_input_lifecycle.py')
    mandatory.append('validate_sticker_status_spacing.py')
    mandatory.append('validate_round_quality_title_layout.py')
    mandatory.append('validate_round_quality_preset_badge.py')
    mandatory.append('validate_file_caption_consistency.py')
    mandatory.append('validate_file_caption_edit.py')
    mandatory.append('validate_font_toggle_alignment.py')
    mandatory.append('validate_original_video_gallery.py')
    mandatory.append('validate_round_quality_checkmark_alignment.py')
    mandatory.append('validate_round_video_encoding.py')
    mandatory.append('validate_tab_visibility_sync.py')
    mandatory.append('validate_native_pip_refinement.py')
    mandatory.append('validate_settings_category_bar_layout.py')
    mandatory.append('validate_round_quality_sheet_navigation.py')
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
    changed=text.replace('test "$nagramix_pre_sdk_failed" -eq 0','true',1)
    try:check(changed)
    except AssertionError:pass
    else:raise AssertionError('Failed pre-SDK gate could reach application compilation')
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
    for script in ['validate_release_095_composer_strings_compile.py','validate_native_string_references.py','validate_wide_channel_post_consistency.py','validate_font_theme_contrast.py','validate_system_web_picture_in_picture.py','validate_wide_panel_consistency.py','validate_settings_section_header_case.py','validate_premium_temporary_transcription.py','validate_font_preview_apply.py','validate_edit_result_consistency.py','validate_youtube_playback_policy.py','validate_input_effects.py','validate_snowfall.py','validate_snowfall_holidays.py','validate_composer_copy_integrity.py','validate_single_touch_message_selection.py','validate_release_096_calendar_compatibility.py','validate_release_096_transcription_compatibility.py','validate_release_096_font_node_compatibility.py','validate_font_apply_node_lifecycle.py','validate_video_audio_continuity.py','validate_pip_preview_continuity.py','validate_recording_start_recovery.py','validate_selection_column_coordinates.py','validate_selection_scroll_continuity.py','validate_original_video_mode.py','validate_feature_contract_consistency.py','validate_transcription_cached_read.py','validate_round_editor_quality.py']:
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
