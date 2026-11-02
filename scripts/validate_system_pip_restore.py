#!/usr/bin/env python3
"""Проверить итоговый системный PiP и сохранение исправлений видео.

Swift-проверки используют production-код с границами Apple API.
Они не заменяют Apple SDK и проверку на физическом iPhone.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from validate_video_now_playing import block, native_manager

ROOT = Path(__file__).resolve().parents[1]
GALLERY = 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'
MANAGER = 'submodules/TelegramUI/Sources/MediaManager.swift'
API = 'submodules/AccountContext/Sources/MediaManager.swift'


def plan(name):
    return json.loads((ROOT / 'ios' / (name + '_patches.json')).read_text())


def verify_source(source):
    # Reverse newer overlays before asserting the exact historical guards.
    import importlib
    for name in (
        "ghostgram_pip_compile_fix", "gallery_export_privacy_gate", "rich_content_copy", "ghostgram_pip_cleanup", "ghostgram_pip_gallery_exact", "ghostgram_pip_replacement", "protected_copy_send_timing", "protected_copy_selection_flow", "author_check_badge_icon", "protected_copy_draft", "expanded_editor_stability", "pip_no_status_wait", "pip_ghost_source_layer", "pip_active_gallery_restore", "pip_ghost_handoff", "pip_gallery_native_gesture", "pip_caption_quotes", "pip_mode_label", "upright_author_icon", "pip_gallery_capture_fix", "deletion_effect_setting", "disable_next_swipe", "forward_single_person_icon", "author_selection_icon", "single_player_pip", "telegram_translation_defaults", "settings_labels", "pip_transition_lifecycle", "pip_stream_request_lifetime", "author_selection_fix", "story_preview_copy", "emoji_keyboard_stability", "context_translation_toggles", "transcription_context_telegram", "translation_manual_always",
        "pip_streaming", "copy_actions_consistency", "unified_temporary_messages",
    ):
        stage = importlib.import_module("validate_" + name)
        if stage.is_applied(source):
            stage.verify(source)
            with tempfile.TemporaryDirectory(prefix="recent-overlay-reverse-") as folder:
                previous = Path(folder)
                stage.reverse(source, previous)
                return verify_source(previous)
    from validate_onboarding_privacy_text import is_applied as text_applied, verify as verify_text, reverse as reverse_text
    if text_applied(source):
        verify_text(source)
        with tempfile.TemporaryDirectory(prefix="onboarding-text-reverse-") as folder:
            previous = Path(folder); reverse_text(source, previous)
            return verify_source(previous)
    from validate_view_once_existing_in_chat import is_applied as existing_applied, verify as verify_existing, reverse as reverse_existing
    if existing_applied(source):
        verify_existing(source)
        with tempfile.TemporaryDirectory(prefix="view-once-existing-reverse-") as folder:
            previous = Path(folder); reverse_existing(source, previous)
            return verify_source(previous)
    from validate_view_once_server_deletion import is_applied as delete_applied, verify as verify_delete, reverse as reverse_delete
    if delete_applied(source):
        verify_delete(source)
        with tempfile.TemporaryDirectory(prefix="view-once-delete-reverse-") as folder:
            previous = Path(folder); reverse_delete(source, previous)
            return verify_source(previous)
    from validate_view_once_short_media import is_applied as short_applied, verify as verify_short, reverse as reverse_short
    if short_applied(source):
        verify_short(source)
        with tempfile.TemporaryDirectory(prefix="view-once-short-reverse-") as folder:
            previous = Path(folder); reverse_short(source, previous)
            return verify_source(previous)
    from validate_view_once_preserve_capture import is_applied as preserve_applied, verify as verify_preserve, reverse as reverse_preserve
    if preserve_applied(source):
        verify_preserve(source)
        with tempfile.TemporaryDirectory(prefix="view-once-preserve-reverse-") as folder:
            previous = Path(folder); reverse_preserve(source, previous)
            return verify_source(previous)
    from validate_view_once_setting import is_applied as setting_applied, verify as verify_setting, reverse as reverse_setting
    if setting_applied(source):
        verify_setting(source)
        with tempfile.TemporaryDirectory(prefix="view-once-setting-reverse-") as folder:
            previous = Path(folder); reverse_setting(source, previous)
            return verify_source(previous)
    from validate_view_once_capture_on_receive import is_applied as receive_applied, verify as verify_receive, reverse as reverse_receive
    if receive_applied(source):
        verify_receive(source)
        with tempfile.TemporaryDirectory(prefix="view-once-receive-reverse-") as folder:
            previous = Path(folder); reverse_receive(source, previous)
            return verify_source(previous)
    from validate_view_once_copy_marker import is_applied as marker_applied, verify as verify_marker, reverse as reverse_marker
    if marker_applied(source):
        verify_marker(source)
        with tempfile.TemporaryDirectory(prefix="view-once-marker-reverse-") as folder:
            previous = Path(folder); reverse_marker(source, previous)
            return verify_source(previous)
    from validate_view_once_receipt_queue import is_applied as receipt_applied, verify as verify_receipt, reverse as reverse_receipt
    if receipt_applied(source):
        verify_receipt(source)
        with tempfile.TemporaryDirectory(prefix="view-once-receipt-reverse-") as folder:
            previous = Path(folder); reverse_receipt(source, previous)
            return verify_source(previous)
    from validate_view_once_copy_actions import is_applied as copy_applied, verify as verify_copy, reverse as reverse_copy
    if copy_applied(source):
        verify_copy(source)
        with tempfile.TemporaryDirectory(prefix="view-once-copy-reverse-") as folder:
            previous = Path(folder); reverse_copy(source, previous)
            return verify_source(previous)
    from validate_view_once_archive_render import is_applied as render_applied, verify as verify_render, reverse as reverse_render
    if render_applied(source):
        verify_render(source)
        with tempfile.TemporaryDirectory(prefix="view-once-render-reverse-") as folder:
            previous = Path(folder); reverse_render(source, previous)
            return verify_source(previous)
    from validate_view_once_archive_foundation import is_applied as archive_applied, verify as verify_archive, reverse as reverse_archive
    if archive_applied(source):
        verify_archive(source)
        with tempfile.TemporaryDirectory(prefix="view-once-archive-reverse-") as folder:
            previous = Path(folder); reverse_archive(source, previous)
            return verify_source(previous)
    from validate_view_once_consumption_guard import is_applied as once_applied, verify as verify_once, reverse as reverse_once
    if once_applied(source):
        verify_once(source)
        with tempfile.TemporaryDirectory(prefix="view-once-reverse-") as folder:
            previous = Path(folder); reverse_once(source, previous)
            return verify_source(previous)
    from validate_pip_playback_handoff import is_applied as handoff_applied, verify as verify_handoff, reverse as reverse_handoff
    if handoff_applied(source):
        verify_handoff(source)
        with tempfile.TemporaryDirectory(prefix="pip-handoff-reverse-") as folder:
            previous = Path(folder); reverse_handoff(source, previous)
            return verify_source(previous)
    from validate_pip_readiness_observation import is_applied as readiness_applied, verify as verify_readiness, reverse as reverse_readiness
    if readiness_applied(source):
        verify_readiness(source)
        with tempfile.TemporaryDirectory(prefix="pip-readiness-reverse-") as folder:
            previous = Path(folder); reverse_readiness(source, previous)
            return verify_source(previous)
    from validate_remove_groq import is_applied as removed_applied, verify as verify_removed, reverse as reverse_removed
    if removed_applied(source):
        verify_removed(source)
        with tempfile.TemporaryDirectory(prefix="remove-groq-reverse-") as folder:
            previous = Path(folder); reverse_removed(source, previous)
            return verify_source(previous)
    from validate_transcription_link_accent import is_applied as link_applied, verify as verify_link, reverse as reverse_link
    if link_applied(source):
        verify_link(source)
        with tempfile.TemporaryDirectory(prefix="transcription-link-reverse-") as folder:
            previous = Path(folder); reverse_link(source, previous)
            return verify_source(previous)
    from validate_translation_panel_visibility import is_applied as panel_applied, verify as verify_panel, reverse as reverse_panel
    if panel_applied(source):
        verify_panel(source)
        with tempfile.TemporaryDirectory(prefix="translation-panel-reverse-") as folder:
            previous = Path(folder); reverse_panel(source, previous)
            return verify_source(previous)
    from validate_translation_language_search_alignment import is_applied as search_applied, verify as verify_search, reverse as reverse_search
    if search_applied(source):
        verify_search(source)
        with tempfile.TemporaryDirectory(prefix="language-search-reverse-") as folder:
            previous = Path(folder); reverse_search(source, previous)
            return verify_source(previous)
    from validate_translation_auto_flow import is_applied as auto_applied, verify as verify_auto, reverse as reverse_auto
    if auto_applied(source):
        verify_auto(source)
        with tempfile.TemporaryDirectory(prefix="translation-auto-reverse-") as folder:
            previous = Path(folder); reverse_auto(source, previous)
            return verify_source(previous)
    from validate_translation_speech_text_only import is_applied as text_applied, verify as verify_text, reverse as reverse_text
    if text_applied(source):
        verify_text(source)
        with tempfile.TemporaryDirectory(prefix="service-text-reverse-") as folder:
            previous = Path(folder); reverse_text(source, previous)
            return verify_source(previous)
    from validate_translation_preferred_layout import is_applied as preferred_applied, verify as verify_preferred, reverse as reverse_preferred
    if preferred_applied(source):
        verify_preferred(source)
        with tempfile.TemporaryDirectory(prefix="preferred-layout-reverse-") as folder:
            previous = Path(folder); reverse_preferred(source, previous)
            return verify_source(previous)
    from validate_chat_russian_language_guard import is_applied as language_applied, verify as verify_language, reverse as reverse_language
    if language_applied(source):
        verify_language(source)
        with tempfile.TemporaryDirectory(prefix="chat-language-reverse-") as folder:
            previous = Path(folder); reverse_language(source, previous)
            return verify_source(previous)
    from validate_remote_model_catalog import is_applied as catalog_applied, verify as verify_catalog, reverse as reverse_catalog
    if catalog_applied(source):
        verify_catalog(source)
        with tempfile.TemporaryDirectory(prefix="remote-catalog-reverse-") as folder:
            previous = Path(folder); reverse_catalog(source, previous)
            return verify_source(previous)
    from validate_provider_settings_consistency import is_applied as ui_applied, verify as verify_ui, reverse as reverse_ui
    if ui_applied(source):
        verify_ui(source)
        with tempfile.TemporaryDirectory(prefix="provider-ui-reverse-") as folder:
            previous = Path(folder); reverse_ui(source, previous)
            return verify_source(previous)
    from validate_whisper_footer_removal import is_applied as footer_applied, verify as verify_footer, reverse as reverse_footer
    if footer_applied(source):
        verify_footer(source)
        with tempfile.TemporaryDirectory(prefix="whisper-footer-reverse-") as folder:
            previous = Path(folder); reverse_footer(source, previous)
            return verify_source(previous)
    from validate_speech_download_no_bar import is_applied as progress_applied, verify as verify_progress, reverse as reverse_progress
    if progress_applied(source):
        verify_progress(source)
        with tempfile.TemporaryDirectory(prefix="speech-no-bar-reverse-") as folder:
            previous = Path(folder); reverse_progress(source, previous)
            return verify_source(previous)
    from validate_round_slider_kbps import is_applied as kbps_applied, verify as verify_kbps, reverse as reverse_kbps
    if kbps_applied(source):
        verify_kbps(source)
        with tempfile.TemporaryDirectory(prefix="round-kbps-reverse-") as folder:
            previous = Path(folder); reverse_kbps(source, previous)
            return verify_source(previous)
    from validate_round_slider_touch import is_applied as slider_applied, verify as verify_slider, reverse as reverse_slider
    if slider_applied(source):
        verify_slider(source)
        with tempfile.TemporaryDirectory(prefix="round-slider-reverse-") as folder:
            previous = Path(folder); reverse_slider(source, previous)
            return verify_source(previous)
    from validate_pip_transition_surface import is_applied as surface_applied, verify as verify_surface, reverse as reverse_surface
    if surface_applied(source):
        verify_surface(source)
        with tempfile.TemporaryDirectory(prefix="pip-surface-reverse-") as folder:
            previous = Path(folder); reverse_surface(source, previous)
            return verify_source(previous)
    from validate_license_readable import is_applied as license_applied, verify as verify_license, reverse as reverse_license
    if license_applied(source):
        verify_license(source)
        with tempfile.TemporaryDirectory(prefix="license-layout-reverse-") as folder:
            previous = Path(folder); reverse_license(source, previous)
            return verify_source(previous)
    from validate_formatting_keyboard_height import is_applied as format_applied, verify as verify_format, reverse as reverse_format
    if format_applied(source):
        verify_format(source)
        with tempfile.TemporaryDirectory(prefix="format-height-reverse-") as folder:
            previous = Path(folder); reverse_format(source, previous)
            return verify_source(previous)
    from validate_pip_asset_audio_recovery import is_applied as recovery_applied, verify as verify_recovery, reverse as reverse_recovery
    if recovery_applied(source):
        verify_recovery(source)
        with tempfile.TemporaryDirectory(prefix="pip-asset-reverse-") as folder:
            previous = Path(folder); reverse_recovery(source, previous)
            return verify_source(previous)
    from validate_whisper_three_models import is_applied as models_applied, verify as verify_models, reverse as reverse_models
    if models_applied(source):
        verify_models(source)
        with tempfile.TemporaryDirectory(prefix="whisper-model-reverse-") as folder:
            previous = Path(folder); reverse_models(source, previous)
            return verify_source(previous)
    from validate_translation_chat_language import is_applied as language_applied, verify as verify_language, reverse as reverse_language
    if language_applied(source):
        verify_language(source)
        with tempfile.TemporaryDirectory(prefix="chat-language-reverse-") as folder:
            previous = Path(folder); reverse_language(source, previous)
            return verify_source(previous)
    from validate_speech_provider_permission import is_applied as permission_applied, verify as verify_permission, reverse as reverse_permission
    if permission_applied(source):
        verify_permission(source)
        with tempfile.TemporaryDirectory(prefix="speech-permission-reverse-") as folder:
            previous = Path(folder); reverse_permission(source, previous)
            return verify_source(previous)
    from validate_speech_cloudflare_display import is_applied as cloudflare_applied, verify as verify_cloudflare, reverse as reverse_cloudflare
    if cloudflare_applied(source):
        verify_cloudflare(source)
        with tempfile.TemporaryDirectory(prefix="speech-cloudflare-reverse-") as folder:
            previous = Path(folder); reverse_cloudflare(source, previous)
            return verify_source(previous)
    from validate_speech_model_display import is_applied as model_applied, verify as verify_model, reverse as reverse_model
    if model_applied(source):
        verify_model(source)
        with tempfile.TemporaryDirectory(prefix="speech-model-reverse-") as folder:
            previous = Path(folder); reverse_model(source, previous)
            return verify_source(previous)
    from validate_translation_speech_ui import is_applied as unified_applied, verify as verify_unified, reverse as reverse_unified
    if unified_applied(source):
        verify_unified(source)
        with tempfile.TemporaryDirectory(prefix="unified-reverse-") as folder:
            previous = Path(folder); reverse_unified(source, previous)
            return verify_source(previous)
    from validate_file_bubble_spacing import is_applied as file_applied, verify as verify_file, reverse as reverse_file
    if file_applied(source):
        verify_file(source)
        with tempfile.TemporaryDirectory(prefix="file-bubble-reverse-") as folder:
            previous = Path(folder); reverse_file(source, previous)
            return verify_source(previous)
    from validate_repost_schedule import is_applied as repost_applied, verify as verify_repost, reverse as reverse_repost
    if repost_applied(source):
        verify_repost(source)
        with tempfile.TemporaryDirectory(prefix="repost-reverse-") as folder:
            previous = Path(folder); reverse_repost(source, previous)
            return verify_source(previous)
    from validate_transcription_context_refresh import is_applied as refresh_applied, verify as verify_refresh, reverse as reverse_refresh
    if refresh_applied(source):
        verify_refresh(source)
        with tempfile.TemporaryDirectory(prefix="transcription-refresh-reverse-") as folder:
            previous = Path(folder); reverse_refresh(source, previous)
            return verify_source(previous)
    from validate_keyboard_handoff import is_applied as handoff_applied, verify as verify_handoff, reverse as reverse_handoff
    if handoff_applied(source):
        verify_handoff(source)
        with tempfile.TemporaryDirectory(prefix="handoff-reverse-") as folder:
            previous = Path(folder); reverse_handoff(source, previous)
            return verify_source(previous)
    from validate_pip_readiness_fix import is_applied as pip_fix_applied, verify as verify_pip_fix, reverse as reverse_pip_fix
    if pip_fix_applied(source):
        verify_pip_fix(source)
        with tempfile.TemporaryDirectory(prefix="pip-fix-reverse-") as folder:
            previous = Path(folder); reverse_pip_fix(source, previous)
            return verify_source(previous)
    from validate_keyboard_transition import is_applied as keyboard_applied, verify as verify_keyboard, reverse as reverse_keyboard
    if keyboard_applied(source):
        verify_keyboard(source)
        with tempfile.TemporaryDirectory(prefix='keyboard-reverse-') as folder:
            previous = Path(folder); reverse_keyboard(source, previous)
            return verify_source(previous)
    from validate_transcription_vosk import is_applied as vosk_applied, verify as verify_vosk, reverse as reverse_vosk
    if vosk_applied(source):
        verify_vosk(source)
        with tempfile.TemporaryDirectory(prefix='vosk-reverse-') as folder:
            previous = Path(folder); reverse_vosk(source, previous)
            return verify_source(previous)
    from validate_transcription_cloudflare import is_applied as cf_applied, verify as verify_cf, reverse as reverse_cf
    if cf_applied(source):
        verify_cf(source)
        with tempfile.TemporaryDirectory(prefix='transcription-cf-reverse-') as folder:
            previous = Path(folder); reverse_cf(source, previous)
            return verify_source(previous)
    from validate_transcription_local_fallback import is_applied as fallback_applied, verify as verify_fallback, reverse as reverse_fallback
    if fallback_applied(source):
        verify_fallback(source)
        with tempfile.TemporaryDirectory(prefix='transcription-fallback-reverse-') as folder:
            previous = Path(folder); reverse_fallback(source, previous)
            return verify_source(previous)
    from validate_transcription_cloud_ui import is_applied as cloud_applied, verify as verify_cloud, reverse as reverse_cloud
    if cloud_applied(source):
        verify_cloud(source)
        with tempfile.TemporaryDirectory(prefix='transcription-cloud-reverse-') as folder:
            previous = Path(folder); reverse_cloud(source, previous)
            return verify_source(previous)
    from validate_transcription_whisper_safety import is_applied as whisper_applied, verify as verify_whisper, reverse as reverse_whisper
    if whisper_applied(source):
        verify_whisper(source)
        with tempfile.TemporaryDirectory(prefix='whisper-safety-reverse-') as folder:
            previous = Path(folder); reverse_whisper(source, previous)
            return verify_source(previous)
    from validate_broadcast_stable_order import is_applied as order_applied, verify as verify_order, reverse as reverse_order
    if order_applied(source):
        verify_order(source)
        with tempfile.TemporaryDirectory(prefix='broadcast-order-reverse-') as folder:
            previous = Path(folder); reverse_order(source, previous)
            return verify_source(previous)
    from validate_translation_premium_visibility import is_applied as premium_applied, verify as verify_premium, reverse as reverse_premium
    if premium_applied(source):
        verify_premium(source)
        with tempfile.TemporaryDirectory(prefix='translation-premium-reverse-') as folder:
            previous = Path(folder); reverse_premium(source, previous)
            return verify_source(previous)
    from validate_translation_inline_telegram import is_applied as inline_applied, verify as verify_inline, reverse as reverse_inline
    if inline_applied(source):
        verify_inline(source)
        with tempfile.TemporaryDirectory(prefix='translation-inline-reverse-') as folder:
            previous = Path(folder); reverse_inline(source, previous)
            result = verify_source(previous)
            result['translation_inline'] = 'telegram-and-inline'
            return result
    from validate_translation_simplification import is_applied as simple_applied, verify as verify_simple, reverse as reverse_simple
    if simple_applied(source):
        verify_simple(source)
        with tempfile.TemporaryDirectory(prefix='translation-simple-reverse-') as folder:
            previous = Path(folder); reverse_simple(source, previous)
            result = verify_source(previous)
            result['translation_settings'] = 'simplified'
            return result
    from validate_media_privacy_fixes import is_applied as media_applied, verify as verify_media, reverse as reverse_media
    if media_applied(source):
        verify_media(source)
        with tempfile.TemporaryDirectory(prefix='media-privacy-reverse-') as folder:
            previous = Path(folder); reverse_media(source, previous)
            result = verify_source(previous)
            result['media_privacy'] = 'source_checked'
            return result
    from validate_native_player_pip import is_applied as native_applied, reverse as reverse_native
    if native_applied(source):
        subprocess.run(['python3', str(ROOT / 'scripts/validate_native_player_pip.py'), '--source', str(source), '--standalone'], check=True)
        with tempfile.TemporaryDirectory(prefix='native-pip-reverse-') as folder:
            previous = Path(folder); reverse_native(source, previous)
            result = verify_source(previous)
            result['video_PiP'] = 'native_AVPlayerLayer'
            return result
    from validate_pip_removal_work import is_applied as removal_applied, PLAN as removal_plan
    if removal_applied(source):
        subprocess.run(['python3', str(ROOT / 'scripts/validate_pip_removal_work.py'), '--source', str(source), '--standalone'], check=True)
        with tempfile.TemporaryDirectory(prefix='pip-removal-reverse-') as folder:
            previous = Path(folder)
            names = set(removal_plan['inputs'])
            for manifest in (ROOT / 'ios').glob('*_patches.json'):
                content = json.loads(manifest.read_text())
                for field in ('inputs', 'outputs', 'guards', 'copies'): names.update(content.get(field, {}))
            for name in names:
                path = source / name
                if not path.is_file(): continue
                target = previous / name; target.parent.mkdir(parents=True, exist_ok=True)
                original = removal_plan['previous'].get(name)
                target.write_bytes((ROOT / 'ios' / original).read_bytes() if original else path.read_bytes())
            for name, item in removal_plan['deletions'].items():
                path = previous / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / 'ios' / item['source']).read_bytes())
            result = verify_source(previous)
            result['video_PiP'] = 'removed'
            return result
    tree = ast.parse((ROOT / 'ios/apply_overlay.py').read_text())
    calls = [node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    assert 'apply_hybrid_pip' not in calls, 'Внутренний PiP снова подключён'
    assert not any(isinstance(node, ast.ImportFrom) and node.module == 'hybrid_pip'
                   for node in ast.walk(tree)), 'Остался импорт внутреннего PiP'
    stages = ['video_rotation_registration', 'crash_report_bot', 'video_display_resume',
              'quick_format_adaptive', 'broadcast_inline_topics', 'round_video_quality',
              'settings_download_layout', 'round_video_sheet', 'quick_format_no_heading', 'quick_format_equal_spacing', 'pip_presentation', 'round_video_page', 'story_explicit_view', 'story_download_quality', 'story_icon_consistency', 'pip_native_transaction', 'round_video_refinement', 'recovery_storage_fixes', 'scheduled_archive_isolation', 'round_video_bitrate', 'pip_native_entry', 'message_translation', 'translation_free_modes', 'translation_gpt_oss', 'voice_transcription', 'release_076_sdk', 'release_076_dependencies', 'release_076_compile', 'release_076_import', 'video_ownership_fix', 'transcription_settings_refinement', 'transcription_settings_complete', 'translation_settings_revision', 'translation_completion', 'translation_sdk_fix']
    order = [calls.index('apply_' + stage) for stage in stages]
    assert order == sorted(order), 'Нарушен порядок сохранённых исправлений'

    # Полные SHA входов отключённого эксперимента задают точное состояние
    # до него, уже с исправленной регистрацией AVKit и единым Now Playing.
    hybrid = plan('hybrid_pip')
    expected = {**hybrid['inputs'], **hybrid['guards']}
    for stage in stages:
        for name, digest in plan(stage)['outputs'].items():
            expected[name] = digest
        for name, item in plan(stage)['copies'].items():
            expected[name] = item['sha256']
    for name, digest in expected.items():
        path = source / name
        assert path.is_file(), 'Нет файла: ' + name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
    for name in hybrid['copies']:
        assert not (source / name).exists(), 'В приложение попал helper внутреннего PiP'

    video = (source / GALLERY).read_text()
    assert 'return self.nagramiXStartSystemPiP(requiresSwipeSetting: true, completion: completion)' in video
    assert 'self.nagramiXStartSystemPiP(requiresSwipeSetting: false' in video
    assert video.count('startPictureInPicture()') == 1
    assert 'self.lifecycle.phase == .preparing' in video
    for name in hybrid['inputs']:
        text = (source / name).read_text()
        assert 'nagramiXHybrid' not in text and 'NagramiXHybrid' not in text, name
    now_playing = plan('video_now_playing')
    for name in [MANAGER, API]:
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == now_playing['outputs'][name]
    for name, item in now_playing['copies'].items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == item['sha256']
    return {'checked_files': len(expected), 'restored_native_files': len(hybrid['inputs']),
            'internal_player': 'absent', 'renderer_recovery': 'preserved', 'Now_Playing': 'preserved'}


def execute(source, swiftc):
    manager = (source / MANAGER).read_text()
    api = (source / API).read_text()
    media = (source / 'submodules/MediaPlayer/Sources/MediaPlayer.swift').read_text()
    actions = (source / 'submodules/AccountContext/Sources/SharedMediaPlayer.swift').read_text()
    declarations = block(media, 'public enum MediaPlayerPlaybackStatus: Equatable')
    declarations += '\n' + block(media, 'public struct MediaPlayerStatus: Equatable')
    declarations += '\n' + block(actions, 'public enum SharedMediaPlayerPlaybackControlAction')
    declarations += '\n' + block(actions, 'public enum SharedMediaPlayerControlAction')
    declarations += '\n' + block(api, 'public struct NagramiXVideoNowPlayingState')
    declarations += '\n' + block(manager, 'private struct GlobalControlOptions: OptionSet').replace('private struct', 'struct', 1)
    helper = (source / 'submodules/TelegramUI/Sources/NagramiXVideoNowPlaying.swift').read_text()
    helper = '\n'.join(line for line in helper.splitlines() if not line.startswith('import '))
    results = []
    with tempfile.TemporaryDirectory(prefix='system-pip-restore-') as directory:
        temp = Path(directory)
        production = temp / 'NowPlaying.swift'
        production.write_text('import Foundation\ntypealias SharedMediaPlaybackAlbumArt = String\n'
                              + declarations.replace('public ', '') + '\n' + helper + '\n'
                              + native_manager(manager))
        lifecycle = source / 'submodules/GalleryUI/Sources/NagramiXPiPLifecycle.swift'
        groups = [
            ('now-playing', [production, ROOT / 'scripts/tests/NagramiXVideoNowPlayingBoundary.swift',
                             ROOT / 'scripts/tests/NagramiXVideoNowPlayingTests.swift']),
        ]
        if lifecycle.is_file():
            groups.extend([
                ('lifecycle', [lifecycle, ROOT / 'scripts/tests/NagramiXPiPLifecycleTests.swift']),
                ('audio', [lifecycle, ROOT / 'scripts/tests/NagramiXPiPAudioPolicyTests.swift']),
            ])
        for mode in [[], ['-O']]:
            for label, files in groups:
                binary = temp / 'test'
                subprocess.run([str(swiftc), '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'),
                                *mode, *map(str, files), '-o', str(binary)], check=True)
                output = subprocess.check_output([str(binary)], text=True, timeout=30).strip()
                results.append({'test': label, 'optimized': bool(mode), 'output': output})
        subprocess.run([str(swiftc), '-frontend', '-parse',
                        *[str(source / name) for name in plan('hybrid_pip')['inputs']]], check=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Итоговое дерево после полного overlay')
    parser.add_argument('--swiftc', type=Path, help='Дополнительно исполнить Swift-проверки')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify_source(args.source)
    result['execution'] = execute(args.source, args.swiftc) if args.swiftc else []
    result.update(Apple_SDK='pending', physical_iPhone='pending')
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
