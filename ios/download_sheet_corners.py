"""Совпадение верхней маски панели с клипом и чистый полупрозрачный буфер."""
import hashlib
import json
from pathlib import Path


def apply_download_sheet_corners(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'download_sheet_corners_patches.json').read_text())
    expected_inputs = set(['submodules/Display/Source/ActionSheetItemGroupNode.swift'])
    required_guards = set(['submodules/Display/Source/GenerateImage.swift', 'submodules/Display/Source/ActionSheetController.swift', 'submodules/Display/Source/ActionSheetControllerNode.swift', 'submodules/Display/Source/ActionSheetItemGroupsContainerNode.swift', 'submodules/Display/Source/ActionSheetItemNode.swift', 'submodules/Display/Source/ActionSheetTheme.swift', 'submodules/Display/BUILD', 'submodules/AsyncDisplayKit/Source/ASCGImageBuffer.mm', 'submodules/SettingsUI/Sources/NagramiXOptionSheet.swift', 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift', 'submodules/SettingsUI/BUILD', 'submodules/NagramiXMediaSettings/Sources/NagramiXDownloadSettings.swift', 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift', 'submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift', 'submodules/SettingsUI/Sources/NagramiXCustomDohController.swift'])
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'proxy_doh_editor'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('download_sheet_corners: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('download_sheet_corners: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('download_sheet_corners: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('download_sheet_corners: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('download_sheet_corners: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('download_sheet_corners: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('download_sheet_corners: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('download_sheet_corners: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('download_sheet_corners: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
