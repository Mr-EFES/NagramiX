"""Сохранить текст и файлы в общем черновике нового сообщения."""
import hashlib
import json
from pathlib import Path


def apply_composer_file_attachments(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'composer_file_attachments_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Sources/Chat/ChatControllerOpenDocumentScanner.swift', 'submodules/TelegramUI/Sources/ChatControllerOpenAttachmentMenu.swift', 'submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextAttachmentScreen.swift', 'submodules/TelegramUI/Sources/ChatControllerNode.swift'}
    required_guards = {'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaFile.swift', 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentButton.swift', 'submodules/TelegramUI/Components/Chat/ChatRichTextEditorComposer/Sources/ComposerExpandedEditorBridge.swift', 'submodules/ICloudResources/Sources/ICloudResources.swift', 'submodules/AccountContext/Sources/ChatController.swift', 'submodules/TelegramUI/BUILD', 'submodules/TelegramUI/Sources/ChatController.swift', 'submodules/TelegramUI/Components/AttachmentFileController/Sources/AttachmentFileController.swift', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentModel.swift', 'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_MediaReference.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift', 'submodules/TextFormat/Sources/ChatComposerSendPlan.swift', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentMedia.swift', 'submodules/LegacyMediaPickerUI/Sources/LegacyICloudFilePicker.swift', 'submodules/TelegramUI/Components/Chat/ChatRichTextEditorComposer/Sources/DocumentChatInputContentBridge.swift', 'submodules/TelegramUI/Components/RichTextAttachmentScreen/BUILD', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentReplaceRange.swift', 'submodules/TelegramUI/Components/RichTextEditorMessageConversion/Sources/ComposedRichMessage.swift', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentInstantPage.swift', 'submodules/TelegramUI/Sources/Chat/ChatControllerPaidMessage.swift', 'submodules/TelegramUI/Components/RichTextEditorMessageConversion/Sources/InstantPageBuilder.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'bubble_selection_edge'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('composer_file_attachments: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('composer_file_attachments: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('composer_file_attachments: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('composer_file_attachments: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('composer_file_attachments: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('composer_file_attachments: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('composer_file_attachments: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('composer_file_attachments: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('composer_file_attachments: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
