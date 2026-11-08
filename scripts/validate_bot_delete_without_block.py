#!/usr/bin/env python3
"""Проверить отдельное удаление бота и сохранность штатных удаления/Undo."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
NAME = 'submodules/ChatListUI/Sources/ChatListController.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def plan():
    return json.loads((OVERLAY / 'bot_delete_without_block_patches.json').read_text())


def seed(source, item):
    originals = {**item['previous'], **item['guard_sources']}
    for name, template in originals.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((OVERLAY / template).read_bytes())


def verify(source, item):
    for name, value in {**item['outputs'], **item['guards']}.items():
        assert sha((source / name).read_bytes()) == value, name
    for name, value in item['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == value, name
    before = (OVERLAY / item['previous'][NAME]).read_text()
    after = (source / NAME).read_text()
    old_menu = block(before, '    func deletePeerChat(peerId:')
    new_menu = block(after, '    func deletePeerChat(peerId:')
    old_actions = block(old_menu, '                    if canStop {')
    new_actions = block(new_menu, '                    if canStop {')
    addition = '''                        actions.append(AlertScreen.Action(title: strongSelf.presentationData.strings.Common_Delete, type: .destructive, action: {
                            self?.maybeAskForPeerChatRemoval(peer: peer, completion: { _ in
                            }, removed: {})
                        }))
'''
    assert new_actions.count(addition) == 1
    assert new_actions.replace(addition, '') == old_actions
    assert after.replace(new_actions, old_actions, 1) == before, 'Unrelated source changed'
    for marker in ('    public func maybeAskForPeerChatRemoval(', '    private func schedulePeerChatRemoval('):
        assert block(after, marker) == block(before, marker), marker
    assert block(new_menu, '                    if canClear {') == block(old_menu, '                    if canClear {')
    assert 'public func removePeerChat(peerId: PeerId, reportChatSpam: Bool, deleteGloballyIfPossible: Bool = false)' in (source / 'submodules/TelegramCore/Sources/TelegramEngine/Peers/TelegramEnginePeers.swift').read_text()
    assert 'public func clearHistoryInteractively(peerId: PeerId, threadId: Int64?, type: InteractiveHistoryClearingType)' in (source / 'submodules/TelegramCore/Sources/TelegramEngine/Messages/TelegramEngineMessages.swift').read_text()
    assert '"Common.Delete" = "Delete";' in (source / 'Telegram/Telegram-iOS/en.lproj/Localizable.strings').read_text()
    return new_actions, old_actions


def guard_checks(item, folder):
    spec = importlib.util.spec_from_file_location('bot_delete_without_block', OVERLAY / 'bot_delete_without_block.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tested = 0

    def snapshot(root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def rejected(source, overlay=OVERLAY):
        nonlocal tested
        old = snapshot(source)
        try:
            module.apply_bot_delete_without_block(source, overlay)
        except (SystemExit, FileNotFoundError):
            pass
        else:
            raise AssertionError('Invalid bot delete input accepted')
        assert snapshot(source) == old, 'Partial write before validation'
        tested += 1

    source = folder / 'source'
    seed(source, item)
    module.apply_bot_delete_without_block(source, OVERLAY)
    verify(source, item)
    rejected(source)
    for name in {**item['inputs'], **item['guards']}:
        seed(source, item)
        p = source / name
        p.write_bytes(p.read_bytes() + b'drift')
        rejected(source)
    seed(source, item)
    (source / NAME).unlink()
    rejected(source)
    for key, value in [('required_previous_stage', 'wrong'), ('target_pin', 'wrong')]:
        seed(source, item)
        altered = folder / ('overlay-' + key)
        shutil.copytree(OVERLAY / 'bot_delete_without_block', altered / 'bot_delete_without_block')
        bad = copy.deepcopy(item)
        bad[key] = value
        (altered / 'bot_delete_without_block_patches.json').write_text(json.dumps(bad))
        rejected(source, altered)
    seed(source, item)
    corrupt = folder / 'overlay-template'
    for name in item['templates']:
        p = corrupt / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((OVERLAY / name).read_bytes())
    p = corrupt / item['replacements'][NAME]
    p.write_bytes(p.read_bytes() + b'drift')
    (corrupt / 'bot_delete_without_block_patches.json').write_text(json.dumps(item))
    rejected(source, corrupt)
    return tested


def runtime_source(menu):
    # Production menu closures execute unchanged; scheduling/privacy/AlertScreen
    # are explicit adapters. Native scheduling and Undo bodies are byte-checked.
    return '''
import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
var checks = 0
func check(_ value: Bool, _ label: String) {
    if !value { fputs("FAIL: " + label + "\\n", stderr); exit(91) }
    checks += 1
}
struct Peer { let peerId: Int }
enum AlertScreen {
    struct Action {
        enum Kind { case destructive }
        let title: String
        let type: Kind
        let action: () -> Void
    }
}
final class Log {
    var asks: [Int] = []
    var blocks: [Int] = []
    var pendingRemoved: [() -> Void] = []
}
final class Request {
    let body: () -> Void
    init(_ body: @escaping () -> Void) { self.body = body }
    func startStandalone() { self.body() }
}
final class Privacy {
    let log: Log
    init(_ log: Log) { self.log = log }
    func requestUpdatePeerIsBlocked(peerId: Int, isBlocked: Bool) -> Request {
        return Request { if isBlocked { self.log.blocks.append(peerId) } }
    }
}
struct Engine { let privacy: Privacy }
struct Context { let engine: Engine }
struct Strings {
    let DialogList_DeleteBotConversationConfirmation = "delete-and-block"
    let Common_Delete = "delete"
}
struct PresentationData { let strings = Strings() }
final class Controller {
    let log: Log
    let context: Context
    let presentationData = PresentationData()
    init(_ log: Log) { self.log = log; self.context = Context(engine: Engine(privacy: Privacy(log))) }
    func maybeAskForPeerChatRemoval(peer: Peer, completion: @escaping (Bool) -> Void, removed: @escaping () -> Void) {
        self.log.asks.append(peer.peerId)
        self.log.pendingRemoved.append(removed)
        completion(true)
    }
    func makeActions(canStop: Bool, peer: Peer) -> [AlertScreen.Action] {
        var actions: [AlertScreen.Action] = []
        let build = { [weak self] in
            guard let strongSelf = self else { return }
''' + menu + '''
        }
        build()
        return actions
    }
}
let log = Log()
var controller: Controller? = Controller(log)
check(controller!.makeActions(canStop: false, peer: Peer(peerId: 7)).isEmpty, "support or non-stop bot unchanged")
let actions = controller!.makeActions(canStop: true, peer: Peer(peerId: 7))
check(actions.count == 2, "bot offers delete without block")
check(actions[0].title == "delete-and-block", "original destructive action order")
check(actions[1].title == "delete", "plain delete is native localized title")
check(actions.allSatisfy { $0.type == .destructive }, "both actions are destructive")
check(log.asks.isEmpty && log.blocks.isEmpty, "opening menu has no effects")
actions[1].action()
check(log.asks == [7], "plain delete uses native confirmation and scheduling")
check(log.blocks.isEmpty, "plain delete does not block before commit")
check(log.pendingRemoved.count == 1, "plain delete uses removed callback")
log.pendingRemoved.removeFirst()()
check(log.blocks.isEmpty, "plain delete does not block after commit")
actions[0].action()
check(log.asks == [7, 7], "delete and block keeps native confirmation")
check(log.blocks.isEmpty, "delete and block waits for committed removal")
log.pendingRemoved.removeFirst()()
check(log.blocks == [7], "original action blocks after commit")
actions[1].action()
check(log.pendingRemoved.count == 1, "another plain removal reaches native scheduling")
log.pendingRemoved.removeAll()
check(log.blocks == [7], "cancel or undo does not block plain delete")
let weakActions = controller!.makeActions(canStop: true, peer: Peer(peerId: 9))
controller = nil
weakActions[0].action()
weakActions[1].action()
check(log.asks == [7, 7, 7], "stale menu has no controller side effects")
check(log.blocks == [7], "stale menu has no privacy side effects")
print("PASS bot menu production checks: \\(checks)")
'''


def run_swift(menu, old_menu, swiftc, folder):
    mutations = {
        'old-menu': old_menu,
        'plain-delete-blocks': menu.replace('}, removed: {})', '}, removed: {\n                                let _ = self?.context.engine.privacy.requestUpdatePeerIsBlocked(peerId: peer.peerId, isBlocked: true).startStandalone()\n                            })'),
        'plain-delete-no-op': menu.replace('                            self?.maybeAskForPeerChatRemoval(peer: peer, completion: { _ in\n                            }, removed: {})', '                            _ = peer.peerId'),
    }
    runs = []
    negatives = 0
    for optimized in (False, True):
        flags = ['-warnings-as-errors', '-module-cache-path', str(folder / 'module-cache')] + (['-O'] if optimized else [])
        path = folder / ('menu-optimized.swift' if optimized else 'menu-debug.swift')
        path.write_text(runtime_source(menu))
        binary = path.with_suffix('')
        subprocess.run([swiftc, *flags, str(path), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], check=True, text=True, capture_output=True)
        runs.append(result.stdout.strip())
        for key, mutation in mutations.items():
            negative = folder / (key + ('-optimized.swift' if optimized else '-debug.swift'))
            negative.write_text(runtime_source(mutation))
            executable = negative.with_suffix('')
            subprocess.run([swiftc, *flags, str(negative), '-o', str(executable)], check=True)
            result = subprocess.run([str(executable)], text=True, capture_output=True)
            assert result.returncode == 91 and 'FAIL:' in result.stderr, key
            negatives += 1
    return runs, negatives


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path)
    parser.add_argument('--swiftc')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    item = plan()
    with tempfile.TemporaryDirectory(prefix='bot-delete-without-block-') as temp:
        folder = Path(temp)
        source = args.source
        if source is None:
            source = folder / 'candidate'
            seed(source, item)
            (source / NAME).write_bytes((OVERLAY / item['replacements'][NAME]).read_bytes())
        menu, old_menu = verify(source, item)
        report = {'outputs': item['outputs'], 'guards': len(item['guards']), 'fail_closed': guard_checks(item, folder), 'new_ui_keys': 0, 'native_undo_scheduling': 'byte-identical', 'boundaries': 'Actual menu closures; AlertScreen, privacy and removal scheduling are adapters. Native scheduling, clear-history and Undo source remains byte-identical.', 'apple_sdk': 'pending', 'physical_iphone': 'pending'}
        if args.swiftc:
            runs, negatives = run_swift(menu, old_menu, args.swiftc, folder)
            report.update(production_runs=runs, semantic_negative_runs=negatives)
            full = folder / 'ChatListController.swift'
            full.write_bytes((source / NAME).read_bytes())
            subprocess.run([args.swiftc, '-frontend', '-parse', str(full)], check=True)
            report['swift_parse_outputs'] = 1
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
