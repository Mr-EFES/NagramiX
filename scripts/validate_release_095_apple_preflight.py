#!/usr/bin/env python3
"""Compile complete new runtime fixtures early, before the long overlay step.

Use immutable canonical source checkpoints, never invented copies of application
functions. Apple UIKit typechecking remains mandatory on macOS; whole native
modules still require the subsequent SDK build.
"""
import argparse
from pre_sdk_check_collection import CheckCollection
from release_098_compile_contract import check as release098_compile_check
import hashlib
import json
import shutil
from pathlib import Path
import tempfile

from validate_upstream_13_2_release import OVERLAY, SDK_STAGES, checked_plan, checked_sdk_plans
from validate_private_temporary_transcription import execute
from app_font_selection_apple import check as apple_check, access_check, navigation_check
import bubble_selection_edge_runtime as bubble
import composer_file_attachments_runtime as composer
import archived_round_native_controls_runtime as archived
import transcription_account_defaults_runtime as transcription
import app_font_selection_runtime as fonts
import font_preview_apply_runtime as font_preview
import edit_result_consistency_runtime as edit_result
import youtube_playback_policy_runtime as youtube_policy
import input_effects_runtime as input_effects
import snowfall_runtime as snowfall
import snowfall_holidays_runtime as snowfall_holidays
import composer_copy_integrity_runtime as composer_copy
import single_touch_message_selection_runtime as single_selection
import calendar_compatibility_runtime as calendar_compatibility
import transcription_compatibility_runtime as transcription_compatibility
import video_audio_continuity_runtime as video_audio_continuity
from video_audio_continuity_js import check as video_audio_js_check
from video_audio_continuity_apple import check as video_audio_apple_check
import original_video_mode_runtime as original_video_mode
import feature_photo_policy_runtime as feature_photo
import feature_wide_post_envelope_runtime as feature_wide
import feature_transcription_master_runtime as feature_master
import transcription_cached_read_runtime as cached_transcription
import round_editor_quality_runtime as round_editor_quality
from round_editor_quality_apple import check as round_editor_quality_api_check
from validate_wide_portal_api import native_api_check as wide_portal_native_api_check
from wide_portal_api_runtime import fixture as wide_portal_fixture
from doh_empty_action_runtime import fixture as doh_empty_action_fixture
from validate_doh_clear_input_lifecycle import regressions as doh_clear_native_check
from validate_sticker_status_spacing import check as sticker_status_check
from validate_round_quality_title_layout import check as round_title_check
from validate_round_quality_preset_badge import check as round_badge_check
from validate_file_caption_consistency import check as file_caption_check
from archived_playlist_lifetime_runtime import fixture as archived_playlist_lifetime_fixture
from story_avatar_visibility_runtime import fixture as story_avatar_visibility_fixture
from original_video_media_runtime import fixture as original_video_media_fixture
from original_video_media_runtime import routing_fixture as original_video_media_routing_fixture
from original_video_media_apple import check as original_video_media_api_check
from named_link_preview_runtime import ui_fixture as named_link_ui_fixture, copy_fixture as named_link_copy_fixture
from rich_file_padding_runtime import fixture as rich_file_padding_fixture
from snow_density_glass_runtime import fixture as snow_density_glass_fixture
from snow_density_glass_apple import check as snow_density_glass_api_check
from settings_glass_sliders_runtime import fixture as settings_glass_sliders_fixture
from settings_glass_sliders_apple import check as settings_glass_sliders_api_check
from font_license_compact_runtime import fixture as font_license_compact_fixture
from font_license_compact_apple import check as font_license_compact_api_check
from font_license_compact_modules import check as font_license_compact_modules_check
from round_quality_summary_runtime import fixture as round_quality_summary_fixture, ui_fixture as round_quality_summary_ui_fixture, route_fixture as round_quality_summary_route_fixture
from round_quality_summary_apple import check as round_quality_summary_api_check
from font_apply_glass_apple import check as font_apply_glass_api_check
from round_bitrate_levels_apple import check as round_bitrate_levels_api_check
from round_quality_compact_apple import check as round_quality_compact_api_check
from pip_transition_coordinator_apple import check as pip_transition_coordinator_api_check
from youtube_background_continuity_apple import check as youtube_background_api_check
from youtube_background_continuity_runtime import fixture as youtube_background_fixture
from youtube_background_continuity_js import check as youtube_background_js_check
from pip_transition_coordinator_runtime import entry_fixture as pip_coordinator_entry_fixture, poster_fixture as pip_coordinator_poster_fixture, native_fixture as pip_coordinator_native_fixture
from round_quality_compact_runtime import fixture as round_quality_compact_fixture
from round_bitrate_levels_runtime import fixture as round_bitrate_levels_fixture, ui_fixture as round_bitrate_levels_ui_fixture
from translation_account_defaults_runtime import fixture as translation_account_defaults_fixture
from unified_glass_menus_runtime import fixture as unified_glass_menus_fixture
from unified_glass_menus_apple import check as unified_glass_menus_api_check, modules_check as unified_glass_menus_modules_check
from feature_contract_consistency_apple import check as feature_contract_apple_check
from original_video_mode_apple import check as original_video_mode_apple_check
import selection_scroll_continuity_runtime as selection_scroll
import selection_column_coordinates_runtime as selection_column
from selection_column_coordinates_apple import check as selection_column_apple_check
import recording_start_recovery_runtime as recording_recovery
import pip_preview_continuity_runtime as pip_preview
from pip_preview_continuity_gallery import fixture as pip_preview_gallery_fixture
from pip_preview_continuity_apple import check as pip_preview_apple_check
from transcription_compatibility_apple import check as rpc_error_check
from single_touch_message_selection_apple import check as single_selection_apple_check
from composer_copy_integrity_apple import check as composer_copy_apple_check,foundation_check
from snowfall_holidays_apple import check as snowfall_holidays_apple_check
from snowfall_apple import check as snowfall_apple_check
from input_effects_apple import check as input_effects_apple_check
from youtube_playback_policy_js import check as youtube_js_check
from font_preview_apply_native import check as font_node_check
import web_video_picture_in_picture_runtime as pip
import temporary_expiration_semantics_runtime as expiry
import wide_channel_post_consistency_runtime as wide
import font_theme_contrast_runtime as font_theme
from font_theme_contrast_apple import icon_check,member_check
import premium_temporary_transcription_runtime as premium_asr
import wide_panel_consistency_runtime as wide_panels
import system_web_picture_in_picture_runtime as system_web
import system_web_picture_in_picture_gallery_runtime as system_gallery
from system_web_picture_in_picture_js import check as system_js_check
from system_web_picture_in_picture_apple import check as system_apple_check

