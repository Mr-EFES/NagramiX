#!/usr/bin/env python3
"""Проверить private ASR временного голоса/кружков и запрет server-ID RPC."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from private_temporary_transcription_runtime import R, T, A, E, P, fixture
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'private_temporary_transcription'


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
            assert result.returncode == 96 and diagnostic in output, (name, result.returncode, output)
        results.append({'name': name, 'mode': mode, 'exit_code': result.returncode, 'output': output})
        binary.unlink()
    return results


def negatives(text):
    guard = block(text, 'private func nagramiXBlocksTelegramTranscription(')
    variants = [
        ('native-rpc-guard', guard, 'private func nagramiXBlocksTelegramTranscription(_ message: Message?) -> Bool { return false }', 'core blocks protected voice and round RPC', 1),
        ('last-network-gate', '!nagramiXBlocksTelegramTranscription(target.message)', 'true', 'last network boundary rechecks changed retention', 2),
        ('telegram-private-route', 'configuration.provider = .apple', 'configuration.provider = .telegram', 'temporary voice and round always use safe route', 1),
        ('wrong-cache-provider', 'stamp.tag == self.configuration(for: message).cacheTag', 'stamp.tag == NagramiXTranscriptionSettings.current.cacheTag', 'private result cache uses effective provider', 1),
        ('disabled-native-button', 'configuration.enabled = true', 'configuration.enabled = NagramiXTranscriptionSettings.current.enabled', 'context menu retains private native-button fallback', 1),
        ('asr-consumes', '            return attributes', '            attributes.append(ConsumableContentMessageAttribute(consumed: true))\n            return attributes', 'ASR never marks media consumed', 1),
        ('automatic-override', 'configuration.automatic = configuration.enabled && configuration.automatic', 'configuration.automatic = true', 'disabled automatic request terminates', 1),
        ('expired-id', '|| (nagramiXTemporaryMessagesEnabled() && nagramiXIsTemporaryMessage(message))', '|| false', 'expired temporary ID cannot reach native RPC', 1),
    ]
    for name, before, after, diagnostic, count in variants:
        assert text.count(before) == count, (name, text.count(before))
        yield name, text.replace(before, after), diagnostic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'pip_backdrop_stability'
    assert set(plan['outputs']) == {R, T}
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    before_runtime = (ROOT / 'ios' / plan['previous'][R]).read_text()
    runtime = (args.source / R).read_text()
    for marker in ('    private static func load(', '    private static func identity(', 'public final class NagramiXTranscriptionAutomatic'):
        assert block(runtime, marker) == block(before_runtime, marker), marker
    before_native = (ROOT / 'ios' / plan['previous'][T]).read_text()
    native = (args.source / T).read_text()
    for marker in ('func _internal_transcribeAudio(', 'func _internal_rateAudioTranscription('):
        previous = block(before_native, marker)
        current = block(native, marker)
        network = '        return network.request('
        assert previous[previous.index(network):] == current[current.index(network):], marker
    assert 'markTemporaryExpired' not in runtime and 'markMessageContentAsConsumed' not in runtime
    initial = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='private-temporary-asr-') as temporary:
        root = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, root / 'guards')
        text = fixture(args.source)
        executions = execute(args.swiftc, root, 'private-temporary-asr', text)
        for name, mutated, diagnostic in negatives(text):
            executions += execute(args.swiftc, root, name, mutated, diagnostic)
        for name in plan['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    assert manifest(args.source) == initial
    result = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']), 'loader_refusals': len(refusals),
              'executions': executions, 'swift_parse': 2,
              'boundary': 'Full production Runtime, Settings, Coordinator, native transcription/rating functions, eligibility, engine ASR attribute transaction and archive update execute with explicit network, speech, resource I/O and Postbox storage adapters. Tests assert zero protected Telegram RPCs, unchanged live TTL/consumed/media/identity and unchanged archive deletion timestamps. Real provider/server behavior and iPhone UI are not exercised.',
              'apple_sdk': 'not_run', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
