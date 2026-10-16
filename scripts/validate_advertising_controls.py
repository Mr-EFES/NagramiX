#!/usr/bin/env python3
"""Проверить область рекламной правки и отказ при drift без нативной сборки."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ADS = "submodules/TelegramCore/Sources/TelegramEngine/Messages/AdMessages.swift"
PEERS = "submodules/TelegramCore/Sources/TelegramEngine/Peers/AdPeers.swift"
SEARCH = "submodules/ChatListUI/Sources/ChatListSearchListPaneNode.swift"
HISTORY = "submodules/TelegramUI/Sources/ChatHistoryListNode.swift"
LIST = "submodules/ChatListUI/Sources/Node/ChatListNode.swift"
HELPER = "submodules/NagramiXMediaSettings/Sources/NagramiXAdvertisingSettings.swift"
MODEL = "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift"
UI = "submodules/SettingsUI/Sources/NagramiXSettingsController.swift"
PROVIDER = "submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift"
LOCALES = {f"submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings" for lang in ["ru", "en"]}


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def section(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


def validate(before: Path, after: Path) -> dict:
    previous, current = hashes(before), hashes(after)
    assert current.keys() - previous.keys() == {HELPER}
    assert not previous.keys() - current.keys()
    expected = {ADS, PEERS, SEARCH, HISTORY, LIST, MODEL, UI, PROVIDER} | LOCALES
    changed = {name for name in previous if previous[name] != current[name]}
    assert changed == expected, changed
    read = lambda name: (after / name).read_text()
    ads, peers, search, history, chat_list = map(read, [ADS, PEERS, SEARCH, HISTORY, LIST])
    helper, model, ui = map(read, [HELPER, MODEL, UI])
    assert '"nagramix.interface.hideProxySponsorChannel"' in helper
    assert '"nagramix.interface.showProxySponsorChannel"' in helper
    assert "return !hidden" in helper and "as? Bool ?? false" in helper
    assert "let hideProxySponsorChannel = !NagramiXAdvertisingSettings.showAdvertising" in model
    assert "get { return !self.hideProxySponsorChannel }" in model
    assert "set { self.hideProxySponsorChannel = !newValue }" in model
    assert "defaults.set(value.hideProxySponsorChannel, forKey: Key.hideProxySponsorChannel)" in model
    assert "if previousShowAdvertising != value.showAdvertising" in model
    assert '.showAdvertising(settings.showAdvertising)' in ui
    assert 'updateShowAdvertising: { value in update { $0.showAdvertising = value } }' in ui
    assert 'case .showAdvertising: return 5' in ui
    assert 'nagramiXShowAdvertising' in ui and 'nagramiXHideProxySponsorChannel' not in ui
    assert '"NagramiX.Interface.HideProxySponsorChannel" = "Показать рекламу";' in read(next(x for x in LOCALES if '/ru.' in x))
    assert '"NagramiX.Interface.HideProxySponsorChannel" = "Show ads";' in read(next(x for x in LOCALES if '/en.' in x))
    assert 'if messageId == nil && NagramiXAdvertisingSettings.showAdvertising' in ads
    assert 'guard NagramiXAdvertisingSettings.showAdvertising, let inputPeer else' in ads
    assert 'advertisingGeneration == strongSelf.nagramiXAdvertisingGeneration' in ads
    assert 'self.nagramiXAdvertisingGeneration += 1' in ads
    disabled = section(ads, '    private func nagramiXUpdateAdvertising', '    func activate()')
    for needle in ['self.disposable.set(nil)', 'self.isActivated = false', 'self.state.set(.single(State(interPostInterval: nil, messages: [])))', 'if self.nagramiXActivationRequested']:
        assert needle in disabled
    for start in ['    func markAsSeen(opaqueId: Data) {', 'func _internal_markAdAsSeen(account: Account, opaqueId: Data) {', 'func _internal_markAdAction(account: Account, opaqueId: Data, media: Bool, fullscreen: Bool) {']:
        assert start + '\n' in ads
        assert ads[ads.index(start):].splitlines()[1].strip() == 'guard NagramiXAdvertisingSettings.showAdvertising else { return }'
    assert 'self.nagramiXAdvertisingDisposable.dispose()' in ads
    assert 'NotificationCenter.default.removeObserver(observer)' in ads
    assert 'subscriber.putNext((nil, [], nil, nil))' in ads
    # Enabled requests retain native parsing, APIs, permissions and activation rules.
    original_ads = (before / ADS).read_text()
    assert section(original_ads, 'private class AdMessagesHistoryContextImpl {', '    private let queue: Queue') == section(ads, 'private class AdMessagesHistoryContextImpl {', '    private let queue: Queue')
    activate = section(ads, '    func activate() {', '    func markAsSeen(')
    activate = activate.replace('        self.nagramiXActivationRequested = true\n        guard NagramiXAdvertisingSettings.showAdvertising else { return }\n', '').replace('        let advertisingGeneration = self.nagramiXAdvertisingGeneration\n', '').replace('guard NagramiXAdvertisingSettings.showAdvertising, let inputPeer else', 'guard let inputPeer else').replace('guard let strongSelf = self, NagramiXAdvertisingSettings.showAdvertising, advertisingGeneration == strongSelf.nagramiXAdvertisingGeneration else', 'guard let strongSelf = self else')
    assert activate == section(original_ads, '    func activate() {', '    func markAsSeen(')
    assert 'guard enabled, NagramiXAdvertisingSettings.showAdvertising else { return .single([]) }' in peers
    nested = peers[peers.index('        return account.network.request'):peers.rindex('    }\n}\n')]
    lines = nested.splitlines(keepends=True)
    restored_body = ''.join(line[4:] if line.startswith('    ') else line for line in lines)
    restored_body = restored_body.replace('guard NagramiXAdvertisingSettings.showAdvertising, let result else', 'guard let result else')
    original_peers = (before / PEERS).read_text()
    assert restored_body == original_peers[original_peers.index('    return account.network.request'):-2]
    assert 'combineLatest(adsHiddenPromise.get(), nagramiXAdvertisingEnabledSignal())' in search
    assert 'hidden || !enabled' in search
    assert 'self.allAdMessages = (nil, [], self.allAdMessages.version + 1)' in history
    for needle in ['self.pendingDynamicAdMessages = []', 'self.remainingDynamicAdMessageInterval = nil', 'self.remainingDynamicAdMessageDistance = nil', 'self.preloadAdPeerDisposable.set(nil)', 'adMessage: NagramiXAdvertisingSettings.showAdvertising ? allAdMessages.fixed : nil', 'dynamicAdMessages: NagramiXAdvertisingSettings.showAdvertising ? allAdMessages.opportunistic : []']:
        assert needle in history
    assert 'NagramiXTabSettings.advertisingChangedNotification' in chat_list
    assert 'NotificationCenter.default.removeObserver(observer)' in chat_list
    assert 'self?.nagramiXRefreshSettings()' in chat_list
    # The existing native proxy-only filter and all icon assets remain byte-identical.
    assert previous['submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift'] == current['submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift']
    spec = importlib.util.spec_from_file_location('advertising_patch', ROOT / 'ios/apply_features.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    targets = [ADS, PEERS, SEARCH, HISTORY, LIST]
    with tempfile.TemporaryDirectory() as temporary:
        fixture = Path(temporary)
        for name in targets:
            target = fixture / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(before / name, target)
        module.apply_advertising_controls(fixture)
        assert all((fixture / name).read_bytes() == (after / name).read_bytes() for name in targets)
        patched_hashes = hashes(fixture)
        try:
            module.apply_advertising_controls(fixture)
            raise AssertionError('Repeated patch accepted')
        except SystemExit:
            assert hashes(fixture) == patched_hashes
        for drift_target in targets:
            for name in targets:
                shutil.copy2(before / name, fixture / name)
            with (fixture / drift_target).open('a') as f:
                f.write('\n// Изменённый вход для проверки отказа.\n')
            drift_hashes = hashes(fixture)
            try:
                module.apply_advertising_controls(fixture)
                raise AssertionError('Changed input accepted')
            except SystemExit:
                assert hashes(fixture) == drift_hashes
    return {'before_outputs': len(previous), 'after_outputs': len(current), 'changed': sorted(changed), 'added': [HELPER], 'unchanged_outputs': len(previous) - len(changed), 'native_enabled_fetch_and_parser_exact_reversal': 'PASS', 'drift_and_repeat_rejected_without_writes': 6, 'source_contracts': 'PASS', 'native_compile': 'pending', 'physical_device': 'pending'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.before, args.after), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
