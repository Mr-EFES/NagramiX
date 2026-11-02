#!/usr/bin/env python3
"""Проверить изоляцию отложенной отправки от локального архива переписки."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import tempfile

from validate_quick_format import manifest
from validate_outgoing_archive import production

ROOT = Path(__file__).resolve().parents[1]
HISTORY = 'submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift'
ARCHIVE = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
MEDIA = 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift'
SUBJECT = 'submodules/AccountContext/Sources/ChatController.swift'
NAMESPACES = 'submodules/TelegramCore/Sources/SyncCore/SyncCore_Namespaces.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_entries(text):
    marker = '    var sourceEntries = view.entries\n'
    assert text.count(marker) == 1
    start = text.index(marker)
    end = text.index('\n    let hideBlockedMessages', start)
    return text[start:end]


def guard_checks(source, plan, temp):
    spec = importlib.util.spec_from_file_location('scheduled_archive_isolation', ROOT / 'ios/scheduled_archive_isolation.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    before = {name: (source / name).read_bytes() for name in {**plan['guards'], **plan['inputs']}}
    history = before[HISTORY].decode()
    for name, old, new, count in reversed(plan['patches']):
        assert name == HISTORY and history.count(new) == count
        history = history.replace(new, old, count)
    assert sha(history.encode()) == plan['inputs'][HISTORY]
    before[HISTORY] = history.encode()
    def seed(label):
        target = temp / label
        for name, data in before.items():
            path = target / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        return target
    rejected = []
    def reject(target, label, overlay=ROOT / 'ios'):
        old = manifest(target)
        try: mod.apply_scheduled_archive_isolation(target, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят некорректный вход: ' + label)
        assert manifest(target) == old, 'Частичная запись: ' + label
        rejected.append(label)
    target = seed('valid'); mod.apply_scheduled_archive_isolation(target, ROOT / 'ios')
    assert all((target / name).read_bytes() == (source / name).read_bytes() for name in before)
    reject(target, 'reapply')
    for name in before:
        for mode in ['missing', 'drift']:
            target = seed('bad-' + str(len(rejected)))
            path = target / name
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes() + b'\n// drift\n')
            reject(target, mode + ' ' + name)
    mutations = []
    altered = copy.deepcopy(plan); altered['patches'][0][1] += ' broken'; mutations.append(('anchor', altered))
    for section in ['inputs', 'outputs', 'guards']:
        altered = copy.deepcopy(plan); altered[section][next(iter(altered[section]))] = '0' * 64
        mutations.append((section + '-sha', altered))
    altered = copy.deepcopy(plan); altered['inputs']['../outside'] = '0' * 64; altered['outputs']['../outside'] = '0' * 64
    mutations.append(('traversal', altered))
    altered = copy.deepcopy(plan); altered['patches'][0][0] = '/outside.swift'; mutations.append(('operation-path', altered))
    for label, altered in mutations:
        overlay = temp / ('plan-' + label); overlay.mkdir()
        (overlay / 'scheduled_archive_isolation_patches.json').write_text(json.dumps(altered))
        reject(seed('root-' + label), label, overlay)
    return history, rejected


def run_swift(source, before_history, swiftc, temp):
    # The existing archive integration harness executes actual capture/list/
    # snapshot/render/store bodies. The scheduled UI types are small DTOs.
    before = temp / 'before-outgoing'
    canonical = (ROOT / 'ios/Sources/TelegramCore/NagramiXMessageArchive.swift').read_bytes()
    original = json.loads((ROOT / 'ios/outgoing_archive_patches.json').read_text())
    assert sha(canonical) == original['hashes'][ARCHIVE]
    path = before / ARCHIVE; path.parent.mkdir(parents=True); path.write_bytes(canonical)
    prefix = (ROOT / 'scripts/tests/NagramiXOutgoingArchiveBoundary.swift').read_text() + '\n' + production(before, source) + '\n'
    constants = (source / NAMESPACES).read_text()
    for name in ['ScheduledCloud', 'ScheduledLocal']:
        value = re.search(r'public static let ' + name + r': Int32 = (\d+)', constants)
        assert value, name
        prefix += 'extension Namespaces.Message { static let ' + name + ': Int32 = ' + value[1] + ' }\n'
    tests = (ROOT / 'scripts/tests/NagramiXScheduledArchiveIsolationTests.swift').read_text()
    current = temp / 'Current.swift'; current.write_text(prefix + tests.replace('    // PRODUCTION_SOURCE_ENTRIES', source_entries((source / HISTORY).read_text())))
    previous = temp / 'Previous.swift'; previous.write_text(prefix + tests.replace('    // PRODUCTION_SOURCE_ENTRIES', source_entries(before_history)))
    old_tests = temp / 'Outgoing.swift'; old_tests.write_text(prefix + (ROOT / 'scripts/tests/NagramiXOutgoingArchiveTests.swift').read_text())
    runs = []
    for optimized in [False, True]:
        for name, input_path, negative in [('scheduled', current, False), ('old-scheduled', previous, True), ('outgoing', old_tests, False)]:
            label = name + ('-O' if optimized else '-debug')
            binary = temp / label
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized: command.append('-O')
            subprocess.run([*command, str(input_path), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], env=dict(os.environ, XDG_CONFIG_HOME=str(temp / (label + '-prefs'))),
                                    capture_output=True, text=True, timeout=45,
                                    preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if negative:
                assert result.returncode != 0 and 'scheduled list must contain only native scheduled message' in result.stderr, result.stdout + result.stderr
                runs.append(label + ': прежнее подмешивание архива воспроизведено и отвергнуто')
            else:
                assert result.returncode == 0, result.stdout + result.stderr
                runs.append(label + ': ' + result.stdout.strip())
            print(runs[-1], flush=True)
    subprocess.run([str(swiftc), '-frontend', '-parse', str(source / HISTORY)], check=True)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_message_translation import delegate_if_applied
    if delegate_if_applied(args): return
    plan = json.loads((ROOT / 'ios/scheduled_archive_isolation_patches.json').read_text())
    for name, digest in {**plan['guards'], **plan['outputs']}.items():
        assert sha((args.source / name).read_bytes()) == digest, name
    subject = (args.source / SUBJECT).read_text()
    assert 'public enum ChatControllerSubject: Equatable {' in subject and '    case scheduledMessages\n' in subject
    caller = (args.source / 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift').read_text()
    assert 'scheduled: isScheduledMessages' in caller and '                    subject: subject,\n' in caller
    routing = (args.source / 'submodules/TelegramUI/Sources/ChatHistoryViewForLocation.swift').read_text()
    assert 'if scheduled {' in routing and 'scheduledMessagesViewForLocation(' in routing
    calls = [n.func.id for n in ast.walk(ast.parse((ROOT / 'ios/apply_overlay.py').read_text()))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert calls.index('apply_recovery_storage_fixes') < calls.index('apply_scheduled_archive_isolation')
    with tempfile.TemporaryDirectory(prefix='nagramix-scheduled-archive-') as folder:
        temp = Path(folder)
        before, rejected = guard_checks(args.source, plan, temp)
        runs = run_swift(args.source, before, args.swiftc, temp) if args.swiftc else []
    result = dict(files=1, operations=1, guards=len(plan['guards']), fail_closed=rejected, runs=runs,
                  runtime='actual history merge/capture/list/snapshot/render/media-store bodies; UIKit/Postbox/network boundaries; real Foundation IO',
                  SDK='не запускалась', physical_iPhone='ожидается', previous_fixes='сохранены')
    if args.report: args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
