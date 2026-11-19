"""Install the Worker client and connect it to the main app lifecycle."""
import hashlib
import json
from pathlib import Path


def apply_installation_metrics(source: Path, overlay: Path) -> None:
    app = 'submodules/TelegramUI/Sources/AppDelegate.swift'
    helper = 'submodules/TelegramUI/Sources/NagramiXInstallationMetrics.swift'
    build = 'submodules/TelegramUI/BUILD'
    plan = json.loads((overlay / 'installation_metrics_patches.json').read_text())
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan['required_previous_stage'] != 'pip_session_recovery'
            or any(set(plan[key]) != {app} for key in ('inputs', 'previous', 'outputs', 'replacements'))
            or any(set(plan[key]) != {build} for key in ('guards', 'guard_sources'))
            or set(plan['copies']) != {helper}
            or any(plan[key] for key in ('deletions', 'native_inputs', 'native_guards'))):
        raise SystemExit('installation_metrics: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = root / name
        if (Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit('installation_metrics: invalid file ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('installation_metrics: unexpected contents ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('installation_metrics: unregistered template ' + name)
        return checked(overlay, name, expected)

    for target, snapshots, hashes in ((app, 'previous', 'inputs'), (build, 'guard_sources', 'guards')):
        expected = plan[hashes][target]
        if checked(source, target, expected) != template(plan[snapshots][target], expected):
            raise SystemExit('installation_metrics: snapshot mismatch ' + target)
    app_data = template(plan['replacements'][app], plan['outputs'][app])
    item = plan['copies'][helper]
    helper_data = template(item['source'], item['sha256'])
    destination = source / helper
    if destination.exists() or destination.is_symlink() or not destination.parent.resolve().is_relative_to(source.resolve()):
        raise SystemExit('installation_metrics: unexpected helper destination')

    destination.write_bytes(helper_data)
    (source / app).write_bytes(app_data)
