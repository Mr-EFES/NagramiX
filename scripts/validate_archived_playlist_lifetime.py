#!/usr/bin/env python3
"""Отклонить отмену локального плейлиста из-за отсутствия удалённого исходника."""
import argparse
import json
from pathlib import Path
import tempfile
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import archived_playlist_lifetime_runtime as runtime

STAGE = 'archived_playlist_lifetime'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--swiftc', type=Path, required=True)
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'doh_empty_action'
    assert set(plan['inputs']) == {runtime.PLAYLIST} and len(plan['guards']) == 20
    assert not plan['copies'] and not plan['deletions']
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    before = (OVERLAY / plan['previous'][runtime.PLAYLIST]).read_text()
    after = (args.source / runtime.PLAYLIST).read_text()
    marker = '    private func updateState() {'
    old_method, new_method = block(before, marker), block(after, marker)
    assert before.replace(old_method, new_method, 1) == after, 'Other playlist methods changed'
    addition = new_method[new_method.index('        } else if case let .recentActions(message)'):new_method.index('        } else if item?.message.id')]
    assert new_method.replace(addition, '', 1) == old_method, 'Native watcher/state logic changed'
    assert 'let nagramiXContentAlpha: CGFloat = nagramiXIsArchived ? 0.5 : 1.0' in (args.source / 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift').read_text()
    state = manifest(args.source)
    code = runtime.fixture(args.source)
    assert code.count(new_method) == 1
    with tempfile.TemporaryDirectory(prefix='archived-playlist-lifetime-') as d:
        folder = Path(d)
        refused = guard_checks(args.source, STAGE, plan, folder / 'guards')
        runs = execute(args.swiftc, folder, STAGE, code)
        runs += execute(args.swiftc, folder, 'original75-cancels-local-copy', code.replace(new_method, old_method, 1), 'retained missing original never cancels native player')
        condition = 'message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })'
        assert code.count(condition) == 1
        runs += execute(args.swiftc, folder, 'ignore-all-recent-actions', code.replace(condition, '(' + condition + ' || true)', 1), 'ordinary source still observes existing message')
        dispose = '            self.currentlyObservedMessageId = nil\n            self.currentlyObservedMessageDisposable.set(nil)'
        assert code.count(dispose) == 1
        runs += execute(args.swiftc, folder, 'stale-original-watcher', code.replace(dispose, '            self.currentlyObservedMessageId = nil\n            _ = self.currentlyObservedMessageDisposable', 1), 'retained branch disposes old original watcher')
        run([args.swiftc, '-frontend', '-parse', args.source / runtime.PLAYLIST])
    assert state == manifest(args.source)
    report = {
        'stage': STAGE, 'runtime_paths': [runtime.PLAYLIST], 'guards': 20,
        'loader_refusals': len(refused), 'executions': runs,
        'root_cause': 'updateState observes the original Postbox ID even for recentActions archived snapshots; missing original invokes SharedMediaPlayer.cancelled and native MediaManager stops/clears the voice player.',
        'scope': 'Skip/dispose original observation only for recentActions carrying NagramiXArchivedMessageAttribute. All ordinary message/recentActions/custom policies, state/controls/end handling, decoder, identity, 50percent alpha/footer, one-time consumption and archive storage remain unchanged.',
        'boundary': 'Actual updateState and native SharedMediaPlayer→MediaManager cancellation closures execute with real SwiftSignalKit. Engine replies, message/item graph and stop hardware edge are explicit adapters; UIKit frames, live Postbox/database and actual video decoder not exercised.',
        'source_unchanged_by_checks': True, 'full_application_sdk': 'pending', 'physical_iphone': 'pending',
        'new_sdk_actions_ipa_started': False,
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
