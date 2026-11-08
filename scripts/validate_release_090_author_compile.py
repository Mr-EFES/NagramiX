#!/usr/bin/env python3
"""Reproduce SDK186 name-visibility errors and check the extracted author handler."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

import validate_author_selection_no_restore as author
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'release_090_author_compile'
UI = 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift'
TAB = 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift'
ENGINE = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Message.swift'
PEER = 'submodules/TelegramCore/Sources/TelegramEngine/Peers/Peer.swift'
MARKER = '    private func nagramiXSelectMessagesByAuthor('


def expected_output(before):
    begin = '        }, selectMessagesByAuthor: { [weak self] authorId in\n'
    a = before.index(begin) + len(begin)
    b = before.index('        }, updateForwardOptionsState:', a)
    body = before[a:b]
    assert body.count('guard let self, self.isNodeLoaded') == 1
    body = body.replace('guard let self, self.isNodeLoaded', 'guard self.isNodeLoaded', 1)
    assert len(re.findall(r'\bMessageId\b', body)) == 3
    body = re.sub(r'\bMessageId\b', 'EngineMessage.Id', body)
    body = '\n'.join(line[4:] if line.startswith('    ') else line for line in body.rstrip('\n').splitlines()) + '\n'
    method = MARKER + '_ authorId: EnginePeer.Id) {\n' + body + '    }\n\n'
    after = before[:a] + '            self?.nagramiXSelectMessagesByAuthor(authorId)\n' + before[b:]
    assert 'import NagramiXCore\n' not in after
    after = after.replace('import TelegramCore\n', 'import TelegramCore\nimport NagramiXCore\n', 1)
    return after.replace('extension ChatControllerImpl {\n', 'extension ChatControllerImpl {\n' + method, 1)


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, **kwargs)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def api_boundary(source, swiftc, folder):
    folder.mkdir()
    common = [swiftc, '-swift-version', '5', '-warnings-as-errors', '-module-cache-path', folder / 'cache']
    media = sorted((source / 'submodules/NagramiXMediaSettings/Sources').glob('*.swift'))
    assert len(media) == 12
    run(common + ['-emit-module', '-module-name', 'NagramiXMediaSettings', *media,
                  '-emit-module-path', folder / 'NagramiXMediaSettings.swiftmodule'])
    run(common + ['-emit-module', '-module-name', 'NagramiXCore', '-I', folder, source / TAB,
                  '-emit-module-path', folder / 'NagramiXCore.swiftmodule'])
    # Only the backing Postbox type is an adapter. The public alias below is read
    # verbatim from native TelegramCore and its dependency stays a separate module.
    postbox = folder / 'Postbox.swift'
    postbox.write_text('public struct MessageId: Hashable { public init() {} }\npublic struct PeerId: Hashable { public init() {} }\n')
    run(common + ['-emit-module', '-module-name', 'Postbox', postbox,
                  '-emit-module-path', folder / 'Postbox.swiftmodule'])
    native = (source / ENGINE).read_text()
    alias = next(line for line in native.splitlines() if 'public typealias Id = MessageId' in line)
    post = checked_plan('upstream_13_2_release_post')
    assert digest(source / PEER) == {**post['guards'], **post['outputs']}[PEER]
    peer_alias = next(line for line in (source / PEER).read_text().splitlines() if 'public typealias Id = PeerId' in line)
    engine = folder / 'TelegramCore.swift'
    engine.write_text('import Postbox\npublic final class EngineMessage {\n' + alias + '\n}\npublic enum EnginePeer {\n' + peer_alias + '\n}\n')
    run(common + ['-emit-module', '-module-name', 'TelegramCore', '-I', folder, engine,
                  '-emit-module-path', folder / 'TelegramCore.swiftmodule'])
    text = (source / UI).read_text()
    assert 'import NagramiXCore\n' in text and 'import TelegramCore\n' in text
    method = block(text, MARKER)
    declaration = next(line.strip() for line in method.splitlines() if 'let archivedIds:' in line)
    probe = ('import TelegramCore\nimport NagramiXCore\n'
             'func probe(_ authorId: EnginePeer.Id) -> [EngineMessage.Id] {\n    ' + declaration + '\n'
             '    archivedIds = []\n'
             '    if NagramiXTabSettings.current.showDeletedMessages { return archivedIds }\n'
             '    return []\n}\n')
    results = []
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        for label, contents, diagnostic in [
            ('production-imports', probe, None),
            ('missing-settings-import', probe.replace('import NagramiXCore\n', ''), "cannot find 'NagramiXTabSettings'"),
            ('private-postbox-name', probe.replace('EngineMessage.Id', 'MessageId'), "cannot find type 'MessageId'"),
        ]:
            path = folder / (mode + '-' + label + '.swift'); path.write_text(contents)
            result = subprocess.run(list(map(str, common + flags + ['-typecheck', '-I', folder, path])), capture_output=True, text=True)
            if diagnostic is None:
                assert result.returncode == 0, result.stderr
            else:
                assert result.returncode != 0 and diagnostic in result.stderr, result.stderr
            results.append({'mode': mode, 'case': label, 'expected_diagnostic': diagnostic})
    return {'actual_media_files': len(media), 'actual_settings_file': TAB, 'native_alias': alias.strip(),
            'native_peer_alias': peer_alias.strip(), 'native_peer_protected_by_post_plan': True, 'cases': results,
            'boundary': 'Actual settings files compile as independent modules. Postbox backing storage is an explicit adapter; no UIKit/Apple SDK typecheck is claimed.'}


def behavior(source, swiftc, folder):
    folder.mkdir()
    text = (source / UI).read_text()
    method = block(text, MARKER)
    closure_start = text.index('        }, selectMessagesByAuthor: { [weak self] authorId in\n')
    closure_end = text.index('        }, updateForwardOptionsState:', closure_start)
    closure = text[closure_start:closure_end].split('\n', 1)[1]
    assert closure.strip() == 'self?.nagramiXSelectMessagesByAuthor(authorId)'
    wrapper = ('    func selectAuthor(_ authorId: PeerId) {\n'
               '        let action: (PeerId) -> Void = { [weak self] authorId in\n' + closure +
               '        }\n        action(authorId)\n    }\n')
    aliases = '\nenum EnginePeer { typealias Id = PeerId }\nenum EngineMessage { typealias Id = MessageId }\n'
    header = author.HEADER.replace('// ACTUAL_UI_METHOD', method + '\n' + wrapper)
    core = '\n'.join(line for line in (source / author.CORE).read_text().splitlines() if not line.startswith('import '))
    fixture = header + aliases + '\n' + core + '\n' + author.TESTS
    checks = []
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        for label, contents in [
            ('production', fixture),
            ('stale-archive', fixture.replace('currentArchivedIds.contains($0)', 'currentArchivedIds.contains($0) || archivedIds.contains($0)')),
            ('late-local-deletion', fixture.replace('return localIds.filter { transaction.getMessage($0)?.author?.id == authorId }', 'return localIds')),
        ]:
            path = folder / (mode + '-' + label + '.swift'); path.write_text(contents); binary = path.with_suffix('')
            run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-module-cache-path', folder / 'cache', *flags, path, '-o', binary])
            result = subprocess.run([str(binary)], capture_output=True, text=True, preexec_fn=author.no_core)
            if label == 'production':
                assert result.returncode == 0 and 'PASS author selection production checks: 34' in result.stdout, result.stdout + result.stderr
            else:
                assert result.returncode == 91 and result.stdout.startswith('FAIL '), result.stdout + result.stderr
            checks.append({'mode': mode, 'case': label, 'production_assertions': 34 if label == 'production' else 0})
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert set(plan['inputs']) == {UI} and len(plan['guards']) == 16
    assert not plan['copies'] and not plan['deletions'] and not plan['native_inputs']
    before = (ROOT / 'ios' / plan['previous'][UI]).read_text()
    after = (args.source / UI).read_text()
    assert after == expected_output(before), 'Unexpected functional changes beyond author extraction/import/type aliases'
    for name, value in {**plan['outputs'], **plan['guards']}.items(): assert digest(args.source / name) == value, name
    prefix = LATE_SOURCE_STAGES.index(STAGE)
    assert verified_prefix(args.source) == prefix + 1
    full_before = manifest(args.source)
    if args.baseline:
        assert verified_prefix(args.baseline) == prefix
        baseline = manifest(args.baseline)
        assert baseline.keys() == full_before.keys() and len(baseline) > 37000
        assert {name for name in baseline if baseline[name] != full_before[name]} == {UI}
    with tempfile.TemporaryDirectory(prefix='nagramix-author-sdk186-') as tmp:
        folder = Path(tmp)
        rejected = guard_checks(args.source, STAGE, plan, folder / 'guards')
        api = api_boundary(args.source, args.swiftc, folder / 'api')
        semantics = behavior(args.source, args.swiftc, folder / 'semantics')
        run([args.swiftc, '-frontend', '-parse', args.source / UI])
    assert manifest(args.source) == full_before
    run(['python3', args.source / 'build-system/Make/PostboxImportCheck.py', args.source])
    report = {'stage': STAGE, 'source_output_sha256': plan['outputs'], 'guards': len(plan['guards']),
              'fail_closed': len(rejected), 'api_boundary': api, 'author_behavior': semantics,
              'source_files_unchanged_during_checks': len(full_before), 'swift_parse': 1,
              'native_postbox_import_check': 'passed', 'whole_module_sdk': 'pending', 'physical_iphone': 'pending',
              'sdk186_typecheck_timeout': 'Handler extracted out of the giant initializer; native SDK retry remains required.'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
