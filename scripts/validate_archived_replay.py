#!/usr/bin/env python3
"""Check retained replay integration and real filesystem pinning primitives.

This validates source scope/guards and filesystem contracts, not AVFoundation,
Postbox playback, server uploads or UIKit on an iPhone.
"""

import argparse
import ast
import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
HELPER = "submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift"
MODELS = {
    "submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift": "Sources/TelegramCore/NagramiXArchivedMediaStore.swift",
    "submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift": "Sources/TelegramCore/NagramiXArchivedMediaCopy.swift",
}


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def filesystem_contracts():
    with tempfile.TemporaryDirectory(prefix="nagramix-replay-fs-", dir="/workspace") as folder:
        root = Path(folder)
        source, cache, pending = root / "archive.bin", root / "cache", root / "pending"
        payload = bytes(range(256)) * 4096
        source.write_bytes(payload)
        os.link(source, cache)
        os.link(source, pending)
        assert source.stat().st_ino == cache.stat().st_ino == pending.stat().st_ino
        try:
            os.link(source, cache)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Existing destination overwritten")
        cache.unlink()
        assert source.read_bytes() == payload and pending.read_bytes() == payload
        source.unlink()
        assert pending.read_bytes() == payload, "Archive removal invalidated upload pin"
        # Cross-filesystem copy fallback uses a sibling staging path: a complete
        # cache name is published only after all bytes have been copied.
        staging = root / ".staging"
        with staging.open("wb") as stream:
            stream.write(payload[:512])
            assert not cache.exists()
            stream.write(payload[512:])
        staging.rename(cache)
        assert cache.read_bytes() == payload and not staging.exists()
        key = b"nagramix-retained-upload-v1:local-file-reference-123"
        encoded = base64.urlsafe_b64encode(key).decode()
        names = ["nagramix-archive-copy-" + str(uuid.uuid4()) + "." + encoded for _ in range(2)]
        assert names[0] != names[1]
        assert all(base64.urlsafe_b64decode(n.split(".", 1)[1]) == key for n in names)
        assert len(names[0]) < 255
    print("Filesystem contracts: complete atomic link/publication, independent upload pin, stable cache-key encoding PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    patcher = ROOT / "ios/apply_features.py"
    helper = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "apply_archived_replay_and_upload_cache_fix")
    assignments = {t.id: n.value for n in helper.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    guards = ast.literal_eval(assignments["guards"])
    native_names = dict(zip(("auxiliary", "native", "decoration", "embedded", "file", "account_build", "bubble", "fetch"), guards))
    patches = [(native_names[p.elts[0].id], ast.literal_eval(p.elts[1]), ast.literal_eval(p.elts[2])) for p in assignments["patches"].elts]
    assert len(patches) == 14 and len(guards) == 8
    assert set(after) - set(before) == {HELPER} and not set(before) - set(after)
    changed = {n for n in before if before[n] != after[n]}
    assert changed == {n for n, _, _ in patches} | set(MODELS), changed
    restored = {n: after[n].decode() for n in guards}
    for name, old, new in reversed(patches):
        assert restored[name].count(new) == 1
        restored[name] = restored[name].replace(new, old, 1)
    for name, digest in guards.items():
        assert restored[name].encode() == before[name], name
        assert hashlib.sha256(before[name]).hexdigest() == digest
    for name, overlay in MODELS.items():
        assert after[name] == (ROOT / "ios" / overlay).read_bytes()
    assert after[HELPER] == (ROOT / "ios/Sources/AccountContext/NagramiXArchivedPlaybackAction.swift").read_bytes()

    store_name, copy_name = MODELS
    store = after[store_name].decode()
    start = store.index("        let localResource = LocalFileReferenceMediaResource(")
    end = store.index("        return localResource\n", start) + len("        return localResource\n")
    original_return = "        return LocalFileReferenceMediaResource(localFilePath: path, randomId: file.localId, isUniquelyReferencedTemporaryFile: false, size: file.size)\n"
    assert (store[:start] + original_return + store[end:]).encode() == before[store_name]
    assert "file.size > 0" in store[start:end] and "linkItem" in store[start:end]
    assert "copyItem" not in store[start:end] and "Data(contentsOf" not in store[start:end]
    copy = after[copy_name].decode()
    start = copy.index("    /// Native sent-media caching")
    end = copy.index("    private func resource", start)
    restored_copy = copy[:start] + copy[end:]
    start = restored_copy.index('        var cacheKeySuffix = ""')
    end = restored_copy.index("        do {\n", start)
    old_path = '        let path = NSTemporaryDirectory() + "nagramix-archive-copy-" + UUID().uuidString\n'
    assert (restored_copy[:start] + old_path + restored_copy[end:]).encode() == before[copy_name]
    assert "resource.isUniquelyReferencedTemporaryFile" in copy and "UUID(uuidString:" in copy
    assert 'lastPathComponent == "nagramix-message-media"' in copy
    action = after[HELPER].decode()
    for contract in ("self.generation == generation", "isCurrent()", "filteredPlaylistState", "accountId: context.account.id", "type: .voice", "|> take(1)", "[weak self]", "self.disposable.dispose()"):
        assert contract in action
    assert "if state != nil && !ended" in action and "open()" in action
    assert "case .paused = state.status.status" in action and "state.status.duration.isFinite" in action
    assert "getMessage" not in action and "after(" not in action
    # Scope reversal keeps the existing 50% parent alpha, IDs, archive settings,
    # native playlist end policy, unrelated send metadata and earlier fixes.
    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", "collision", *guards):
        with tempfile.TemporaryDirectory(prefix="nagramix-replay-", dir="/workspace") as folder:
            tree = Path(folder)
            initial = {}
            for name in guards:
                data = after[name] if scenario == "rerun" else before[name]
                if scenario == name:
                    data += b"\n// Unexpected native drift\n"
                initial[name] = data
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if scenario in ("rerun", "collision"):
                target = tree / HELPER
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(after[HELPER] if scenario == "rerun" else b"collision")
                initial[HELPER] = target.read_bytes()
            if scenario == "clean":
                module.apply_archived_replay_and_upload_cache_fix(tree)
                assert all((tree / n).read_bytes() == after[n] for n in guards)
                assert (tree / HELPER).read_bytes() == after[HELPER]
            else:
                try:
                    module.apply_archived_replay_and_upload_cache_fix(tree)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted drift/reapply/collision")
                assert files(tree) == initial, "Partial write on rejection"
    filesystem_contracts()
    print("PASS: exact scope, 14 reversals, 8 SHA guards/rerun/collision; Core metadata and copy rollback unchanged")
    print("Not executed: native Swift/Apple SDK, playback/geometry or cached upload delivery on iPhone")


if __name__ == "__main__":
    main()
