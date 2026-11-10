#!/usr/bin/env python3
"""Check fresh ASR defaults, account Premium routing and preservation of saved preferences."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import transcription_account_defaults_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'transcription_account_defaults'
ASR = runtime.ASR
UI = 'submodules/TelegramUI/'
FILE = UI + 'Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift'
ROUND = UI + 'Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift'
MENU = UI + 'Sources/ChatInterfaceStateContextMenus.swift'
ROOT_UI = 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift'


def source_contract(source, plan):
    assert plan['required_previous_stage'] == 'archived_round_native_controls'
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    assert set(plan['outputs']) == {ASR + n + '.swift' for n in ('Settings', 'Coordinator', 'Runtime', 'Preferences')} | {runtime.ACCOUNT, FILE, ROUND, MENU, ROOT_UI}
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    previous = {n: (ROOT / 'ios' / plan['previous'][n]).read_text() for n in plan['outputs']}
    current = {n: (source / n).read_text() for n in plan['outputs']}

    account = previous[runtime.ACCOUNT].replace('import NagramiXCore\n', 'import NagramiXCore\nimport NagramiXTranscription\n', 1)
    anchor = '        |> mapToSignal { peer -> Signal<(Bool, EngineConfiguration.UserLimits), NoError> in\n'
    assert account.count(anchor) == 1
    account = account.replace(anchor, anchor + '            if let peer {\n                NagramiXTranscriptionSettings.registerAccountDefault(accountId: account.id.int64, isPremium: peer.isPremium)\n            }\n', 1)
    assert account == current[runtime.ACCOUNT], 'Startup only registers a known actual account peer'
    assert '//submodules/NagramiXTranscription' in (source / (UI + 'BUILD')).read_text()
    assert 'public var int64: Int64' in (source / 'submodules/TelegramCore/Sources/AccountManager/AccountRecord.swift').read_text()
    peer = (source / 'submodules/TelegramCore/Sources/TelegramEngine/Peers/Peer.swift').read_text()
    assert 'public extension EnginePeer {' in peer and 'var isPremium: Bool' in peer

    # Nodes retain every native geometry, animation and player byte; only ASR calls receive context.
    for path, arguments in [(FILE, [('message', 'context'), ('arguments.message', 'arguments.context')]), (ROUND, [('item.message', 'item.context')]), (MENU, [('message', 'context')])]:
        expected = previous[path]
        for method in ('handlesContext', 'handles', 'cached', 'hasTemporaryTranscript'):
            for message, context in arguments:
                expected = expected.replace('NagramiXTranscriptionRuntime.' + method + '(' + message + ')', 'NagramiXTranscriptionRuntime.' + method + '(' + message + ', context: ' + context + ')')
        if path == MENU:
            expected = expected.replace('NagramiXTranscriptionSettings.current.provider', 'NagramiXTranscriptionSettings.configuration(accountId: context.account.id.int64).provider')
        assert current[path] == expected, path

    settings = current[ASR + 'Settings.swift']
    old = previous[ASR + 'Settings.swift']
    assert settings[:settings.index('public struct NagramiXTranscriptionConfiguration:')] == old[:old.index('public struct NagramiXTranscriptionConfiguration:')], 'Provider/model catalogs unchanged'
    assert block(settings, '    public static var current:') == block(old, '    public static var current:'), 'Legacy decoding/migration unchanged'
    assert block(settings, '    public var cacheTag:') == block(old, '    public var cacheTag:'), 'Cache identity unchanged'
    assert 'public var usesAccountDefaultProvider: Bool? = true' in settings
    assert 'value.sourceAccountId = nil' in block(settings, '    public static func update(')
    prefs = current[runtime.PREFS]
    assert '$0.usesAccountDefaultProvider = false; $0.provider = provider;' in prefs
    assert prefs.count('NagramiXTranscriptionSettings.current.revision') == 2, 'Existing model-download revision guards remain shared'
    assert 'if provider == .telegram && !self.isPremium { return }' in prefs

    execution = current[ASR + 'Runtime.swift']
    old_execution = previous[ASR + 'Runtime.swift']
    for name in ('    public static func file(', '    public static func canUseTelegram(', '    private static func identity(', '    private static func load('):
        assert block(execution, name) == block(old_execution, name), name
    safe_config = block(execution, '    private static func configuration(for message:')
    original = block(old_execution, '    private static func configuration(for message:')
    safe_config = safe_config.replace(', context: AccountContext? = nil', '', 1)
    safe_config = safe_config.replace('context.map { NagramiXTranscriptionSettings.configuration(accountId: $0.account.id.int64) } ?? NagramiXTranscriptionSettings.current', 'NagramiXTranscriptionSettings.current', 1)
    assert safe_config == original, 'Private temporary override stays byte-for-byte equivalent'
    assert 'guard peer?.isPremium == true' in execution
    coordinator = current[ASR + 'Coordinator.swift']
    for name in ('    private func pump()', '    func cancelAll()', '    private func completeListeners('):
        assert block(coordinator, name) == block(previous[ASR + 'Coordinator.swift'], name), name
    assert 'configuration(matching: job.configuration)' in coordinator

    root_ui = current[ROOT_UI]
    assert 'let transcription = NagramiXTranscriptionSettings.configuration(accountId: context.account.id.int64)' in root_ui
    for name in ('nagramiXAllSettingsEntries', 'nagramiXSettingsEntries', 'nagramiXSearchEntries'):
        declaration = block(root_ui, 'private func ' + name + '(')
        assert 'transcription: NagramiXTranscriptionConfiguration' in declaration
        assert ('transcription.enabled' in declaration) if name == 'nagramiXAllSettingsEntries' else ('transcription: transcription' in declaration)
    assert 'category: category, transcription: transcription)' in root_ui
    assert 'query: normalizedQuery, transcription: transcription)' in root_ui
    # No unregistered/orphan snapshots in the newly introduced stage.
    assert {str(p.relative_to(ROOT / 'ios')) for p in (ROOT / 'ios' / STAGE).glob('*.inc')} == set(plan['templates'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    source_contract(args.source, plan)
    initial = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='transcription-defaults-') as temporary:
        folder = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, folder / 'guards')
        code = runtime.fixture(args.source)
        executions = execute(args.swiftc, folder, 'account-defaults', code)
        for name, mutated, diagnostic in runtime.negatives(code):
            executions += execute(args.swiftc, folder, name, mutated, diagnostic)
        for name in plan['outputs']:
            run([args.swiftc, '-frontend', '-parse', args.source / name])
    assert manifest(args.source) == initial
    report = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
              'loader_refusals': len(refusals), 'executions': executions, 'swift_parse': len(plan['outputs']),
              'source_files': len(initial), 'source_unchanged_by_checks': True,
              'boundary': 'Complete production Settings, Coordinator, ASR Runtime and existing private-temporary engine/RPC tests execute with explicit IO/Postbox adapters. Actual startup registration and manual-choice transform are extracted from native callers. Root/search and native voice/round call sites are checked exactly; UIKit/whole-module Apple SDK, Speech permission and account login need the next authorized SDK/device check.',
              'apple_sdk': 'not_run', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
