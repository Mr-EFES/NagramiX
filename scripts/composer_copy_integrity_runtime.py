"""Actual clipboard/RTF/document and draft/send paths; OS and storage edges explicit."""
from pathlib import Path
from validate_quick_format import block
from composer_file_attachments_runtime import without_imports,MODEL,ACCOUNT,CORE,MENU,NODE

ROOT=Path(__file__).resolve().parents[1]
PASTE='submodules/Pasteboard/Sources/Pasteboard.swift'
CLIP='submodules/TelegramUI/Components/Chat/ChatRichTextEditorComposer/Sources/RichMessageClipboard.swift'
BRIDGE='submodules/TelegramUI/Components/Chat/ChatRichTextEditorComposer/Sources/DocumentChatInputContentBridge.swift'
CONTEXT='submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift'
UPDATE='submodules/TelegramUI/Sources/Chat/UpdateChatPresentationInterfaceState.swift'
RICH='submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextAttachmentScreen.swift'
TEXT='submodules/TextFormat/Sources/'
RTE='submodules/TelegramUI/Components/RichTextEditor/Sources/'
ENTITIES='submodules/TelegramCore/Sources/SyncCore/SyncCore_TextEntitiesMessageAttribute.swift'


def dependencies(source):
    return sorted([p.relative_to(source).as_posix() for p in (source/(RTE+'RichTextEditorCore')).rglob('*.swift')])+[
        MODEL,ACCOUNT,CORE+'ChatInputContentButton.swift',CORE+'ChatInputContentRuns.swift',CORE+'ChatInputContentReplaceRange.swift',CORE+'ChatInputContentMedia.swift',
        ENTITIES,TEXT+'GenerateTextEntities.swift',TEXT+'ChatTextInputAttributes.swift',TEXT+'StringWithAppliedEntities.swift',TEXT+'ChatInputContentConversion.swift',TEXT+'CodeBlockMarkers.swift',TEXT+'MentionDateMarkers.swift',
        BRIDGE,RTE+'RichTextEditorUIKit/RichTextEditorClipboard.swift',RTE+'RichTextEditorUIKit/Canvas/RTFConversion.swift',
        'submodules/TextFormat/Sources/ChatComposerSendPlan.swift','submodules/TelegramUI/Components/RichTextEditorMessageConversion/Sources/ButtonActionCodec.swift',
        RTE+'RichTextEngineEditor/RichTextEditorProtocol.swift',RTE+'RichTextEngineEditor/RichTextEngineEditorView+ArticleHost.swift',RTE+'RichTextEditorUIKit/RichTextEditorView.swift',
    ]


