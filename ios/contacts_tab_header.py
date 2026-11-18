"""Place the Contacts tab actions on opposite sides of the header."""
import hashlib
import json
from pathlib import Path


def apply_contacts_tab_header(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'contacts_tab_header_patches.json').read_text())
    name = 'submodules/ContactListUI/Sources/ContactsControllerNode.swift'
    guards = {
        'submodules/ContactListUI/Sources/ContactsController.swift',
        'submodules/ContactListUI/Sources/ContactListNode.swift',
        'submodules/TelegramUI/Components/ChatListHeaderComponent/Sources/ChatListNavigationBar.swift',
        'submodules/TelegramUI/Components/NavigationBarComponent/Sources/NavigationBarRowLayout.swift',
    }
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
            or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
            or plan['required_previous_stage'] != 'contacts_tab_add'
            or any(plan[field].keys() != {name} for field in ('inputs', 'outputs', 'previous', 'replacements'))
            or any(plan[field].keys() != guards for field in ('guards', 'guard_sources'))
            or any(plan[field] for field in ('copies', 'deletions', 'native_inputs', 'native_guards'))):
        raise SystemExit('contacts_tab_header: inconsistent manifest')

    def checked(root: Path, name: str, expected: str) -> bytes:
        relative = Path(name)
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
            raise SystemExit(f'contacts_tab_header: invalid file {name}')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f'contacts_tab_header: drift {name}')
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit(f'contacts_tab_header: unregistered template {name}')
        return checked(overlay, name, expected)

    for path, expected in plan['guards'].items():
        if checked(source, path, expected) != template(plan['guard_sources'][path], expected):
            raise SystemExit(f'contacts_tab_header: guard mismatch {path}')

    expected = plan['inputs'][name]
    if checked(source, name, expected) != template(plan['previous'][name], expected):
        raise SystemExit(f'contacts_tab_header: input mismatch {name}')
    output = template(plan['replacements'][name], plan['outputs'][name])
    (source / name).write_bytes(output)
