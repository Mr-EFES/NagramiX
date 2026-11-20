#!/usr/bin/env python3
"""Exercise the revision comparison and verify the four snapshot export routes."""
import argparse
from pathlib import Path
import tempfile

from late_source_stages import ROOT
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest

STAGE = 'edit_history_revision_actions'
UI = Path('submodules/TelegramUI/Sources')


def validate(source, swiftc, folder):
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    screen = source / UI / 'Chat/NagramiXEditHistoryController.swift'
    text = screen.read_text()
    row = block(text, '    func tableView(_ tableView: UITableView, cellForRowAt')
    assert 'let index = self.revisions.count - 1 - indexPath.row' in row
    assert 'let adjacentIndex = isCurrent ? index - 1 : index + 1' in row
    assert 'self.revisions[index]' in row and 'cell.configure(revision: revision, index: index' in row
    assert row.count('guard let self, self.canExport else { return }') == 4
    assert 'storeMessageTextInPasteboard(revision.text, entities: revision.entities)' in row
    snapshot = 'nagramiXEditHistorySnapshot(message: self.message, revision: revision)'
    assert 'self.forwardRevision?(' + snapshot + ')' in row
    assert 'self.broadcastRevision?([' + snapshot + '])' in row
    assert 'subject: .text(revision.text), externalShare: true, immediateExternalShare: true' in row
    menu = (source / UI / 'ChatInterfaceStateContextMenus.swift').read_text()
    assert 'forward: interfaceInteraction.forwardEditHistoryVersion, broadcast: interfaceInteraction.copyMessagesWithoutSource' in menu
    route = (source / UI / 'Chat/ChatControllerLoadDisplayNode.swift').read_text().split('}, copyMessagesWithoutSource:', 1)[1].split('}, forwardEditHistoryVersion:', 1)[0]
    assert 'NagramiXArchivedMessageAttribute' in route and 'self.forwardMessages(messages: messages.sorted' in route
    assert 'NagramiXArchivedMessageAttribute(' in block(text, 'func nagramiXEditHistorySnapshot')
    assert 'self.actions.isHidden = !canExport || revision.text.isEmpty' in text
    assert 'self.textView.isSelectable = canExport && !revision.text.isEmpty' in text
    assert 'self.actions.distribution = .fillEqually' in text and 'greaterThanOrEqualToConstant: 44.0' in text
    assert 'configuration.imagePlacement = accessibleSize ? .leading : .top' in text
    assert '.underlineStyle : .strikethroughStyle' in text
    run([swiftc, '-frontend', '-parse', screen, source / UI / 'ChatInterfaceStateContextMenus.swift'])
    fixture = (ROOT / 'scripts/tests/NagramiXRevisionComparison.swift').read_text()
    fixture = fixture.replace('// COMPARISON', block(text, 'private enum NagramiXRevisionComparison'))
    fixture = fixture.replace('// SNAPSHOT', 'private ' + block(text, 'func nagramiXEditHistorySnapshot'))
    fixture = fixture.replace('// ROW', row)
    for result in execute(swiftc, folder, 'RevisionComparison', fixture):
        print(result['mode'], result['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='revision-actions-') as tmp:
        validate(args.source, args.swiftc, Path(tmp))
