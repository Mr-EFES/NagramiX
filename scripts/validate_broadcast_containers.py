#!/usr/bin/env python3
"""Execute both native row paths plus the existing copy routing regressions."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from validate_quick_format import ROOT, block, manifest
from validate_broadcast_topics import production as routing_production

FILTER = 'submodules/AccountContext/Sources/PeerSelectionController.swift'
ROWS = 'submodules/ChatListUI/Sources/Node/ChatListNode.swift'
FORWARD = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
CONTROLLER = 'submodules/TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionController.swift'


def row_production(text, prefix):
    matches = list(re.finditer(r'(?ms)^[ ]+var isForum = false\n.*?(?=^[ ]+return ListView(?:Insert|Update)Item)', text))
    assert len(matches) == 2
    functions = []
    for phase, match in zip(['Insert', 'Update'], matches):
        action_start = text.index('action: { _ in', match.end())
        action_end = text.index('}, disabledAction:', action_start) + 1
        action = block(text[action_start:action_end], 'action: { _ in')
        action = action.replace('action: { _ in', 'let action: (Int) -> Void = { _ in', 1)
        functions.append(f'''
func {prefix}Row{phase}(_ chatPeer: EnginePeer?, _ editing: Bool, _ isSelecting: Bool,
                       _ threadId: Int64?, _ filter: ChatListNodePeersFilter, _ permitted: Bool) -> RowResult {{
    var enabled = permitted
    let nodeInteraction = RowInteraction()
{match.group()}
    {action}
    // ContactsPeerItem's enabled gating is a UIKit boundary.
    if enabled {{ action(0) }}
    return RowResult(enabled: enabled, selectable: selectable, opened: nodeInteraction.opened,
                     threads: nodeInteraction.threads, toggled: nodeInteraction.toggled)
}}
''')
    return '\n'.join(functions)


def validate(args):
    plan = json.loads((ROOT / 'ios/broadcast_containers_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    assert before.keys() == after.keys()
    assert {n for n in before if before[n] != after[n]} == set(plan['inputs'])
    assert all(before[n] == sha for n, sha in plan['inputs'].items())
    assert all(after[n] == sha for n, sha in plan['outputs'].items())
    # Native topic picking, topic snapshots, fee guards and enqueue paths stay
    # unchanged. Only the previously disabled row becomes a navigation entry.
    assert (args.before / CONTROLLER).read_bytes() == (args.after / CONTROLLER).read_bytes()
    f = (args.after / FORWARD).read_text()
    a = (args.before / FORWARD).read_text()
    unchanged_tail = '            if transferMode.copiesAsNew {\n                controller.nagramiXConfigureCopySelection()'
    assert a[a.index(unchanged_tail):] == f[f.index(unchanged_tail):]
    flag = block(f, 'if transferMode == .copyAsNew && !nagramiXOwnViewOnceCopy')
    options = block((args.after / FILTER).read_text(), 'public struct ChatListNodePeersFilter:')
    assert '1 << 19' not in (args.before / FILTER).read_text()
    helper = block((args.after / ROWS).read_text(), 'private func isIncludedCommunityContainer(')
    production = options + '\n' + helper + '\n' + row_production((args.before / ROWS).read_text(), 'legacy')
    production += '\n' + row_production((args.after / ROWS).read_text(), 'copy')
    production += '''
func makeBroadcastFilter(_ transferMode: NagramiXMessageTransferMode, ownViewOnce nagramiXOwnViewOnceCopy: Bool) -> ChatListNodePeersFilter {
    var filter: ChatListNodePeersFilter = [.onlyWriteable, .excludeDisabled, .doNotSearchMessages]
''' + flag + '''
    return filter
}
'''
    production += routing_production(args.routing_before, args.after)
    executions = []
    with tempfile.TemporaryDirectory(prefix='broadcast-containers-') as directory:
        tmp = Path(directory)
        (tmp / 'Production.swift').write_text('import Foundation\n' + production)
        old_tests = (ROOT / 'scripts/tests/NagramiXBroadcastTopicsTests.swift').read_text()
        assert old_tests.count('@main struct Tests') == 1
        (tmp / 'RoutingTests.swift').write_text(old_tests.replace('@main struct Tests', 'struct Tests', 1))
        for mode in ['debug', 'optimized']:
            binary = tmp / mode
            command = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(tmp / 'cache'),
                str(tmp / 'RoutingTests.swift'), str(tmp / 'Production.swift'),
                str(ROOT / 'scripts/tests/NagramiXBroadcastContainerTests.swift'), '-o', str(binary)]
            if mode == 'optimized':
                command.insert(1, '-O')
            subprocess.run(command, check=True)
            output = subprocess.check_output([str(binary)], text=True, timeout=30,
                env=dict(os.environ, XDG_CONFIG_HOME=str(tmp / ('prefs-' + mode))))
            executions.append(dict(mode=mode, output=output.strip()))
        subprocess.run([str(args.swiftc), '-frontend', '-parse', *[str(args.after / n) for n in plan['inputs']]], check=True)
    return dict(execution=executions, topic_controller='byte-identical',
        UIKit='enabled state/widget/lifecycle boundaries', network='not executed', Apple_SDK='pending', physical_iPhone='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'routing-before', 'swiftc', 'report']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
