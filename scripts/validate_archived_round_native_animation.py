#!/usr/bin/env python3
"""Проверить интеграцию штатной анимации сохранённых кружков.

Нужны результаты полного feature overlay до/после и исходники закреплённого
Telegram. Проверяет реальные файлы и отказ без частичной записи; UIKit не запускает.
"""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def between(text, start, end):
    assert text.count(start) == 1
    offset = text.index(start)
    return text[offset:text.index(end, offset)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("before", "after", "upstream"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    patcher = ROOT / "ios/apply_features.py"
    tree = ast.parse(patcher.read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "apply_archived_round_native_animation")
    assignments = {t.id: n.value for n in helper.body if isinstance(n, ast.Assign)
                   for t in n.targets if isinstance(t, ast.Name)}
    guards = ast.literal_eval(assignments["guards"])
    native, decoration, embedded = guards
    names = dict(zip(("native", "decoration", "embedded"), guards))
    patches = [(names[p.elts[0].id], ast.literal_eval(p.elts[1]), ast.literal_eval(p.elts[2]))
               for p in assignments["patches"].elts]
    assert len(guards) == 3 and len(patches) == 6
    assert set(before) == set(after), "Добавлены или удалены файлы вне задачи"
    assert {n for n in before if before[n] != after[n]} == set(guards)
    expected = {n: before[n].decode() for n in guards}
    for name, digest in guards.items():
        assert hashlib.sha256(before[name]).hexdigest() == digest
    for name, old, new in patches:
        assert expected[name].count(old) == 1
        expected[name] = expected[name].replace(old, new, 1)
    assert all(expected[n].encode() == after[n] for n in guards), "Необъяснённые изменения"

    # Полный компонент маски снова побайтно совпадает с Telegram, включая
    # attach/detach, cornerRadius, frame, subnodeTransform и передачу transition.
    assert after[decoration] == (args.upstream / decoration).read_bytes()
    layout_start = "    func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition) {\n"
    layout_end = "    func play() {\n"
    assert between(after[native].decode(), layout_start, layout_end) == between(
        (args.upstream / native).read_text(), layout_start, layout_end)
    # Внешний scale/position/bounds и его animator остаются штатными. Отдельный
    # callback больше не удаляет анимацию узла после возврата видеоповерхности.
    embedded_text = after[embedded].decode()
    assert "ownsContentNodeUpdated" not in embedded_text
    outer_start = "                    if let videoNode = strongSelf.videoNode {\n                        videoNode.bounds ="
    outer_end = "                    animation.animator.updateFrame(layer: strongSelf.secretVideoPlaceholderBackground.layer,"
    assert between(embedded_text, outer_start, outer_end) == between(
        (args.upstream / embedded).read_text(), outer_start, outer_end)
    for contract in (
        "videoNode.canAttachContent = false\n                                    videoNode.removeFromSupernode()",
        "videoNode.transform = CATransform3DMakeScale(imageScale, imageScale, 1.0)",
        "nagramiXArchivedMessageId: nagramiXArchivedInstantVideo ? item.message.id : nil",
        "self.nagramiXArchivedPlaybackAction.activate(context: item.context",
    ):
        assert contract in embedded_text
    native_text = after[native].decode()
    assert "NagramiXArchivedInstantVideoId(messageId: messageId, fileId: fileReference.media.fileId, resourceId: fileReference.media.resource.id)" in native_text
    assert "value || (self.nagramiXArchivedInstantVideo && self.nagramiXArchivedInstantVideoHasFrame)" in native_text
    # Все другие outputs идентичны, включая родительскую группу 50%/footer,
    # archive store/copy, playlist и стандартную передачу одного decoder.
    parent = "submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift"
    assert "let nagramiXContentAlpha: CGFloat = nagramiXIsArchived ? 0.5 : 1.0" in after[parent].decode()

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", "partial", "missing", *guards):
        with tempfile.TemporaryDirectory(prefix="nagramix-round-native-") as directory:
            root = Path(directory)
            for name in guards:
                if scenario == "missing" and name == embedded:
                    continue
                data = after[name] if scenario == "rerun" or (scenario == "partial" and name == decoration) else before[name]
                if scenario == name:
                    data += b"\n// drift\n"
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            snapshot = files(root)
            if scenario == "clean":
                module.apply_archived_round_native_animation(root)
                assert files(root) == {n: after[n] for n in guards}
            else:
                try:
                    module.apply_archived_round_native_animation(root)
                except (SystemExit, FileNotFoundError):
                    pass
                else:
                    raise AssertionError("Принято изменённое или повторно применённое состояние: " + scenario)
                assert files(root) == snapshot, "Частичная запись при отказе"
    print(f"PASS: {len(after)} файлов, ровно 3 изменения/6 замен; stock decoration/layout/outer animator, 7 сценариев guards")
    print("Не выполнены: компиляция Apple SDK и повторное воспроизведение/анимация на iPhone")


if __name__ == "__main__":
    main()
