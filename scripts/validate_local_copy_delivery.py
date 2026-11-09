#!/usr/bin/env python3
"""Проверить завершение отправки самостоятельных копий без Apple SDK."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

import local_copy_delivery_runtime as delivery
import local_copy_manager_runtime as manager_runtime
import local_copy_media_runtime as media_runtime
import local_copy_payload_runtime as payload_runtime
import local_copy_group_failure_runtime as group_runtime


ROOT = Path(__file__).resolve().parents[1]
STAGE = 'local_copy_delivery'
CORE = 'submodules/TelegramCore/Sources/'
UPLOAD = CORE + 'PendingMessages/PendingMessageUploadedContent.swift'
MANAGER = CORE + 'State/PendingMessageManager.swift'
COPIER = CORE + 'Utils/NagramiXOutgoingCopy.swift'


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, **kwargs)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def execute(swiftc, root, name, text, diagnostic=None, failure_code=91):
    path = root / (name + '.swift')
    path.write_text(text)
    results = []
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        binary = root / (name + '-' + mode)
        run([swiftc, '-swift-version', '5', '-parse-as-library', '-warnings-as-errors',
             '-module-cache-path', root / 'cache', *flags, path, '-o', binary])
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
        output = result.stdout + result.stderr
        if diagnostic is None:
            assert result.returncode == 0, (name, mode, output)
        else:
            assert result.returncode == failure_code and diagnostic in output, (name, mode, diagnostic, output)
        results.append({'name': name, 'mode': mode, 'exit_code': result.returncode,
                        'output': output.strip()})
        binary.unlink()
    return results


def capture_negative(swiftc, root, name, text, diagnostic):
    path = root / (name + '.swift')
    path.write_text(text)
    result = subprocess.run([str(swiftc), '-swift-version', '5', '-parse-as-library',
                             '-warnings-as-errors', '-module-cache-path', str(root / 'cache'),
                             '-typecheck', str(path)], capture_output=True, text=True)
    output = result.stdout + result.stderr
    assert result.returncode != 0 and diagnostic in output, (name, output)
    return {'name': name, 'typecheck_rejected': True, 'diagnostic': diagnostic}


def source_contract(source):
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'pip_visual_continuity'
    assert set(plan['inputs']) == {UPLOAD, MANAGER, COPIER}
    assert not plan['copies'] and not plan['deletions']
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    current = {name: (source / name).read_text() for name in plan['outputs']}
    previous = {name: (ROOT / 'ios' / plan['previous'][name]).read_text() for name in plan['inputs']}
    # Correlation/random IDs, server acceptance, reference retry and batching
    # retain their existing production bodies, rather than being modeled anew.
    for marker in ['    private func applyAcknowledgedMessage(', '    private func applySentMessage(',
                   '    private func applySentGroupMessages(',
                   '    private func dataForPendingMessageGroup(',
                   '    private func beginSendingGroupIfPossible(',
                   '    private func nagramiXRefreshCopiedMediaReferencesIfNeeded(']:
        assert block(current[MANAGER], marker) == block(previous[MANAGER], marker), marker
    for marker in ['private func nagramiXCopyPollAsNew(', 'public final class NagramiXRecipientCopyBatch',
                   'public func nagramiXPrepareRecipientCopies(', 'public func nagramiXRetryCopiedMessages(']:
        assert block(current[COPIER], marker) == block(previous[COPIER], marker), marker
    for marker in ['func nagramiXCopyRefreshSignal<Value>(', 'func nagramiXCopyRefreshedMedia(',
                   'private func uploadedVideoCover(',
                   '        let assemble: ([MediaId: Api.InputMedia]) -> PendingMessageUploadedContentResult =']:
        assert block(current[UPLOAD], marker) == block(previous[UPLOAD], marker), marker
    fast = 'if unique.isEmpty || (!forceReupload && attachments.allSatisfy({ pollCloudMediaToInputMedia($0) != nil })) { return .single(assemble([:])) }'
    assert fast in current[UPLOAD] and fast in previous[UPLOAD]
    assert 'mediaReference = .message(message: MessageReference(message), media: copy)' in current[COPIER]
    assert 'nagramiXCopyNetworkIsOnline(strongSelf.network)' in current[MANAGER]
    assert current[MANAGER].count('automaticFloodWait: !nagramiXIsLocalCopyMessage(message)') == 2
    assert current[MANAGER].count('automaticFloodWait: !messages.allSatisfy({ nagramiXIsLocalCopyMessage($0.0) })') == 1
    assert current[MANAGER].count('idleTimeout: 120.0') == 2
    assert 'idleTimeout: 60.0' in current[MANAGER]
    for forbidden in ['.forwardMessages(', 'hideNames:']:
        assert current[COPIER].count(forbidden) == previous[COPIER].count(forbidden), forbidden
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = source_contract(args.source)
    before = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='local-copy-delivery-') as temporary:
        root = Path(temporary)
        rejected = guard_checks(args.source, STAGE, plan, root / 'guards')
        fixtures = {
            'signal': delivery.fixture(args.source),
            'request-policy': delivery.policy_fixture(args.source),
            'queued-manager': manager_runtime.fixture(args.source),
            'admission': manager_runtime.admission_fixture(args.source),
            'failure-reason': manager_runtime.failure_reason_fixture(args.source),
            'video-preview': media_runtime.fixture(args.source),
            'atomic-group': group_runtime.fixture(args.source),
            **payload_runtime.fixtures(args.source),
        }
        runs = []
        for name, text in fixtures.items():
            runs += execute(args.swiftc, root, name, text)
        negative_sets = [
            (delivery.semantic_negatives(fixtures['signal']), 91),
            (delivery.policy_negatives(fixtures['request-policy']), 91),
            (manager_runtime.semantic_negatives(fixtures['queued-manager']), 93),
            (media_runtime.semantic_negatives(fixtures['video-preview']), 91),
            (group_runtime.semantic_negatives(fixtures['atomic-group']), 91),
        ]
        for variants, failure_code in negative_sets:
            for name, text, diagnostic in variants:
                runs += execute(args.swiftc, root, name, text, diagnostic, failure_code)
        # Payload module exports its own production snippet and sensitive cases.
        for name, text in payload_runtime.fixtures(args.source).items():
            for variant, mutated, diagnostic in payload_runtime.semantic_negatives(text):
                runs += execute(args.swiftc, root, name + '-' + variant, mutated, diagnostic, 93)
        name, code, diagnostic = manager_runtime.admission_capture_negative(fixtures['admission'])
        capture_checks = [capture_negative(args.swiftc, root, name, code, diagnostic)]
        for name in plan['outputs']:
            run([args.swiftc, '-frontend', '-parse', args.source / name])
    assert manifest(args.source) == before
    run(['python3', args.source / 'build-system/Make/PostboxImportCheck.py', args.source])
    sk = args.source / 'submodules/SSignalKit/SwiftSignalKit/Source'
    report = {
        'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
        'fail_closed': len(rejected), 'executions': runs,
        'capture_typecheck_negatives': capture_checks,
        'swift_parse': len(plan['outputs']), 'source_files': len(before),
        'source_unchanged_by_checks': True, 'native_postbox_imports': 'passed',
        'native_signalkit': {name: hashlib.sha256((sk / name).read_bytes()).hexdigest()
                            for name in ['Atomic.swift', 'Disposable.swift', 'Subscriber.swift',
                                         'Signal.swift', 'Signal_Mapping.swift', 'Signal_Meta.swift']},
        'boundary': 'Actual production copy/watchdog helpers, RPC policy, queue admission and payload '
                    'and atomic album-failure snippets execute with native SignalKit primitives/operators. Time/Queue/Timer, '
                    'peer/resource values, Postbox side effects, network RPC and UIKit are explicit '
                    'adapters. Filesystem preview checks use real temporary regular files. No Telegram '
                    'RPC, full native app typecheck, Apple SDK or physical-device delivery is proven.',
        'apple_sdk': 'not_run', 'ipa': 'not_built', 'physical_iphone': 'pending',
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ('executions', 'outputs', 'native_signalkit')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
