#!/usr/bin/env python3
"""Verify that a retained row reaches the native deletion transition without being hidden."""
import argparse
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, ROOT, checked_plan

STAGE = 'archive_local_delete_transition'
ARCHIVE = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
CHAT = 'submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift'
HISTORY = 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift'


def fixture(source: Path, plan: dict) -> str:
    archive = (source / ARCHIVE).read_text()
    chat = (source / CHAT).read_text()
    history = (source / HISTORY).read_text()
    original_history = (OVERLAY / plan['previous'][HISTORY]).read_text()
    original_chat = (OVERLAY / plan['previous'][CHAT]).read_text()
    history_state = next(line for line in history.splitlines() if 'var nagramiXPendingRetainedDeletionIds:' in line)
    delete_method = block(chat, '    private func nagramiXDeleteArchivedPostsWithUndo(')
    assert block(history, '    private func dequeueHistoryViewTransitions(') == block(original_history, '    private func dequeueHistoryViewTransitions(')
    assert block(chat, '    private func nagramiXBeginNativeDeleteMessagesWithUndo(') == block(original_chat, '    private func nagramiXBeginNativeDeleteMessagesWithUndo(')
    assert 'self.recordForDeletion(message)' in block(archive, '    public func archiveMessagesBeforeDeletion(')
    test = (ROOT / 'scripts/tests/NagramiXArchiveLocalDeleteTransition.swift').read_text()
    declarations = '\n'.join(block(archive, marker) for marker in (
        'private struct NagramiXArchivePostKey:', 'public struct NagramiXArchivePostDeletionPlan',
    ))
    methods = '\n'.join(block(archive, marker) for marker in (
        '    private static func isRegularArchiveIdentifier(',
        '    private func recordForDeletion(',
        '    public func postMessageIds(',
        '    public func postDeletionPlan(',
    ))
    return (test.replace('// ACTUAL_ARCHIVE_PLAN', declarations, 1)
            .replace('// ACTUAL_ARCHIVE_METHODS', methods, 1)
            .replace('// ACTUAL_HISTORY_STATE', history_state, 1)
            .replace('// ACTUAL_CONTROLLER_METHOD', delete_method.replace('private func nagramiXDeleteArchivedPostsWithUndo', 'func confirm', 1), 1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name in plan['inputs']:
        run([args.swiftc, '-frontend', '-parse', args.source / name], timeout=60)
    with tempfile.TemporaryDirectory(prefix='archive-local-delete-') as directory:
        folder = Path(directory)
        code = folder / 'LocalDelete.swift'
        code.write_text(fixture(args.source, plan))
        for mode, flags in [('debug', []), ('optimized', ['-O'])]:
            app = folder / mode
            run([args.swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
                 '-module-cache-path', folder / 'cache', *flags, code, '-o', app], timeout=100)
            print(f'{mode}: {run([app], timeout=30).stdout.strip()}', flush=True)


if __name__ == '__main__':
    main()
