"""Выделение сообщений одним пальцем в области штатных галочек."""
import hashlib
import json
from pathlib import Path


def apply_single_touch_message_selection(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'single_touch_message_selection_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Sources/ChatHistoryListNode.swift'}
    required_guards = {'submodules/TelegramUI/Components/CoreList/CoreListDemo/UIKitScrollEngine.swift', 'submodules/TelegramUI/Components/ChatControllerInteraction/Sources/ChatControllerInteraction.swift', 'submodules/TelegramUI/Components/CoreList/CoreListDemo/PhysicsScrollEngine.swift', 'submodules/TelegramUI/Components/Chat/ChatHistoryEntry/Sources/ChatHistoryEntry.swift', 'submodules/ChatInterfaceState/Sources/ChatInterfaceState.swift', 'submodules/TelegramUI/Components/CoreList/CoreListDemo/CoreVirtualListView.swift', 'submodules/TelegramUI/BUILD', 'submodules/TelegramUI/Sources/ChatController.swift', 'submodules/Postbox/Sources/Message.swift', 'submodules/TelegramUI/Components/Chat/ChatHistoryListViewBackend/Sources/ChatHistoryListViewBackend.swift', 'submodules/Display/Source/ListViewScroller.swift', 'submodules/Postbox/Sources/MessageHistoryView.swift', 'submodules/TelegramUI/Components/Chat/ChatHistoryListViewBackend/Sources/CoreListChatHistoryBackend.swift', 'submodules/ChatListUI/BUILD', 'submodules/ChatListUI/Sources/Node/ChatListNode.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageSelectionNode/Sources/ChatMessageSelectionNode.swift'}
    expected_copies = {'submodules/TelegramUI/Sources/Chat/NagramiXMessageDragSelection.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'composer_copy_integrity'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != {}
        or plan.get('native_guards', {})):
        raise SystemExit('single_touch_message_selection: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('single_touch_message_selection: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('single_touch_message_selection: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('single_touch_message_selection: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('single_touch_message_selection: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('single_touch_message_selection: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('single_touch_message_selection: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('single_touch_message_selection: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('single_touch_message_selection: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('single_touch_message_selection: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('single_touch_message_selection: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('single_touch_message_selection: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('single_touch_message_selection: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
