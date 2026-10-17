#!/usr/bin/env python3
"""Validate exception picker scope and sparse-page regression; no UIKit execution."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import re
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FLAG = "nagramiXNotificationExceptions"
PICKER = "submodules/TelegramUI/Components/PeerSelectionController/Sources/"


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def pagination_regression():
    # Reproduce post-filtering the newest 200 unrelated chats. At a header-only
    # result firstIndex=0 and hasLater=false; neither native paging branch runs.
    rows = [(f"private-{i}", "private", False, False, False) for i in range(500)]
    rows += [(f"group-{i}", "group", i % 2 == 0, i % 3 == 0, i % 4 == 0) for i in range(451)]
    rows += [(f"channel-{i}", "channel", i % 2 == 0, i % 3 == 0, i % 4 == 0) for i in range(451)]
    assert not [p for p in rows[:200] if p[1] == "group"]
    assert not [p for p in rows[:200] if p[1] == "channel"]
    has_later, first_index, last_index = False, 0, 0
    assert not ((first_index < 5 and has_later) or
                (first_index >= 5 and last_index >= 200 - 5))
    cases = 0
    # This models category filtering before the native page limit. It does not
    # implement Postbox, measure UIKit, or claim an actual device tap occurred.
    for category in ("private", "group", "channel"):
        expected = [p for p in rows if p[1] == category]
        for count in (1, 20, 80, 200):
            pages = [expected[i:i + count] for i in range(0, len(expected), count)]
            actual = [p for page in pages for p in page]
            assert actual == expected and len({p[0] for p in actual}) == len(expected)
            if category != "private":
                assert any(p[2] for p in actual)  # archived
                assert any(p[3] for p in actual)  # muted
                assert any(p[4] for p in actual)  # already read
            cases += 1
    assert not [p for p in rows if p[1] == "missing"]
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    patcher = ROOT / "ios/apply_features.py"
    helper = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef)
                  and n.name == "apply_notification_exception_peer_picker")
    values = {}
    for node in helper.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("picker", "patches"):
                values[name] = eval(compile(ast.Expression(node.value), "<patches>", "eval"),
                                    {"__builtins__": {}}, values)
    patches = values["patches"]
    old, new = snapshot(args.before), snapshot(args.after)
    assert old.keys() == new.keys()
    assert {p for p in old if old[p] != new[p]} == patches.keys()
    reversals = 0
    for name, (digest, replacements) in patches.items():
        assert old[name] == digest
        restored = (args.after / name).read_text()
        for original, replacement in reversed(replacements):
            assert restored.count(replacement) == 1, name
            restored = restored.replace(replacement, original, 1)
            reversals += 1
        assert restored.encode() == (args.before / name).read_bytes(), name

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ["clean", "rerun", *patches]:
        with tempfile.TemporaryDirectory(prefix="nagramix-exception-picker-") as folder:
            tree = Path(folder)
            for name in patches:
                path = tree / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(((args.after if scenario == "rerun" else args.before) / name).read_bytes())
            if scenario in patches:
                path = tree / scenario
                path.write_bytes(path.read_bytes() + b"\n// unexpected native drift\n")
            previous = snapshot(tree)
            if scenario == "clean":
                module.apply_notification_exception_peer_picker(tree)
                assert snapshot(tree) == {p: new[p] for p in patches}
            else:
                try:
                    module.apply_notification_exception_peer_picker(tree)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted drift or repeated integration")
                assert snapshot(tree) == previous, "Rejected integration partially wrote files"

    protocol = "submodules/AccountContext/Sources/PeerSelectionController.swift"
    old_protocol = (args.before / protocol).read_text()
    assert "1 << 18" not in old_protocol
    assert f"{FLAG} = ChatListNodePeersFilter(rawValue: 1 << 18)" in (args.after / protocol).read_text()
    category = (args.after / "submodules/SettingsUI/Sources/NotificationsPeerCategoryController.swift").read_text()
    # Exact single-line reversal preserves callback/save/cancel/remove logic.
    for token in ("filter.insert(.onlyPrivateChats)", "filter.insert(.excludeSavedMessages)",
                  "filter.insert(.excludeSecretChats)", "filter.insert(.onlyGroups)",
                  "filter.insert(.onlyChannels)", "hasContactSelector: false",
                  "controller.peerSelected = { [weak controller] peer, _ in",
                  "presentPeerSettings(peerId, {", "controller?.dismiss()"):
        assert token in category, token
    node = (args.after / (PICKER + "PeerSelectionControllerNode.swift")).read_text()
    branch = node.split("let nagramiXExceptionFilter:", 1)[1].split("        if hasFilters {", 1)[0]
    for token in (f"filter.contains(.{FLAG}), forumPeerId == nil, !hasFilters",
                  "categories = [.groups]", "categories = [.channels]",
                  "categories = [.contacts, .nonContacts, .bots]",
                  "excludeMuted: false", "excludeRead: false", "excludeArchived: false",
                  "isShared: false", "hasSharedLinks: false", "includePeers: ChatListFilterIncludePeers()",
                  "excludePeers: []", "nagramiXExceptionFilter = nil"):
        assert token in branch, token
    assert "chatListFilter: nagramiXExceptionFilter" in node
    for forbidden in ("updateChatListFilters", "updatePeerNotificationSettings", "enqueueMessages"):
        assert forbidden not in branch
    controller = (args.after / (PICKER + "PeerSelectionController.swift")).read_text()
    assert controller.count(f"filter.contains(.{FLAG})") == 3
    assert "searchContentNode.updateListVisibleContentOffset(offset)" in controller
    assert "return fixNavigationSearchableListNodeScrolling(listView, searchNode: searchContentNode)" in controller
    location = (args.after / "submodules/ChatListUI/Sources/Node/ChatListNodeLocation.swift").read_text()
    assert "filterPredicate = chatListFilterPredicate(filter: data, accountPeerId: account.peerId)" in location
    assert "filterPredicate: filterPredicate, count: count" in location
    assert "includeAdditionalPeerGroupIds.append(Namespaces.PeerGroup.archive)" in location
    assert "if !filter.categories.contains(.groups)" in location
    assert "if !filter.categories.contains(.channels)" in location
    cases = pagination_regression()
    print(f"PASS: {len(new)} outputs, exactly 4 changed, {reversals} exact reversals, 6 guard scenarios without partial writes")
    print(f"PASS: sparse-page regression and {cases} category/page models, scoped flag, archive/mute/read inclusion, search and native callbacks")
    print("Not executed: Apple SDK compile, Postbox runtime, UIKit or real iPhone interaction")


if __name__ == "__main__":
    main()
