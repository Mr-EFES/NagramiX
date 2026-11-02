#!/usr/bin/env python3
"""Проверка приватности и ограниченных прочтений без сборки iOS-приложения."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/NagramiXMediaSettings/Sources/'
CORE = 'submodules/TelegramCore/Sources/'


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def validate(before, after, swiftc):
    plan = json.loads((ROOT / 'ios/privacy_actions_patches.json').read_text())
    a, b = manifest(before), manifest(after)
    changed = {n for n in a.keys() & b.keys() if a[n] != b[n]}
    expected = set(plan['hashes']) | {PREFIX + 'NagramiXReadModeSettings.swift', PREFIX + 'NagramiXPrivacySettings.swift', CORE + 'NagramiXGhostReadActions.swift', CORE + 'NagramiXReadModeActions.swift', *[f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings' for lang in ['ru', 'en']]}
    assert a.keys() == b.keys() and changed == expected, changed ^ expected
    texts = {n: (before / n).read_text() for n in plan['hashes']}
    assert all(hashlib.sha256((before / n).read_bytes()).hexdigest() == sha for n, sha in plan['hashes'].items())
    for name, old, new, count in plan['patches']:
        assert texts[name].count(old) == count
        texts[name] = texts[name].replace(old, new, count)
    assert all(texts[n].encode() == (after / n).read_bytes() for n in texts)
    for name in ['NagramiXPrivacySettings.swift', 'NagramiXReadModeSettings.swift', 'NagramiXGhostSettings.swift', 'NagramiXStorySettings.swift']:
        assert (after / (PREFIX + name)).read_bytes() == (ROOT / 'ios/Sources/NagramiXMediaSettings/Sources' / name).read_bytes()
    for name in ['NagramiXGhostReadActions.swift', 'NagramiXReadModeActions.swift']:
        assert (after / (CORE + name)).read_bytes() == (ROOT / 'ios/Sources/TelegramCore' / name).read_bytes()
    spec = importlib.util.spec_from_file_location('privacy_actions', ROOT / 'ios/privacy_actions.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected = []
    with tempfile.TemporaryDirectory() as tmp:
        native = Path(tmp)
        def seed():
            for n in plan['hashes']:
                p = native / n; p.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(before / n, p)
        def reject(label):
            saved = manifest(native)
            try: module.apply_privacy_actions(native, ROOT / 'ios')
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError(label)
            assert manifest(native) == saved, 'partial write ' + label
            rejected.append(label)
        seed(); module.apply_privacy_actions(native, ROOT / 'ios')
        assert all((native / n).read_bytes() == (after / n).read_bytes() for n in plan['hashes'])
        reject('reapply')
        for n in plan['hashes']:
            seed(); (native / n).write_bytes((native / n).read_bytes() + b'\n// drift'); reject('drift ' + n)
            seed(); (native / n).unlink(); reject('missing ' + n)
    execution = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        env = dict(os.environ, XDG_CONFIG_HOME=str(folder / 'preferences'))
        # Compile the real ledger, action and acknowledgement implementation,
        # with contract doubles only at Postbox/network interfaces.
        for name in ['NagramiXGhostReadActions.swift', 'NagramiXReadModeActions.swift']:
            text = (after / (CORE + name)).read_text()
            (folder / name).write_text('import Foundation\n' + '\n'.join(line for line in text.splitlines() if not line.startswith('import ')) + '\n')
        activity_source = (after / (CORE + 'State/ManagedLocalInputActivities.swift')).read_text()
        native_filter = activity_source.split('            let activities = settings.hidesTyping ?', 1)[1].split('            let (start, dispose)', 1)[0]
        native_guard = activity_source.split('private func requestActivity(', 1)[1].split('        if let peer = transaction.getPeer(peerId)', 1)[0].split('in\n', 1)[1]
        tracker = (after / (CORE + 'State/AccountViewTracker.swift')).read_text()
        native_increment = tracker.split('getMessagesViews(peer: inputPeer, id: messageIds.map { $0.id }, increment: ', 1)[1].split('))', 1)[0]
        (folder / 'ProductionActivityPolicy.swift').write_text(
            'import Foundation\n'
            + 'func productionFilteredActivities(activities: [Int: [(Int, PeerInputActivityRecord)]], settings: NagramiXPrivacySettings) -> [Int: [(Int, PeerInputActivityRecord)]] {\n'
            + 'let activities = settings.hidesTyping ?' + native_filter + '\nreturn activities\n}\n'
            + 'func productionActivityAdmission(activity: PeerInputActivity?) -> TestAdmission {\n' + native_guard + '\nreturn .send\n}\n'
            + 'func productionViewIncrement() -> Api.Bool { ' + native_increment + ' }\n')
        presence = (after / (CORE + 'State/ManagedAccountPresence.swift')).read_text()
        presence = presence.split('private final class AccountPresenceManagerImpl {', 1)[1].split('\nfinal class AccountPresenceManager {', 1)[0]
        (folder / 'ProductionPresenceManager.swift').write_text('import Foundation\nfinal class AccountPresenceManagerImpl {' + presence)
        network = (after / (CORE + 'Network/Network.swift')).read_text()
        classifier = network.split('    private static func nagramiXRPCMayRestoreOnline(_ name: String) -> Bool {', 1)[1].split('    private let isUserOnlineDisposable', 1)[0]
        (folder / 'ProductionOnlineRPCPolicy.swift').write_text('func productionRPCMayRestoreOnline(_ name: String) -> Bool {' + classifier)
        assert network.count('if nagramiXMayRestoreOnline && NagramiXPrivacySettings.current.automaticOffline {') == 2
        assert network.count('nagramiXActivity.putNext(())') == 2
        models = [after / (PREFIX + n) for n in ['NagramiXReadModeSettings.swift', 'NagramiXPrivacySettings.swift', 'NagramiXGhostSettings.swift', 'NagramiXStorySettings.swift']]
        suites = {
            'actual presence manager timers': [folder / 'ProductionPresenceManager.swift', folder / 'ProductionOnlineRPCPolicy.swift', ROOT / 'scripts/tests/NagramiXAutomaticOfflineTests.swift'],
            'privacy/presence policy': [ROOT / 'scripts/tests/NagramiXGhostSettingsTests.swift'],
            'defaults and migration': [ROOT / 'scripts/tests/NagramiXPrivacySettingsTests.swift'],
            'cold process persistence': [ROOT / 'scripts/tests/NagramiXReadModeTests.swift'],
            'native activity and channel views': [folder / 'ProductionActivityPolicy.swift', ROOT / 'scripts/tests/NagramiXPrivacyActivityTests.swift'],
            # Read/action tests now need the final topic/Enqueue integration.
            # validate_thread_read_scope.py runs them with actual final bodies,
            # including the baseline regression and native completion hooks.
        }
        for mode in ['debug', 'optimized']:
            for name, sources in suites.items():
                print(mode + ' ' + name, flush=True)
                binary = folder / 'test'
                cmd = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *map(str, models + sources), '-o', str(binary)]
                if mode == 'optimized': cmd.insert(1, '-O')
                subprocess.run(cmd, check=True, env=env, cwd=folder)
                result = subprocess.check_output([str(binary)], text=True, env=env, cwd=folder, timeout=45).strip()
                execution.append(mode + ' ' + name + ': ' + result)
                # Spawn cold processes here: Foundation.Process needs a wakeup
                # socket unavailable in some Linux execution sandboxes.
                cold = 0
                def run_cold(*args):
                    nonlocal cold
                    subprocess.run([str(binary), *args], check=True, env=env, cwd=folder, timeout=15)
                    cold += 1
                if name == 'defaults and migration':
                    for online in ['false', 'true']:
                        for automatic in ['false', 'true']:
                            suite = 'nagramix.cold.online.' + mode + online + automatic
                            run_cold('--seed-online', suite, online, automatic)
                            run_cold('--cold-online', suite, 'true' if 'true' in [online, automatic] else 'false')
                            for enabled in ['false', 'true', 'false']:
                                run_cold('--set-online', suite, enabled)
                                run_cold('--cold-online', suite, enabled)
                if name == 'cold process persistence':
                    for selected in ['local', 'standard', 'local']:
                        run_cold('--set-cold', 'nagramix.cold.read.' + mode, selected)
                        run_cold('--cold', 'nagramix.cold.read.' + mode, selected)
                if cold:
                    execution.append(mode + ' ' + name + ': PASS ' + str(cold) + ' separate cold processes')
        subprocess.run([str(swiftc), '-frontend', '-parse', *[str(after / n) for n in changed if n.endswith('.swift')]], check=True, cwd=folder)
    ui = (after / 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift').read_text()
    assert all(n not in ui for n in ['readOnServer', 'ghostMode', 'openGhostSettings', 'anonymousStoryViewing', '.server'])
    rows = ui.split('private func nagramiXAllSettingsEntries', 1)[1].split('private func nagramiXSettingsEntries', 1)[0]
    assert rows.index('.messagesHeader') < rows.index('.privacyHeader') < rows.index('.callsHeader')
    assert rows.count('.privacyHeader') == 1 and rows.count('.readLocally(') == 1 and rows.count('.privacyToggle(') == 4
    assert '.automaticOffline' not in ui and rows.count('.privacyToggle(.online,') == 1
    for lang in ['ru', 'en']:
        text = (after / f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        assert '"NagramiX.ReadMode.Server' not in text
        for key in ['NagramiX.ReadMode.Local', 'NagramiX.ReadMode.Local.Search', 'NagramiX.Privacy.Title', *['NagramiX.Privacy.' + option + suffix for option in ['storyReads', 'online', 'typing', 'readOnAction'] for suffix in ['', '.Search']]]:
            assert text.count('"' + key + '" = ') == 1
        assert '"NagramiX.Privacy.automaticOffline' not in text
        title = 'Скрывать статус «Онлайн»' if lang == 'ru' else 'Hide online status'
        assert '"NagramiX.Privacy.online" = "' + title + '";' in text
    # Check actual native hooks in addition to the executable contract tests.
    history = (after / 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift').read_text()
    assert 'self.canReadHistory.get(), nagramiXPrivacySettingsSignal()' in history
    assert 'if !canRead {' in history and 'previousPrivateReading != privacy.hidesMessageReads' in history
    enqueue = (after / (CORE + 'PendingMessages/EnqueueMessage.swift')).read_text().split('public func enqueueMessages(account:', 1)[1].split('public func enqueueWelcomeMessages', 1)[0]
    assert enqueue.index('let nagramiXReadBoundary') < enqueue.index('var resultIds') < enqueue.index('return (resultIds, ephemeralMessageIds, nagramiXReadBoundary)')
    assert 'hadImmediateSend, let nagramiXReadBoundary' in enqueue and 'upTo: nagramiXReadBoundary' in enqueue and 'OutgoingScheduleInfoMessageAttribute' in enqueue
    reactions = (after / (CORE + 'State/MessageReactions.swift')).read_text().split('func _internal_sendStarsReactionsInteractively', 1)[0]
    assert 'if let shouldApply, !shouldApply() { return [] }' in reactions
    assert 'return nagramiXReadBoundaries' in reactions and 'mappedReactions.contains(where: { !previousSelected.contains($0.value) })' in reactions
    tracker = (after / (CORE + 'State/AccountViewTracker.swift')).read_text()
    assert tracker.count('getMessagesViews(') == 1 and 'increment: NagramiXPrivacySettings.current.hidesMessageReads ? .boolFalse : .boolTrue' in tracker
    activities = (after / (CORE + 'State/ManagedLocalInputActivities.swift')).read_text()
    assert 'combineLatest(activities, nagramiXGhostSettingsSignal())' in activities
    assert 'if case .speakingInGroupCall = value.1.activity { return true }\n                return false' in activities
    assert 'if NagramiXGhostSettings.current.hidesTyping, let activity {' in activities
    return {'outputs': len(b), 'changed': sorted(changed), 'unchanged': len(b) - len(changed), 'sha_guards': len(plan['hashes']), 'exact_operations': len(plan['patches']), 'fail_closed': rejected, 'execution': execution, 'read_action_suite': 'validate_thread_read_scope.py: final topic integration stage', 'apple_sdk': 'not run: no build authorization for this change', 'physical_iphone': 'pending'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']: p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    result = validate(args.before, args.after, args.swiftc)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
