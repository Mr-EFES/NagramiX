#!/usr/bin/env python3
"""Exercise folder handoff and real enqueue copy routing without Apple SDK."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
C = 'submodules/ChatListUI/Sources/ChatListControllerNode.swift'
N = 'submodules/TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionControllerNode.swift'
F = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
E = 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift'


def production(before, after):
    container = (after/C).read_text()
    assert 'nagramiXPreserveCopyRecipients' not in (before/C).read_text()
    assignment = 'self.currentItemNodeValue = itemNode'
    assert assignment in block((before/C).read_text(), 'private func applyItemNodeAsCurrent(')
    handoff = block(container, 'if self.nagramiXPreserveCopyRecipients,')
    configure = block((after/N).read_text(), 'var nagramiXCopySelection = false')
    def route(root):
        text = (root/F).read_text()
        start = text.index('                                    var peerMessages = result')
        end = text.index('                                    if shouldDivert {', start)
        return text[start:end]
    enqueue = (after/E).read_text()
    forward = (after/F).read_text()
    rejected = forward.split('if transferMode.copiesAsNew && peers.contains(where: { peer in\n',1)[1].split('\n                }) {',1)[0]
    snapshot = forward.split('                let destinationThreadIds = ',1)[1].split('\n                if transferMode.copiesAsNew',1)[0]
    methods = '\n'.join(block(enqueue, 'public func '+name+'(').replace('public ', '')
                        for name in ['withUpdatedThreadId', 'withUpdatedReplyToMessageId'])
    # Only the selection handoff/assignment is executed. UIKit callback wiring
    # after the assignment is deliberately a boundary, not a claimed UI test.
    return '''
extension FolderContainer {
    func activate(_ itemNode: Folder) {
''' + handoff + '''
        self.currentItemNodeValue = itemNode
    }
    func legacyActivate(_ itemNode: Folder) { ''' + assignment + ''' }
}
final class Picker {
    var mainContainerNode: FolderContainer? = FolderContainer()
''' + configure + '''
}
extension EnqueueMessage {
''' + methods + '''
}
func route(_ result: [EnqueueMessage], to peer: EnginePeer, topics destinationThreadIds: [Int:Int64], copy: Bool = true) -> [EnqueueMessage] {
    let transferMode = Mode(copiesAsNew: copy)
''' + route(after) + '''
    return peerMessages
}
func legacyRoute(_ result: [EnqueueMessage], to peer: EnginePeer, topics destinationThreadIds: [Int:Int64]) -> [EnqueueMessage] {
    let transferMode = Mode(copiesAsNew: true)
''' + route(before) + '''
    return peerMessages
}
func rejects(_ peers: [EnginePeer], topics destinationThreadIds: [Int:Int64]) -> Bool {
    peers.contains(where: { peer in
''' + rejected + '''
    })
}
func snapshotTopics(_ nagramiXCopyThreadIds: [Int:Int64], recipients recipientIds: Set<Int>) -> [Int:Int64] {
''' + snapshot + '''
}
'''


def validate(args):
    plan = json.loads((ROOT/'ios/broadcast_topics_patches.json').read_text())
    a, b = manifest(args.before), manifest(args.after)
    assert a.keys() == b.keys()
    changed = {n for n in a if a[n] != b[n]}
    assert changed == set(plan['hashes']), changed
    assert all(a[n] == digest for n, digest in plan['hashes'].items())
    forward = (args.after/F).read_text().split('controller.multiplePeersSelected = ',1)[1]
    assert forward.index('let destinationThreadIds =') < forward.index('if transferMode.copiesAsNew && peers.contains') < forward.index('context.engine.data.get(')
    spec = importlib.util.spec_from_file_location('broadcast_topics', ROOT/'ios/broadcast_topics.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    failures, runs = [], []
    with tempfile.TemporaryDirectory(prefix='nagramix-broadcast-') as temp:
        temp = Path(temp)
        def seed(target):
            for n in plan['hashes']:
                (target/n).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(args.before/n, target/n)
        def reject(target, label, overlay=ROOT/'ios'):
            snapshot = manifest(target)
            try: mod.apply_broadcast_topics(target, overlay)
            except SystemExit: pass
            else: raise AssertionError('Accepted invalid overlay: '+label)
            assert manifest(target) == snapshot, label
            failures.append(label)
        replay = temp/'replay'; seed(replay); mod.apply_broadcast_topics(replay, ROOT/'ios')
        assert all((replay/n).read_bytes() == (args.after/n).read_bytes() for n in changed)
        reject(replay, 'already applied')
        for n in plan['hashes']:
            for kind in ['missing', 'drift']:
                target = temp/(kind+str(len(failures))); seed(target)
                if kind == 'missing': (target/n).unlink()
                else: (target/n).write_text((target/n).read_text()+'\n// drift\n')
                reject(target, kind+' '+n)
        for index in range(len(plan['patches'])):
            broken = json.loads(json.dumps(plan)); broken['patches'][index][1] += ' invalid anchor'
            overlay = temp/('bad'+str(index)); overlay.mkdir()
            (overlay/'broadcast_topics_patches.json').write_text(json.dumps(broken))
            target = temp/('anchor'+str(index)); seed(target); reject(target, 'anchor '+str(index), overlay)
        source = temp/'Production.swift'; source.write_text(production(args.before,args.after))
        for mode in ['debug', 'optimized']:
            binary = temp/mode
            command = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(temp/'cache'),
                       str(ROOT/'scripts/tests/NagramiXBroadcastTopicsTests.swift'), str(source), '-o', str(binary)]
            if mode == 'optimized': command.insert(1, '-O')
            subprocess.run(command, check=True)
            runs.append(mode+': '+subprocess.check_output([str(binary)],text=True,timeout=30).strip())
        subprocess.run([str(args.swiftc), '-frontend', '-parse', *[str(args.after/n) for n in sorted(changed)]],check=True)
    # Prove the native state/remapping and per-recipient enqueue remain the same
    # outside the precise patch operations, including fee/schedule/one-shot code.
    for n in changed:
        text = (args.before/n).read_text()
        for path, old, new, count in plan['patches']:
            if n == path: text = text.replace(old,new,count)
        assert text == (args.after/n).read_text()
    for name in ['ios/broadcast_topics.py','ios/apply_features.py','scripts/validate_broadcast_topics.py']:
        ast.parse((ROOT/name).read_text())
    return dict(native_outputs=len(b), changed=sorted(changed), unchanged=len(b)-len(changed),
                sha_guards=len(plan['hashes']), operations=len(plan['patches']), fail_closed=failures,
                runs=runs, sdk='not run', physical_iPhone='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before','after','swiftc','report']: parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    result = validate(args)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
