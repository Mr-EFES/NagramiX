#!/usr/bin/env python3
"""Проверить целые опросы, вложения и сохранение локального архива."""
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
from validate_copy_delivery import clean, model_boundary, preparation_fixture

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
STAGE = 'extended_poll_integrity'
PLAN = json.loads((OVERLAY / (STAGE + '_patches.json')).read_text())
CORE = 'submodules/TelegramCore/Sources/'
POLICY = CORE + 'Utils/NagramiXContentCopy.swift'
COPIER = CORE + 'Utils/NagramiXOutgoingCopy.swift'
STAGER = CORE + 'Utils/NagramiXArchivedMediaCopy.swift'
ARCHIVE = CORE + 'Utils/NagramiXMessageArchive.swift'
NODE = 'submodules/TelegramUI/Sources/ChatControllerNode.swift'
UPLOAD = CORE + 'PendingMessages/PendingMessageUploadedContent.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source):
    assert PLAN['inputs'].keys() == PLAN['outputs'].keys() == PLAN['previous'].keys() == PLAN['replacements'].keys()
    for n, h in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / n).read_bytes()) == h, n
    for n, h in PLAN['templates'].items():
        assert sha((OVERLAY / n).read_bytes()) == h, n
    before = (OVERLAY / PLAN['previous'][ARCHIVE]).read_text()
    after = (source / ARCHIVE).read_text()
    # Two-phase deletion, tombstones, Undo and durable purge are independent
    # of the newly supported payload. Keep their real implementations intact.
    for marker in ['public func archiveMessagesBeforeDeletion(', 'public func removeLocal(',
                   'public func clearAll(', 'public func archiveServerDeletion(messageIds:',
                   'public func postDeletionPlan(', 'public func purgeLocal(',
                   'private func renderDeletedRecord(']:
        if marker in before:
            assert block(before, marker) == block(after, marker), marker
    for marker in ['private func localImage(', 'private func localFile(', 'private static func encodedRootObject(',
                   'private static func decodedRootObject(']:
        assert block(before, marker) == block(after, marker), marker
    old = (OVERLAY / PLAN['previous'][COPIER]).read_text()
    new = (source / COPIER).read_text()
    old_poll = block(old, 'private func nagramiXCopyPollAsNew(')
    new_poll = block(new, 'private func nagramiXCopyPollAsNew(')
    assert old_poll.replace('$0 is TelegramMediaImage || $0 is TelegramMediaFile })', '$0 is TelegramMediaImage || $0 is TelegramMediaFile || pollCloudMediaToInputMedia($0) != nil })') == new_poll
    assert block(old, 'public final class NagramiXRecipientCopyBatch') == block(new, 'public final class NagramiXRecipientCopyBatch')
    assert block(old, 'public func nagramiXPrepareRecipientCopies(') == block(new, 'public func nagramiXPrepareRecipientCopies(')
    old_upload = (OVERLAY / PLAN['previous'][UPLOAD]).read_text()
    new_upload = (source / UPLOAD).read_text()
    expected = '''        for media in attachments {
            if media is TelegramMediaImage || media is TelegramMediaFile {
                guard let id = media.id else { return .fail(.generic) }
                unique[id] = media
            } else if pollCloudMediaToInputMedia(media) == nil {
                return .fail(.generic)
            }
        }'''
    assert old_upload.replace('        for media in attachments { if let id = media.id { unique[id] = media } }', expected) == new_upload


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location(STAGE, OVERLAY / (STAGE + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []

    def seed(label):
        target = temp / label
        for n in {**PLAN['inputs'], **PLAN['guards']}:
            origin = OVERLAY / PLAN['previous'][n] if n in PLAN['previous'] else source / n
            p = target / n
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(origin.read_bytes())
        return target

    def reject(target, label, overlay=OVERLAY):
        before = manifest(target)
        try:
            module.apply_extended_poll_integrity(target, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid stage accepted: ' + label)
        assert manifest(target) == before, 'Partial writes: ' + label
        rejected.append(label)

    target = seed('valid')
    module.apply_extended_poll_integrity(target, OVERLAY)
    assert all((target / n).read_bytes() == (source / n).read_bytes() for n in PLAN['outputs'])
    reject(target, 'repeat')
    for n in {**PLAN['inputs'], **PLAN['guards']}:
        for kind in ['missing', 'drift']:
            target = seed(str(len(rejected)))
            p = target / n
            if kind == 'missing':
                p.unlink()
            else:
                p.write_bytes(p.read_bytes() + b'\n// drift\n')
            reject(target, kind + ' ' + n)
    mutations = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        mutations.append((field + '-sha', bad))
    for field in ['previous', 'replacements']:
        bad = copy.deepcopy(PLAN)
        bad[field][POLICY] = '../outside.swift'
        mutations.append((field + '-traversal', bad))
    bad = copy.deepcopy(PLAN)
    for field in ['inputs', 'outputs', 'previous', 'replacements']:
        bad[field]['/outside.swift'] = bad[field].pop(POLICY)
    mutations.append(('absolute-source', bad))
    for label, plan in mutations:
        overlay = temp / ('bad-' + label)
        for n in PLAN['templates']:
            p = overlay / n
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((OVERLAY / n).read_bytes())
        (overlay / (STAGE + '_patches.json')).write_text(json.dumps(plan))
        reject(seed('tree-' + label), label, overlay)
    for n in [POLICY, next(iter(PLAN['guards']))]:
        target = seed('symlink-' + str(len(rejected)))
        p = target / n
        external = temp / ('outside-' + str(len(rejected)))
        external.write_bytes(p.read_bytes())
        p.unlink()
        p.symlink_to(external)
        reject(target, 'external symlink ' + n)
    return rejected


def fixture(source, mode):
    policy = (source / POLICY).read_text()
    copier = (OVERLAY / PLAN['previous'][COPIER] if mode == 'old-copier' else source / COPIER).read_text()
    stager = (OVERLAY / PLAN['previous'][STAGER] if mode == 'old-stager' else source / STAGER).read_text()
    archive = (OVERLAY / PLAN['previous'][ARCHIVE] if mode == 'old-archive' else source / ARCHIVE).read_text()
    node = (OVERLAY / PLAN['previous'][NODE] if mode == 'old-preview' else source / NODE).read_text()
    upload = (OVERLAY / PLAN['previous'][UPLOAD] if mode == 'old-native-upload' else source / UPLOAD).read_text()
    encoded = block(archive, '        let media = message.media.compactMap { media -> Data? in')
    mapped = block(archive, '    private func localMedia(')
    request = block(block(archive, '    private func mediaRequests('), '            if let poll = media as? TelegramMediaPoll') if 'if let poll = media as? TelegramMediaPoll' in block(archive, '    private func mediaRequests(') else ''
    preview = next(line.strip() for line in node.splitlines() if 'updatedMedia.append(TelegramMediaPoll(' in line)
    upload_start = upload.index('        var unique: [MediaId: Media] = [:]')
    upload_end = upload.index('        let ordered = Array(unique)', upload_start)
    upload_collection = upload[upload_start:upload_end].replace('return .fail(.generic)', 'return nil').replace('return .single(assemble([:]))', 'return []')
    probes = '''
final class ArchivePollProbe {
    private static func encodedRootObject(_ media: Media) -> Data { Data(String(describing: type(of: media)).utf8) }
    static func encodedMedia(_ message: Message) -> [Data] {
''' + encoded + '''
        return media
    }
    func localImage(_ image: TelegramMediaImage) -> TelegramMediaImage {
        TelegramMediaImage(imageId: image.imageId, representations: image.representations.map { TelegramMediaImageRepresentation(dimensions: $0.dimensions, resource: CloudResource("retained:" + $0.resource.id.stringRepresentation)) }, reference: nil, partialReference: nil)
    }
    func localFile(_ file: TelegramMediaFile) -> TelegramMediaFile {
        TelegramMediaFile(fileId: file.fileId, partialReference: nil, resource: CloudResource("retained:" + file.resource.id.stringRepresentation), size: file.size, attributes: file.attributes)
    }
''' + mapped + '''
    func retained(_ media: Media) -> Media { self.localMedia(media) }
    func resources(_ poll: TelegramMediaPoll) -> [String] {
        let media: Media = poll
        let message = Message()
        let reference = MessageReference(message)
        var mediaReference = AnyMediaReference.message(message: reference, media: media)
        var result: [String] = []
        func appendImage(_ image: TelegramMediaImage) { result.append(contentsOf: image.representations.map { $0.resource.id.stringRepresentation }) }
        func appendFile(_ file: TelegramMediaFile) { result.append(file.resource.id.stringRepresentation) }
''' + request + '''
        _ = mediaReference
        return result
    }
}
func previewPoll(_ poll: TelegramMediaPoll) -> TelegramMediaPoll {
    var updatedMedia: [Media] = []
''' + preview + '''
    return updatedMedia[0] as! TelegramMediaPoll
}
func nativePollUploads(_ poll: TelegramMediaPoll, forceReupload: Bool) -> [Media]? {
''' + upload_collection + '''
    return Array(unique.values)
}
'''
    if not request:
        probes = probes.replace('var mediaReference = AnyMediaReference.message', 'let mediaReference = AnyMediaReference.message')
    base = model_boundary(source)
    # Media identity and TL conversion are explicit native boundaries. Their
    # real declarations/converter remain pinned dependencies; no custom API is
    # added to production doubles merely to satisfy a missing member.
    base = base.replace('protocol Media {}', 'protocol Media { var id: MediaId? { get } }\nextension Media { var id: MediaId? { nil } }')
    base = base.replace('struct TelegramMediaWebpage: Media {}', 'struct TelegramMediaWebpage: Media { var id: MediaId? = MediaId(namespace: 9, id: 77); var convertibleURL = false }')
    base = base.replace('    if media is TelegramMediaMap { return 1 }', '    if media is TelegramMediaMap { return 1 }\n    if let page = media as? TelegramMediaWebpage, page.convertibleURL { return 1 }')
    base += '\nextension TelegramMediaImage { var id: MediaId? { imageId } }\nextension TelegramMediaFile { var id: MediaId? { fileId } }\n'
    return base + clean(policy.split('private enum NagramiXContentCopyFetchError')[0]) + clean(copier.split('/// Retrying a rejected copy')[0]) + clean(stager) + probes + PAYLOAD_TESTS


PAYLOAD_TESTS = r'''
func pollSample() -> TelegramMediaPoll {
    let q = TelegramMediaImage(representations: [TelegramMediaImageRepresentation(dimensions: Dimensions(width: 40, height: 60), resource: CloudResource("question"))])
    let a = TelegramMediaFile(resource: CloudResource("option-a"), size: 4, attributes: ["video"])
    let b = TelegramMediaFile(resource: CloudResource("option-b"), size: 4, attributes: ["audio"])
    let s = TelegramMediaImage(representations: [TelegramMediaImageRepresentation(dimensions: Dimensions(width: 90, height: 60), resource: CloudResource("solution"))])
    let options = [TelegramMediaPollOption(text: "Первый", entities: [Entity(value: "bold")], opaqueIdentifier: Data([1]), media: a, date: 9, addedBy: PeerId(value: 91)), TelegramMediaPollOption(text: "Второй", entities: [Entity(value: "italic")], opaqueIdentifier: Data([2]), media: b, date: 10, addedBy: PeerId(value: 92))]
    let results = TelegramMediaPollResults(voters: [TelegramMediaPollOptionVoters(selected: true, opaqueIdentifier: Data([1]), count: 42, isCorrect: true, recentVoters: [PeerId(value: 93)])], totalVoters: 42, recentVoters: [PeerId(value: 94)], solution: TelegramMediaPollResults.Solution(text: "Объяснение", entities: [Entity(value: "link")], media: s), hasUnseenVotes: true, canViewStats: true)
    return TelegramMediaPoll(pollId: MediaId(namespace: 99, id: 42), publicity: .public, kind: .quiz(multipleAnswers: true), text: "Вопрос 😀", textEntities: [Entity(value: "question-entity")], options: options, correctAnswers: [Data([1])], results: results, isClosed: true, deadlineTimeout: 30, deadlineDate: 200, pollHash: 998, openAnswers: true, revotingDisabled: true, shuffleAnswers: true, hideResultsUntilClose: true, isCreator: false, attachedMedia: q, restrictToSubscribers: true, countries: ["RU", "DE"])
}
func attachmentNames(_ poll: TelegramMediaPoll) -> [String] {
    nagramiXPollMediaAttachments(poll).compactMap { media in
        if let file = media as? TelegramMediaFile { return file.resource.id.stringRepresentation }
        return (media as? TelegramMediaImage)?.representations.first?.resource.id.stringRepresentation
    }
}
@main struct ExtendedPollPayloadTests {
    static func main() throws {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) {
            if !value() { FileHandle.standardError.write(Data(("Extended poll regression: " + label + "\n").utf8)); exit(91) }
            checks += 1
        }
        let original = pollSample()
        let names = ["question", "option-a", "option-b", "solution"]
        var transformed: [String] = []
        let mapped = nagramiXMapPollMedia(original) { media in
            if let file = media as? TelegramMediaFile { transformed.append(file.resource.id.stringRepresentation) }
            if let image = media as? TelegramMediaImage { transformed.append(image.representations[0].resource.id.stringRepresentation) }
            return media
        }!
        check(transformed == names && attachmentNames(mapped) == names, "all slots and their order")
        check(mapped.pollId == original.pollId && mapped.pollHash == original.pollHash, "archive identity and hash preserved")
        check(mapped.publicity == original.publicity && mapped.correctAnswers == original.correctAnswers, "publicity and known answers preserved")
        if case let .quiz(multiple) = mapped.kind { check(multiple, "quiz kind and multiple answers") } else { check(false, "quiz kind") }
        check(mapped.text == original.text && mapped.textEntities.map { $0.value } == ["question-entity"], "question and entities")
        check(mapped.options.map { $0.text } == original.options.map { $0.text }, "options text and order")
        check(mapped.options.map { $0.opaqueIdentifier } == original.options.map { $0.opaqueIdentifier }, "opaque identifiers")
        check(mapped.options.map { $0.entities.first!.value } == ["bold", "italic"], "option entities")
        check(mapped.options.map { $0.date } == [9, 10] && mapped.options.map { $0.addedBy!.value } == [91, 92], "archive authors and dates")
        check(mapped.results.totalVoters == 42 && mapped.results.voters?.first?.selected == true, "archive votes remain snapshot")
        check(mapped.results.recentVoters.map { $0.value } == [94] && mapped.results.voters?.first?.recentVoters.first?.value == 93, "archive voter metadata")
        check(mapped.results.solution?.text == "Объяснение" && mapped.results.solution?.entities.first?.value == "link", "solution metadata")
        check(mapped.results.hasUnseenVotes == true && mapped.results.canViewStats, "result flags preserved")
        check(mapped.isClosed && mapped.deadlineTimeout == 30 && mapped.deadlineDate == 200, "archive closed state and deadlines")
        check(mapped.openAnswers && mapped.revotingDisabled && mapped.shuffleAnswers && mapped.hideResultsUntilClose, "extended behavior flags")
        check(!mapped.isCreator && mapped.restrictToSubscribers && mapped.countries == ["RU", "DE"], "creator and eligibility metadata")
        for failedSlot in 0..<4 {
            var position = 0
            let failed = nagramiXMapPollMedia(original) { media in defer { position += 1 }; return position == failedSlot ? nil : media }
            check(failed == nil, "failed required slot rejects whole poll")
        }
        let probe = ArchivePollProbe()
        var post = Message(); post.media = [original]; post.groupingKey = 77; post.text = "Подпись https://example.org"; post.attributes = [TextEntitiesMessageAttribute(entities: [Entity(value: "caption-entity")])]
        check(ArchivePollProbe.encodedMedia(post).count == 1, "archive persists intact poll")
        check(probe.resources(original) == names, "archive reserves every nested attachment")
        let retained = probe.retained(original) as! TelegramMediaPoll
        check(attachmentNames(retained) == names.map { "retained:" + $0 }, "archive display uses retained resources in every slot")
        check(retained.pollId == original.pollId && retained.results.totalVoters == 42, "archive resource mapping preserves metadata")
        let preview = previewPoll(original)
        check(attachmentNames(preview) == names, "preview keeps every attachment")
        check(preview.openAnswers && preview.revotingDisabled && preview.shuffleAnswers && preview.hideResultsUntilClose, "preview keeps extended flags")
        check(preview.restrictToSubscribers && preview.countries == ["RU", "DE"], "preview keeps eligibility")
        check(preview.results.totalVoters == nil && preview.results.solution?.text == "Объяснение", "new copy preview resets votes but keeps solution")
        let box = MediaBox(); let account = Account(box)
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let file = root.appendingPathComponent("source"); let bytes = Data([1,2,3,4]); try bytes.write(to: file)
        for name in names { box.paths[name] = file.path }
        var page = TelegramMediaWebpage(); page.convertibleURL = true
        let local = LocalFileReferenceMediaResource(localFilePath: file.path, randomId: 17, isUniquelyReferencedTemporaryFile: false, size: 4)
        let localPhoto = TelegramMediaImage(representations: [TelegramMediaImageRepresentation(dimensions: Dimensions(width: 20, height: 30), resource: local)], reference: nil, partialReference: nil)
        var mediaSlot = 0
        let mixedPoll = nagramiXMapPollMedia(original) { _ in defer { mediaSlot += 1 }; return mediaSlot == 1 ? page : localPhoto }!
        for force in [false, true] {
            let uploads = nativePollUploads(mixedPoll, forceReupload: force)
            check(uploads?.count == 1 && uploads?.allSatisfy { $0 is TelegramMediaImage } == true, "native mixed local photo and URL uploads only byte attachments")
        }
        let urlPoll = nagramiXMapPollMedia(original) { _ in page }!
        check(nativePollUploads(urlPoll, forceReupload: true)?.isEmpty == true, "native URL-only forced retry needs no byte uploader")
        let noURL = nagramiXMapPollMedia(original) { _ in TelegramMediaWebpage() }!
        check(nativePollUploads(noURL, forceReupload: true) == nil, "native unresolved URL slot fails before partial assembly")
        post.media = [urlPoll]; post.protected = true
        check(nagramiXPrepareRecipientCopies([post], account: account, recipientCount: 2)?.recipientMessages.count == 2, "supported URL poll copies from protected source")
        post.media = [noURL]
        check(nagramiXPrepareRecipientCopies([post], account: account, recipientCount: 2) == nil, "unresolved URL poll is never silently truncated")
        post.media = [original]
        for protected in [false, true] {
            post.protected = protected
            var batch: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies([post], account: account, recipientCount: 2)
            check(batch?.recipientMessages.count == 2 && batch?.recipientMessages.allSatisfy { $0.count == 1 } == true, "one intact poll per recipient")
            var paths: [Set<String>] = []
            for recipient in batch!.recipientMessages {
                let copy = recipient[0]
                check(copy.text == post.text && copy.attributes.compactMap { $0 as? TextEntitiesMessageAttribute }.first?.entities.first?.value == "caption-entity", "caption and entities stay attached")
                let poll = copy.mediaReference!.media as! TelegramMediaPoll
                check(poll.pollId.namespace == Namespaces.Media.LocalPoll && poll.pollId != original.pollId, "independent local poll identity")
                check(poll.results.voters == nil && poll.results.totalVoters == nil && poll.results.recentVoters.isEmpty, "new poll does not copy old votes")
                check(!poll.isClosed && poll.deadlineDate == nil && poll.deadlineTimeout == nil && poll.pollHash == 0 && poll.isCreator, "new poll lifetime and creator")
                check(poll.options.allSatisfy { $0.date == nil && $0.addedBy == nil }, "new options do not impersonate old authors")
                check(poll.correctAnswers == [Data([1])] && poll.results.solution?.text == "Объяснение", "known quiz answer and explanation retained")
                if protected {
                    var current: Set<String> = []
                    for media in nagramiXPollMediaAttachments(poll) {
                        let resource = (media as? TelegramMediaFile)?.resource ?? (media as! TelegramMediaImage).representations[0].resource
                        check(resource is LocalFileReferenceMediaResource, "protected nested media is independent local upload")
                        let local = resource as! LocalFileReferenceMediaResource
                        let copiedBytes = try Data(contentsOf: URL(fileURLWithPath: local.localFilePath))
                        check(copiedBytes == bytes, "staged nested bytes intact")
                        current.insert(local.localFilePath)
                    }
                    paths.append(current)
                } else {
                    check(attachmentNames(poll) == names, "ordinary cloud poll avoids full download")
                }
            }
            if protected { check(paths[0].isDisjoint(with: paths[1]), "recipient nested staging files are independent") }
            batch = nil
            for path in paths.flatMap({ $0 }) { check(!FileManager.default.fileExists(atPath: path), "cancel rolls back nested staging") }
        }
        post.protected = true
        box.paths.removeValue(forKey: "solution")
        check(nagramiXPrepareRecipientCopies([post], account: account, recipientCount: 2) == nil, "missing nested bytes reject full recipient batch")
        let locationPoll = nagramiXMapPollMedia(original) { _ in TelegramMediaMap() }!
        for protected in [false, true] {
            post.protected = protected; post.media = [locationPoll]
            let locationBatch = nagramiXPrepareRecipientCopies([post], account: account, recipientCount: 2)
            check(locationBatch?.recipientMessages.count == 2, "native supported poll locations copy without local files")
            let copied = locationBatch!.recipientMessages[0][0].mediaReference!.media as! TelegramMediaPoll
            check(nagramiXPollMediaAttachments(copied).allSatisfy { $0 is TelegramMediaMap }, "all location slots preserved")
        }
        let unsupported = nagramiXMapPollMedia(original) { _ in UnsupportedMedia() }!
        post.media = [unsupported]
        check(nagramiXPrepareRecipientCopies([post], account: account, recipientCount: 2) == nil, "unrepresentable slot never silently omitted")
        let repeated = original.options[0].media!
        post.media = [nagramiXMapPollMedia(original) { _ in repeated }!]
        var repeatedBatch: NagramiXRecipientCopyBatch? = nagramiXPrepareRecipientCopies([post], account: account, recipientCount: 2)
        check(repeatedBatch?.recipientMessages.count == 2, "repeated attachment keeps both complete recipient polls")
        var repeatedPaths: [Set<String>] = []
        for recipient in repeatedBatch!.recipientMessages {
            let poll = recipient[0].mediaReference!.media as! TelegramMediaPoll
            let slots = nagramiXPollMediaAttachments(poll)
            check(slots.count == 4, "repeated attachment stays in every slot")
            repeatedPaths.append(Set(slots.map { (($0 as! TelegramMediaFile).resource as! LocalFileReferenceMediaResource).localFilePath }))
        }
        check(repeatedPaths[0].isDisjoint(with: repeatedPaths[1]), "repeated attachments are owned per recipient")
        try FileManager.default.removeItem(at: file)
        for path in repeatedPaths.flatMap({ $0 }) {
            let staged = try Data(contentsOf: URL(fileURLWithPath: path))
            check(staged == bytes, "staging pins repeated bytes after original removal")
        }
        repeatedBatch = nil
        for path in repeatedPaths.flatMap({ $0 }) { check(!FileManager.default.fileExists(atPath: path), "repeated staging rolls back once batch releases") }
        print("Extended poll payload checks: \(checks)")
    }
}
'''


PREPARATION_TESTS = r'''
@main struct ExtendedPollPreparationTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) {
            if !value() { FileHandle.standardError.write(Data(("Extended poll preparation regression: " + label + "\n").utf8)); exit(91) }
            checks += 1
        }
        let box = MediaBox()
        let files = ["question", "answer", "solution"].map { TelegramMediaFile(resource: CloudResource($0), size: 4) }
        let poll = TelegramMediaPoll(pollId: MediaId(namespace: 99, id: 42), publicity: .anonymous, kind: .poll(multipleAnswers: false), text: "Опрос", textEntities: [], options: [TelegramMediaPollOption(text: "A", entities: [], opaqueIdentifier: Data([1]), media: files[1], date: nil, addedBy: nil), TelegramMediaPollOption(text: "B", entities: [], opaqueIdentifier: Data([2]), media: files[1], date: nil, addedBy: nil)], correctAnswers: nil, results: TelegramMediaPollResults(voters: nil, totalVoters: nil, recentVoters: [], solution: TelegramMediaPollResults.Solution(text: "S", entities: [], media: files[2]), hasUnseenVotes: nil, canViewStats: false), isClosed: false, deadlineTimeout: nil, deadlineDate: nil, pollHash: 0, attachedMedia: files[0])
        var post = Message(); post.media = [poll]
        var ready: NagramiXCopyMediaLease?, failed = false
        func listen(_ event: NagramiXCopyMediaPreparationEvent) { switch event { case let .ready(lease): ready = lease; case .failed: failed = true; case .progress: break } }
        let ordinary = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post]).start(next: listen)
        check(ready != nil && box.activeFetches == 0, "ordinary poll keeps cloud-reference fast path")
        ordinary.dispose(); ready?.dispose(); ready = nil
        post.protected = true
        let transfer = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post, post]).start(next: listen)
        check(ready == nil && box.activeFetches == 3 && box.activeKeeps == 3, "all poll slots fetched and duplicates deduplicated")
        check(Set(box.fetched) == Set(["question", "answer", "solution"]), "question/options/solution all reserved")
        box.emit("question", ResourceData(complete: true))
        box.emit("answer", ResourceData(complete: true))
        check(ready == nil, "missing solution blocks incomplete poll")
        box.emit("solution", ResourceData(complete: true))
        check(ready != nil && !failed && box.activeKeeps == 3, "complete poll transfers all pins")
        transfer.dispose(); check(box.activeKeeps == 3, "delivered lease survives signal disposal")
        ready?.dispose(); ready = nil; check(box.activeKeeps == 0 && box.activeFetches == 0, "lease releases all nested resources")
        let cancel = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post]).start(next: listen)
        cancel.dispose(); check(box.activeKeeps == 0 && box.activeFetches == 0 && ready == nil, "cancel releases all nested transfers")
        let broken = nagramiXPrepareCopyMedia(mediaBox: box, messages: [post]).start(next: listen)
        box.errors["answer"]?(.failed)
        check(failed && ready == nil && box.activeKeeps == 0, "nested failure fails entire poll without partial readiness")
        broken.dispose()
        print("Extended poll real SignalKit preparation checks: \(checks)")
    }
}
'''


def run_swift(source, swiftc, temp):
    runs = []
    for label in ['current', 'old-copier', 'old-stager', 'old-archive', 'old-preview', 'old-native-upload']:
        text = fixture(source, label)
        path = temp / (label + '.swift')
        path.write_text(text)
        for optimized in [False, True]:
            binary = temp / (label + ('-O' if optimized else '-debug'))
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized:
                command.append('-O')
            subprocess.run([*command, str(path), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                                    preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if label == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                message = result.stdout.strip()
            else:
                assert result.returncode == 91 and 'Extended poll regression:' in result.stderr, result.stdout + result.stderr
                message = result.stderr.strip()
            runs.append(binary.name + ': ' + message)
            print(runs[-1], flush=True)
    prep = preparation_fixture(source).split('@main struct CopyPreparationTests')[0]
    for label in ['preparation', 'old-preparation']:
        text = prep
        if label == 'old-preparation':
            text = text.replace('''            if let poll = item as? TelegramMediaPoll {
                return nagramiXPollMediaAttachments(poll).allSatisfy { collect($0, depth: depth + 1) }
            } else if let image = item as? TelegramMediaImage {''', '''            if let image = item as? TelegramMediaImage {''')
            assert text != prep
        path = temp / (label + '.swift')
        path.write_text(text + PREPARATION_TESTS)
        for optimized in [False, True]:
            binary = temp / (label + ('-O' if optimized else '-debug'))
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized:
                command.append('-O')
            subprocess.run([*command, str(path), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                                    preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if label == 'preparation':
                assert result.returncode == 0, result.stdout + result.stderr
                message = result.stdout.strip()
            else:
                assert result.returncode == 91 and 'Extended poll preparation regression:' in result.stderr, result.stdout + result.stderr
                message = result.stderr.strip()
            runs.append(binary.name + ': ' + message)
            print(runs[-1], flush=True)
    return runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-extended-poll-') as directory:
        temp = Path(directory)
        rejected = guard_checks(args.source, temp)
        runs = run_swift(args.source, args.swiftc, temp) if args.swiftc else []
        if args.swiftc:
            for name in PLAN['outputs']:
                subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    report = {'outputs': len(PLAN['outputs']), 'guards': len(PLAN['guards']), 'rejected': rejected,
              'executions': runs, 'source_outputs': PLAN['outputs'], 'swift_parse': len(PLAN['outputs']) if args.swiftc else 0,
              'boundaries': 'Actual poll constructors, mapper, copier, file stager, preparation with real SignalKit, archive selection/localMedia/poll request branch, native preview constructor. Postbox codec/media store, UIKit, Telegram API/network/decoder remain adapters. Native archive deletion/purge/Undo methods remain byte-identical; full app and physical device pending.',
              'apple_sdk': 'not run', 'physical_device': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Extended poll integrity source checks passed')


if __name__ == '__main__':
    main()
