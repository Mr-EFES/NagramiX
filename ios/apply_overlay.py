#!/usr/bin/env python3
"""Apply the smallest possible NagramiX branding layer to Telegram-iOS."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path



ALTERNATE_ICON_SIZES = {
    "@2x.png": 120,
    "@3x.png": 180,
    "-76.png": 76,
    "-76@2x.png": 152,
    "-83.5@2x.png": 167,
    "_29x29.png": 29,
    "_58x58.png": 58,
    "_80x80.png": 80,
    "_87x87.png": 87,
    "_notification.png": 20,
    "_notification@2x.png": 40,
    "_notification@3x.png": 60,
}

PRIMARY_ICON_IMAGES = [
    ("iphone", "20x20", "2x", "NagramiX1-40.png", 40),
    ("iphone", "20x20", "3x", "NagramiX1-60.png", 60),
    ("iphone", "29x29", "2x", "NagramiX1-58.png", 58),
    ("iphone", "29x29", "3x", "NagramiX1-87.png", 87),
    ("iphone", "40x40", "2x", "NagramiX1-80.png", 80),
    ("iphone", "40x40", "3x", "NagramiX1-120.png", 120),
    ("iphone", "60x60", "2x", "NagramiX1-120-home.png", 120),
    ("iphone", "60x60", "3x", "NagramiX1-180.png", 180),
    ("ipad", "20x20", "1x", "NagramiX1-20.png", 20),
    ("ipad", "20x20", "2x", "NagramiX1-40-ipad.png", 40),
    ("ipad", "29x29", "1x", "NagramiX1-29.png", 29),
    ("ipad", "29x29", "2x", "NagramiX1-58-ipad.png", 58),
    ("ipad", "40x40", "1x", "NagramiX1-40-settings.png", 40),
    ("ipad", "40x40", "2x", "NagramiX1-80-ipad.png", 80),
    ("ipad", "76x76", "2x", "NagramiX1-152.png", 152),
    ("ipad", "83.5x83.5", "2x", "NagramiX1-167.png", 167),
    ("ios-marketing", "1024x1024", "1x", "NagramiX1-1024.png", 1024),
]

PRIMARY_ICON_PREVIEW_IMAGES = [
    ("1x", "NagramiX1Preview.png", 60),
    ("2x", "NagramiX1Preview@2x.png", 120),
    ("3x", "NagramiX1Preview@3x.png", 180),
]


def resize_icon(source: Path, destination: Path, size: int) -> None:
    try:
        from PIL import Image
    except ImportError:
        subprocess.run(
            ["sips", "-z", str(size), str(size), str(source), "--out", str(destination)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    else:
        with Image.open(source) as image:
            resized = image.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            opaque = Image.new("RGB", resized.size, (0, 0, 0))
            opaque.paste(resized, mask=resized.getchannel("A"))
            opaque.save(destination, format="PNG")


def replace_text(path: Path, old: str, new: str) -> bool:
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    if old not in content:
        return False
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    return True


def create_primary_icon_set(source_icon: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    images = []
    for idiom, size_name, scale, filename, pixels in PRIMARY_ICON_IMAGES:
        resize_icon(source_icon, destination / filename, pixels)
        images.append({
            "size": size_name,
            "idiom": idiom,
            "filename": filename,
            "scale": scale,
        })
    contents = {
        "images": images,
        "info": {"version": 1, "author": "xcode"},
    }
    (destination / "Contents.json").write_text(
        json.dumps(contents, indent=2) + "\n",
        encoding="utf-8",
    )


def create_primary_icon_preview_set(source_icon: Path, destination: Path) -> None:
    """Create a normal image asset used by the in-app icon picker.

    An AppIcon asset is available to iOS as the primary application icon, but
    it cannot be loaded reliably through UIImage(named:). Keeping the picker
    preview separate lets the default icon remain a true primary icon while
    still providing a tappable image in Telegram's icon grid.
    """
    destination.mkdir(parents=True, exist_ok=True)
    images = []
    for scale, filename, pixels in PRIMARY_ICON_PREVIEW_IMAGES:
        resize_icon(source_icon, destination / filename, pixels)
        images.append({
            "idiom": "universal",
            "filename": filename,
            "scale": scale,
        })
    contents = {
        "images": images,
        "info": {"version": 1, "author": "xcode"},
    }
    (destination / "Contents.json").write_text(
        json.dumps(contents, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--legacy-source", type=Path, required=True,
                        help="Clean pinned 13.0 transformation input (never compiled)")
    args = parser.parse_args()

    source = args.source.resolve()
    if not (source / "Telegram" / "BUILD").exists() and not (source / "Telegram" / "BUILD.bazel").exists():
        raise SystemExit(f"Not a Telegram-iOS source tree: {source}")

    from upstream_13_2_pre import apply_upstream_13_2_pre
    apply_upstream_13_2_pre(source, Path(__file__).resolve().parent)
    from upstream_13_1 import apply_upstream_131
    apply_upstream_131(source, args.legacy_source.resolve())
    from quick_format_panel import apply_quick_format_panel
    apply_quick_format_panel(source, Path(__file__).resolve().parent)
    from debug_menu_localization import apply_debug_menu_localization
    apply_debug_menu_localization(source, Path(__file__).resolve().parent)
    from story_profile import apply_story_profile
    apply_story_profile(source, Path(__file__).resolve().parent)
    from quick_format_surface import apply_quick_format_surface
    apply_quick_format_surface(source, Path(__file__).resolve().parent)
    from broadcast_containers import apply_broadcast_containers
    apply_broadcast_containers(source, Path(__file__).resolve().parent)
    from protected_stories import apply_protected_stories
    apply_protected_stories(source, Path(__file__).resolve().parent)
    from app_icons import apply_app_icons
    apply_app_icons(source, Path(__file__).resolve().parent)
    from video_now_playing import apply_video_now_playing
    apply_video_now_playing(source, Path(__file__).resolve().parent)
    from video_rotation_registration import apply_video_rotation_registration
    apply_video_rotation_registration(source, Path(__file__).resolve().parent)
    from crash_report_bot import apply_crash_report_bot
    apply_crash_report_bot(source, Path(__file__).resolve().parent)
    from video_display_resume import apply_video_display_resume
    apply_video_display_resume(source, Path(__file__).resolve().parent)
    from quick_format_adaptive import apply_quick_format_adaptive
    apply_quick_format_adaptive(source, Path(__file__).resolve().parent)
    from broadcast_inline_topics import apply_broadcast_inline_topics
    apply_broadcast_inline_topics(source, Path(__file__).resolve().parent)
    from round_video_quality import apply_round_video_quality
    apply_round_video_quality(source, Path(__file__).resolve().parent)
    from settings_download_layout import apply_settings_download_layout
    apply_settings_download_layout(source, Path(__file__).resolve().parent)
    from round_video_sheet import apply_round_video_sheet
    apply_round_video_sheet(source, Path(__file__).resolve().parent)
    from quick_format_no_heading import apply_quick_format_no_heading
    apply_quick_format_no_heading(source, Path(__file__).resolve().parent)
    from quick_format_equal_spacing import apply_quick_format_equal_spacing
    apply_quick_format_equal_spacing(source, Path(__file__).resolve().parent)
    from pip_presentation import apply_pip_presentation
    apply_pip_presentation(source, Path(__file__).resolve().parent)
    from round_video_page import apply_round_video_page
    apply_round_video_page(source, Path(__file__).resolve().parent)
    from story_explicit_view import apply_story_explicit_view
    apply_story_explicit_view(source, Path(__file__).resolve().parent)
    from story_download_quality import apply_story_download_quality
    apply_story_download_quality(source, Path(__file__).resolve().parent)
    from story_icon_consistency import apply_story_icon_consistency
    apply_story_icon_consistency(source, Path(__file__).resolve().parent)
    from pip_native_transaction import apply_pip_native_transaction
    apply_pip_native_transaction(source, Path(__file__).resolve().parent)
    from round_video_refinement import apply_round_video_refinement
    apply_round_video_refinement(source, Path(__file__).resolve().parent)
    from recovery_storage_fixes import apply_recovery_storage_fixes
    apply_recovery_storage_fixes(source, Path(__file__).resolve().parent)
    from scheduled_archive_isolation import apply_scheduled_archive_isolation
    apply_scheduled_archive_isolation(source, Path(__file__).resolve().parent)
    from round_video_bitrate import apply_round_video_bitrate
    apply_round_video_bitrate(source, Path(__file__).resolve().parent)
    from pip_native_entry import apply_pip_native_entry
    apply_pip_native_entry(source, Path(__file__).resolve().parent)
    from message_translation import apply_message_translation
    apply_message_translation(source, Path(__file__).resolve().parent)
    from translation_free_modes import apply_translation_free_modes
    apply_translation_free_modes(source, Path(__file__).resolve().parent)
    from translation_gpt_oss import apply_translation_gpt_oss
    apply_translation_gpt_oss(source, Path(__file__).resolve().parent)
    from voice_transcription import apply_voice_transcription
    apply_voice_transcription(source, Path(__file__).resolve().parent)
    from release_076_sdk import apply_release_076_sdk
    apply_release_076_sdk(source, Path(__file__).resolve().parent)
    from release_076_dependencies import apply_release_076_dependencies
    apply_release_076_dependencies(source, Path(__file__).resolve().parent)
    from release_076_compile import apply_release_076_compile
    apply_release_076_compile(source, Path(__file__).resolve().parent)
    from release_076_import import apply_release_076_import
    apply_release_076_import(source, Path(__file__).resolve().parent)
    from video_ownership_fix import apply_video_ownership_fix
    apply_video_ownership_fix(source, Path(__file__).resolve().parent)
    from transcription_settings_refinement import apply_transcription_settings_refinement
    apply_transcription_settings_refinement(source, Path(__file__).resolve().parent)
    from transcription_settings_complete import apply_transcription_settings_complete
    apply_transcription_settings_complete(source, Path(__file__).resolve().parent)
    from translation_settings_revision import apply_translation_settings_revision
    apply_translation_settings_revision(source, Path(__file__).resolve().parent)
    from translation_completion import apply_translation_completion
    apply_translation_completion(source, Path(__file__).resolve().parent)
    from translation_sdk_fix import apply_translation_sdk_fix
    apply_translation_sdk_fix(source, Path(__file__).resolve().parent)
    from pip_removal_work import apply_pip_removal_work
    apply_pip_removal_work(source, Path(__file__).resolve().parent)
    from native_player_pip import apply_native_player_pip
    apply_native_player_pip(source, Path(__file__).resolve().parent)
    from media_privacy_fixes import apply_media_privacy_fixes
    apply_media_privacy_fixes(source, Path(__file__).resolve().parent)
    from translation_simplification import apply_translation_simplification
    apply_translation_simplification(source, Path(__file__).resolve().parent)
    from translation_inline_telegram import apply_translation_inline_telegram
    apply_translation_inline_telegram(source, Path(__file__).resolve().parent)
    from translation_premium_visibility import apply_translation_premium_visibility
    apply_translation_premium_visibility(source, Path(__file__).resolve().parent)
    from broadcast_stable_order import apply_broadcast_stable_order
    apply_broadcast_stable_order(source, Path(__file__).resolve().parent)
    from transcription_whisper_safety import apply_transcription_whisper_safety
    apply_transcription_whisper_safety(source, Path(__file__).resolve().parent)
    from transcription_cloud_ui import apply_transcription_cloud_ui
    apply_transcription_cloud_ui(source, Path(__file__).resolve().parent)
    from transcription_local_fallback import apply_transcription_local_fallback
    apply_transcription_local_fallback(source, Path(__file__).resolve().parent)
    from transcription_cloudflare import apply_transcription_cloudflare
    apply_transcription_cloudflare(source, Path(__file__).resolve().parent)
    from transcription_vosk import apply_transcription_vosk
    apply_transcription_vosk(source, Path(__file__).resolve().parent)
    from keyboard_transition import apply_keyboard_transition
    apply_keyboard_transition(source, Path(__file__).resolve().parent)
    from pip_readiness_fix import apply_pip_readiness_fix
    apply_pip_readiness_fix(source, Path(__file__).resolve().parent)
    from keyboard_handoff import apply_keyboard_handoff
    apply_keyboard_handoff(source, Path(__file__).resolve().parent)
    from transcription_context_refresh import apply_transcription_context_refresh
    apply_transcription_context_refresh(source, Path(__file__).resolve().parent)
    from repost_schedule import apply_repost_schedule
    apply_repost_schedule(source, Path(__file__).resolve().parent)
    from file_bubble_spacing import apply_file_bubble_spacing
    apply_file_bubble_spacing(source, Path(__file__).resolve().parent)
    from translation_speech_ui import apply_translation_speech_ui
    apply_translation_speech_ui(source, Path(__file__).resolve().parent)
    from speech_model_display import apply_speech_model_display
    apply_speech_model_display(source, Path(__file__).resolve().parent)
    from speech_cloudflare_display import apply_speech_cloudflare_display
    apply_speech_cloudflare_display(source, Path(__file__).resolve().parent)
    from speech_provider_permission import apply_speech_provider_permission
    apply_speech_provider_permission(source, Path(__file__).resolve().parent)
    from translation_chat_language import apply_translation_chat_language
    apply_translation_chat_language(source, Path(__file__).resolve().parent)
    from whisper_three_models import apply_whisper_three_models
    apply_whisper_three_models(source, Path(__file__).resolve().parent)
    from pip_asset_audio_recovery import apply_pip_asset_audio_recovery
    apply_pip_asset_audio_recovery(source, Path(__file__).resolve().parent)
    from formatting_keyboard_height import apply_formatting_keyboard_height
    apply_formatting_keyboard_height(source, Path(__file__).resolve().parent)
    from license_readable import apply_license_readable
    apply_license_readable(source, Path(__file__).resolve().parent)
    from pip_transition_surface import apply_pip_transition_surface
    apply_pip_transition_surface(source, Path(__file__).resolve().parent)
    from round_slider_touch import apply_round_slider_touch
    apply_round_slider_touch(source, Path(__file__).resolve().parent)
    from round_slider_kbps import apply_round_slider_kbps
    apply_round_slider_kbps(source, Path(__file__).resolve().parent)
    from speech_download_no_bar import apply_speech_download_no_bar
    apply_speech_download_no_bar(source, Path(__file__).resolve().parent)
    from whisper_footer_removal import apply_whisper_footer_removal
    apply_whisper_footer_removal(source, Path(__file__).resolve().parent)
    from provider_settings_consistency import apply_provider_settings_consistency
    apply_provider_settings_consistency(source, Path(__file__).resolve().parent)
    from remote_model_catalog import apply_remote_model_catalog
    apply_remote_model_catalog(source, Path(__file__).resolve().parent)
    from chat_russian_language_guard import apply_chat_russian_language_guard
    apply_chat_russian_language_guard(source, Path(__file__).resolve().parent)
    from translation_preferred_layout import apply_translation_preferred_layout
    apply_translation_preferred_layout(source, Path(__file__).resolve().parent)
    from translation_speech_text_only import apply_translation_speech_text_only
    apply_translation_speech_text_only(source, Path(__file__).resolve().parent)
    from translation_auto_flow import apply_translation_auto_flow
    apply_translation_auto_flow(source, Path(__file__).resolve().parent)
    from translation_language_search_alignment import apply_translation_language_search_alignment
    apply_translation_language_search_alignment(source, Path(__file__).resolve().parent)
    from translation_panel_visibility import apply_translation_panel_visibility
    apply_translation_panel_visibility(source, Path(__file__).resolve().parent)
    from transcription_link_accent import apply_transcription_link_accent
    apply_transcription_link_accent(source, Path(__file__).resolve().parent)
    from remove_groq import apply_remove_groq
    apply_remove_groq(source, Path(__file__).resolve().parent)
    from pip_readiness_observation import apply_pip_readiness_observation
    apply_pip_readiness_observation(source, Path(__file__).resolve().parent)
    from pip_playback_handoff import apply_pip_playback_handoff
    apply_pip_playback_handoff(source, Path(__file__).resolve().parent)
    from view_once_consumption_guard import apply_view_once_consumption_guard
    apply_view_once_consumption_guard(source, Path(__file__).resolve().parent)
    from view_once_archive_foundation import apply_view_once_archive_foundation
    apply_view_once_archive_foundation(source, Path(__file__).resolve().parent)
    from view_once_archive_render import apply_view_once_archive_render
    apply_view_once_archive_render(source, Path(__file__).resolve().parent)
    from view_once_copy_actions import apply_view_once_copy_actions
    apply_view_once_copy_actions(source, Path(__file__).resolve().parent)
    from view_once_receipt_queue import apply_view_once_receipt_queue
    apply_view_once_receipt_queue(source, Path(__file__).resolve().parent)
    from view_once_copy_marker import apply_view_once_copy_marker
    apply_view_once_copy_marker(source, Path(__file__).resolve().parent)
    from view_once_capture_on_receive import apply_view_once_capture_on_receive
    apply_view_once_capture_on_receive(source, Path(__file__).resolve().parent)
    from view_once_setting import apply_view_once_setting
    apply_view_once_setting(source, Path(__file__).resolve().parent)
    from view_once_preserve_capture import apply_view_once_preserve_capture
    apply_view_once_preserve_capture(source, Path(__file__).resolve().parent)
    from view_once_short_media import apply_view_once_short_media
    apply_view_once_short_media(source, Path(__file__).resolve().parent)
    from view_once_server_deletion import apply_view_once_server_deletion
    apply_view_once_server_deletion(source, Path(__file__).resolve().parent)
    from view_once_existing_in_chat import apply_view_once_existing_in_chat
    apply_view_once_existing_in_chat(source, Path(__file__).resolve().parent)
    from onboarding_privacy_text import apply_onboarding_privacy_text
    apply_onboarding_privacy_text(source, Path(__file__).resolve().parent)
    from unified_temporary_messages import apply_unified_temporary_messages
    apply_unified_temporary_messages(source, Path(__file__).resolve().parent)
    from copy_actions_consistency import apply_copy_actions_consistency
    apply_copy_actions_consistency(source, Path(__file__).resolve().parent)
    from pip_streaming import apply_pip_streaming
    apply_pip_streaming(source, Path(__file__).resolve().parent)
    from translation_manual_always import apply_translation_manual_always
    apply_translation_manual_always(source, Path(__file__).resolve().parent)
    from transcription_context_telegram import apply_transcription_context_telegram
    apply_transcription_context_telegram(source, Path(__file__).resolve().parent)
    from context_translation_toggles import apply_context_translation_toggles
    apply_context_translation_toggles(source, Path(__file__).resolve().parent)
    from emoji_keyboard_stability import apply_emoji_keyboard_stability
    apply_emoji_keyboard_stability(source, Path(__file__).resolve().parent)
    from story_preview_copy import apply_story_preview_copy
    apply_story_preview_copy(source, Path(__file__).resolve().parent)
    from author_selection_fix import apply_author_selection_fix
    apply_author_selection_fix(source, Path(__file__).resolve().parent)
    from pip_stream_request_lifetime import apply_pip_stream_request_lifetime
    apply_pip_stream_request_lifetime(source, Path(__file__).resolve().parent)
    from pip_transition_lifecycle import apply_pip_transition_lifecycle
    apply_pip_transition_lifecycle(source, Path(__file__).resolve().parent)
    from settings_labels import apply_settings_labels
    apply_settings_labels(source, Path(__file__).resolve().parent)
    from telegram_translation_defaults import apply_telegram_translation_defaults
    apply_telegram_translation_defaults(source, Path(__file__).resolve().parent)
    from single_player_pip import apply_single_player_pip
    apply_single_player_pip(source, Path(__file__).resolve().parent)
    from author_selection_icon import apply_author_selection_icon
    apply_author_selection_icon(source, Path(__file__).resolve().parent)
    from forward_single_person_icon import apply_forward_single_person_icon
    apply_forward_single_person_icon(source, Path(__file__).resolve().parent)
    from disable_next_swipe import apply_disable_next_swipe
    apply_disable_next_swipe(source, Path(__file__).resolve().parent)
    from deletion_effect_setting import apply_deletion_effect_setting
    apply_deletion_effect_setting(source, Path(__file__).resolve().parent)
    from pip_gallery_capture_fix import apply_pip_gallery_capture_fix
    apply_pip_gallery_capture_fix(source, Path(__file__).resolve().parent)
    from upright_author_icon import apply_upright_author_icon
    apply_upright_author_icon(source, Path(__file__).resolve().parent)
    from pip_mode_label import apply_pip_mode_label
    apply_pip_mode_label(source, Path(__file__).resolve().parent)
    from pip_caption_quotes import apply_pip_caption_quotes
    apply_pip_caption_quotes(source, Path(__file__).resolve().parent)
    from pip_gallery_native_gesture import apply_pip_gallery_native_gesture
    apply_pip_gallery_native_gesture(source, Path(__file__).resolve().parent)
    from pip_ghost_handoff import apply_pip_ghost_handoff
    apply_pip_ghost_handoff(source, Path(__file__).resolve().parent)
    from pip_active_gallery_restore import apply_pip_active_gallery_restore
    apply_pip_active_gallery_restore(source, Path(__file__).resolve().parent)
    from pip_ghost_source_layer import apply_pip_ghost_source_layer
    apply_pip_ghost_source_layer(source, Path(__file__).resolve().parent)
    from pip_no_status_wait import apply_pip_no_status_wait
    apply_pip_no_status_wait(source, Path(__file__).resolve().parent)
    from expanded_editor_stability import apply_expanded_editor_stability
    apply_expanded_editor_stability(source, Path(__file__).resolve().parent)
    from protected_copy_draft import apply_protected_copy_draft
    apply_protected_copy_draft(source, Path(__file__).resolve().parent)
    from author_check_badge_icon import apply_author_check_badge_icon
    apply_author_check_badge_icon(source, Path(__file__).resolve().parent)
    from protected_copy_selection_flow import apply_protected_copy_selection_flow
    apply_protected_copy_selection_flow(source, Path(__file__).resolve().parent)
    from protected_copy_send_timing import apply_protected_copy_send_timing
    apply_protected_copy_send_timing(source, Path(__file__).resolve().parent)
    from ghostgram_pip_replacement import apply_ghostgram_pip_replacement
    apply_ghostgram_pip_replacement(source, Path(__file__).resolve().parent)
    from ghostgram_pip_gallery_exact import apply_ghostgram_pip_gallery_exact
    apply_ghostgram_pip_gallery_exact(source, Path(__file__).resolve().parent)
    from ghostgram_pip_cleanup import apply_ghostgram_pip_cleanup
    apply_ghostgram_pip_cleanup(source, Path(__file__).resolve().parent)
    from rich_content_copy import apply_rich_content_copy
    apply_rich_content_copy(source, Path(__file__).resolve().parent)
    from gallery_export_privacy_gate import apply_gallery_export_privacy_gate
    apply_gallery_export_privacy_gate(source, Path(__file__).resolve().parent)
    from ghostgram_pip_compile_fix import apply_ghostgram_pip_compile_fix
    apply_ghostgram_pip_compile_fix(source, Path(__file__).resolve().parent)
    from archive_chat_scope import apply_archive_chat_scope
    apply_archive_chat_scope(source, Path(__file__).resolve().parent)
    from free_content import apply_free_content
    apply_free_content(source, Path(__file__).resolve().parent)
    from recipient_copy_isolation import apply_recipient_copy_isolation
    apply_recipient_copy_isolation(source, Path(__file__).resolve().parent)
    from inline_temporary_voice import apply_inline_temporary_voice
    apply_inline_temporary_voice(source, Path(__file__).resolve().parent)
    from expanded_keyboard_handoff import apply_expanded_keyboard_handoff
    apply_expanded_keyboard_handoff(source, Path(__file__).resolve().parent)
    from author_icon_variant_five import apply_author_icon_variant_five
    apply_author_icon_variant_five(source, Path(__file__).resolve().parent)
    from avatar_preview_navigation import apply_avatar_preview_navigation
    apply_avatar_preview_navigation(source, Path(__file__).resolve().parent)
    from system_video_pip import apply_system_video_pip
    apply_system_video_pip(source, Path(__file__).resolve().parent)
    # Системный PiP: экспериментальный hybrid_pip больше не включается в приложение.

    api_id = os.environ.get("TELEGRAM_API_ID", "")
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    if not api_id.isdigit() or not api_hash:
        raise SystemExit("TELEGRAM_API_ID and TELEGRAM_API_HASH must be configured")

    template = Path(__file__).with_name("configuration.template.json")
    configuration = json.loads(template.read_text(encoding="utf-8"))
    configuration["api_id"] = api_id
    configuration["api_hash"] = api_hash
    args.configuration.parent.mkdir(parents=True, exist_ok=True)
    args.configuration.write_text(json.dumps(configuration, indent=2) + "\n", encoding="utf-8")

    # This exact fragment is pinned to the audited Telegram-iOS commit. Failing
    # instead of guessing prevents a silent loss of branding after an update.
    build_file = source / "Telegram" / "BUILD"
    old_fragment = "<key>CFBundleDisplayName</key>\n    <string>Telegram</string>"
    new_fragment = "<key>CFBundleDisplayName</key>\n    <string>NagramiX</string>"
    if not replace_text(build_file, old_fragment, new_fragment):
        raise SystemExit("Pinned CFBundleDisplayName fragment was not found")

    old_region = "<key>CFBundleAllowMixedLocalizations</key>\n    <true/>\n    <key>CFBundleDevelopmentRegion</key>\n    <string>en</string>"
    new_region = old_region.replace("<string>en</string>", "<string>ru</string>")
    if not replace_text(build_file, old_region, new_region):
        raise SystemExit("Pinned application development-region fragment was not found")

    # Build the device app with its real identifier and generated build-only
    # profiles. Extensions stay out of the first login checkpoint.
    make_file = source / "build-system" / "Make" / "Make.py"
    anchor = "    bazel_command_line.set_configuration(arguments.configuration)"
    replacement = """    bazel_command_line.common_build_args += ['--//Telegram:disableExtensions']
    bazel_command_line.set_configuration(arguments.configuration)"""
    if not replace_text(make_file, anchor, replacement):
        raise SystemExit("Pinned unsigned-build anchor was not found in Make.py")

    icon_sources = Path(__file__).with_name("branding") / "AppIcons"
    icon_source = icon_sources / "1.png"
    # The primary icon must be an .appiconset for rules_apple. It is generated
    # from the same prepared source as the seven conventional alternate icons,
    # so all eight retain the same visual scale without using Icon Composer.
    create_primary_icon_set(
        icon_source,
        source / "Telegram" / "Telegram-iOS" / "AppIcons.xcassets" / "NagramiX1.appiconset",
    )
    create_primary_icon_preview_set(
        icon_source,
        source / "Telegram" / "Telegram-iOS" / "Icons.xcassets" / "NagramiX1Preview.imageset",
    )
    for index in range(2, 9):
        source_icon = icon_sources / f"{index}.png"
        if not source_icon.exists():
            raise SystemExit(f"Missing NagramiX icon source: {source_icon}")
        icon_name = f"NagramiX{index}"
        destination = source / "Telegram" / "Telegram-iOS" / f"{icon_name}.alticon"
        destination.mkdir(parents=True, exist_ok=True)
        for suffix, size in ALTERNATE_ICON_SIZES.items():
            resize_icon(source_icon, destination / f"{icon_name}{suffix}", size)

    print(f"Generated configuration: {args.configuration}")
    print(f"Applied NagramiX primary icon and picker preview from: {icon_source}")
    print("Applied 8 consistently prepared NagramiX system app icons")


if __name__ == "__main__":
    main()
