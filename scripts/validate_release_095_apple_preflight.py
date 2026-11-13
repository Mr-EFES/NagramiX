#!/usr/bin/env python3
"""Compile complete new runtime fixtures early, before the long overlay step.

Use immutable canonical source checkpoints, never invented copies of application
functions. Apple UIKit typechecking remains mandatory on macOS; whole native
modules still require the subsequent SDK build.
"""
import argparse
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
    native_headers = {'submodules/MtProtoKit/PublicHeaders/MtProtoKit/MTRpcError.h'} if through_stage in {'release_096_transcription_compatibility','release_096_font_node_compatibility','font_apply_node_lifecycle','video_audio_continuity','pip_preview_continuity','recording_start_recovery','selection_column_coordinates','selection_scroll_continuity'} else set()
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
    return {'written':written, 'pinned_native_dependencies':added, 'unused_unavailable_native_guards':len(expected)-written}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    runs = []
    with tempfile.TemporaryDirectory(prefix='nagramix-095-early-') as temporary:
        root = Path(temporary)
        foundation=foundation_check(args.swiftc,root)
        files = {}
        # Check the final calendar at the actual iOS15 target before the large
        # runtime matrix. Stage57 remains an exact historical runtime checkpoint.
        calendar_source=root/'calendar-native-final'
        files['native_final69']=canonical_projection(calendar_source,'selection_scroll_continuity')
        initial_font_node=font_node_check(calendar_source,args.swiftc,root)
        rpc_error=rpc_error_check(calendar_source,args.swiftc,root/'rpc-error-native')
        runs+=execute(args.swiftc,root,'nullable-premium-asr',transcription_compatibility.fixture(calendar_source))
        snowfall_holidays_apple=snowfall_holidays_apple_check(calendar_source,args.swiftc,root)
        composer_copy_apple=composer_copy_apple_check(calendar_source,args.swiftc,root)
        video_audio_js=video_audio_js_check(calendar_source,root)
        video_audio_apple=video_audio_apple_check(calendar_source,args.swiftc,root)
        pip_preview_apple=pip_preview_apple_check(calendar_source,args.swiftc,root)
        selection_column_apple=selection_column_apple_check(calendar_source,args.swiftc,root)
        shutil.rmtree(calendar_source)
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
        ]
        for stage, fixtures in entries:
            source = root / stage
            files[stage] = canonical_projection(source, stage)
            for name, build in fixtures: runs += execute(args.swiftc, root, name, build(source))
            if stage == 'single_touch_message_selection':
                single_selection_apple = single_selection_apple_check(source, args.swiftc, root)
            # The framework checks recreate the same pinned checkpoint on demand.
            # Keep one projection at a time instead of four large dormant copies.
            assert source.resolve().is_relative_to(root.resolve())
            shutil.rmtree(source)
        # Stage41 remains an immutable historical checkpoint with SDK199's
        # known invalid call. Only the corrected final screen is a build target.
        stage='font_preview_apply'
        source=root/stage
        files[stage]=canonical_projection(source,stage)
        node=font_node_check(source,args.swiftc,root)
        navigation=navigation_check(source,args.swiftc,root)
        access = access_check(source, args.swiftc, root)
        apple = apple_check(source, args.swiftc, root)
        icon = icon_check(source, args.swiftc, root)
        theme_members = member_check(source, args.swiftc, root)
        shutil.rmtree(source)
        def replay_projection(stage):
            destination=root/stage
            assert not destination.exists()
            assert canonical_projection(destination,stage)==files[stage]
            return destination
        system_source = replay_projection('system_web_picture_in_picture')
        system_js = system_js_check(system_source, root)
        system_apple = system_apple_check(system_source, args.swiftc, root)
        shutil.rmtree(system_source)
        youtube_source = replay_projection('youtube_playback_policy')
        youtube_js = youtube_js_check(youtube_source, root)
        youtube_apple = system_apple_check(youtube_source, args.swiftc, root)
        shutil.rmtree(youtube_source)
        input_source = replay_projection('input_effects')
        input_effects_apple = input_effects_apple_check(input_source, args.swiftc, root)
        shutil.rmtree(input_source)
        snow_source = replay_projection('snowfall')
        snowfall_apple = snowfall_apple_check(snow_source, args.swiftc, root)
        shutil.rmtree(snow_source)
    report = {'canonical_swift_files_by_checkpoint':files, 'complete_fixtures':len(runs)//2, 'executions':runs,
              'font_apply_node_contract':node,'native_navigation_contract':navigation, 'font_adapter_access_contract':access, 'apple_uikit_precheck':apple, 'font_icon_uikit_precheck':icon, 'warnings_as_errors':True, 'historical_projection_cleanup':'completed checkpoints removed; native framework checkpoints recreated one at a time with identical pinned projection metadata; final66 preserves font64 default initializer/view factory with mixed ObjC runtime first; native RPC/IUO/calendar/clipboard gates retained; video audio65 and preview/geometry/restore66 runtimes plus real framework/image API gates retained',
              'full_application_sdk':'pending', 'device':'pending'}
    report['actual_font_theme_adapter_members']=theme_members
    report['system_web_javascript']=system_js
    report['system_web_real_sdk']=system_apple
    report['youtube_playback_policy_js']=youtube_js
    report['youtube_playback_policy_apple']=youtube_apple
    report['video_audio_continuity_javascript']=video_audio_js
    report['video_audio_continuity_real_sdk']=video_audio_apple
    report['pip_preview_continuity_real_sdk']=pip_preview_apple
    report['selection_column_real_sdk']=selection_column_apple
    report['input_effects_real_sdk']=input_effects_apple
    report['snowfall_real_sdk']=snowfall_apple
    report['snowfall_holidays_real_sdk']=snowfall_holidays_apple
    report['composer_copy_real_sdk']=composer_copy_apple
    report['font_node_first_real_contract']=initial_font_node
    report['rpc_error_nullability']=rpc_error
    report['foundation_fixture_precheck']=foundation
    report['single_touch_selection_real_sdk']=single_selection_apple
    if args.report: args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
