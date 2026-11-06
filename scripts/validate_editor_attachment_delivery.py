#!/usr/bin/env python3
"""Проверить вложения расширенного редактора и исходный выбор preview при копировании."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
STAGE = 'editor_attachment_delivery'
PLAN = json.loads((OVERLAY / (STAGE + '_patches.json')).read_text())
CORE = 'submodules/TelegramCore/Sources/'
UPLOAD, PENDING, STANDALONE, EPHEMERAL, EDIT, COPY = PLAN['inputs']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    upload = (source / UPLOAD).read_text()
    route = block(upload, 'func messageContentToUpload(accountPeerId: PeerId, network: Network, postbox: Postbox, auxiliaryMethods: AccountAuxiliaryMethods, transformOutgoingMessageMedia: TransformOutgoingMessageMedia?, messageMediaPreuploadManager: MessageMediaPreuploadManager, revalidationContext: MediaReferenceRevalidationContext, forceReupload: Bool, isGrouped: Bool, passFetchProgress: Bool, forceNoBigParts: Bool, peerId: PeerId, messageId:')
    assert route.index('let richAttribute =') < route.index('case let .Loaded(content)')
    assert '!media.isEmpty && media.allSatisfy({ $0 is TelegramMediaWebpage })' in route
    assert route.count('richMessageContentToUpload(') == 2
    old = (OVERLAY / PLAN['previous'][UPLOAD]).read_text()
    assert block(upload, 'func richMessageContentToUpload(') == block(old, 'func richMessageContentToUpload(')
    resolver = block(upload, 'func uploadedRichMessage(')
    assert 'catch' not in resolver and 'PendingMessageUploadError' in resolver
    assert 'take(1)' in resolver
    for name in [PENDING, STANDALONE, EPHEMERAL]:
        assert 'content.resolvedRichMessage' in (source / name).read_text(), name
    assert 'return .error(.generic)' in (source / EDIT).read_text()
    # The native media uploader, expanded editor handoff, draft, grouping, rights,
    # fees, scheduling and playback remain exact dependencies, not reimplementations.
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_local_model_size(') < pipeline.index('    apply_editor_attachment_delivery(')


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location(STAGE, OVERLAY / (STAGE + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    apply = getattr(module, 'apply_' + STAGE)
    rejected = []

    def seed(label):
        tree = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name).read_bytes())
        return tree

    def reject(tree, label, overlay=OVERLAY):
        before = manifest(tree)
        try:
            apply(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == before, 'Partial write: ' + label
        rejected.append(label)

    valid = seed('valid')
    apply(valid, OVERLAY)
    assert all((valid / name).read_bytes() == (source / name).read_bytes() for name in PLAN['outputs'])
    reject(valid, 'repeat')
    for index, name in enumerate({**PLAN['inputs'], **PLAN['guards']}):
        for kind in ['missing', 'drift']:
            tree = seed(str(index) + '-' + kind)
            if kind == 'missing':
                (tree / name).unlink()
            else:
                (tree / name).write_bytes(b'drift')
            reject(tree, kind + ' ' + name)
    variants = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        variants.append((field, bad))
    for field in ['previous', 'replacements']:
        bad = copy.deepcopy(PLAN)
        bad[field][UPLOAD] = '../outside.swift'
        variants.append((field, bad))
    bad = copy.deepcopy(PLAN)
    bad['outputs'].clear()
    variants.append(('inconsistent', bad))
    for label, bad in variants:
        overlay = temp / ('overlay-' + label)
        for name in PLAN['templates']:
            path = overlay / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / name).read_bytes())
        (overlay / (STAGE + '_patches.json')).write_text(json.dumps(bad))
        reject(seed('source-' + label), label, overlay)
    for index, name in enumerate([UPLOAD, next(iter(PLAN['guards']))]):
        tree = seed('symlink-' + str(index))
        path = tree / name
        outside = temp / ('outside-' + str(index))
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        reject(tree, 'external symlink ' + name)
    return rejected


def upload_fixture(source):
    upload = (source / UPLOAD).read_text()
    fixture = (ROOT / 'scripts/tests/NagramiXEditorUploadBoundary.swift').read_text()
    route = block(upload, 'func messageContentToUpload(accountPeerId: PeerId, network: Network, postbox: Postbox, auxiliaryMethods: AccountAuxiliaryMethods, transformOutgoingMessageMedia: TransformOutgoingMessageMedia?, messageMediaPreuploadManager: MessageMediaPreuploadManager, revalidationContext: MediaReferenceRevalidationContext, forceReupload: Bool, isGrouped: Bool, passFetchProgress: Bool, forceNoBigParts: Bool, peerId: PeerId, messageId:')
    for marker, body in [
        ('UPLOADED_RECORD', block(upload, 'struct PendingMessageUploadedContentAndReuploadInfo')),
        ('PREVIEW_MERGE', block(upload, 'func nagramiXRichUploadWithPreview(')),
        ('UPLOAD_ROUTE', route),
        ('EDIT_RESOLVER', block(upload, 'func uploadedRichMessage(')),
        ('PENDING_HANDOFF', block((source / PENDING).read_text(), '                if let resolvedRichMessage = content.resolvedRichMessage')),
        ('STANDALONE_HANDOFF', block((source / STANDALONE).read_text(), '            if let resolvedRichMessage = content.resolvedRichMessage')),
    ]:
        fixture = fixture.replace('// PRODUCTION_' + marker, body)
    ephemeral = (source / EPHEMERAL).read_text()
    start = ephemeral.index('        case let .media(inputMedia, text):', ephemeral.index('private func sendPreparedEphemeralMessage') if 'private func sendPreparedEphemeralMessage' in ephemeral else 0)
    fixture = fixture.replace('// PRODUCTION_EPHEMERAL_HANDOFF', ephemeral[start:ephemeral.index('        case let .richMessage', start)])
    return fixture


def copy_fixture(source):
    from validate_recipient_copy_isolation import common_source
    from validate_message_copy_availability import poll_boundary, stripped
    common = common_source(source).replace('    var id = MessageId(); var text', '    var peers: [PeerId: Any] = [:]\n    var id = MessageId(); var text') + '\n' + poll_boundary(source)
    common = common.replace('struct NagramiXArchivedMessageAttribute: MessageAttribute {}', 'struct NagramiXArchivedMessageAttribute: MessageAttribute {var isTemporary=false}')
    common = common.replace('    func isCopyProtected() -> Bool { protected }', '    var isSelfExpiring: Bool { minAutoremoveOrClearTimeout != nil }; var paidContent: Media? {media.first{$0 is TelegramMediaPaidContent}}\n    func isCopyProtected() -> Bool { protected }')
    common = common.replace('    var isVoice: Bool {', '    var isVideo: Bool {attributes.contains("video")}\n    var isVoice: Bool {')
    common += '''
struct OutgoingContentInfoMessageAttribute: MessageAttribute {
    struct Flags: OptionSet { let rawValue: Int; static let disableLinkPreviews=Self(rawValue:1) }
    var flags: Flags
}
struct WebpagePreviewMessageAttribute: MessageAttribute { var leadingPreview: Bool; var forceLargeMedia: Bool? }
struct InvertMediaMessageAttribute: MessageAttribute {}
extension AnyMediaReference {
    var media: Media { switch self { case let .standalone(media): return media; case let .message(_,media): return media } }
}
'''
    # Same production predicate as the existing retained-media regression harness.
    from validate_temporary_media_actions import P
    helpers = block((source / P).read_text(), 'public func nagramiXCanUseTemporaryMediaActions(') + '\n'
    for name in [CORE + 'Utils/NagramiXContentCopy.swift', COPY, CORE + 'Utils/NagramiXArchivedMediaCopy.swift']:
        helpers += (source / name).read_text() + '\n'
    return common + '\n' + stripped(helpers) + '\n' + (ROOT / 'scripts/tests/NagramiXEditorCopyTests.swift').read_text()


def run_swift(source, swiftc, temp):
    upload = upload_fixture(source)
    copies = copy_fixture(source)
    variants = {
        'upload': upload,
        'copy': copies,
        'old-preview-skips-upload': upload.replace('!media.isEmpty && media.allSatisfy({ $0 is TelegramMediaWebpage })', 'media.isEmpty && media.allSatisfy({ $0 is TelegramMediaWebpage })'),
        'lost-resolved-files': upload.replace('combined.resolvedRichMessage = richMessage', 'combined.resolvedRichMessage = nil; _ = richMessage'),
        'pending-uses-bare-serializer': upload.replace('apiRichMessage = resolvedRichMessage', 'apiRichMessage = nil; _ = resolvedRichMessage', 1),
        'standalone-uses-bare-serializer': upload.replace(block(upload, 'func standaloneRich('), block(upload, 'func standaloneRich(').replace('apiRichMessage = resolvedRichMessage', 'apiRichMessage = nil; _ = resolvedRichMessage')),
        'ephemeral-loses-rich': upload.replace('richMessage = content.resolvedRichMessage', 'richMessage = nil'),
        'edit-strips-on-failure': upload.replace('    |> take(1)\n}', '    |> take(1)\n    |> `catch` { _ -> Signal<Api.InputRichMessage?, PendingMessageUploadError> in .single(richText.apiInputRichMessage()) }\n}'),
        'copy-generates-new-preview': copies.replace('attributes.append(OutgoingContentInfoMessageAttribute(flags: [.disableLinkPreviews]))', ''),
        'copy-loses-original-preview': copies.replace('if mediaReference == nil, let sourceWebpage {', 'if false, let sourceWebpage {'),
    }
    runs = []
    for label, text in variants.items():
        fixture = temp / (label + '.swift')
        fixture.write_text(text)
        for optimized in [False, True]:
            binary = temp / (label + ('-O' if optimized else '-debug'))
            subprocess.run([str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), *(['-O'] if optimized else []), str(fixture), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if label in ['upload', 'copy']:
                assert result.returncode == 0, result.stdout + result.stderr
                status = result.stdout.strip()
            else:
                assert result.returncode != 0 and 'regression:' in result.stderr, label + result.stdout + result.stderr
                status = 'regression reproduced and rejected'
            runs.append(binary.name + ': ' + status)
            print(runs[-1], flush=True)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'rich_draft_upload_retry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_transition_geometry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'transfer_consistency'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-editor-delivery-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp / 'guards')
        runtime = temp / 'runtime'
        runtime.mkdir()
        runs = run_swift(args.source, args.swiftc, runtime) if args.swiftc else []
        if args.swiftc:
            for name in PLAN['outputs']:
                subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    report = {'replacements': len(PLAN['outputs']), 'guards': len(PLAN['guards']), 'fail_closed': len(rejected), 'executions': runs, 'sdk': 'not run', 'device': 'pending', 'boundaries': 'Actual upload route, preview merge, edit resolver, pending/standalone/ephemeral handoffs and current full copy builder. IO, upload results, Postbox/API/Signals are explicit boundaries. Existing native uploads, editor keyboard/attachment handoff, archive effect and model sizes are exact guards.'}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
