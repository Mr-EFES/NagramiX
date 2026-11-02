#!/usr/bin/env python3
"""Проверить приватность захвата, ACK просмотра и единое сохранение истории."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'media_privacy_fixes_patches.json').read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_applied(source):
    expected = {**PLAN['outputs'], **{n: x['sha256'] for n, x in PLAN['copies'].items()}}
    return all((source / n).is_file() and sha((source / n).read_bytes()) == h for n, h in expected.items())


def previous_bytes(source):
    previous = {n: (source / n).read_text() for n in PLAN['outputs']}
    for name, old, new, count in reversed(PLAN['patches']):
        assert previous[name].count(new) == count, name
        previous[name] = previous[name].replace(new, old, count)
    result = {n: s.encode() for n, s in previous.items()}
    assert all(sha(data) == PLAN['inputs'][n] for n, data in result.items())
    return result


def reverse(source, target):
    before = previous_bytes(source)
    names = set(before)
    for manifest in OVERLAY.glob('*_patches.json'):
        plan = json.loads(manifest.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(plan.get(field, {}))
    # Keep the same sparse validation view used by the preceding final stages.
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.add('Telegram/Telegram-iOS/en.lproj/Localizable.strings')
    names.add('submodules/TelegramPresentationData/Sources/PresentationData.swift')
    for name in names - set(PLAN['copies']):
        path = source / name
        if not path.is_file():
            continue
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(before[name] if name in before else path.read_bytes())


def delegate_if_applied(args, script):
    from validate_translation_simplification import delegate_if_applied as delegate_latest
    if delegate_latest(args, script): return True
    if not is_applied(args.source):
        return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-before-media-') as folder:
        prior = Path(folder)
        reverse(args.source, prior)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source':
                arguments += ['--source', str(prior)]
            elif value is True:
                arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False:
                arguments += ['--' + key.replace('_', '-'), str(value)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def verify(source):
    assert is_applied(source)
    for n, h in PLAN['guards'].items():
        assert sha((source / n).read_bytes()) == h, n
    for n, h in PLAN['templates'].items():
        assert sha((OVERLAY / n).read_bytes()) == h, n
    before = previous_bytes(source)
    by_name = {Path(n).name: (source / n).read_text() for n in PLAN['outputs']}
    policy = by_name['NagramiXCaptureProtectionPolicy.swift']
    assert 'return !NagramiXPrivacySettings.current.bypassScreenshots' in policy
    assert 'self.paidContent == nil' in policy and '!self.id.peerId.isVerificationCodes' in policy
    assert 'containsSecretMedia' not in policy and '!= viewOnceTimeout' not in policy
    secret = by_name['SecretMediaPreviewController.swift']
    assert 'strongSelf.traceVisibility(), nagramiXShouldNotifyScreenCapture()' in secret
    # Only the event gate changes: both CloudUser enqueue and SecretChat RPC
    # remain below it, preserving the whole controller and the OFF behavior.
    name = next(n for n in before if n.endswith('/SecretMediaPreviewController.swift'))
    expected = before[name].decode().replace('strongSelf.traceVisibility() {', 'strongSelf.traceVisibility(), nagramiXShouldNotifyScreenCapture() {')
    assert secret == expected
    image = by_name['ChatImageGalleryItem.swift']
    assert 'self.imageNode.nagramiXAllowsScreenshotBypass = message.nagramiXAllowsScreenshotBypass\n' in image
    core = by_name['Stories.swift']
    method = block(core, 'func _internal_nagramiXRecordStoryView(')
    assert 'incrementStoryViews(peer: inputPeer, id: [id])' in method
    assert '|> map { _ -> Bool in return true }' in method
    assert 'return .single(false)' in method and '|> `catch`' in method
    assert not any(x in method for x in ('readStories(', 'setPeerStoryState', 'maxReadId'))
    name = next(n for n in before if n.endswith('/Stories.swift'))
    assert block(core, 'func _internal_markStoryAsSeen(') == block(before[name].decode(), 'func _internal_markStoryAsSeen(')
    story = by_name['StoryItemSetContainerComponent.swift']
    assert 'controller.present(progress, in: .window(.root))' in story
    name = next(n for n in before if n.endswith('/StoryItemSetContainerComponent.swift'))
    for marker in ('private func nagramiXRecordView(', 'private var nagramiXCanDownloadStory:', 'private func requestSave('):
        assert block(story, marker) == block(before[name].decode(), marker), marker
    saver = by_name['NagramiXStorySave.swift']
    assert saver == (OVERLAY / 'media_privacy_fixes/Saver.swift').read_text()
    assert saver.count('PHPhotoLibrary.shared().performChanges(') == 1
    assert saver.index('beginCommit()') < saver.index('PHPhotoLibrary.shared().performChanges(')
    assert 'if success && error == nil' in saver and 'fail(.permissionDenied)' in saver
    assert 'NagramiXStorySaveJob.jobs[key]' in saver
    assert not any(x in saver for x in ('enqueueMessages(', 'incrementStoryViews(', 'markStoryAsSeen('))
    job = (source / next(iter(PLAN['copies']))).read_text()
    assert '!self.committing && !self.finished' in job
    assert 'if Self.jobs[self.key] === self' in job
    assert 'self?.finish(.failed(error), keepSaved: false)' in job
    assert 'self?.finish(.saved, keepSaved: true)' in job
    archive = by_name['NagramiXMessageArchive.swift']
    assert 'isTemporary: record.temporary == true' in archive
    assert 'isTemporary: Bool = false' in archive
    assert 'decodeBoolForKey("t", orElse: false)' in archive
    assert 'return !archived.isTemporary' in archive
    bubble = by_name['ChatMessageBubbleItemNode.swift']
    assert 'let nagramiXArchivedMessage = firstMessage.nagramiXShowsArchiveNotice' in bubble
    assert 'let nagramiXIsArchived = item.content.firstMessage.nagramiXShowsArchiveNotice' in bubble
    assert 'if nagramiXArchivedMessage {' in bubble and 'if nagramiXIsArchived {' in bubble
    return before


def guard_tests(source, before):
    spec = importlib.util.spec_from_file_location('media_privacy_fixes', OVERLAY / 'media_privacy_fixes.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = {**{n: (source / n).read_bytes() for n in PLAN['guards']}, **before}
    with tempfile.TemporaryDirectory(prefix='nagramix-media-guards-') as folder:
        temp = Path(folder)

        def seed():
            base = temp / 'input'
            for n, data in original.items():
                path = base / n
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            return base

        def snapshot(base):
            return {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}

        def reject(base, overlay=OVERLAY):
            old = snapshot(base)
            try:
                module.apply_media_privacy_fixes(base, overlay)
            except (SystemExit, FileNotFoundError):
                pass
            else:
                raise AssertionError('Принят повреждённый вход')
            assert snapshot(base) == old, 'Частичная запись'
            shutil.rmtree(base)

        base = seed()
        module.apply_media_privacy_fixes(base, OVERLAY)
        assert is_applied(base)
        reject(base)  # Reapplication must fail, including copied helpers.
        count = 1
        for n in original:
            for missing in (False, True):
                base = seed()
                if missing:
                    (base / n).unlink()
                else:
                    (base / n).write_bytes(b'// drift')
                reject(base)
                count += 1
        for kind in ('template', 'collision', 'anchor', 'output', 'path'):
            base = seed()
            custom = temp / kind
            plan = json.loads(json.dumps(PLAN))
            for n in PLAN['templates']:
                path = custom / n
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((OVERLAY / n).read_bytes())
            if kind == 'template':
                (custom / next(iter(PLAN['templates']))).write_bytes(b'// drift')
            elif kind == 'collision':
                path = base / next(iter(PLAN['copies']))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'// existing')
            elif kind == 'anchor':
                plan['patches'][-1][1] += '// drift'
            elif kind == 'output':
                plan['outputs'][next(iter(plan['outputs']))] = '0' * 64
            else:
                plan['inputs']['../outside'] = '0' * 64
                plan['outputs']['../outside'] = '0' * 64
            (custom / 'media_privacy_fixes_patches.json').write_text(json.dumps(plan))
            reject(base, custom)
            count += 1
    print(f'PASS: {count} fail-closed cases, no partial writes')


def execute_swift_tests(source, swiftc, upstream):
    from validate_contact_chat_readiness import KIT, NATIVE
    story_name = next(n for n in PLAN['outputs'] if n.endswith('/StoryItemSetContainerComponent.swift'))
    core_name = next(n for n in PLAN['outputs'] if n.endswith('/Stories.swift'))
    policy_name = next(n for n in PLAN['outputs'] if n.endswith('/NagramiXCaptureProtectionPolicy.swift'))
    archive_name = next(n for n in PLAN['outputs'] if n.endswith('/NagramiXMessageArchive.swift'))
    story = (source / story_name).read_text()
    with tempfile.TemporaryDirectory(prefix='nagramix-media-swift-') as folder:
        temp = Path(folder)
        signal = []
        for name in NATIVE + ['Signal_Catch.swift']:
            text = (upstream / (KIT + name)).read_text()
            if name == 'Signal_Meta.swift':
                text = 'import CoreFoundation\n' + text
            path = temp / name
            path.write_text(text)
            signal.append(path)
        boundary = (ROOT / 'scripts/tests/NagramiXStoryExplicitViewBoundary.swift').read_text()
        boundary = boundary.replace('    public func async(_ action: @escaping () -> Void) { action() }', '''    public func async(_ action: @escaping () -> Void) { action() }
    static var delayed: [() -> Void] = []
    public func after(_ delay: Double, _ action: @escaping () -> Void) { Self.delayed.append(action) }
    static func flushDelayed() { let actions = delayed; delayed.removeAll(); for action in actions { action() } }''')
        method = block((source / core_name).read_text(), 'func _internal_nagramiXRecordStoryView(')
        # Unchanged engine wrapper and menu use the same tested boundaries as
        # story_explicit_view; the RPC mapper below is the final production one.
        engine = '''func nagramiXRecordStoryView(peerId: PeerId, id: Int32) -> Signal<Bool, NoError> {
            _internal_nagramiXRecordStoryView(account: self.account, peerId: peerId, id: id)
        }'''
        properties = '\n'.join(block(story, marker) for marker in ('var nagramiXViewDisclosureKey:', 'var nagramiXUsesAnonymousViewing:'))
        menu = (OVERLAY / 'story_explicit_view/Menu.swift.inc').read_text().replace('private func', 'func')
        boundary = boundary.replace('// ENGINE_METHOD', engine).replace('// COMPONENT_PROPERTIES', properties).replace('// MENU_METHODS', menu)
        boundary += '''
public enum NagramiXStorySaveError: Error, Equatable { case unavailable, permissionDenied, library }
struct NagramiXPrivacySettings { static var current = NagramiXPrivacySettings(); var bypassScreenshots = false }
extension PeerId { var isVerificationCodes: Bool { value == 777000 } }
struct MessageId { let peerId: PeerId }
public struct Message { var paidContent: Int?; var id: MessageId; var attributes: [Any] }
public protocol MessageAttribute {}
public struct NagramiXMessageRevision {}
public final class PostboxDecoder {
    let values: [String: Any]
    init(_ values: [String: Any]) { self.values = values }
    func decodeInt32ForKey(_ key: String, orElse: Int32) -> Int32 { values[key] as? Int32 ?? orElse }
    func decodeBoolForKey(_ key: String, orElse: Bool) -> Bool { values[key] as? Bool ?? orElse }
}
public final class PostboxEncoder {
    var values: [String: Any] = [:]
    func encodeInt32(_ value: Int32, forKey key: String) { values[key] = value }
    func encodeBool(_ value: Bool, forKey key: String) { values[key] = value }
}
'''
        policy = '\n'.join(line for line in (source / policy_name).read_text().splitlines() if not line.startswith('import '))
        archive = (source / archive_name).read_text()
        archive = block(archive, 'public final class NagramiXArchivedMessageAttribute:') + '\npublic extension Message {\n' + block(archive, 'var nagramiXShowsArchiveNotice:') + '\n}'
        job = (source / next(iter(PLAN['copies']))).read_text().replace('import SwiftSignalKit\n', '')
        harness = temp / 'Boundary.swift'
        harness.write_text(boundary + '\n' + method + '\n' + policy + '\n' + archive + '\n' + job)
        for flags in ([], ['-O']):
            binary = temp / 'tests'
            subprocess.run([str(swiftc), '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), *flags,
                *map(str, signal), str(harness), str(OVERLAY / 'story_explicit_view/Disclosure.swift'),
                str(ROOT / 'scripts/tests/NagramiXMediaPrivacyTests.swift'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--standalone', action='store_true')
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--upstream', type=Path)
    args = parser.parse_args()
    from validate_translation_simplification import delegate_if_applied as delegate_latest
    if delegate_latest(args, __file__): return
    before = verify(args.source)
    guard_tests(args.source, before)
    if args.swiftc:
        subprocess.run([str(args.swiftc), '-frontend', '-parse', *[str(args.source / n) for n in [*PLAN['outputs'], *PLAN['copies']] if n.endswith('.swift')]], check=True)
        execute_swift_tests(args.source, args.swiftc, args.upstream or args.source)
    if not args.standalone:
        with tempfile.TemporaryDirectory(prefix='nagramix-media-previous-') as folder:
            prior = Path(folder)
            reverse(args.source, prior)
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_native_player_pip.py'), '--source', str(prior), *(['--swiftc', str(args.swiftc)] if args.swiftc else [])], check=True)
    print('PASS: media privacy / explicit story RPC / shared Photos save; SDK and iPhone pending')


if __name__ == '__main__':
    main()