ROOT = Path(__file__).resolve().parents[1]


def canonical_projection(destination, through_stage):
    post = checked_plan('upstream_13_2_release_post')
    plans, expected = checked_sdk_plans(post)
    sources = {**post.get('guard_sources', {}), **post['replacements']}
    expected = {**post['guards'], **post['outputs']}
    for stage, plan in zip(SDK_STAGES, plans):
        sources.update(plan.get('guard_sources', {}))
        sources.update(plan['replacements'])
        sources.update({n:v['source'] for n,v in plan['copies'].items()})
        expected.update(plan['guards'])
        expected.update(plan['outputs'])
        expected.update({n:v['sha256'] for n,v in plan['copies'].items()})
        if stage == through_stage: break
    else: raise AssertionError('Unknown checkpoint: '+through_stage)
    # Complete application trees are built by the normal guarded overlay.
    # This earlier fixture gate needs only real canonical Swift sources.
    native_headers = {'submodules/MtProtoKit/PublicHeaders/MtProtoKit/MTRpcError.h'} if through_stage in {'release_096_transcription_compatibility','release_096_font_node_compatibility','font_apply_node_lifecycle','video_audio_continuity','pip_preview_continuity','recording_start_recovery','selection_column_coordinates','selection_scroll_continuity','original_video_mode','feature_contract_consistency','transcription_cached_read','round_editor_quality','wide_portal_api'} else set()
    if through_stage == 'font_apply_glass':
        native_headers.add('submodules/UIKitRuntimeUtils/Source/UIKitRuntimeUtils/UIBarButtonItem+Proxy.h')
    if through_stage in {'snow_density_glass','settings_glass_sliders','round_bitrate_levels'}:
        native_headers.update({'submodules/LegacyComponents/PublicHeaders/LegacyComponents/TGPhotoEditorSliderView.h','submodules/LegacyComponents/Sources/TGPhotoEditorSliderView.m'})
    expected = {n:sha for n,sha in expected.items() if (n.endswith('.swift') or n in native_headers) and n not in post['deletions']}
    missing = {n:sha for n,sha in expected.items() if n not in sources}
    if missing:
        by_hash = {}
        for path in [*OVERLAY.rglob('*.inc'), *OVERLAY.rglob('*.swift')]:
            value = hashlib.sha256(path.read_bytes()).hexdigest()
            if value in missing.values(): by_hash[value] = path.relative_to(OVERLAY).as_posix()
        for name, sha in missing.items():
            # Some unrelated native guards are generated by earlier overlay
            # transforms and have no exported source snapshot. They are still
            # mandatory in the normal full-tree check. A fixture requesting
            # such a missing dependency fails when reading it below.
            if sha in by_hash: sources[name] = by_hash[sha]
    written = 0
    for name, sha in expected.items():
        if name not in sources: continue
        data = (OVERLAY / sources[name]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == sha, name
        path = destination / name
        assert path.resolve().is_relative_to(destination.resolve()), name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        written += 1
    additional = json.loads((ROOT/'scripts/tests/release095_native_sources.json').read_text())
    assert additional['pin'] == post['target_pin']
    added = 0
    for name, item in additional['files'].items():
        native_path = ROOT/'scripts/tests'/item['source']
        assert native_path.resolve().is_relative_to((ROOT/'scripts/tests').resolve()), name
        data = native_path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256'], name
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == item['git_blob'], name
        target = destination/name
        if not target.exists():
            assert name not in expected or expected[name] == item['sha256'], name
            assert target.resolve().is_relative_to(destination.resolve()), name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            added += 1
    localized_resources = 0
    if stage in {'round_quality_summary','round_bitrate_levels','round_quality_preset_badge'}:
        plan = checked_plan('round_bitrate_levels' if stage == 'round_quality_preset_badge' else stage)
        for name, expected_hash in plan['outputs'].items():
            if not name.endswith('.lproj/Localizable.strings'): continue
            data = (OVERLAY/plan['replacements'][name]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == expected_hash, name
            path = destination/name
            assert path.resolve().is_relative_to(destination.resolve()) and not path.exists(), name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
            localized_resources += 1
        assert localized_resources == 71
    return {'written':written, 'pinned_native_dependencies':added, 'unused_unavailable_native_guards':len(expected)-written, 'localized_resources':localized_resources}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    checks=CheckCollection(args.report.with_name("pre-sdk-failed-checks.json") if args.report else None)
    runs = []
    with tempfile.TemporaryDirectory(prefix='nagramix-095-early-') as temporary:
        root = Path(temporary)
        def cleanup(path):
            assert path.resolve().is_relative_to(root.resolve())
            if path.exists():
                assert path.is_dir() and not path.is_symlink()
                shutil.rmtree(path)
        foundation=checks.run('foundation_check:191', lambda: foundation_check(args.swiftc,root))
        files = {}
        caption_source=root/'file-caption-native-final97'
        files['native_final97']=canonical_projection(caption_source,'file_caption_consistency')
        file_caption=checks.run('file-caption-consistency', lambda: file_caption_check(caption_source,args.swiftc,root/'file-caption'), fallback={})
        for group in ('executions','geometry_executions'):
            runs += file_caption.get(group,[])
        cleanup(caption_source)
        cleanup(root/'file-caption')
        badge_source=root/'round-badge-native-final96'
        files['native_final96']=canonical_projection(badge_source,'round_quality_preset_badge')
        round_badge=checks.run('round-quality-preset-badge', lambda: round_badge_check(badge_source,args.swiftc,root/'round-badge'), fallback={})
        for group in ('executions','existing_toolbar_executions','existing_routing_executions'):
            runs += round_badge.get(group,[])
        cleanup(badge_source)
        cleanup(root/'round-badge')
        title_source=root/'round-title-native-final95'
        files['native_final95']=canonical_projection(title_source,'round_quality_title_layout')
        round_title=checks.run('round-quality-title-layout', lambda: round_title_check(title_source,args.swiftc,root/'round-title'), fallback={})
        for group in ('executions','resize_executions','existing_routing_executions'):
            runs += round_title.get(group,[])
        cleanup(title_source)
        cleanup(root/'round-title')
        sticker_source=root/'sticker-status-native-final94'
        files['native_final94']=canonical_projection(sticker_source,'sticker_status_spacing')
        sticker_status=checks.run('sticker-status-spacing', lambda: sticker_status_check(sticker_source,args.swiftc,root/'sticker-status'), fallback={})
        runs += sticker_status.get('executions',[])
        cleanup(sticker_source)
        cleanup(root/'sticker-status')
        doh_clear_source=root/'doh-clear-native-final93'
        files['native_final93']=canonical_projection(doh_clear_source,'doh_clear_input_lifecycle')
        doh_clear_lifecycle=checks.run('doh-clear-native-lifecycle', lambda: doh_clear_native_check(doh_clear_source,args.swiftc,root/'doh-clear-native'), fallback=[])
        runs += doh_clear_lifecycle[:2]
        cleanup(doh_clear_source)
        cleanup(root/'doh-clear-native')
        compile_source=root/'release098-native-final92'
        files['native_final92']=canonical_projection(compile_source,'release_098_compile_compatibility')
        release098_compilation=checks.run('release098-cross-file-compilation', lambda: release098_compile_check(compile_source,args.swiftc,root/'release098-cross-file'))
        cleanup(compile_source)
        cleanup(root/'release098-cross-file')
        youtube_background_source=root/'youtube-background-native-final'
        files['native_final91']=canonical_projection(youtube_background_source,'youtube_background_continuity')
        youtube_background_api=checks.run('youtube_background_api_check:195', lambda: youtube_background_api_check(youtube_background_source,args.swiftc,root/'youtube-background-api-first'))
        runs += checks.run('youtube-background', lambda: execute(args.swiftc,root,'youtube-background',youtube_background_fixture(youtube_background_source)), fallback=[])
        youtube_background_js=checks.run('youtube_background_js_check:197', lambda: youtube_background_js_check(youtube_background_source,root/'youtube-background-dom-first'))
        cleanup(youtube_background_source)
        cleanup(root/'youtube-background-api-first')
        cleanup(root/'youtube-background-dom-first')
        coordinator_source=root/'pip-transition-coordinator-native-final'
        files['native_final90']=canonical_projection(coordinator_source,'pip_transition_coordinator')
        pip_transition_coordinator_api=checks.run('pip_transition_coordinator_api_check:203', lambda: pip_transition_coordinator_api_check(coordinator_source,args.swiftc,root/'pip-coordinator-api-first'))
        for name,build in [('pip-coordinator-entry',pip_coordinator_entry_fixture),('pip-coordinator-poster',pip_coordinator_poster_fixture),('pip-coordinator-native',pip_coordinator_native_fixture)]:
            runs += checks.run(name, lambda: execute(args.swiftc,root,name,build(coordinator_source)), fallback=[])
        cleanup(coordinator_source)
        cleanup(root/'pip-coordinator-api-first')
        compact_source=root/'round-quality-compact-native-final'
        files['native_final89']=canonical_projection(compact_source,'round_quality_compact_page')
        round_quality_compact_api=checks.run('round_quality_compact_api_check:210', lambda: round_quality_compact_api_check(compact_source,args.swiftc,root/'round-compact-api-first'))
        runs += checks.run('round-quality-compact-page', lambda: execute(args.swiftc,root,'round-quality-compact-page',round_quality_compact_fixture(compact_source)), fallback=[])
        cleanup(compact_source)
        cleanup(root/'round-compact-api-first')
        bitrate_source=root/'round-bitrate-levels-native-final'
        files['native_final88']=canonical_projection(bitrate_source,'round_bitrate_levels')
        round_bitrate_levels_api=checks.run('round_bitrate_levels_api_check:216', lambda: round_bitrate_levels_api_check(bitrate_source,args.swiftc,root/'round-bitrate-api-first'))
        for name, build in [('round-bitrate-model-export',round_bitrate_levels_fixture),('round-bitrate-control',round_bitrate_levels_ui_fixture)]:
            runs += checks.run(name, lambda: execute(args.swiftc,root,name,build(bitrate_source)), fallback=[])
        cleanup(bitrate_source)
        cleanup(root/'round-bitrate-api-first')
        apply_source=root/'font-apply-glass-native-final'
        files['native_final87']=canonical_projection(apply_source,'font_apply_glass')
        font_apply_glass_api=checks.run('font_apply_glass_api_check:223', lambda: font_apply_glass_api_check(apply_source,args.swiftc,root/'font-apply-api-first'))
        runs += checks.run('font-preview-apply-final87', lambda: execute(args.swiftc,root,'font-preview-apply-final87',font_preview.fixture(apply_source)), fallback=[])
        cleanup(apply_source)
        if (root/'font-apply-api-first').is_dir(): cleanup(root/'font-apply-api-first')
        round_summary_source=root/'round-summary-native-final'
        files['native_final86']=canonical_projection(round_summary_source,'round_quality_summary')
        round_quality_summary_api=checks.run('round_quality_summary_api_check:229', lambda: round_quality_summary_api_check(round_summary_source,args.swiftc,root/'round-summary-api-first'))
        for name, build in [('round-quality-summary-values', round_quality_summary_fixture), ('round-quality-summary-sheet', round_quality_summary_ui_fixture), ('round-quality-summary-route', round_quality_summary_route_fixture)]:
            runs += checks.run(name, lambda: execute(args.swiftc,root,name,build(round_summary_source)), fallback=[])
        cleanup(round_summary_source)
        cleanup(root/'round-summary-api-first')
        menus_source=root/'unified-menus-native-final'
        files['native_final84']=canonical_projection(menus_source,'unified_glass_menus')
        unified_glass_menus_api=checks.run('unified_glass_menus_api_check:236', lambda: unified_glass_menus_api_check(menus_source,args.swiftc,root/'unified-menus-api-first'))
        unified_glass_menus_modules=checks.run('unified_glass_menus_modules_check:237', lambda: unified_glass_menus_modules_check(menus_source,args.swiftc,root/'unified-menus-modules-first'))
        cleanup(menus_source)
        if (root/'unified-menus-api-first').is_dir(): cleanup(root/'unified-menus-api-first')
        cleanup(root/'unified-menus-modules-first')
        license_source=root/'font-license-native-final'
        files['native_final83']=canonical_projection(license_source,'font_license_compact')
        font_license_compact_api=checks.run('font_license_compact_api_check:243', lambda: font_license_compact_api_check(license_source,args.swiftc,root/'font-license-api-first'))
        font_license_compact_modules=checks.run('font_license_compact_modules_check:244', lambda: font_license_compact_modules_check(license_source,args.swiftc,root/'font-license-modules-first'))
        cleanup(root/'font-license-modules-first')
        cleanup(license_source)
        if (root/'font-license-api-first').is_dir(): cleanup(root/'font-license-api-first')
        sliders_source=root/'settings-glass-native-final'
        files['native_final82']=canonical_projection(sliders_source,'settings_glass_sliders')
        settings_glass_sliders_api=checks.run('settings_glass_sliders_api_check:250', lambda: settings_glass_sliders_api_check(sliders_source,args.swiftc,root/'settings-glass-api-first'))
        cleanup(sliders_source)
        if (root/'settings-glass-api-first').is_dir(): cleanup(root/'settings-glass-api-first')
        density_source=root/'snow-density-native-final'
        files['native_final81']=canonical_projection(density_source,'snow_density_glass')
        snow_density_glass_api=checks.run('snow_density_glass_api_check:255', lambda: snow_density_glass_api_check(density_source,args.swiftc,root/'snow-density-api-first'))
        cleanup(density_source)
        if (root/'snow-density-api-first').is_dir(): cleanup(root/'snow-density-api-first')
        # Check the final calendar at the actual iOS15 target before the large
        # runtime matrix. Stage57 remains an exact historical runtime checkpoint.
        calendar_source=root/'calendar-native-final'
        files['native_final74']=canonical_projection(calendar_source,'wide_portal_api')
        wide_portal_api=checks.run('wide_portal_native_api_check:262', lambda: wide_portal_native_api_check(calendar_source,args.swiftc,root/'wide-portal-api-first'))
        cleanup(root/'wide-portal-api-first')
        initial_font_node=checks.run('font_node_check:264', lambda: font_node_check(calendar_source,args.swiftc,root))
        rpc_error=checks.run('rpc_error_check:265', lambda: rpc_error_check(calendar_source,args.swiftc,root/'rpc-error-native'))
        runs+=checks.run('nullable-premium-asr', lambda: execute(args.swiftc,root,'nullable-premium-asr',transcription_compatibility.fixture(calendar_source)), fallback=[])
        # Completed first-pass compiler caches have no later consumers. The
        # independent final font probe recreates its own cache when reached.
        for completed_cache in [root/'rpc-error-native/cache', root/'node-cache']:
            if completed_cache.is_dir(): cleanup(completed_cache)
        snowfall_holidays_apple=checks.run('snowfall_holidays_apple_check:271', lambda: snowfall_holidays_apple_check(calendar_source,args.swiftc,root))
        composer_copy_apple=checks.run('composer_copy_apple_check:272', lambda: composer_copy_apple_check(calendar_source,args.swiftc,root))
        video_audio_js=checks.run('video_audio_js_check:273', lambda: video_audio_js_check(calendar_source,root))
        video_audio_apple=checks.run('video_audio_apple_check:274', lambda: video_audio_apple_check(calendar_source,args.swiftc,root))
        pip_preview_apple=checks.run('pip_preview_apple_check:275', lambda: pip_preview_apple_check(calendar_source,args.swiftc,root))
        selection_column_apple=checks.run('selection_column_apple_check:276', lambda: selection_column_apple_check(calendar_source,args.swiftc,root))
        original_video_api=checks.run('original_video_mode_apple_check:277', lambda: original_video_mode_apple_check(calendar_source,args.swiftc,root/'original-video-api'))
        # The completed API probe is reported as data; its generated module/cache
        # is not used by later runtime or replay gates. Release it before replay.
        cleanup(root/'original-video-api')
        feature_contract_api=checks.run('feature_contract_apple_check:281', lambda: feature_contract_apple_check(calendar_source,args.swiftc,root/'feature-contract-api'))
        cleanup(root/'feature-contract-api')
        round_editor_quality_api=checks.run('round_editor_quality_api_check:283', lambda: round_editor_quality_api_check(calendar_source,args.swiftc,root/'round-editor-quality-api'))
        cleanup(root/'round-editor-quality-api')
        cleanup(calendar_source)
        original_media_source = root / 'original-video-media-native-final'
        files['original_video_media_native'] = canonical_projection(original_media_source, 'original_video_media')
        original_video_media_api = checks.run('original_video_media_api_check:288', lambda: original_video_media_api_check(original_media_source, args.swiftc, root / 'original-video-media-api'))
        cleanup(root / 'original-video-media-api')
        cleanup(original_media_source)
        entries = [
            ('bubble_selection_edge', [('bubble-edge', lambda s: bubble.fixture(s, (OVERLAY/checked_plan('bubble_selection_edge')['previous'][bubble.BUBBLE]).read_text()))]),
            ('composer_file_attachments', [('composer-attachments', composer.fixture)]),
            ('archived_round_native_controls', [('archived-round-controls', archived.fixture)]),
            ('transcription_account_defaults', [('transcription-defaults', transcription.fixture)]),
            ('app_font_selection', [('font-selection', fonts.fixture)]),
            ('web_video_picture_in_picture', [('web-video-pip', pip.fixture)]),
            ('temporary_expiration_semantics', [('expiry-archive', expiry.archive), ('expiry-consumption', expiry.consumption), ('expiry-read', expiry.history)]),
            ('wide_channel_post_consistency', [('wide-channel-posts', wide.fixture)]),
            ('font_theme_contrast', [('font-theme-contrast', font_theme.fixture)]),
            ('system_web_picture_in_picture', [('system-web-bridges', system_web.fixture), ('system-web-gallery', system_gallery.fixture)]),
            ('wide_panel_consistency', [('wide-panels', wide_panels.fixture)]),
            ('premium_temporary_transcription', [('premium-file-asr', premium_asr.fixture)]),
            ('font_preview_apply', [('font-preview-apply', font_preview.fixture), ('final-font-resolver', fonts.fixture)]),
            ('edit_result_consistency', [('edit-result-consistency', edit_result.fixture)]),
            ('youtube_playback_policy', [('youtube-policy-bridge', youtube_policy.bridge_fixture), ('youtube-policy-setting', youtube_policy.hook_fixture)]),
            ('input_effects', [('input-effects', input_effects.fixture)]),
            ('snowfall', [('snowfall', snowfall.fixture)]),
            ('snowfall_holidays', [('snowfall-holidays', snowfall_holidays.fixture)]),
            ('composer_copy_integrity', [('composer-copy-integrity', composer_copy.fixture)]),
            ('single_touch_message_selection', [('single-touch-message-selection', single_selection.fixture)]),
            ('release_096_calendar_compatibility', [('calendar-ios15', calendar_compatibility.fixture)]),
            ('video_audio_continuity', [('video-audio-continuity', video_audio_continuity.fixture)]),
            ('pip_preview_continuity', [('pip-preview-poster', pip_preview.poster_fixture), ('pip-preview-restore', pip_preview.restore_fixture), ('pip-preview-gallery', pip_preview_gallery_fixture)]),
            ('recording_start_recovery', [('recording-transfer', recording_recovery.fixture)]),
            ('selection_column_coordinates', [('visual-left-selection-column', selection_column.fixture)]),
            ('selection_scroll_continuity', [('held-edge-selection-scroll', selection_scroll.fixture)]),
            ('original_video_mode', [('original-video-mode', original_video_mode.fixture)]),
            ('feature_contract_consistency', [('photo-policy', feature_photo.fixture), ('wide-post-envelope', feature_wide.fixture), ('transcription-master', feature_master.fixture), ('original-video-with-photo-policy', original_video_mode.fixture)]),
            ('transcription_cached_read', [('cached-transcription-read', cached_transcription.fixture)]),
            ('round_editor_quality', [('round-editor-quality', round_editor_quality.fixture), ('round-editor-state', round_editor_quality.ui_fixture), ('round-editor-quality-badge', round_editor_quality.badge_fixture)]),
            ('wide_portal_api', [('wide-portal-api', wide_portal_fixture)]),
            ('doh_empty_action', [('doh-empty-action', doh_empty_action_fixture)]),
            ('archived_playlist_lifetime', [('archived-playlist-lifetime', archived_playlist_lifetime_fixture)]),
            ('story_avatar_visibility', [('story-avatar-visibility', story_avatar_visibility_fixture)]),
            ('original_video_media', [('original-video-bytes-media', original_video_media_fixture), ('original-video-routing-final', original_video_media_routing_fixture)]),
            ('named_link_preview', [('named-link-editor-send', named_link_ui_fixture), ('named-link-copy-broadcast', named_link_copy_fixture)]),
            ('rich_file_padding', [('rich-file-padding', rich_file_padding_fixture)]),
            ('snow_density_glass', [('snow-density-glass', snow_density_glass_fixture)]),
            ('settings_glass_sliders', [('settings-glass-sliders', settings_glass_sliders_fixture)]),
            ('font_license_compact', [('font-license-compact', font_license_compact_fixture)]),
            ('unified_glass_menus', [('unified-glass-menus', unified_glass_menus_fixture)]),
            ('translation_account_defaults', [('translation-account-defaults', translation_account_defaults_fixture)]),
        ]
        for stage, fixtures in entries:
            source = root / stage
            files[stage] = canonical_projection(source, stage)
            for name, build in fixtures: runs += checks.run(name, lambda: execute(args.swiftc, root, name, build(source)), fallback=[])
            if stage == 'single_touch_message_selection':
                single_selection_apple = checks.run('single_selection_apple_check:340', lambda: single_selection_apple_check(source, args.swiftc, root))
            # The framework checks recreate the same pinned checkpoint on demand.
            # Keep one projection at a time instead of four large dormant copies.
            assert source.resolve().is_relative_to(root.resolve())
            cleanup(source)
        # Stage41 remains an immutable historical checkpoint with SDK199's
        # known invalid call. Only the corrected final screen is a build target.
        stage='font_preview_apply'
        source=root/stage
        files[stage]=canonical_projection(source,stage)
        node=checks.run('font_node_check:350', lambda: font_node_check(source,args.swiftc,root))
        navigation=checks.run('navigation_check:351', lambda: navigation_check(source,args.swiftc,root))
        access = checks.run('access_check:352', lambda: access_check(source, args.swiftc, root))
        apple = checks.run('apple_check:353', lambda: apple_check(source, args.swiftc, root))
        icon = checks.run('icon_check:354', lambda: icon_check(source, args.swiftc, root))
        theme_members = checks.run('member_check:355', lambda: member_check(source, args.swiftc, root))
        # The independent final font API checks have also finished. Keep their
        # reports, then release only the compiler cache before framework replay.
        if (root/'node-cache').is_dir(): cleanup(root/'node-cache')
        cleanup(source)
        def replay_projection(stage):
            destination=root/stage
            assert not destination.exists()
            assert canonical_projection(destination,stage)==files[stage]
            return destination
        system_source = replay_projection('system_web_picture_in_picture')
        system_js = checks.run('system_js_check:366', lambda: system_js_check(system_source, root))
        system_apple = checks.run('system_apple_check:367', lambda: system_apple_check(system_source, args.swiftc, root))
        cleanup(system_source)
        youtube_source = replay_projection('youtube_playback_policy')
        youtube_js = checks.run('youtube_js_check:370', lambda: youtube_js_check(youtube_source, root))
        youtube_apple = checks.run('system_apple_check:371', lambda: system_apple_check(youtube_source, args.swiftc, root))
        cleanup(youtube_source)
        input_source = replay_projection('input_effects')
        input_effects_apple = checks.run('input_effects_apple_check:374', lambda: input_effects_apple_check(input_source, args.swiftc, root))
        cleanup(input_source)
        snow_source = replay_projection('snowfall')
        snowfall_apple = checks.run('snowfall_apple_check:377', lambda: snowfall_apple_check(snow_source, args.swiftc, root))
        cleanup(snow_source)
    report = {'canonical_swift_files_by_checkpoint':files, 'complete_fixtures':len(runs)//2, 'executions':runs,
              'font_apply_node_contract':node,'native_navigation_contract':navigation, 'font_adapter_access_contract':access, 'apple_uikit_precheck':apple, 'font_icon_uikit_precheck':icon, 'warnings_as_errors':True, 'historical_projection_cleanup':'completed checkpoints removed; native framework checkpoints recreated one at a time with identical pinned projection metadata; final66 preserves font64 default initializer/view factory with mixed ObjC runtime first; native RPC/IUO/calendar/clipboard gates retained; video audio65 and preview/geometry/restore66 runtimes plus real framework/image API gates retained',
              'full_application_sdk':'pending', 'device':'pending'}
    report['actual_font_theme_adapter_members']=theme_members
    report['release098_cross_file_compilation']=release098_compilation
    report['doh_clear_input_native_lifecycle']=doh_clear_lifecycle
    report['sticker_status_spacing']=sticker_status
    report['round_quality_title_layout']=round_title
    report['round_quality_preset_badge']=round_badge
    report['file_caption_consistency']=file_caption
    report['system_web_javascript']=system_js
    report['system_web_real_sdk']=system_apple
    report['youtube_playback_policy_js']=youtube_js
    report['youtube_playback_policy_apple']=youtube_apple
    report['video_audio_continuity_javascript']=video_audio_js
    report['video_audio_continuity_real_sdk']=video_audio_apple
    report['pip_preview_continuity_real_sdk']=pip_preview_apple
    report['selection_column_real_sdk']=selection_column_apple
    report['original_video_mode_native_api']=original_video_api
    report['feature_contract_consistency_native_api']=feature_contract_api
    report['round_editor_quality_native_api']=round_editor_quality_api
    report['wide_portal_native_api']=wide_portal_api
    report['original_video_media_native_api']=original_video_media_api
    report['snow_density_glass_native_api']=snow_density_glass_api
    report['settings_glass_sliders_native_api']=settings_glass_sliders_api
    report['font_license_compact_native_api']=font_license_compact_api
    report['font_license_compact_modules']=font_license_compact_modules
    report['youtube_background_native_api']=youtube_background_api
    report['youtube_background_dom']=youtube_background_js
    report['pip_transition_coordinator_native_api']=pip_transition_coordinator_api
    report['round_quality_compact_native_api']=round_quality_compact_api
    report['round_bitrate_levels_native_api']=round_bitrate_levels_api
    report['font_apply_glass_native_api']=font_apply_glass_api
    report['round_quality_summary_native_api']=round_quality_summary_api
    report['unified_glass_menus_native_api']=unified_glass_menus_api
    report['unified_glass_menus_modules']=unified_glass_menus_modules
    report['input_effects_real_sdk']=input_effects_apple
    report['snowfall_real_sdk']=snowfall_apple
    report['snowfall_holidays_real_sdk']=snowfall_holidays_apple
    report['composer_copy_real_sdk']=composer_copy_apple
    report['font_node_first_real_contract']=initial_font_node
    report['rpc_error_nullability']=rpc_error
    report['foundation_fixture_precheck']=foundation
    report['single_touch_selection_real_sdk']=single_selection_apple
    report.update(preflight_status='failed' if checks.failures else 'passed', checks=checks.results, failed_checks=checks.failures)
    if args.report: args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    checks.require_success()


if __name__ == '__main__': main()
