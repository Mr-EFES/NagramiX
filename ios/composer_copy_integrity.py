"""Полное копирование поста, верхнее вложение и штатная отправка из обоих редакторов."""
import hashlib
import json
from pathlib import Path


def apply_composer_copy_integrity(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'composer_copy_integrity_patches.json').read_text())
    expected_inputs = {'submodules/TelegramUI/Sources/Chat/UpdateChatPresentationInterfaceState.swift', 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift', 'submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextAttachmentScreen.swift', 'submodules/Pasteboard/Sources/Pasteboard.swift', 'submodules/TelegramUI/Components/Chat/ChatRichTextEditorComposer/Sources/RichMessageClipboard.swift', 'submodules/TelegramUI/Sources/ChatControllerNode.swift', 'submodules/TelegramUI/Sources/ChatControllerOpenAttachmentMenu.swift'}
    required_guards = {'submodules/TextFormat/Sources/ChatComposerSendPlan.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/Document.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEngineEditor/RichTextEditorProtocol.swift', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentButton.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/ButtonRef.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Position/DocumentTree.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/TableBlock+Editing.swift', 'submodules/TextFormat/Sources/StringWithAppliedEntities.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/SelfReferentialLinks.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/TextRun.swift', 'submodules/TextFormat/BUILD', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentMedia.swift', 'submodules/TelegramUI/BUILD', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/ParagraphAttributes.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/MediaItem.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/BlockQuote.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/CodeBlock.swift', 'submodules/ChatPresentationInterfaceState/Sources/ChatPresentationInterfaceState.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Position/TextNodeRef.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/CaretReveal.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/DocumentFragment.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Position/ResolvedPos.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/RGBAColor.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorUIKit/RichTextEditorView.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/Block.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/EmojiRef.swift', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentRuns.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEngineEditor/RichTextEngineEditorView+ArticleHost.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/PullQuote.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Lists/ListNumbering.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/BlockID.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Position/DocNode.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Selection/RTSelection.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEngineEditor/RichTextEngineEditorView+Clipboard.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorUIKit/Canvas/RTFConversion.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/MediaKind.swift', 'submodules/TextFormat/Sources/ChatInputContentConversion.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/ListMembership.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_OutgoingContentInfoMessageAttribute.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/StandaloneFormula.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/RichTextEditorCore.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Serialization/RTFTokenizer.swift', 'submodules/AccountContext/Sources/ChatController.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/Enums.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/DetailsBlock.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Serialization/DocumentCodec.swift', 'submodules/TextFormat/Sources/MentionDateMarkers.swift', 'submodules/Pasteboard/BUILD', 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/ParagraphBlock+Editing.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Selection/TableMap.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorUIKit/RichTextEditorClipboard.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Position/TextNodeRuns.swift', 'submodules/TelegramUI/Components/RichTextEditorMessageConversion/Sources/ButtonActionCodec.swift', 'submodules/TextFormat/Sources/CodeBlockMarkers.swift', 'submodules/TextFormat/Sources/GenerateTextEntities.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Selection/TableSelectionConversion.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/MediaBlock.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/CaretRevealRequest.swift', 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TextEntitiesMessageAttribute.swift', 'submodules/TelegramUI/Components/Chat/ChatRichTextEditorComposer/BUILD', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentModel.swift', 'submodules/TelegramCore/Sources/ChatInputContent/ChatInputContentReplaceRange.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Serialization/RTFImport.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Position/PositionResolver.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/TextRunSlicing.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorUIKit/Canvas/DocumentCanvasView+Clipboard.swift', 'submodules/TelegramUI/Components/RichTextEditor/BUILD', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/ParagraphBlock.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Serialization/ChecklistEmojiMarker.swift', 'submodules/TextFormat/Sources/ChatTextInputAttributes.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/CharacterAttributes.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Position/PositionMapping.swift', 'submodules/TelegramUI/Components/Chat/ChatRichTextEditorComposer/Sources/DocumentChatInputContentBridge.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Serialization/DocumentPackage.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/Size2D.swift', 'submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextEditorCore/Model/TableBlock.swift', 'submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/ChatTextInputPanelNode.swift'}
    expected_copies = set()
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'local_read_label'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != {'submodules/Pasteboard/Sources/Pasteboard.swift': '2e5007d9edac5f57257bb820e74a8b7553c539c5', 'submodules/TelegramUI/Components/Chat/ChatRichTextEditorComposer/Sources/RichMessageClipboard.swift': 'a0741b2b7b8ddf19f5a63396c9b84bc2f7762a89'}
        or plan.get('native_guards', {})):
        raise SystemExit('composer_copy_integrity: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('composer_copy_integrity: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('composer_copy_integrity: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('composer_copy_integrity: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('composer_copy_integrity: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('composer_copy_integrity: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('composer_copy_integrity: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('composer_copy_integrity: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('composer_copy_integrity: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('composer_copy_integrity: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('composer_copy_integrity: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('composer_copy_integrity: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('composer_copy_integrity: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
