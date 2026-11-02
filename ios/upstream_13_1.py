"""Port the audited feature delta onto Telegram 13.1, with exact input/output guards.

The 13.0 checkout is a transformation input only. It is never compiled. Keeping
its canonical overlay stages intact preserves their checks and test fixtures.
Only the reviewed delta is merged into the actual 13.1 application checkout.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked(data: bytes, expected: str, label: str) -> bytes:
    if digest(data) != expected:
        raise SystemExit(f"Telegram 13.1 port input/output drift: {label}")
    return data


def safe_path(root: Path, name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise SystemExit(f"Unsafe migration path: {name}")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise SystemExit(f"Migration path escapes checkout: {name}")
    return path


def apply_upstream_131(source: Path, legacy_source: Path) -> None:
    from apply_features import apply_features
    overlay = Path(__file__).resolve().parent
    manifest = json.loads((overlay / 'upstream_13_1_manifest.json').read_text())
    checked((source / 'versions.json').read_bytes(), manifest['versions_sha256'], '13.1 versions.json')
    if source.resolve() == legacy_source.resolve():
        raise SystemExit('The application and transformation checkouts must be separate')
    for name, sha in manifest['legacy_inputs'].items():
        checked(safe_path(legacy_source, name).read_bytes(), sha, '13.0 source ' + name)
    # Stage every output before mutating the actual application tree. A failed
    # anchor, conflict, destination or hash check leaves that tree untouched.
    prepared: dict[str, bytes] = {}
    with tempfile.TemporaryDirectory(prefix='nagramix-port-131-') as directory:
        scratch = Path(directory)
        transformed = scratch / 'legacy'
        shutil.copytree(legacy_source, transformed, ignore=shutil.ignore_patterns('.git'))
        legacy_copy = overlay / 'upstream_13_2/onboarding_legacy.json'
        checked(legacy_copy.read_bytes(), '4fe5d540dd7b28596b9e20c1f42e7eb207a6835f28165b941572843e4d08a0d5', 'legacy onboarding')
        apply_features(transformed, onboarding_path=legacy_copy)
        for name, sha in manifest['legacy_outputs'].items():
            checked(safe_path(transformed, name).read_bytes(), sha, '13.0 overlay ' + name)
        for name, item in manifest['files'].items():
            target = safe_path(source, name)
            if item['upstream_sha256'] is None:
                if target.exists():
                    raise SystemExit('Telegram 13.1 port destination exists: ' + name)
                upstream = b''
            else:
                upstream = checked(target.read_bytes(), item['upstream_sha256'], '13.1 source ' + name)
            kind = item['kind']
            if kind == 'merge':
                result = subprocess.run([
                    'git', 'merge-file', '-p', '--diff3',
                    '-L', 'NagramiX-13.0', '-L', 'Telegram-13.0', '-L', 'Telegram-13.1',
                    str(safe_path(transformed, name)), str(safe_path(legacy_source, name)), str(target)
                ], capture_output=True)
                if result.returncode < 0 or result.returncode > 127:
                    raise SystemExit('Cannot merge migration input: ' + name)
                data = result.stdout
            elif kind == 'legacy_added':
                data = safe_path(transformed, name).read_bytes()
            elif kind == 'native':
                data = upstream
            elif kind == 'created':
                data = item['content'].encode('utf-8')
            else:
                raise SystemExit('Unknown migration operation: ' + kind)
            checked(data, item['merged_sha256'], 'three-way merge ' + name)
            text = data.decode('utf-8') if item['edits'] else None
            for edit in item['edits']:
                old, new = edit['old'], edit['new']
                if text.count(old) != 1:
                    raise SystemExit('Reviewed 13.1 resolution anchor drift: ' + name)
                text = text.replace(old, new, 1)
            data = checked(text.encode('utf-8') if text is not None else data, item['output_sha256'], 'reviewed output ' + name)
            if re.search(rb'^(?:<<<<<<< NagramiX-13.0|\|\|\|\|\|\|\| Telegram-13.0|>>>>>>> Telegram-13.1)$', data, re.M):
                raise SystemExit('Unresolved migration conflict: ' + name)
            prepared[name] = data
        for name in manifest['removed_upstream']:
            if safe_path(source, name).exists():
                raise SystemExit('Removed native implementation was reintroduced: ' + name)
    for name, data in prepared.items():
        target = safe_path(source, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(f'Applied reviewed Telegram 13.1 port: {len(prepared)} outputs; canonical guards preserved')
