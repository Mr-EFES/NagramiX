#!/usr/bin/env python3
"""Проверить замену только окон отказа, сохранив штатную авторизацию Telegram.

Проверка реальных результатов overlay; UIKit и системные разрешения не исполняются.
"""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
HELPER = "submodules/DeviceAccess/Sources/NagramiXPermissionAlertController.swift"


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    patcher = ROOT / "ios/apply_features.py"
    helper = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef)
                  and n.name == "apply_native_permission_alerts")
    assignments = {t.id: n.value for n in helper.body if isinstance(n, ast.Assign)
                   for t in n.targets if isinstance(t, ast.Name)}
    guards = ast.literal_eval(assignments["guards"])
    names = dict(zip(("device", "build", "add_contact", "compose", "resolved", "contacts"), guards))
    patches = [(names[p.elts[0].id], *(ast.literal_eval(v) for v in p.elts[1:]))
               for p in assignments["patches"].elts]
    assert len(guards) == 6 and sum(count for _, count, _, _ in patches) == 13
    assert set(after) - set(before) == {HELPER} and not set(before) - set(after)
    assert {n for n in before if before[n] != after[n]} == {n for n, _, _, _ in patches}
    restored = {n: after[n].decode() for n in guards}
    for name, count, old, new in reversed(patches):
        assert before[name].decode().count(old) == count
        assert restored[name].count(new) == count
        restored[name] = restored[name].replace(new, old)
    for name, digest in guards.items():
        assert restored[name].encode() == before[name], "Изменена логика доступа: " + name
        assert hashlib.sha256(before[name]).hexdigest() == digest
    source = ROOT / "ios/Sources/DeviceAccess/NagramiXPermissionAlertController.swift"
    assert after[HELPER] == source.read_bytes()
    text = source.read_text()
    for native_contract in (
        "UIAlertController(title: title, message: text, preferredStyle: .alert)",
        "LegacyPresentedController(legacyController: alert, presentation: .custom)",
        "controller.blocksBackgroundWhenInOverlay = true",
        "alert.overrideUserInterfaceStyle = theme.backgroundType == .dark ? .dark : .light",
        "style = .cancel", "style = .default", "[weak controller]",
        "controller?.dismiss(completion: action.action)",
    ):
        assert native_contract in text
    for forbidden in ("requestAccess(", "requestRecordPermission(", "requestAuthorization(",
                      "standardTextAlertController(", ".frame =", ".font =", "maximumNumberOfLines"):
        assert forbidden not in text, "Контроллер меняет авторизацию или ручную геометрию"
    # Благодаря точному обратному сравнению все first-request API, denied /
    # restricted / limited ветки, callback/promise, onlyCheck и тексты прежние.
    device = after[names["device"]].decode()
    for request in ("AVCaptureDevice.requestAccess", "requestRecordPermission", "PHPhotoLibrary.requestAuthorization",
                    "requestWhenInUseAuthorization", "requestAlwaysAuthorization", "store.requestAccess",
                    "registerForNotifications { result in", "requestSiriAuthorization { result in"):
        assert request in device
    assert "standardTextAlertController(" not in device

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", "collision", "partial", "missing", *guards):
        with tempfile.TemporaryDirectory(prefix="nagramix-permission-") as directory:
            root = Path(directory)
            for name in guards:
                if scenario == "missing" and name == names["contacts"]:
                    continue
                data = after[name] if scenario == "rerun" or (scenario == "partial" and name == names["device"]) else before[name]
                if scenario == name:
                    data += b"\n// drift\n"
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if scenario in ("rerun", "collision"):
                (root / HELPER).write_bytes(after[HELPER] if scenario == "rerun" else b"collision")
            snapshot = files(root)
            if scenario == "clean":
                module.apply_native_permission_alerts(root, ROOT / "ios")
                assert files(root) == {n: after[n] for n in (*guards, HELPER)}
            else:
                try:
                    module.apply_native_permission_alerts(root, ROOT / "ios")
                except (SystemExit, FileNotFoundError):
                    pass
                else:
                    raise AssertionError("Принято изменённое состояние: " + scenario)
                assert files(root) == snapshot, "Частичная запись при отказе"
    print(f"PASS: {len(before)}→{len(after)} outputs, 13 окон/5 файлов + UIKit helper, 6 SHA/11 сценариев отказа и применения")
    print("Штатная авторизация и остальные файлы побайтно сохранены; Apple SDK/iPhone не запускались")


if __name__ == "__main__":
    main()
