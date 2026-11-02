#!/usr/bin/env python3
"""Exercise native transfer selection/draft code without Apple SDK or IPA."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
F = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
N = 'submodules/TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionControllerNode.swift'
D = 'submodules/TelegramUI/Sources/ChatControllerNode.swift'


def between(text, begin, end):
    return text.split(begin, 1)[1].split(end, 1)[0]


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def swift_sources(before, after):
    node, forward, draft = [(after / p).read_text() for p in [N, F, D]]
    contact = (after / 'submodules/ContactListUI/Sources/ContactListNode.swift').read_text()
    # Execute the actual immutable native contact selection value type too.
    state = 'public struct ContactListNodeGroupSelectionState:' + between(contact,
        'public struct ContactListNodeGroupSelectionState:', '\npublic final class ContactListNode:')
    state = state.replace('public ', '')
    start = node.index('    var nagramiXCopySelection = false')
    props = node[start:node.index(' = ([], [:])', start) + len(' = ([], [:])')].replace('private ', '')
    select = between(node, '    func nagramiXSelectCopyRecipient(_ peer: EnginePeer) {', '        // Copy mode deliberately')
    selected = '    var selectedPeers:' + between(node, '    private var selectedPeers:', '\n    func beginSelection()').replace('private ', '')
    begin = between(node, '    func beginSelection() {', '        guard let controller = self.controller else {')
    # The original native UI setup/reset is a boundary; replay its exact contact
    # reset, rather than inventing state changes to match the intended result.
    reset = 'self.contactListNode?.updateSelectionState({ _ in\n                return ContactListNodeGroupSelectionState()\n            })'
    assert reset in node and reset in (before / N).read_text()
    switch = between(node, '        if contactListActive != self.contactListActive {', '            self.contactListActive = contactListActive')
    selection_class = '''final class SelectionNode {
    var contactListActive = false
    let controller: SelectionController? = SelectionController()
    let contactListNode: Contacts? = Contacts()
    let mainContainerNode: Container? = Container()
    let chatListNode: Chats? = nil
    let textInputPanelNode: SendPanel? = SendPanel()
    var resets = 0
''' + props + '\n' + selected + '''
    func nagramiXSelectCopyRecipient(_ peer: EnginePeer) {
''' + select + '''    }
    func legacyBeginSelection() {
        resets += 1
        if contactListActive { ''' + reset + ''' }
    }
    func beginSelection() {
''' + begin + '''        legacyBeginSelection()
    }
    func switchTab(_ contactListActive: Bool) {
        guard contactListActive != self.contactListActive else { return }
''' + switch + '''        self.contactListActive = contactListActive
        self.nagramiXRestoreCopyRecipients()
    }
    var ids: Set<Int> { Set(selectedPeers.0.map { $0.id }) }
}
'''
    preflight = '        if nagramiXResolvedForwards == nil,' + between(draft,
        '        if nagramiXResolvedForwards == nil,', '\n        var effectivePresentationInterfaceState =')
    own_dispatch = '                    let ownRecordings = ' + between(draft,
        '                    let ownRecordings = ', '\n                let doSend:')
    # The native dispatch's outer forwardMessageIds block closes at the end.
    assert own_dispatch.rstrip().endswith('}')
    own_dispatch = own_dispatch.rstrip()[:-1]
    draft_class = '''final class DraftSender {
    let context = Context()
    var interfaceInteraction: Interaction? = Interaction()
    var chatLocation = ChatLocation()
    var chatPresentationInterfaceState = PresentationState()
    var textInputPanelNode: InputPanel? = InputPanel()
    var nagramiXResolvingForwardSend = false
    var sent = 0
    var resolved: [Int:Message]? = nil
    var silent: Bool? = nil
    var enqueued: [EnqueueMessage] = []
    func sendCurrentMessage(silentPosting: Bool? = nil, scheduleTime: Int32? = nil, repeatPeriod: Int32? = nil, postpone: Bool = false, messageEffect: ChatSendMessageEffect? = nil, sendWithoutFormatting: Bool = false, nagramiXResolvedForwards: [MessageId:Message]? = nil, completion: @escaping () -> Void = {}) {
        guard let textInputPanelNode else { return }
''' + preflight + '''
        sent += 1; resolved = nagramiXResolvedForwards; silent = silentPosting
        completion()
    }
    func finishForward() {
        let forwardMessageIds = self.chatPresentationInterfaceState.interfaceState.forwardMessageIds ?? []
        let nagramiXResolvedForwards = resolved
        var messages: [EnqueueMessage] = []
        let replyThreadId: Int64? = self.chatLocation.threadId
        let archivedCopies: [MessageId:EnqueueMessage] = [:]
        let attributes: [Int] = []
''' + own_dispatch + '''
        enqueued = messages
    }
}
'''
    mode = 'enum NagramiXMessageTransferMode:' + between(forward, 'enum NagramiXMessageTransferMode:', '\nfunc nagramiXCanCopyMessagesAsNew')
    allowed = 'func nagramiXAllowsOwnViewOnceDestination(' + between(forward,
        'func nagramiXAllowsOwnViewOnceDestination(', '\nfunc nagramiXCopyMessagesAsNew')
    bridge = between(forward.split('            controller.peerSelected = ', 1)[1], '                if ', ' {\n                    // Assign nil')
    rejected = between(forward, 'if transferMode.copiesAsNew && peers.contains(where: { peer in\n', '\n                }) {')
    snapshot = between(forward, '                let destinationThreadIds = ', '\n                if transferMode.copiesAsNew')
    limit = between(forward, 'multipleSelectionLimit: ', ', forwardedMessageIds:')
    route = '                                    var peerMessages = result' + between(forward,
        '                                    var peerMessages = result', '                                    if shouldDivert {')
    legacy = between((before / F).read_text().split('            controller.peerSelected = ', 1)[1],
        '                if ', ' {\n                    if let threadId')
    helpers = mode + allowed + '''
func productionLegacyUsesCopyPicker(_ transferMode: NagramiXMessageTransferMode, protected nagramiXProtectedCopy: Bool) -> Bool {
    ''' + legacy + '''
}
''' + '''
func productionPickerLimit(_ transferMode: NagramiXMessageTransferMode, protected nagramiXProtectedCopy: Bool, own nagramiXOwnViewOnceCopy: Bool) -> Int? {
    ''' + limit + '''
}
func productionRoute(_ result: [EnqueueMessage], to peer: EnginePeer, threads destinationThreadIds: [Int:Int64]) -> [EnqueueMessage] {
    let transferMode = NagramiXMessageTransferMode.copyAsNew
''' + route + '''
    return peerMessages
}
''' + '''
func productionUsesCopyPicker(_ transferMode: NagramiXMessageTransferMode, protected nagramiXProtectedCopy: Bool, own nagramiXOwnViewOnceCopy: Bool) -> Bool {
    ''' + bridge + '''
}
func productionRejectsDestination(_ peers: [EnginePeer], threads destinationThreadIds: [Int:Int64]) -> Bool {
    peers.contains(where: { peer in
''' + rejected + '''
    })
}
func productionSnapshot(_ nagramiXCopyThreadIds: [Int:Int64], recipients recipientIds: Set<Int>) -> [Int:Int64] {
    ''' + snapshot + '''
}
'''
    return 'import Foundation\n' + state + selection_class + draft_class + helpers


def validate(args):
    plan = json.loads((ROOT / 'ios/transfer_routing_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    assert before.keys() == after.keys()
    changed = {n for n in before if before[n] != after[n]}
    assert changed == set(plan['hashes']), changed
    texts = {n: (args.before / n).read_text() for n in plan['hashes']}
    assert all(before[n] == sha for n, sha in plan['hashes'].items())
    for n, old, new, count in plan['patches']:
        assert texts[n].count(old) == count
        texts[n] = texts[n].replace(old, new, count)
    assert all(text == (args.after / n).read_text() for n, text in texts.items())
    spec = importlib.util.spec_from_file_location('transfer_routing', ROOT / 'ios/transfer_routing.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected, executions = [], []
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        def seed(target):
            for n in plan['hashes']:
                p = target / n; p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(args.before / n, p)
        def reject(target, label, overlay=ROOT / 'ios'):
            saved = manifest(target)
            try: module.apply_transfer_routing(target, overlay)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError(label)
            assert manifest(target) == saved, label
            rejected.append(label)
        target = temp / 'valid'; seed(target); module.apply_transfer_routing(target, ROOT / 'ios')
        assert all((target / n).read_text() == text for n, text in texts.items())
        reject(target, 'reapply')
        for i,n in enumerate(plan['hashes']):
            for kind in ['missing', 'drift']:
                target = temp / (kind + str(i)); seed(target)
                if kind == 'missing': (target / n).unlink()
                else: (target / n).write_text((target / n).read_text() + '\n// drift\n')
                reject(target, kind + ' ' + n)
        overlay = temp / 'broken'; overlay.mkdir()
        broken = json.loads(json.dumps(plan)); broken['patches'][-1][1] += '// bad last anchor'
        (overlay / 'transfer_routing_patches.json').write_text(json.dumps(broken))
        target = temp / 'anchor'; seed(target); reject(target, 'last anchor', overlay)
        production = temp / 'Production.swift'; production.write_text(swift_sources(args.before, args.after))
        for mode in ['debug','optimized']:
            binary = temp / ('tests-' + mode)
            command = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'),
                       str(ROOT / 'scripts/tests/NagramiXTransferRoutingBoundary.swift'), str(production),
                       str(ROOT / 'scripts/tests/NagramiXTransferRoutingTests.swift'), '-o', str(binary)]
            if mode == 'optimized': command.insert(1, '-O')
            subprocess.run(command, check=True)
            executions.append(mode + ': ' + subprocess.check_output([str(binary)], text=True, timeout=30).strip())
        subprocess.run([str(args.swiftc), '-frontend', '-parse', *[str(args.after / n) for n in sorted(changed)]], check=True)
    for n in ['ios/transfer_routing.py', 'ios/apply_features.py', 'scripts/validate_transfer_routing.py']: ast.parse((ROOT / n).read_text())
    # The historical ownership/file/TTL copier is byte-identical to the native
    # SDK113 baseline. No saving/incoming/screenshot/archive expansion.
    f0, f1 = (args.before / F).read_text(), (args.after / F).read_text()
    assert between(f0, 'func nagramiXCanCopyMessagesAsNew', '\nextension ChatControllerImpl') == between(f1, 'func nagramiXCanCopyMessagesAsNew', '\nextension ChatControllerImpl')
    node = (args.after / N).read_text()
    assert 'if strongSelf.nagramiXCopySelection, threadId != nil {' in node
    assert 'strongSelf.requestOpenPeerFromSearch?(peer, threadId)' in node
    assert 'case .community:\n                                    strongSelf.requestOpenPeerFromSearch?(peer, nil)' in node
    assert 'case let .channel(channel) where channel.isForumOrMonoForum:' in node
    assert 'let transferMode = ownRecordingDraft && transferMode == .forwardWithSource ? NagramiXMessageTransferMode.forwardWithoutSource : transferMode' in f1
    callback = f1.split('            controller.multiplePeersSelected = ', 1)[1]
    assert callback.index('let destinationThreadIds =') < callback.index('context.engine.data.get(')
    assert 'if transferMode.copiesAsNew, let threadId = destinationThreadIds[peer.id]' in f1
    load = (args.after / 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift').read_text()
    assert 'if shouldDivert && messages.contains(where:' in load
    return {'native_outputs':len(after), 'changed':sorted(changed), 'unchanged':len(after)-len(changed),
            'sha_guards':len(plan['hashes']), 'exact_operations':len(plan['patches']), 'fail_closed':rejected,
            'execution':executions, 'native_sdk':'not run: separate build command required', 'physical_iPhone':'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']: parser.add_argument('--'+n,type=Path,required=True)
    args = parser.parse_args(); result = validate(args)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
