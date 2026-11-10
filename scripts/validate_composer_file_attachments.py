#!/usr/bin/env python3
"""Проверить единый черновик текста и файлов и штатные варианты отправки до SDK."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import execute, run
import composer_file_attachments_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'composer_file_attachments'


def source_contract(source, plan):
    assert plan['required_previous_stage'] == 'bubble_selection_edge'
    assert set(plan['outputs']) == {runtime.MENU, runtime.NODE, runtime.SCAN, runtime.RICH}
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    current = {name: (source / name).read_text() for name in plan['outputs']}
    previous = {name: (ROOT / 'ios' / plan['previous'][name]).read_text() for name in plan['outputs']}
    # Verify real public declarations before allowing adapters to compile their call sites.
    core = 'submodules/TelegramCore/Sources/'
    native_file = (source / (core + 'SyncCore/SyncCore_TelegramMediaFile.swift')).read_text()
    assert 'public func withUpdatedPartialReference(_ partialReference: PartialMediaReference?) -> TelegramMediaFile' in native_file
    assert 'var isInstantVideo: Bool' in native_file
    reference = (source / (core + 'SyncCore/SyncCore_MediaReference.swift')).read_text()
    assert reference.count('public var partial: PartialMediaReference?') == 2
    enqueue = (source / (core + 'PendingMessages/EnqueueMessage.swift')).read_text()
    boundary = (ROOT / 'scripts/tests/NagramiXComposerFilesBoundary.swift').read_text()
    case = next(line.strip() for line in enqueue.splitlines() if line.strip().startswith('case message(text: String,'))
    assert case in boundary, 'Fixture EnqueueMessage case differs from the real native declaration'

    menu = current[runtime.MENU]
    attach = block(menu, '    func nagramiXAttachFilesToComposer(')
    assert 'editMessage == nil' in attach and 'files.count == references.count' in attach
    assert 'reference.partial ?? file.partialReference' in attach
    assert 'withUpdatedComposeInputState(draft)' in attach
    assert 'if silentPosting || scheduleTime != nil {' in attach
    assert 'sendCurrentMessage(silentPosting: silentPosting, scheduleTime: scheduleTime)' in attach
    assert all(marker not in attach for marker in ('clearInputText', 'withUpdatedReplyMessageSubject', 'sendMessages('))
    cloud = block(menu, '    func presentICloudFileGallery(')
    assert 'results.allSatisfy({ $0 != nil })' in cloud and 'pickerChatLocation' in cloud
    assert 'if editingMessage {' in cloud and 'editMessageMediaWithMessages(messages)' in cloud
    assert 'nagramiXAttachFilesToComposer(references)' in cloud
    assert 'strongSelf.sendMessages(' not in cloud and 'clearInputText' not in cloud
    for marker in ('premiumLimits.maxUploadFileParts', 'limits.maxUploadFileParts', 'ICloudFileResource(urlData: item.urlData', 'audioMetadata', 'hasMultiselection: !editingMessage'):
        assert cloud.count(marker) == block(previous[runtime.MENU], '    func presentICloudFileGallery(').count(marker), marker
    # Edit replacement, gallery Send and the complete expanded send pipeline remain their proven bytes.
    for marker in ('    func presentFileGallery(', '    private func presentFileMediaPicker(',
                   '    func presentRichTextAttachmentMenu(', '    private func sendAttachmentPreparedMediaMessages('):
        assert block(menu, marker) == block(previous[runtime.MENU], marker), marker
    attachment = block(menu, '    func presentAttachmentMenu(')
    old_attachment = block(previous[runtime.MENU], '    func presentAttachmentMenu(')
    rich_marker = '                    case .richText:'
    assert attachment[attachment.index(rich_marker):] == old_attachment[old_attachment.index(rich_marker):], 'Expanded send path changed'
    assert attachment.count('nagramiXAttachFilesToComposer(mediaReferences, caption: caption, initialState: inputState, silentPosting: silentPosting, scheduleTime: scheduleTime)') == 2
    assert attachment.count('controller.mediaPickerContext?.setCaption(inputText)') >= 2
    # Native menus continue taking actual AnyMediaReference and edit metadata; no secondary text enqueue.
    a = attachment.index('case .file:')
    b = attachment.index('case .location:', a)
    files_audio = attachment[a:b]
    assert 'self.sendMessages(' not in files_audio
    assert 'if isEditingMessage {' in files_audio
    prefix = menu[:menu.index('// Files stay in the structural draft until Send.')]
    old_prefix = previous[runtime.MENU][:previous[runtime.MENU].index('extension ChatControllerImpl {')]
    assert prefix == old_prefix
    normalized = menu[menu.index('extension ChatControllerImpl {'):]
    normalized = normalized.replace('    @discardableResult\n' + attach + '\n\n', '', 1)
    old_normalized = previous[runtime.MENU][previous[runtime.MENU].index('extension ChatControllerImpl {'):]
    for marker in ('    func presentAttachmentMenu(', '    func presentICloudFileGallery('):
        normalized = normalized.replace(block(normalized, marker), '<OWNED METHOD>')
        old_normalized = old_normalized.replace(block(old_normalized, marker), '<OWNED METHOD>')
    assert normalized == old_normalized, 'Unrequested attachment controller change'

    node = current[runtime.NODE]
    send = runtime.function(node, '    func sendCurrentMessage(')
    old_send = runtime.function(previous[runtime.NODE], '    func sendCurrentMessage(')
    assert 'min(4096, Int(self.context.userLimits.maxCaptionLength))' in send
    assert '&& nagramiXCaptionFiles == nil' in send
    assert 'if composeContent.allMedia.isEmpty, peerId?.namespace' in send
    assert 'formattingActions.remove(at: 1)' in send
    rich = block(send, 'else if sendAsRichMessage {').removeprefix('else ')
    assert rich.replace('instantPage(from: nagramiXSendContent)', 'instantPage(from: composeContent)') == block(old_send, 'if sendAsRichMessage {'), 'Rich serialization must retain every existing medium'
    assert '(!sendWithoutFormatting || !composeContent.allMedia.isEmpty)' in send
    assert 'sendWithoutFormatting: sendWithoutFormatting && composeContent.allMedia.isEmpty) == .rich' in send
    file_route = block(send, 'if let nagramiXCaptionFiles {')
    assert 'threadId: self.chatLocation.threadId, replyTo: nagramiXReplySubject' in file_route
    assert 'mediaReference = nil' in file_route
    assert 'guard !nagramiXFileMessages.isEmpty else {' in file_route
    assert 'sendMessages(' not in file_route
    assert block(node, '    private func updateRichMediaPreuploadNeeds(') == block(previous[runtime.NODE], '    private func updateRichMediaPreuploadNeeds(')
    # No other method changed in this large controller.
    assert node.replace(send, '<SEND>') == previous[runtime.NODE].replace(old_send, '<SEND>')

    old = '                        let file = fileReference.media\n'
    new = '                        let file = fileReference.media.withUpdatedPartialReference(fileReference.partial ?? fileReference.media.partialReference)\n'
    assert current[runtime.RICH].replace(new, old, 1) == previous[runtime.RICH]
    expanded_pick = block(current[runtime.RICH], '        private func pickMedia(')
    assert 'kind = .document' in expanded_pick and 'kind = .audio' in expanded_pick and 'kind = .video' in expanded_pick
    assert 'self.reconcilePreupload()' in expanded_pick
    scanner = current[runtime.SCAN]
    assert 'self.nagramiXAttachFilesToComposer(references)' in scanner
    assert 'self.sendMessages(' not in scanner
    new_footer = '''        let references = messages.compactMap { message -> AnyMediaReference? in
            if case let .message(_, _, _, reference, _, _, _, _, _, _) = message {
                return reference
            }
            return nil
        }
        self.nagramiXAttachFilesToComposer(references)'''
    old_footer = '        let transformedMessages = self.transformEnqueueMessages(messages)\n        self.sendMessages(transformedMessages)'
    assert scanner.replace(new_footer, old_footer, 1) == previous[runtime.SCAN], 'Scanner resources changed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    source_contract(args.source, plan)
    initial = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='composer-file-attachments-') as temporary:
        root = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, root / 'guards')
        text = runtime.fixture(args.source)
        results = execute(args.swiftc, root, 'composer-files', text)
        for name, mutated, diagnostic in runtime.negatives(text):
            results += execute(args.swiftc, root, name, mutated, diagnostic)
        for name in plan['outputs']:
            run([args.swiftc, '-frontend', '-parse', args.source / name])
    assert manifest(args.source) == initial
    report = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
              'loader_refusals': len(refusals), 'executions': results, 'swift_parse': len(plan['outputs']),
              'source_files': len(initial), 'source_unchanged_by_checks': True,
              'boundary': 'Production ChatInputContent model/selection/run replacement and ChatTextInputState value methods, file draft mutation, caption eligibility, native text-plan and enqueue builder execute together. The real controller insertion executes with only alert rendering and interface/display services adapted. UIKit, TextFormat rendering/Markdown internals, binary Postbox persistence, iCloud security scope, server and iPhone require native checks; these dependencies are pinned, not claimed simulated.',
              'apple_sdk': 'not_run', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
