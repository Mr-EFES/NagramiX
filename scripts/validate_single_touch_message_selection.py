#!/usr/bin/env python3
"""Проверить выделение диапазона одним пальцем и сохранность прежних жестов."""
import argparse
import json
from pathlib import Path
import tempfile
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_quick_format import block, manifest
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import single_touch_message_selection_runtime as runtime
from single_touch_message_selection_apple import check as apple_check

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'single_touch_message_selection'


def contract(source, plan):
    assert plan['required_previous_stage'] == 'composer_copy_integrity'
    assert set(plan['inputs']) == {runtime.HISTORY} and set(plan['copies']) == {runtime.HELPER}
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE)+1
    for name, expected in {**plan['outputs'], **plan['guards'], **{n:v['sha256'] for n,v in plan['copies'].items()}}.items():
        assert digest(source/name) == expected, name
    history = (source/runtime.HISTORY).read_text()
    previous = (ROOT/'ios'/plan['previous'][runtime.HISTORY]).read_text()
    normalized = history.replace('\n        self.nagramiXBindSingleSelection()\n', '', 1)
    start = normalized.index('    private func nagramiXBindSingleSelection()')
    end = normalized.index('    private var selectionPanState:', start)
    normalized = normalized[:start]+normalized[end:]
    normalized = normalized.replace('                self.nagramiXFinishSingleSelection()\n', '', 1)
    marker = '    private func handlePanSelection('
    current = block(normalized, marker)
    branch = '''            if self.nagramiXSingleSelection != nil {
                self.nagramiXApplySingleSelection(at: location)
                guard self.selectionPanState != nil else { return }
            } else {
'''
    start = current.index(branch)
    stop = current.index('\n            }\n        \n            let scrollingAreaHeight:', start)
    native = current[start+len(branch):stop]
    native = '\n'.join(line[4:] if line.strip() and line.startswith('    ') else line for line in native.split('\n'))
    stripped = current[:start]+native+current[stop+len('\n            }'):]
    assert stripped == block(previous, marker), 'Native two-finger range and autoscroll changed'
    normalized = normalized.replace(current, stripped, 1)
    assert normalized == previous, 'Unrelated history/playback/geometry/read/selection code changed'
    assert block(history, '    private func setupSelectionScrolling(') == block(previous, '    private func setupSelectionScrolling(')
    build = (source/'submodules/TelegramUI/BUILD').read_text()
    assert '"Sources/**/*.swift"' in build
    native = (source/'submodules/ChatListUI/Sources/Node/ChatListNode.swift').read_text()
    two = block(native, 'public class ChatHistoryListSelectionRecognizer:')
    assert 'self.minimumNumberOfTouches = 2' in two and 'self.maximumNumberOfTouches = 2' in two
    entries = (source/'submodules/TelegramUI/Components/Chat/ChatHistoryEntry/Sources/ChatHistoryEntry.swift').read_text()
    assert 'case MessageEntry(EngineRawMessage,' in entries and 'case MessageGroupEntry(Int64,' in entries and 'public var firstIndex: EngineMessage.Index' in entries
    message = (source/'submodules/Postbox/Sources/Message.swift').read_text()
    assert 'public struct MessageIndex: Codable, Comparable, Hashable' in message and 'public var index: MessageIndex' in message
    assert 'public final class MessageHistoryView' in (source/'submodules/Postbox/Sources/MessageHistoryView.swift').read_text()
    backend = (source/'submodules/TelegramUI/Components/Chat/ChatHistoryListViewBackend/Sources/ChatHistoryListViewBackend.swift').read_text()
    assert 'var scrollGestureHostView: UIView' in backend and 'func itemNodeFrame(' in backend
    return {'scope': 'One history initializer call, new isolated range/recognizer helper and history methods; original two-finger selection algorithm, edge autoscroll and every unrelated history byte exact.',
            'behavior': 'Selection mode and 44pt checkbox column only. Pre-gesture baseline survives, fast drags include loaded intermediate rows, reverse shrinks added range, cached windows and albums retained. Existing controller selection callback remains authoritative.',
            'unchanged': 'Main chat list, selection UI, send/delete/forward rights, settings, localization, read receipts, media, row geometry, native two-finger recognizer and native edge scroll timing.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    result = contract(args.source, plan)
    before = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='single-selection-check-') as temporary:
        folder = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, folder/'guards')
        code = runtime.fixture(args.source)
        runs = execute(args.swiftc, folder, 'single-touch-message-selection', code)
        for name, mutated, diagnostic in runtime.negatives(code):
            runs += execute(args.swiftc, folder, name, mutated, diagnostic)
        apple = apple_check(args.source, args.swiftc, folder)
        for name in [runtime.HISTORY, runtime.HELPER]:
            run([args.swiftc, '-frontend', '-parse', args.source/name])
    assert before == manifest(args.source)
    report = {'stage': STAGE, 'source_contract': result, 'loader_refusals': len(refusals), 'executions': runs,
              'apple_uikit_precheck': apple, 'source_unchanged_by_checks': True,
              'boundary': 'Full production range helper, recognizer, binding, actual history row extraction/hit testing/apply/lifecycle and unchanged native autoscroll execute with explicit UIKit/list/model/timer I/O. Random range oracle, reversal, fast jumps, grouped media, paging and cancellation covered. Physical UIKit gesture arbitration and rendering require iPhone.',
              'full_application_sdk': 'not_run', 'device': 'pending'}
    if args.report: args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
