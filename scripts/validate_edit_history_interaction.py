#!/usr/bin/env python3
"""Проверить открытие списка и отдельный путь пересылки выбранной редакции.

Проверяет реальные результаты feature overlay и отказы до записи, не UIKit.
"""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
UI = "submodules/TelegramUI/Sources/Chat/NagramiXEditHistoryController.swift"
FORWARD = "submodules/TelegramUI/Sources/Chat/NagramiXEditHistoryForwarding.swift"


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def part(text, start, end):
    assert text.count(start) == 1
    offset = text.index(start)
    return text[offset:text.index(end, offset)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    patcher = ROOT / "ios/apply_features.py"
    function = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef)
                    and n.name == "apply_edit_history_interaction_fix")
    assignments = {t.id: n.value for n in function.body if isinstance(n, ast.Assign)
                   for t in n.targets if isinstance(t, ast.Name)}
    guards = ast.literal_eval(assignments["guards"])
    names = dict(zip(("menu", "interaction", "load", "build"), guards))
    patches = [(names[p.elts[0].id], ast.literal_eval(p.elts[1]), ast.literal_eval(p.elts[2]))
               for p in assignments["patches"].elts]
    assert len(guards) == 4 and len(patches) == 5
    assert set(after) - set(before) == {FORWARD} and not set(before) - set(after)
    assert {n for n in before if before[n] != after[n]} == {UI, *(n for n, _, _ in patches)}
    restored = {n: after[n].decode() for n in guards}
    for name, old, new in reversed(patches):
        assert restored[name].count(new) == 1
        restored[name] = restored[name].replace(new, old, 1)
    for name, digest in guards.items():
        assert restored[name].encode() == before[name], "Изменение вне callback истории: " + name
        assert hashlib.sha256(before[name]).hexdigest() == digest
    for name, origin in ((UI, "NagramiXEditHistoryController.swift"), (FORWARD, "NagramiXEditHistoryForwarding.swift")):
        assert after[name] == (ROOT / "ios/Sources/TelegramUI" / origin).read_bytes()

    ui, old_ui, forward = after[UI].decode(), before[UI].decode(), after[FORWARD].decode()
    # Карточки, ограничения экспорта, выбранный snapshot и копирование не меняются.
    for start, end in (
        ("func nagramiXEditHistorySnapshot", "private final class NagramiXEditHistoryCell"),
        ("private final class NagramiXEditHistoryCell", "final class NagramiXEditHistoryController"),
        ("    private func refreshPresentationAndLayout()", "    @objc private func closePressed()"),
        ("        cell.configure(revision:", "        }, forward:"),
    ):
        assert part(ui, start, end) == part(old_ui, start, end)
    assert "tableHeaderView" not in ui
    assert "self.tableView.tableFooterView = self.noteContainer" in ui
    assert "self.tableView.sectionHeaderTopPadding = 0.0" in ui
    assert "if !self.didApplyInitialLayout, width > 0.0, self.tableView.bounds.height > 0.0" in ui
    assert ui.count("self.didApplyInitialLayout = true") == 1
    assert "self.forwardRevision?(nagramiXEditHistorySnapshot(message: self.message, revision: revision))" in ui
    assert "forward: interfaceInteraction.forwardEditHistoryVersion" in after[names["menu"]].decode()
    for contract in (
        "nagramiXCanCopyMessagesAsNew([message])", "presentAccountFrozenInfoIfNeeded",
        "presentVoiceMessageDiscardAlert", "multipleSelection: false", "forwardedMessageIds: []",
        "controller.peerSelected =", "message.text, entities: entities",
        "updateTextInputState: inputState", "useExisting: false", "activateInput: .text",
        "message.peerId == peer.id, message.threadId == threadId", "chatControllerForForumThread",
        "navigationController.viewControllers.contains(where: { $0 === controller })",
    ):
        assert contract in forward
    for forbidden in ("multiplePeersSelected", "enqueueMessages", ".forward(source:", "forwardMessages(messageIds:",
                      "getMessage(", "copyMessagesWithoutSource", "transferMode: .copyAsNew"):
        assert forbidden not in forward, "Выбранная версия может попасть в рассылку/refetch/enqueue"
    # Сам общий механизм обычной пересылки/рассылки, получение/хранение истории,
    # native send/payment/quiet/schedule и прежние исправления побайтно прежние.

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", "partial", "missing", "collision", "missing-helper", *guards):
        with tempfile.TemporaryDirectory(prefix="nagramix-history-interaction-") as directory:
            root = Path(directory)
            for name in guards:
                if scenario == "missing" and name == names["build"]:
                    continue
                data = after[name] if scenario == "rerun" or (scenario == "partial" and name == names["interaction"]) else before[name]
                if scenario == name:
                    data += b"\n// drift\n"
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if scenario in ("rerun", "collision"):
                (root / FORWARD).write_bytes(after[FORWARD] if scenario == "rerun" else b"collision")
            snapshot = files(root)
            overlay = root / "missing-overlay" if scenario == "missing-helper" else ROOT / "ios"
            if scenario == "clean":
                module.apply_edit_history_interaction_fix(root, overlay)
                assert files(root) == {n: after[n] for n in (*guards, FORWARD)}
            else:
                try:
                    module.apply_edit_history_interaction_fix(root, overlay)
                except (SystemExit, FileNotFoundError):
                    pass
                else:
                    raise AssertionError("Принято изменённое состояние: " + scenario)
                assert files(root) == snapshot, "Частичная запись при отказе"
    print(f"PASS: {len(before)}→{len(after)} outputs, 4 изменения + helper; 5 замен/4SHA/10 guard cases")
    print("Карточки/copy/snapshot, общий forward/send и остальные outputs сохранены; Apple SDK/iPhone не запускались")


if __name__ == "__main__":
    main()
