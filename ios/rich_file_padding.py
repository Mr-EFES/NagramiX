"""Отступ файла внутри расширенного пузырька; весь preflight до записи."""
import hashlib
import json
from pathlib import Path


def apply_rich_file_padding(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'rich_file_padding_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Sources/Chat/ChatSendMessageRichTextPreview.swift', 'submodules/InstantPageUI/Sources/InstantPageV2Layout.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageRichDataBubbleContentNode/Sources/ChatMessageRichDataBubbleContentNode.swift'}
    required_guards = {'submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/ButtonEditorScreen.swift', 'submodules/InstantPageUI/Sources/InstantPageLayout.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageItemCommon/BUILD', 'submodules/InstantPageUI/Sources/InstantPageLayoutSpacings.swift', 'submodules/InstantPageUI/Sources/InstantPageV2ButtonRowLayout.swift', 'submodules/InstantPageUI/Sources/InstantPageV2MediaViews.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageRichDataBubbleContentNode/BUILD', 'submodules/InstantPageUI/Sources/InstantPageV2ContainerStyle.swift', 'submodules/InstantPageUI/Sources/InstantPageV2AudioContentNode.swift', 'submodules/InstantPageUI/Sources/InstantPageRenderer.swift', 'submodules/TelegramUI/BUILD', 'submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/FormulaEditorScreen.swift', 'submodules/InstantPageUI/Sources/InstantPageV2DocumentContentNode.swift', 'submodules/InstantPageUI/BUILD', 'submodules/InstantPageUI/Sources/InstantPageShapeItem.swift', 'submodules/TelegramUI/Components/TextProcessingScreen/Sources/TextProcessingRichContentView.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageItemCommon/Sources/ChatMessageItemCommon.swift', 'submodules/InstantPageUI/Sources/InstantPageMetrics.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageFileBubbleContentNode/Sources/ChatMessageFileBubbleContentNode.swift'}
    expected_copies = set()
    expected_native_inputs = {'submodules/InstantPageUI/Sources/InstantPageV2Layout.swift': '7536b5a2690024da320fbfb1d5cc04363afb010c', 'submodules/TelegramUI/Components/Chat/ChatMessageRichDataBubbleContentNode/Sources/ChatMessageRichDataBubbleContentNode.swift': '968a4ba82656a31891bef607d39f39a5ade905c6', 'submodules/TelegramUI/Sources/Chat/ChatSendMessageRichTextPreview.swift': '5d21405e0af8464e7f4904d70ada63345aa1be71'}
    expected_native_guards = {}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'named_link_preview'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != expected_native_inputs
        or plan.get('native_guards', {}) != expected_native_guards):
        raise SystemExit('rich_file_padding: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('rich_file_padding: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('rich_file_padding: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('rich_file_padding: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('rich_file_padding: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('rich_file_padding: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('rich_file_padding: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('rich_file_padding: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('rich_file_padding: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('rich_file_padding: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('rich_file_padding: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('rich_file_padding: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('rich_file_padding: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
