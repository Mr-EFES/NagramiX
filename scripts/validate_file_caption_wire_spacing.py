#!/usr/bin/env python3
"""Проверить согласованную строку в file-caption обоих редакторов и геометрию."""
import argparse, json, subprocess, tempfile
from pathlib import Path
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from validate_private_temporary_transcription import execute
from late_source_stages import verified_prefix, LATE_SOURCE_STAGES
from file_caption_wire_apple import check as apple_check
import file_caption_wire_runtime as rt

STAGE = 'file_caption_wire_spacing'


def contracts(source):
    p = checked_plan(STAGE)
    assert set(p['inputs']) == {rt.T, rt.M, rt.N, rt.E, rt.F} and len(p['guards']) == 8 and len(p['templates']) == 18
    assert p['required_previous_stage'] == 'round_quality_horizontal_page' and not p['copies'] and not p['deletions']
    before = lambda n: (OVERLAY / p['previous'][n]).read_text()
    text = lambda n: (source / n).read_text()
    assert text(rt.T).startswith(before(rt.T)), 'Native text conversion/route changed'
    media = (source / 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaFile.swift').read_text()
    for name in ['isVoice', 'isInstantVideo', 'isVideo', 'isAnimated', 'isSticker']:
        assert 'public var ' + name + ': Bool' in media
    for marker in ['func nagramiXComposerFileDraft(', 'func nagramiXComposerCaptionFiles(', 'func nagramiXComposerSendContent(', 'private func nagramiXDocumentUsesNativeFileCaption(', '                        let buildRichTextMessages:', '                        let performRichTextSend:']:
        assert block(text(rt.M), marker) == block(before(rt.M), marker), marker
    restored = text(rt.M).replace(block(text(rt.M), 'func nagramiXComposerFileMessages('), block(before(rt.M), 'func nagramiXComposerFileMessages('), 1)
    old_call = 'let messages = nagramiXComposerFileMessages(files: files, caption: caption, inlineStickers: inlineStickers, threadId: threadId, replyTo: replyTo)'
    assert restored.replace(old_call[:-1] + ', maxCaptionLength: maxCaptionLength)', old_call, 1) == before(rt.M)
    old = 'replyTo: nagramiXReplySubject)'
    new = 'replyTo: nagramiXReplySubject, maxCaptionLength: min(4096, Int(self.context.userLimits.maxCaptionLength)))'
    assert text(rt.N).replace(new, old, 1) == before(rt.N), 'Other composer lifecycle changed'
    for marker in ['private func nagramiXEditableCaptionFile(']:
        assert block(text(rt.E), marker) == block(before(rt.E), marker)
    tail = '                var updatingMedia = false'
    a = text(rt.E).index(tail, text(rt.E).index('        }, editMessage:'))
    b = before(rt.E).index(tail, before(rt.E).index('        }, editMessage:'))
    assert text(rt.E)[a:] == before(rt.E)[b:], 'Media priority/RPC/pending/rights lifecycle changed'
    edit = text(rt.E)
    start = edit.index('                let nagramiXSpacingFile: TelegramMediaFile?')
    end = edit.index('                if nagramiXCaptionFile != nil {', start)
    restored = edit[:start] + edit[end:]
    trim = '                let text = trimChatInputText(convertMarkdownToAttributes(expandedInputStateAttributedString(editMessage.inputState.inputText)))\n\n'
    restored = restored.replace('                let content = editMessage.inputState.content', trim + '                let content = editMessage.inputState.content', 1)
    assert restored == before(rt.E), 'Other edit decision code changed'
    assert 'item.attributes.updatingMedia?.text ?? item.message.text' in text(rt.F)
    file = text(rt.F)
    file = file.replace('// The serialized blank caption line supplies the spacing in every client.\n' + block(file, 'private func nagramiXFileCaptionHasWireSpacing(') + '\n\n', '', 1)
    gate = block(file, '                            if !nagramiXFileCaptionHasWireSpacing(')
    legacy = '''                            // The caption follows a .text neighbour, so its own top inset is reduced by 2pt.
                            // Together both insets match the file's top padding; width stays unchanged.
                            let captionTopInset = max(0.0, layoutConstants.text.bubbleInsets.top - 2.0)
                            bottomInset = max(bottomInset, fileInsets.top - captionTopInset)'''
    assert file.replace(gate, legacy, 1) == before(rt.F), 'Unrelated file layout changed'
    for n in [rt.M, rt.N, rt.E, rt.F, rt.T]:
        assert [l for l in text(n).splitlines() if l.startswith('import ')] == [l for l in before(n).splitlines() if l.startswith('import ')]
    return {'runtime_paths': 5, 'new_app_files_strings_dependencies_postbox_consumers': 0,
            'native_ordinary_and_expanded_paths_preserved': True, 'file_caption_contains_one_serialized_line': True,
            'native_trim_markdown_then_utf16_shift': True, 'caption_limit_never_truncates_text': True,
            'rpc_pending_permissions_and_media_priority_unchanged': True,
            'classic_width_and_native_file_top_padding_unchanged': True,
            'pixel_equality_or_server_delivery_not_claimed': True}


def check(source, swiftc, folder):
    folder.mkdir(parents=True, exist_ok=True)
    contract = contracts(source)
    send, edit, geometry = rt.send_fixture(source), rt.edit_fixture(source), rt.geometry_fixture(source)
    runs = []
    for name, code in [('wire-send', send), ('wire-edit', edit), ('wire-geometry', geometry)]:
        runs += execute(swiftc, folder, name, code)
    negatives = []
    variants = [
        ('missing-wire-line', send, 'NSMutableAttributedString(string: "\\n")', 'NSMutableAttributedString(string: "")', 'both editors serialize the same approved spacing'),
        ('lost-entity-offset', send, 'entity.range.lowerBound + captionOffset', 'entity.range.lowerBound + captionOffset * 0', 'UTF16 ranges and named links remain exact'),
        ('exceed-caption-limit', send, 'text.length < maxCaptionLength', 'text.length <= maxCaptionLength', 'limit boundary keeps the complete caption'),
        ('repeat-wire-line', send, '!text.string.hasPrefix("\\n")', 'true', 'shared caption normalizer is idempotent'),
        ('skip-edit-spacing', edit, 'maxCaptionLength: min(4096, Int(strongSelf.context.userLimits.maxCaptionLength)))', 'maxCaptionLength: min(0, Int(strongSelf.context.userLimits.maxCaptionLength)))', 'both edit states keep the serialized caption line'),
        ('old-file-over-replacement', edit, 'nagramiXSpacingFile = replacement.media as? TelegramMediaFile', 'nagramiXSpacingFile = message.media.compactMap { $0 as? TelegramMediaFile }.first; _ = replacement', 'explicit replacement determines caption spacing'),
        ('duplicate-local-gap', geometry, 'if !nagramiXFileCaptionHasWireSpacing(', 'if true || !nagramiXFileCaptionHasWireSpacing(', 'wire line removes duplicate local padding'),
        ('ignore-pending-caption', geometry, 'item.attributes.updatingMedia?.text ?? item.message.text', 'item.message.text', 'pending edited caption uses its own spacing'),
    ]
    for name, code, old, new, why in variants:
        assert old in code, name
        negatives += execute(swiftc, folder, name, code.replace(old, new, 1), why)
    for name in checked_plan(STAGE)['inputs']:
        p = subprocess.run([str(swiftc), '-frontend', '-parse', str(source / name)], capture_output=True, text=True)
        assert p.returncode == 0, p.stdout + p.stderr
    return {'contracts': contract, 'executions': runs, 'semantic_negatives': negatives,
            'apple_api': apple_check(source, swiftc, folder / 'apple'),
            'boundary': 'Actual Document/clipboard/bridges/native Markdown/trim/split/entities, normal caller, standalone builder and edit decisions. Account/media, auto-detected-link parser, pending queue/RPC and renderer IO are explicit hosts; no live server or official-client pixels claimed.',
            'full_application_sdk': 'not_run', 'physical_iphone': 'pending', 'official_telegram_live_render': 'pending'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True); p.add_argument('--swiftc', type=Path, required=True); p.add_argument('--report', type=Path)
    a = p.parse_args(); assert verified_prefix(a.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    before = manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='caption-wire-') as d:
        root = Path(d); refused = guard_checks(a.source, STAGE, checked_plan(STAGE), root / 'guards')
        report = check(a.source, a.swiftc, root / 'runtime')
    assert manifest(a.source) == before
    report.update(stage=109, name=STAGE, loader_refusals=refused, source_unchanged_by_checks=True)
    if a.report: a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
