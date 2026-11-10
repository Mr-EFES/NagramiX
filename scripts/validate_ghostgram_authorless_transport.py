#!/usr/bin/env python3
"""Проверить общий маршрут без автора, резервные копии и сохранность выбора."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from ghostgram_authorless_transport_runtime import COPY, UI, DELIVERY, fixture, negatives
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'ghostgram_authorless_transport'


def execute(swiftc, root, name, text, diagnostic=None):
    source = root / (name + '.swift')
    source.write_text(text)
    results = []
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        binary = root / (name + '-' + mode)
        compiled = subprocess.run([str(swiftc), '-swift-version', '5', '-parse-as-library', '-warnings-as-errors',
                                   '-module-cache-path', str(root / 'cache'), *flags, str(source), '-o', str(binary)],
                                  capture_output=True, text=True)
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
        output = (result.stdout + result.stderr).strip()
        if diagnostic is None:
            assert result.returncode == 0, output
        else:
            assert result.returncode == 97 and diagnostic in output, (name, result.returncode, output)
        results.append({'name': name, 'mode': mode, 'exit_code': result.returncode, 'output': output})
        binary.unlink()
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'private_temporary_transcription'
    assert set(plan['outputs']) == {COPY, UI, DELIVERY}
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    current = (args.source / COPY).read_text()
    previous = (ROOT / 'ios' / plan['previous'][COPY]).read_text()
    for marker in ('public func nagramiXCanCopyMessagesAsNew(', 'private func nagramiXCopyPollAsNew(',
                   'public func nagramiXCopyMessagesAsNew(', 'public func nagramiXCopyMessagesAsNewBySource(',
                   'private func nagramiXBuildCopiedMessages(', 'public final class NagramiXRecipientCopyBatch'):
        assert block(current, marker) == block(previous, marker), marker
    ui = (args.source / UI).read_text()
    old_ui = (ROOT / 'ios' / plan['previous'][UI]).read_text()
    for marker in ('enum NagramiXMessageTransferMode:', 'func nagramiXNativeForwardSource(',
                   '                        let transformForSend:',
                   '                        switch mode {\n                        case .generic:\n                            commit(result)'):
        assert block(ui, marker) == block(old_ui, marker), marker
    assert 'nagramiXMessagesWithoutAuthor(messages, hideCaptions:' in ui
    assert 'nagramiXMessagesRequiringCopy(messages).contains' in ui
    assert 'messages: nagramiXMessagesRequiringCopy(messages)' in (args.source / DELIVERY).read_text()
    assert 'guard nagramiXCanRetryWithoutAuthor(message) else { return .skip }' in current
    initial = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='ghostgram-authorless-') as temporary:
        root = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, root / 'guards')
        text = fixture(args.source)
        executions = execute(args.swiftc, root, 'authorless', text)
        for name, mutated, diagnostic in negatives(text):
            executions += execute(args.swiftc, root, name, mutated, diagnostic)
        for name in plan['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    assert manifest(args.source) == initial
    result = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']), 'loader_refusals': len(refusals),
              'executions': executions, 'swift_parse': 3,
              'reference': {'repository': 'ichmagmaus111/ghostgram', 'commit': '2a6b08272b7da893f88986846022bafd0727df89',
                            'files': ['Ghostgram/Features/Shared/Sources/Messages/GGForwardSend.swift', 'Ghostgram/Features/Shared/Sources/Messages/GGForwardCopy.swift']},
              'boundary': 'Production route eligibility, mixed builder, recipient batch, strict copy builder and file stager; native EnqueueMessage transforms and drop_author/drop_media_captions decisions. Foundation file I/O is real; media/Postbox/network/recipient UI are explicit adapters or pinned unchanged sources. No live Telegram delivery or iPhone UI claim.',
              'apple_sdk': 'not_run', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
