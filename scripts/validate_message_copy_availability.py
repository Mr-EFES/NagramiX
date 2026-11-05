#!/usr/bin/env python3
"""Проверить опросы и единый ON/OFF gate копирования защищённого и secret содержимого."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile
from validate_quick_format import block, manifest
from validate_recipient_copy_isolation import common_source

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'message_copy_availability_patches.json').read_text())
A, C, F, N, M, S = PLAN['inputs']
POLL = 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaPoll.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stripped(text):
    return '\n'.join(line for line in text.splitlines() if not re.match(r'^(?:(?:internal|public|private|fileprivate|package) )?import ', line)).replace('public ', '')


def verify(source):
    for name, h in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == h, name
    for name, h in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == h, name
    before = lambda n: (OVERLAY / PLAN['previous'][n]).read_text()
    menu = (source / M).read_text()
    marker = 'if data.messageActions.options.contains(.forward) && !isCopyProtected'
    end = '            if nagramiXCanCopySelection {'
    current_repost = menu[menu.index(marker):menu.index(end, menu.index(marker))]
    old_menu = before(M)
    old_repost = old_menu[old_menu.index(marker):old_menu.index('            if !isCopyProtected || nagramiXCanCopySelection {', old_menu.index(marker))]
    assert current_repost.replace(' && nagramiXCanRepostMessages(messagesToForward)', '') == old_repost, 'Native Repost callback changed'
    policy = (source / C).read_text()
    assert 'ContentSettings.default.nagramiXAllowsFreeContent' in policy
    assert '!self.nagramiXRequiresFreeContentCopy || allowsFreeContent' in policy
    f = (source / F).read_text()
    assert f.count('guard !nagramiXProtectedOriginal || NagramiXPrivacySettings.current.bypassScreenshots') == 3
    assert 'messages.contains(where: { $0.nagramiXRequiresFreeContentCopy })' in f
    assert '&& (!isCopyProtected || NagramiXPrivacySettings.current.bypassScreenshots)' in menu
    panel = (source / S).read_text()
    assert panel.count(' || copyBlocked') == 2
    assert 'TelegramSecretChat, !ContentSettings.default.nagramiXAllowsFreeContent' in panel
    fetch = (source / 'submodules/TelegramCore/Sources/State/FetchSecretFileResource.swift').read_text()
    assert 'encryptionKey: resource.key' in fetch and 'decryptedSize: resource.decryptedSize' in fetch
    assert 'let transferMode: NagramiXMessageTransferMode = transferMode == .forwardWithoutSource ? .copyToSingleRecipient : transferMode' in f
    assert 'let nagramiXProtectedCopy = transferMode.copiesAsNew' in f
    assert 'if media is TelegramMediaPoll {\n                        filter.insert(.excludeSecretChats)' in f
    assert 'batch.messages(forRecipientAt: destinationIndex, template: result)' in f
    assert 'combineLatest(copyEnqueueSignals)' in f
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_pip_first_request(') < pipeline.index('    apply_message_copy_availability(')


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('copy_availability', OVERLAY / 'message_copy_availability.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    def seed(label):
        tree = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            p = tree / name; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name).read_bytes())
        return tree
    rejected = []
    def reject(tree, label, overlay=OVERLAY):
        start = manifest(tree)
        try:
            module.apply_message_copy_availability(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == start, 'Partial write: ' + label
        rejected.append(label)
    valid = seed('valid'); module.apply_message_copy_availability(valid, OVERLAY)
    assert all((valid / n).read_bytes() == (source / n).read_bytes() for n in PLAN['outputs'])
    reject(valid, 'repeat')
    for i, name in enumerate({**PLAN['inputs'], **PLAN['guards']}):
        for kind in ['missing', 'drift']:
            tree = seed(f'{i}-{kind}')
            if kind == 'missing': (tree / name).unlink()
            else: (tree / name).write_bytes(b'drift')
            reject(tree, kind + ' ' + name)
    variants = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN); bad[field][next(iter(bad[field]))] = '0' * 64; variants.append((field, bad))
    for field in ['previous', 'replacements']:
        bad = copy.deepcopy(PLAN); bad[field][A] = '../outside.swift'; variants.append((field, bad))
    bad = copy.deepcopy(PLAN); bad['outputs'].clear(); variants.append(('inconsistent', bad))
    for label, bad in variants:
        overlay = temp / ('overlay-' + label)
        for name in PLAN['templates']:
            p = overlay / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((OVERLAY / name).read_bytes())
        (overlay / 'message_copy_availability_patches.json').write_text(json.dumps(bad))
        reject(seed('source-' + label), label, overlay)
    for i, name in enumerate([A, next(iter(PLAN['guards']))]):
        tree = seed('symlink-' + str(i)); p = tree / name; outside = temp / ('outside-' + str(i))
        outside.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(outside); reject(tree, 'external symlink ' + name)
    return rejected


def poll_boundary(source):
    text = (source / POLL).read_text()
    result = 'typealias MessageTextEntity = Entity\nextension Namespaces.Peer { static let CloudChannel: Int32 = 2 }\nextension Namespaces.Media { static let LocalPoll: Int32 = 3 }\n'
    for name in ['TelegramMediaPollOption', 'TelegramMediaPollOptionVoters']:
        marker = 'public struct ' + name + ':'
        prefix = text[text.index(marker):]
        prefix = prefix[:prefix.index('    public init(decoder:')]
        prefix = prefix.replace(': Equatable, PostboxCoding', '')
        result += prefix + '}\n'
    results = text[text.index('public struct TelegramMediaPollResults:'):]
    solution = results[results.index('    public struct Solution:'):results.index('        public static func ==')]
    solution = solution.replace(': Equatable', '') + '    }\n'
    fields = results[results.index('    public let voters:'):results.index('    public init(decoder:')]
    result += 'struct TelegramMediaPollResults {\n' + solution + fields + '}\n'
    enum_start = text.index('public enum TelegramMediaPollPublicity:')
    enum_end = text.index('public enum TelegramMediaPollKind:', enum_start)
    result += text[enum_start:enum_end]
    result += 'enum TelegramMediaPollKind { case poll(multipleAnswers: Bool); case quiz(multipleAnswers: Bool) }\n'
    model = text[text.index('public final class TelegramMediaPoll:'):]
    model = model[:model.index('    public init(decoder:')].replace(': Media, Equatable', ': Media')
    result += model + '}\n'
    result += '''
func pollCloudMediaToInputMedia(_ media: Media) -> Int? {
    // API conversion is a boundary; exact native sender/converter are SHA guards.
    if let file = media as? TelegramMediaFile, file.resource is CloudResource { return 1 }
    if let image = media as? TelegramMediaImage, image.reference != nil { return 1 }
    if media is TelegramMediaMap { return 1 }
    return nil
}
struct NagramiXPrivacySettings { static var current = Self(); var bypassScreenshots = false }
enum TelegramGroupMembership { case Member, Left, Removed }
final class TelegramGroup { var membership = TelegramGroupMembership.Member }
enum TelegramChannelParticipationStatus { case member, left, kicked }
struct UsernameFlags: OptionSet { let rawValue: Int; static let isActive = Self(rawValue: 1) }
struct ChannelUsername { var flags: UsernameFlags }
final class TelegramChannel {
    var participationStatus: TelegramChannelParticipationStatus = .member
    var username: String?
    var usernames: [ChannelUsername] = []
}
struct EphemeralMessageAttribute: MessageAttribute { var isForwardingDisabled: Bool }
struct ContentSettings { static var `default` = Self(); var nagramiXAllowsFreeContent: Bool { NagramiXPrivacySettings.current.bypassScreenshots } }
struct ForwardOptions { var hideNames = true }
struct ForwardDraft { var forwardOptionsState: ForwardOptions? = ForwardOptions() }
struct ChatState { var interfaceState = ForwardDraft(); var copyProtectionEnabled = false }
struct ChatLocation { var peerId: PeerId? = PeerId() }
struct SelectionActions { var isCopyProtected = false }
extension Account { var peerId: PeerId { PeerId() } }
struct MenuOptions: OptionSet { let rawValue: Int; static let forward = Self(rawValue: 1) }
struct MenuActions { var options: MenuOptions = [] }
struct MenuData { var messageActions = MenuActions() }
'''
    return stripped(result)


def ui_boundary(source, mode):
    f = (source / F).read_text(); m = (source / M).read_text(); n = (source / N).read_text()
    enum = block(f, 'enum NagramiXMessageTransferMode:')
    route = next(line for line in f.splitlines() if 'let transferMode: NagramiXMessageTransferMode = transferMode ==' in line)
    if mode == 'old-server-forward': route = '        let transferMode = transferMode'
    cap = next(line for line in m.splitlines() if 'let nagramiXCanCopySelection =' in line)
    # context/account accesses belong to UIKit; keep the actual copy expression.
    cap = cap.replace('context.account.peerId', 'PeerId()')
    if mode == 'old-secret-menu': cap += ' && copyMessagesToForward.allSatisfy { $0.id.peerId.namespace != Namespaces.Peer.SecretChat }'
    outer = next(line.strip()[3:-2] for line in m.splitlines() if 'if data.messageActions.options.contains(.forward) ||' in line)
    repost = next(line.strip()[3:-2] for line in m.splitlines() if line.strip().startswith('if data.messageActions.options.contains(.forward) && !isCopyProtected'))
    predicates = [line.strip() for line in n.splitlines() if 'let protectedMessages = messages.values.filter' in line]
    assert len(predicates) == 1
    pred = predicates[0]
    guard_start = n.index('guard draft.forwardOptionsState?.hideNames == true,')
    gate = n[guard_start:n.index(' else {', guard_start)]
    if mode == 'old-draft-off': gate = gate.replace('== true,', '== true, NagramiXPrivacySettings.current.bypassScreenshots,', 1)
    original = next(line for line in f.splitlines() if 'let nagramiXProtectedOriginal =' in line)
    commit = next(line.strip() for line in f.splitlines() if 'guard !nagramiXProtectedOriginal ||' in line)
    panel = (source / S).read_text()
    blocked = next(line for line in panel.splitlines() if 'let copyBlocked =' in line)
    refresh = block(panel, 'if self.nagramiXFreeContentEnabled != freeContentEnabled')
    if mode == 'old-stale-selection': refresh = 'if self.nagramiXFreeContentEnabled != freeContentEnabled { self.nagramiXFreeContentEnabled = freeContentEnabled }'
    return block(m, 'private func nagramiXCanRepostMessages(') + '\n' + enum + '''
private final class CopyPolicyHarness {
    let context: SenderContext
    var presentationInterfaceState = ChatState()
    var chatLocation = ChatLocation()
    var actions: SelectionActions?
    var nagramiXCanCopySelection = true
    var nagramiXFreeContentEnabled = false
    var rechecks = 0
    func updateActions() { self.rechecks += 1 }
    init(_ account: Account) { context = SenderContext(account) }
    func mode(transferMode: NagramiXMessageTransferMode) -> NagramiXMessageTransferMode {
''' + route + '''
        return transferMode
    }
    func menu(_ copyMessagesToForward: [Message], protected isCopyProtected: Bool, native: Bool, own nagramiXOwnViewOnceCopy: Bool = false, replay nagramiXReplayCopy: Bool = false) -> (copy: Bool, repost: Bool) {
        let messagesToForward = copyMessagesToForward
        var data = MenuData(); data.messageActions.options = native ? .forward : []
''' + cap + '\n        return ((' + outer + ') && nagramiXCanCopySelection, ' + repost + ''')
    }
    func commitAllowed(_ messages: [Message], contextProtected: Bool = false) -> Bool {
        self.presentationInterfaceState.copyProtectionEnabled = contextProtected
''' + original + '\n' + commit + '''
            return false
        }
        return true
    }
    func refreshSelection() {
        let freeContentEnabled = ContentSettings.default.nagramiXAllowsFreeContent
''' + refresh + '''
    }
    func selectionBlocked(secret isSecretChat: Bool, protected: Bool, eligible: Bool) -> Bool {
        let interfaceState = ChatState(copyProtectionEnabled: protected)
        self.actions = SelectionActions(isCopyProtected: protected)
        self.nagramiXCanCopySelection = eligible
        let restrictedCopy = isSecretChat || interfaceState.copyProtectionEnabled || self.actions?.isCopyProtected == true
''' + blocked + '''
        return copyBlocked
    }
    func draft(_ selected: [Message], hidden: Bool) -> Bool {
        let draft = ForwardDraft(forwardOptionsState: ForwardOptions(hideNames: hidden))
        let messages = Dictionary(uniqueKeysWithValues: selected.map { ($0.id, $0) })
''' + pred + '''
        if !protectedMessages.isEmpty {
''' + gate + ''' else { return false }
        }
        return true
    }
}
'''


def run_swift(source, swiftc, temp):
    common = common_source(source).replace('    var id = MessageId(); var text', '    var peers: [PeerId: Any] = [:]\n    var id = MessageId(); var text') + '\n' + poll_boundary(source)
    helper_paths = []
    for name in ['submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift', C]:
        p = temp / Path(name).name; p.write_text('import Foundation\n' + stripped((source / name).read_text())); helper_paths.append(p)
    runs = []
    for mode in ['current', 'old-no-polls', 'old-no-secret-copy', 'old-secret-menu', 'old-draft-off', 'old-server-forward', 'old-stale-switch', 'old-stale-selection']:
        policy = (source / C).read_text()
        if mode == 'old-no-secret-copy':
            policy = policy.replace('return (!self.nagramiXRequiresFreeContentCopy || allowsFreeContent)', 'return self.id.peerId.namespace != Namespaces.Peer.SecretChat && (!self.nagramiXRequiresFreeContentCopy || allowsFreeContent)')
        elif mode == 'old-stale-switch':
            policy = policy.replace('let allowsFreeContent = ContentSettings.default.nagramiXAllowsFreeContent', 'let allowsFreeContent = true')
        helper_paths[1].write_text('import Foundation\n' + stripped(policy))
        a = temp / (mode + '-copier.swift')
        a.write_text('import Foundation\n' + stripped((OVERLAY / PLAN['previous'][A] if mode == 'old-no-polls' else source / A).read_text()))
        suite = temp / (mode + '.swift')
        suite.write_text(common + '\n' + ui_boundary(source, mode) + '\n' + (ROOT / 'scripts/tests/NagramiXCopyAvailabilityTests.swift').read_text())
        for opt in [False, True]:
            binary = temp / (mode + ('-O' if opt else '-debug'))
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if opt: command.append('-O')
            subprocess.run([*command, *map(str, helper_paths), str(a), str(suite), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if mode == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                message = result.stdout.strip()
            else:
                assert result.returncode != 0 and 'copy availability regression:' in result.stderr, result.stderr
                message = 'previous behavior reproduced and rejected'
            runs.append(binary.name + ': ' + message); print(runs[-1], flush=True)
    helper_paths[1].write_text('import Foundation\n' + stripped((source / C).read_text()))
    # Existing recipient and rich-content suites execute with protected copying enabled.
    for label, tests in [('recipient-regression', 'NagramiXRecipientCopyTests.swift'), ('rich-regression', 'NagramiXRichContentCopyTests.swift')]:
        runtime = (ROOT / 'scripts/tests' / tests).read_text()
        if label == 'rich-regression': runtime = '@main struct RichContentCopyTests' + runtime.split('@main struct RichContentCopyTests', 1)[1]
        runtime = runtime.replace('var checks = 0', 'NagramiXPrivacySettings.current.bypassScreenshots = true\n        var checks = 0', 1)
        suite = temp / (label + '.swift'); suite.write_text(common + '\n' + runtime)
        for opt in [False, True]:
            binary = temp / (label + ('-O' if opt else '-debug'))
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if opt: command.append('-O')
            subprocess.run([*command, *map(str, helper_paths), str(temp / 'current-copier.swift'), str(suite), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr
            runs.append(binary.name + ': ' + result.stdout.strip()); print(runs[-1], flush=True)
    return runs


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--source', type=Path, required=True); p.add_argument('--swiftc', type=Path); p.add_argument('--report', type=Path)
    args = p.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_visual_handoff'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_menu'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_visibility'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'temporary_media_actions'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-copy-availability-') as folder:
        temp = Path(folder); rejected = guard_checks(args.source, temp)
        runs = run_swift(args.source, args.swiftc, temp) if args.swiftc else []
        if args.swiftc:
            for name in PLAN['outputs']: subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'files': len(PLAN['outputs']), 'guards': len(PLAN['guards']), 'rejected': rejected, 'executions': runs, 'sdk': 'not run', 'device': 'pending', 'boundaries': 'Actual copier/fetch/stager/recipient sender and extracted UI gates; actual poll model constructors; Postbox/network/UIKit/API conversion doubles. Unknown quiz answers are never invented; unavailable bytes and server send restrictions remain explicit failures.'}
    if args.report: args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