def fixture(source):
    boundary=(ROOT/'scripts/tests/NagramiXComposerFilesBoundary.swift').read_text().split('// The attributed-text and Markdown boundary')[0]
    boundary=boundary.replace('public struct MessageTextEntity: Equatable { public var marker: String }','')
    parts=[boundary,(ROOT/'scripts/tests/NagramiXComposerCopyBoundary.swift').read_text()]
    for p in sorted((source/(RTE+'RichTextEditorCore')).rglob('*.swift')):
        text=p.read_text()
        if p.name=='ButtonRef.swift':text=text[:text.index('public extension Document {')] # Unrelated button-action migration, outside clipboard data/model scope.
        parts.append(without_imports(text))
    parts.append(without_imports((source/MODEL).read_text()))
    state=block((source/ACCOUNT).read_text(),'public struct ChatTextInputState:')
    parts.append(state[:state.index('    public init(from decoder:')].replace(': Codable, Equatable',': Equatable',1)+'}')
    for name in ['ChatInputContentButton.swift','ChatInputContentRuns.swift','ChatInputContentReplaceRange.swift','ChatInputContentMedia.swift']:
        parts.append(without_imports((source/(CORE+name)).read_text()))
    entities=(source/ENTITIES).read_text()
    parts.append(block(entities,'public enum MessageTextEntityType:'))
    entity=block(entities,'public struct MessageTextEntity:').replace('PostboxCoding, ','',1)
    for marker in ['    public init(decoder:', '    public func encode(_ encoder:']:
        entity=entity.replace(block(entity,marker),'',1)
    parts.append(entity)
    attrs=(source/(TEXT+'ChatTextInputAttributes.swift')).read_text()
    for marker in ['public struct ChatTextInputAttributes','public final class ChatTextInputTextMentionAttribute:','public final class ChatTextInputTextUrlAttribute:','public final class ChatTextInputTextDateAttribute:','public final class ChatTextInputTextQuoteAttribute:']:
        parts.append(block(attrs,marker))
    parts.append(block((source/(TEXT+'StringWithAppliedEntities.swift')).read_text(),'public func chatInputStateStringWithAppliedEntities('))
    for n in ['ChatInputContentConversion.swift','CodeBlockMarkers.swift','MentionDateMarkers.swift']:
        parts.append(without_imports((source/(TEXT+n)).read_text()))
    bridge=(source/BRIDGE).read_text()
    parts.append(bridge[bridge.index('public func document('):bridge.index('/// True when pasted RTF')])
    parts.append(block((source/'submodules/TelegramUI/Components/RichTextEditorMessageConversion/Sources/ButtonActionCodec.swift').read_text(),'public func buttonRowAlignment('))
    clip=(source/CLIP).read_text()
    parts.append(block(clip,'public func pasteFragmentDocument('))
    rtf=(source/(RTE+'RichTextEditorUIKit/Canvas/RTFConversion.swift')).read_text()
    parts.append(rtf[rtf.index('enum RTFConversion {'):rtf.index('    static func fragment(fromRTF')]+ '\n}')
    parts.append(block((source/(RTE+'RichTextEditorUIKit/RichTextEditorClipboard.swift')).read_text(),'public enum RichTextEditorClipboard {'))
    paste=(source/PASTE).read_text()
    for marker in ['struct AppSpecificPasteboardString:', 'private func appSpecificStringWithAppliedEntities(', 'public func chatInputStateStringFromAppSpecificString(', 'public func messageTextPasteboardItem(']:
        parts.append(block(paste,marker))
    parts.append(block(clip,'public func storeChatMessageTextInPasteboard('))
    parts.append(block((source/RICH).read_text(),'private func nagramiXLeadingAttachmentDocument('))
    parts.append(block((source/(TEXT+'GenerateTextEntities.swift')).read_text(),'public func generateChatInputTextEntities('))
    parts.append(without_imports((source/'submodules/TextFormat/Sources/ChatComposerSendPlan.swift').read_text()))
    menu=(source/MENU).read_text()
    for name in ['nagramiXComposerFileDraft','nagramiXComposerCaptionFiles','nagramiXComposerSendContent','nagramiXComposerFileMessages']:
        parts.append(block(menu,'func '+name+'('))
    update=(source/UPDATE).read_text()
    start=update.index('    let nagramiXHasAttachedMedia =')
    end=update.index('    if case let .customChatContents',start)
    parts.append('func preparePreview(_ original: PreviewState, controller selfController: PreviewController) -> (PreviewState,Bool) {\nvar updatedChatPresentationInterfaceState=original\n'+update[start:end].replace('    var canHaveUrlPreview =','    let canHaveUrlPreview =',1)+'\nreturn (updatedChatPresentationInterfaceState,canHaveUrlPreview)\n}')
    start=update.index('                    guard $0.interfaceState.composeInputState.content.allMedia.isEmpty')
    end=update.index('                })',start)
    parts.append('func acceptLatePreview(_ state: PreviewState) -> PreviewState {\nlet result:(String?)->(String,String)? = {_ in ("late-card","https://t.me/radio_tavria")}\nlet apply:(PreviewState)->PreviewState = {\n'+update[start:end]+'\n}\nreturn apply(state)\n}')
    parts.append((ROOT/'scripts/tests/NagramiXComposerCopyTests.swift').read_text())
    return '\n'.join(parts)


def negatives(code):
    for name,old,new,label in [
        ('omit-native-fragment','    item.merge(RichTextEditorClipboard.pasteboardItem(for: document, plain: text), uniquingKeysWith: { _, native in native })','    item.removeValue(forKey: RichTextEditorClipboard.fragmentUTI); _ = document','native private fragment is present'),
        ('flatten-entities','entities: entities ?? []','entities: []','first native paste preserves named link'),
        ('append-file-below','updated.content.blocks.insert(contentsOf: attachments, at: insertionIndex)','updated.content.blocks.append(contentsOf: attachments)','file begins the draft before upload'),
        ('reject-leading-caption','            if reachedText {','            if reachedText || !reachedText {','leading file uses native caption unless unrepresentable round'),
        ('drop-preview-flag','flags: [.disableLinkPreviews]','flags: []','native file post disables redundant preview'),
        ('stale-caret','updated.selection.start.path[0].blockIndex += attachments.count','updated.selection.start.path[0].blockIndex += 0','text caret offsets remain unchanged'),
        ('retain-old-preview','if nagramiXHasAttachedMedia {','if false && nagramiXHasAttachedMedia {','attachment clears existing preview and query'),
        ('late-preview-return','guard $0.interfaceState.composeInputState.content.allMedia.isEmpty else { return $0.updatedUrlPreview(nil) }','_ = $0.interfaceState.composeInputState.content','late preview cannot return after attachment'),
    ]:
        assert code.count(old)==1,(name,code.count(old));yield name,code.replace(old,new,1),label
