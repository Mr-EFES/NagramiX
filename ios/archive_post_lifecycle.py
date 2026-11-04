"""Keep complete posts on first deletion; explicitly purge selected local copies."""
import hashlib
import json
from pathlib import Path


def apply_archive_post_lifecycle(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'archive_post_lifecycle_patches.json').read_text())
    fields = ('outputs', 'previous', 'replacements')
    if any(plan['inputs'].keys() != plan[field].keys() for field in fields):
        raise SystemExit('Archive post lifecycle: inconsistent manifest')

    def checked(root: Path, name: str, digest: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Archive post lifecycle: unsafe path')
        if not path.is_file():
            raise SystemExit('Archive post lifecycle: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit('Archive post lifecycle: drift ' + name)
        return data

    for name, digest in plan['templates'].items():
        checked(overlay, name, digest)
    for name, digest in plan['guards'].items():
        checked(source, name, digest)
    prepared = {}
    for name, digest in plan['inputs'].items():
        if checked(source, name, digest) != checked(overlay, plan['previous'][name], digest):
            raise SystemExit('Archive post lifecycle: prior mismatch ' + name)
        prepared[name] = checked(overlay, plan['replacements'][name], plan['outputs'][name])
    # All source files, dependencies and templates pass before the first write.
    for name, data in prepared.items():
        (source / name).write_bytes(data)
