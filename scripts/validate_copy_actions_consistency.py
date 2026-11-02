#!/usr/bin/env python3
"""Проверить значки и отправку локальных копий."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'copy_actions_consistency_patches.json').read_text())
def sha(data): return hashlib.sha256(data).hexdigest()
def is_applied(source):
    expected = {**PLAN['outputs'], **{name: item['sha256'] for name, item in PLAN['copies'].items()}}
    return all((source / name).is_file() and sha((source / name).read_bytes()) == digest for name, digest in expected.items())
def verify(source):
    assert is_applied(source)
    for name, digest in PLAN['guards'].items(): assert sha((source / name).read_bytes()) == digest
    for name, digest in PLAN['templates'].items(): assert sha((OVERLAY / name).read_bytes()) == digest
def reverse(source, prior):
    names = set(PLAN['inputs'])
    for manifest in OVERLAY.glob('*_patches.json'):
        item = json.loads(manifest.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'): names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift'])
    for name in names - set(PLAN['copies']):
        old = PLAN['previous'].get(name); path = OVERLAY / old if old else source / name
        if path.is_file():
            target = prior / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(path.read_bytes())
def delegate_if_applied(args, script):
    from validate_pip_streaming import delegate_if_applied as delegate_next
    if delegate_next(args, script): return True
    source = args.source
    if not is_applied(source): return False
    verify(source)
    with tempfile.TemporaryDirectory(prefix='catalog-prior-') as folder:
        prior = Path(folder); reverse(source, prior); arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None: arguments += ['--upstream', str(source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--swiftc"); parser.add_argument("--source", type=Path); args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("copy_actions_consistency", OVERLAY / "copy_actions_consistency.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder)
        for name, template in PLAN["previous"].items():
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / template).read_bytes())
        for i, name in enumerate(PLAN["guards"]):
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / f"copy_actions_consistency/Guard{i}.inc").read_bytes())
        # Drift in one input must fail before any other file is written.
        bad = source / next(iter(PLAN["inputs"]))
        original = bad.read_bytes()
        bad.write_bytes(original + b"\n// drift\n")
        untouched = {name: (source / name).read_bytes() for name in PLAN["inputs"]}
        try: module.apply_copy_actions_consistency(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError("expected drift guard failure")
        assert all((source / name).read_bytes() == data for name, data in untouched.items())
        bad.write_bytes(original)
        module.apply_copy_actions_consistency(source, OVERLAY); verify(source)
        menu=(OVERLAY / "copy_actions_consistency/After0.inc").read_text()
        assert menu.count('iconAnimation: ContextMenuActionItem.IconAnimation(name: "message_preview_person_off")') >= 2
        assert menu.count('UIImage(bundleImageName: "Chat/Context Menu/Groups")') >= 2
        archived=menu[menu.index("        if archivedAttribute != nil {"):]
        assert 'text: chatPresentationInterfaceState.strings.nagramiXForwardWithoutAuthor, icon: { _ in' in archived
        assert 'forwardMessagesWithoutSource(selectAll ? messages : [message])' in archived
        assert 'copyMessagesWithoutSource(selectAll ? messages : [message])' in archived
        assert 'copyMessagesToForward' in menu and 'replayCopyForInteraction' in menu
        if args.source:
            live_menu = (args.source / "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift").read_text()
            assert live_menu == menu or live_menu == (OVERLAY / "translation_manual_always/After0.inc").read_text() or live_menu == (OVERLAY / "transcription_context_telegram/After1.inc").read_text() or sha(live_menu.encode()) == json.loads((OVERLAY / "context_translation_toggles_patches.json").read_text())["outputs"]["submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"] or sha(live_menu.encode()) == json.loads((OVERLAY / "author_selection_fix_patches.json").read_text())["outputs"]["submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"] or sha(live_menu.encode()) == json.loads((OVERLAY / "author_selection_icon_patches.json").read_text())["outputs"]["submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"] or sha(live_menu.encode()) == json.loads((OVERLAY / "upright_author_icon_patches.json").read_text())["outputs"]["submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"] or sha(live_menu.encode()) == json.loads((OVERLAY / "protected_copy_draft_patches.json").read_text())["outputs"]["submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"] or sha(live_menu.encode()) == json.loads((OVERLAY / "author_check_badge_icon_patches.json").read_text())["outputs"]["submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"]
            callbacks = (args.source / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift").read_text()
            for snippet in ("copyMessagesWithoutSource: { [weak self] messages in", "forwardMessagesWithoutSource: { [weak self] messages in", "transferMode: .copyAsNew", "transferMode: .copyToSingleRecipient"):
                assert snippet in callbacks
            forward = (args.source / "submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift").read_text()
            assert "!strongSelf.nagramiXReadHistoryDisabled" in forward
            assert "case .copyAsNew, .copyToSingleRecipient:" in forward
            assert "nagramiXCopyMessagesAsNew(messages" in forward
        if args.swiftc:
            for name in PLAN["outputs"]: subprocess.run([args.swiftc, "-frontend", "-parse", str(source / name)], check=True)
        try: module.apply_copy_actions_consistency(source, OVERLAY)
        except SystemExit: pass
        else: raise AssertionError("expected input guard failure")
    print("copy actions consistency: OK")
if __name__ == "__main__": main()
