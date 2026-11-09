#!/usr/bin/env python3
"""Проверить оформление самостоятельных копий настоящим сборщиком payload."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_copy_delivery import clean, model_boundary
from validate_quick_format import block


CORE = 'submodules/TelegramCore/Sources/'
COPY = CORE + 'Utils/NagramiXOutgoingCopy.swift'
POLICY = CORE + 'Utils/NagramiXContentCopy.swift'
STAGER = CORE + 'Utils/NagramiXArchivedMediaCopy.swift'
RETENTION = CORE + 'Utils/NagramiXCaptureProtectionPolicy.swift'


TESTS = r'''
@main struct LocalCopyPayloadChecks {
    static func main() throws {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ label: String) {
            if !condition() {
                FileHandle.standardError.write(Data(("Local copy payload regression: " + label + "\n").utf8))
                exit(93)
            }
            checks += 1
        }
        let box = MediaBox()
        let account = Account(box)
        let sourceImage = TelegramMediaImage(representations: [.init(dimensions: .init(width: 120, height: 80), resource: CloudResource("image"))])
        let sourceVideo = TelegramMediaFile(resource: CloudResource("video"), size: 4, attributes: ["video"])
        let options = [
            TelegramMediaPollOption(text: "Первый", entities: [Entity(value: "first-entity")], opaqueIdentifier: Data([7]), media: nil, date: nil, addedBy: nil),
            TelegramMediaPollOption(text: "Второй", entities: [], opaqueIdentifier: Data([9]), media: nil, date: nil, addedBy: nil)
        ]
        let sourcePoll = TelegramMediaPoll(pollId: MediaId(namespace: 99, id: 704), publicity: .anonymous, kind: .poll(multipleAnswers: true), text: "Вопрос с видео", textEntities: [Entity(value: "question-entity")], options: options, correctAnswers: nil, results: .init(voters: nil, totalVoters: 77, recentVoters: [], solution: nil, hasUnseenVotes: nil, canViewStats: false), isClosed: false, deadlineTimeout: nil, deadlineDate: nil, pollHash: 888, attachedMedia: sourceVideo)
        let sourceKinds: [(String, Media)] = [("photo", sourceImage), ("video", sourceVideo), ("video-poll", sourcePoll), ("webpage", TelegramMediaWebpage())]
        for (name, medium) in sourceKinds {
            let hasWebpage = medium is TelegramMediaWebpage
            for inverted in [false, true] {
                for hidden in [false, true] {
                    var source = Message()
                    source.id.value = 72
                    source.text = "Подпись 😀 https://example.org/post"
                    source.media = [medium]
                    source.attributes = [
                        TextEntitiesMessageAttribute(entities: [Entity(value: "bold")]),
                        MediaSpoilerMessageAttribute(),
                        WebpagePreviewMessageAttribute(leadingPreview: true, forceLargeMedia: false),
                        ForwardSourceInfoAttribute()
                    ]
                    if inverted { source.attributes.append(InvertMediaMessageAttribute()) }
                    guard let single = nagramiXCopyMessagesAsNew([source], account: account, hideCaptions: hidden), single.count == 1 else {
                        check(false, "complete own payload produced for " + name); return
                    }
                    let payload = single[0]
                    let hidesCaption = hidden && !hasWebpage
                    let expectedInversion = inverted && !hidesCaption
                    check(payload.attributes.contains { $0 is InvertMediaMessageAttribute } == expectedInversion, hidesCaption ? "hidden caption removes its placement flag" : "caption placement is retained for ordinary media: " + name)
                    check(payload.attributes.filter { $0 is InvertMediaMessageAttribute }.count == (expectedInversion ? 1 : 0), "copy does not invent or duplicate caption placement")
                    let previews = payload.attributes.compactMap { $0 as? WebpagePreviewMessageAttribute }
                    check(previews.count == (hasWebpage ? 1 : 0), "preview attributes require a source webpage")
                    if let preview = previews.first {
                        check(preview.leadingPreview && preview.forceLargeMedia == false, "explicit source preview choice retained")
                    }
                    check(payload.text == (hidesCaption ? "" : source.text), "authored caption and links preserved")
                    check(payload.attributes.contains { $0 is TextEntitiesMessageAttribute } == !hidesCaption, "caption entities follow hide-caption choice")
                    check(payload.attributes.contains { $0 is MediaSpoilerMessageAttribute }, "source spoiler retained")
                    check(!payload.attributes.contains { $0 is ForwardSourceInfoAttribute }, "local copy never becomes a native forward")
                    let info = payload.attributes.compactMap { $0 as? OutgoingContentInfoMessageAttribute }.first!
                    check(info.flags.contains(.nagramiXCopy), "new authored copy retains transport marker")
                    check(info.flags.contains(.disableLinkPreviews) == !hasWebpage, "a bare link cannot create a new preview")
                    check(payload.replyToMessageId == nil && payload.threadId == nil, "source reply target is not reused")
                    guard let reference = payload.mediaReference else { check(false, "copy retains its media"); return }
                    if !hasWebpage {
                        if case .message = reference {} else { check(false, "ordinary own copy uses only technical media provenance") }
                    }
                    if let poll = reference.media as? TelegramMediaPoll {
                        check(poll.pollId != sourcePoll.pollId && poll.pollHash == 0, "poll receives fresh identity")
                        check(poll.results.totalVoters == nil && poll.results.voters == nil, "poll does not copy somebody else's votes")
                        check(poll.attachedMedia is TelegramMediaFile && poll.options.map { $0.opaqueIdentifier } == options.map { $0.opaqueIdentifier }, "video-poll keeps all attachment and option fields")
                    }
                    guard let batch = nagramiXPrepareRecipientCopies([source], account: account, recipientCount: 2, hideCaptions: hidden) else {
                        check(false, "recipient copies produced"); return
                    }
                    var template = batch.recipientMessages[0]
                    template[0] = template[0].withUpdatedAttributes { $0 + [NotificationInfoMessageAttribute(muted: true), OutgoingScheduleInfoMessageAttribute(time: 1234)] }
                    for index in 0 ..< 2 {
                        let recipient = batch.messages(forRecipientAt: index, template: template)![0]
                        check(recipient.attributes.contains { $0 is InvertMediaMessageAttribute } == expectedInversion, "recipient copy retains source caption placement")
                        check(recipient.attributes.contains { ($0 as? NotificationInfoMessageAttribute)?.muted == true }, "silent send retains copy presentation")
                        check(recipient.attributes.contains { ($0 as? OutgoingScheduleInfoMessageAttribute)?.time == 1234 }, "scheduled send retains copy presentation")
                        check(!recipient.attributes.contains { $0 is ForwardSourceInfoAttribute }, "broadcast recipient is still an own copy")
                    }
                    check(box.fetched.isEmpty && box.activeFetches == 0, "ordinary media provenance never forces a full download")
                }
            }
        }
        // An actual local upload uses new media identities and independent
        // temporary files; its caption placement must survive as well.
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let bytes = Data([1, 2, 3, 4])
        for name in ["image", "video"] {
            let path = root.appendingPathComponent(name)
            try bytes.write(to: path)
            box.paths[name] = path.path
        }
        var staged = Message()
        staged.text = "Локальная подпись"
        staged.media = [sourceVideo]
        staged.attributes = [InvertMediaMessageAttribute()]
        staged.groupingKey = 91
        var batch: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies([staged], account: account, recipientCount: 2, forceLocalMedia: true)
        check(batch != nil, "full local byte copies prepare")
        var paths: [String] = []
        withExtendedLifetime(batch) {
            let recipients = batch!.recipientMessages
            check(recipients[0][0].localGroupingKey != recipients[1][0].localGroupingKey, "local recipients have independent album identity")
            for recipient in recipients {
                check(recipient[0].attributes.contains { $0 is InvertMediaMessageAttribute }, "local byte copy retains caption placement")
                guard case let .standalone(media)? = recipient[0].mediaReference,
                      let file = media as? TelegramMediaFile,
                      let resource = file.resource as? LocalFileReferenceMediaResource else {
                    check(false, "local copy uses its own upload resource"); continue
                }
                paths.append(resource.localFilePath)
                check(file.fileId.namespace == Namespaces.Media.LocalFile && file.partialReference == nil, "local byte copy has no source cloud identity")
                check((try? Data(contentsOf: URL(fileURLWithPath: resource.localFilePath))) == bytes, "local byte copy retains full payload")
            }
            check(paths.count == 2 && paths[0] != paths[1], "local byte copies never share a movable path")
        }
        batch = nil
        check(paths.allSatisfy { !FileManager.default.fileExists(atPath: $0) }, "cancelled local batch rolls back its own files")
        print("Local copy payload checks: \(checks)")
    }
}
'''


def fixture(source):
    """Реальные copier/policy/stager; Postbox/API и оболочки медиа — адаптеры."""
    source = Path(source)
    policy = (source / POLICY).read_text().split('private enum NagramiXContentCopyFetchError')[0]
    copier = (source / COPY).read_text().split('/// Retrying a rejected copy')[0]
    retention = (source / RETENTION).read_text()
    temporary_policy = '''
extension Namespaces.Peer { static let CloudGroup: Int32 = 3 }
extension Namespaces.Message { static let SecretIncoming: Int32 = 7; static let Local: Int32 = 8 }
struct EphemeralOutgoingMessageAttribute: MessageAttribute {}
final class LocalCopyDefaultsBoundary {
    static let shared = LocalCopyDefaultsBoundary()
    func bool(forKey: String) -> Bool { false }
}
'''
    # Storage is outside this caption test; both existing switches are OFF.
    # Keep the real eligibility functions rather than inventing their producer.
    for marker in (
        'public func nagramiXTemporaryMessagesEnabled()',
        'private func nagramiXIsTemporaryMessage(attributes:',
        'private func nagramiXCanRetainTemporaryMessage(id:',
        'public func nagramiXCanRetainTemporaryMessage(_ message: Message)',
    ):
        temporary_policy += clean(block(retention, marker)).replace('UserDefaults.standard', 'LocalCopyDefaultsBoundary.shared') + '\n'
    return (model_boundary(source) + temporary_policy + clean(policy) + clean(copier)
            + clean((source / STAGER).read_text()) + '\n' + TESTS)


def fixtures(source):
    return {'LocalCopyPayload.swift': fixture(source)}


def semantic_negatives(swift):
    variants = (
        ('webpage-only-caption-position',
         '$0 is InvertMediaMessageAttribute || (sourceWebpage != nil && $0 is WebpagePreviewMessageAttribute)',
         'sourceWebpage != nil && ($0 is InvertMediaMessageAttribute || $0 is WebpagePreviewMessageAttribute)',
         'caption placement is retained for ordinary media'),
        ('unconditional-preview-attributes',
         '$0 is InvertMediaMessageAttribute || (sourceWebpage != nil && $0 is WebpagePreviewMessageAttribute)',
         '$0 is InvertMediaMessageAttribute || $0 is WebpagePreviewMessageAttribute',
         'preview attributes require a source webpage'),
        ('hidden-caption-position',
         'attributes.removeAll(where: { $0 is TextEntitiesMessageAttribute || $0 is InvertMediaMessageAttribute })',
         'attributes.removeAll(where: { $0 is TextEntitiesMessageAttribute })',
         'hidden caption removes its placement flag'),
    )
    for name, before, after, diagnostic in variants:
        assert swift.count(before) == 1, (name, swift.count(before))
        yield name, swift.replace(before, after), diagnostic


def validate(source, swiftc):
    results = []
    with tempfile.TemporaryDirectory(prefix='local-copy-payload-') as temporary:
        root = Path(temporary)
        current = fixture(source)
        variants = [('payload', current, None), *semantic_negatives(current)]
        for name, text, diagnostic in variants:
            path = root / (name + '.swift')
            path.write_text(text)
            for mode, flags in [('debug', []), ('optimized', ['-O'])]:
                binary = root / (name + '-' + mode)
                compiled = subprocess.run([str(swiftc), '-swift-version', '5', '-parse-as-library',
                                           '-warnings-as-errors', '-module-cache-path', str(root / 'cache'),
                                           *flags, str(path), '-o', str(binary)],
                                          capture_output=True, text=True)
                assert compiled.returncode == 0, compiled.stdout + compiled.stderr
                result = subprocess.run([str(binary)], text=True, capture_output=True, timeout=60,
                                        preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
                if diagnostic is None:
                    assert result.returncode == 0, result.stdout + result.stderr
                else:
                    assert result.returncode == 93 and diagnostic in result.stderr, (name, result.stdout + result.stderr)
                results.append({'name': name, 'mode': mode, 'exit_code': result.returncode,
                                'output': (result.stdout + result.stderr).strip()})
                binary.unlink()
    return {'executions': results,
            'boundary': 'Actual production copy builder, recipient batch, policies and file staging; '
                        'real Foundation file I/O. Media values, Postbox and network are explicit '
                        'adapters. No Telegram delivery, UIKit or Apple SDK claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = validate(args.source, args.swiftc)
    output = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.write_text(output)
    print(output, end='')
