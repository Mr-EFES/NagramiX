#!/usr/bin/env python3
"""Verify default OFF and actual original bytes/native Video metadata."""
import argparse
import json
from pathlib import Path
import tempfile
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from validate_quick_format import block, manifest
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from original_video_media_apple import check as api_check
import original_video_media_runtime as runtime

STAGE = 'original_video_media'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'story_avatar_visibility'
    assert set(plan['inputs']) == {runtime.MEDIA, runtime.LEGACY} and len(plan['guards']) == 27
    assert not plan['copies'] and not plan['deletions']
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    old_settings = (OVERLAY / plan['previous'][runtime.MEDIA]).read_text()
    new_settings = (args.source / runtime.MEDIA).read_text()
    assert old_settings.replace('originalVideos: Bool = true', 'originalVideos: Bool = false', 1) == new_settings
    old = (OVERLAY / plan['previous'][runtime.LEGACY]).read_text()
    new = (args.source / runtime.LEGACY).read_text()
    marker = 'public func nagramiXOriginalVideoFile('
    old_export, export = block(old, marker), block(new, marker)
    assert old.replace(old_export, export, 1) == new, 'Unrelated legacy behavior changed'
    assert block(old, 'private func nagramiXOriginalVideoSupportsStreaming(') == block(new, 'private func nagramiXOriginalVideoSupportsStreaming(')
    mime = (args.source / 'submodules/MimeTypes/Sources/TGMimeTypeMap.m').read_text()
    assert 'extensionToMime[@"m4v"] = @"video/m4v"' in mime
    ui = (args.source / 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift').read_text()
    assert 'let isVideo = file.isVideo || (file.isAnimated && file.dimensions != nil)' in ui
    assert 'ChatMessageMediaBubbleContentNode.self' in ui
    messages = (args.source / 'submodules/TelegramUI/Components/ChatMediaSend/Sources/ChatMediaSendMessages.swift').read_text()
    assert 'isFile: false' in block(messages, 'func chatMediaSendMessage(')
    state = manifest(args.source)
    code = runtime.fixture(args.source)
    assert code.count(export) == 1
    with tempfile.TemporaryDirectory(prefix='original-video-media-') as folder:
        temp = Path(folder)
        refused = guard_checks(args.source, STAGE, plan, temp / 'guards')
        runs = execute(args.swiftc, temp, 'original-video-bytes-media', code)
        runs += execute(args.swiftc, temp, 'original-video-routing-final', runtime.routing_fixture(args.source))
        default = 'originalVideos: Bool = false'
        assert code.count(default) == 1
        runs += execute(args.swiftc, temp, 'old-default-on', code.replace(default, 'originalVideos: Bool = true', 1), 'fresh default is native compression OFF')
        runs += execute(args.swiftc, temp, 'original77-mime-whitelist', code.replace(export, old_export, 1), 'every Photos video retains native Video classification')
        metadata = '                attributes.append(.Video(duration: duration, size: dimensions, flags: flags, preloadSize: nil, coverTime: nil, videoCodec: nil))'
        assert code.count(metadata) == 1
        runs += execute(args.swiftc, temp, 'metadata-lost', code.replace(metadata, '                _ = (flags, duration)', 1), 'every Photos video retains native Video classification')
        native_api = api_check(args.source, args.swiftc, temp / 'native-api')
        run([args.swiftc, '-frontend', '-parse', *[args.source / n for n in plan['inputs']]])
    assert state == manifest(args.source)
    report = {
        'stage': STAGE, 'runtime_paths': list(plan['inputs']), 'loader_refusals': len(refused), 'guards': len(plan['guards']), 'executions': runs,
        'actual_settings_and_complete_exporter_api': native_api,
        'root_cause': 'The setting initializer still defaulted ON. The actual raw Photos exporter whitelisted only video/mp4 and video/quicktime for .Video; native video/m4v and other Photos video MIME values lost that attribute, so native file classification/upload selected document behavior.',
        'behavior': 'Missing persisted preference is OFF; saved explicit ON/OFF is retained. OFF keeps the existing Telegram compression pipeline. ON preserves raw Photos resource bytes and true MIME/filename with ordinary .Video metadata, inline preview and the native upload force_file bit unset.',
        'bytes_and_lifecycle': 'Actual FileHandle chunk writes, size/metadata construction, bounded BMFF streaming parser and hardlink/copy pin execute on genuine synthetic H.264/AAC MP4/MOV samples. Original bytes survive a deliberately deferred MediaBox move and post-send disposal. No encoder/remux path was added.',
        'scope_preserved': 'Modern/legacy sending, captions/entities, cover/spoiler/grouping, edited/special media policies, explicit send-as-file, decoder, audio, circles and archive behavior remain unchanged.',
        'boundaries': 'Photos delivery/UTI metadata, UIKit thumbnail/scaler and Telegram storage/API models are adapters. Native SignalKit, settings/exporter/parser/getters and force_file predicate are actual source. No real Photos library, server delivery/byte download, Apple SDK app compilation or physical iPhone was executed on Linux.',
        'new_actions_or_ipa_started': False, 'full_application_sdk': 'pending', 'physical_iphone': 'pending', 'source_unchanged_by_checks': True,
    }
    if args.report: args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
