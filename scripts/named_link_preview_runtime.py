"""Real named-link/editor/send/transport decisions, explicit UI/storage edges."""
from pathlib import Path
from validate_quick_format import block
from original_video_mode_runtime import signal_library
from ghostgram_authorless_transport_runtime import fixture as authorless_fixture
from story_avatar_visibility_runtime import declaration

ROOT = Path(__file__).resolve().parents[1]
COPY = 'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift'
QUERY = 'submodules/TelegramUI/Sources/ChatInterfaceStateContextQueries.swift'
UPDATE = 'submodules/TelegramUI/Sources/Chat/UpdateChatPresentationInterfaceState.swift'
MENU = 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift'
NODE = 'submodules/TelegramUI/Sources/ChatControllerNode.swift'
SAVE = 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift'
EDIT = 'submodules/TelegramCore/Sources/PendingMessages/RequestEditMessage.swift'
ENTITIES = 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TextEntitiesMessageAttribute.swift'
ATTRS = 'submodules/TextFormat/Sources/ChatTextInputAttributes.swift'


def ui_fixture(source):
    query, update, menu, node, save, edit = [(source / n).read_text() for n in [QUERY, UPDATE, MENU, NODE, SAVE, EDIT]]
    entities = (source / ENTITIES).read_text()
    entity = block(entities, 'public struct MessageTextEntity:').replace('PostboxCoding, ', '', 1)
    for marker in ['    public init(decoder:', '    public func encode(_ encoder:']:
        entity = entity.replace(block(entity, marker), '', 1)
    parts = [signal_library(source), block(entities, 'public enum MessageTextEntityType:'), entity]
    attrs = (source / ATTRS).read_text()
    for marker in ['public struct ChatTextInputAttributes', 'public final class ChatTextInputTextUrlAttribute:']:
        parts.append(block(attrs, marker))
    parts.append((ROOT / 'scripts/tests/NagramiXNamedLinkBoundary.swift').read_text())
    parts += [block(query, 'func nagramiXHasNamedLink('), block(edit, 'public func nagramiXHasNamedLinkEntities('), block(query, 'struct UrlPreviewState {'), block(query, 'func urlPreviewStateForInputText(')]
    start = update.index('    let nagramiXHasAttachedMedia =')
    end = update.index('    if case let .customChatContents', start)
    parts.append('func prepareCompose(_ state: ChatPresentationInterfaceState, _ selfController: PreviewController) -> (ChatPresentationInterfaceState, Bool) {\nvar updatedChatPresentationInterfaceState=state\n' + update[start:end].replace('    var canHaveUrlPreview =', '    let canHaveUrlPreview =', 1) + '\nreturn (updatedChatPresentationInterfaceState, canHaveUrlPreview)\n}')
    start = update.index('    let nagramiXEditingNamedLink =')
    end = update.index('    if let (updatedEditingUrlPreviewState', start)
    parts.append('func prepareEdit(_ state: ChatPresentationInterfaceState, _ selfController: PreviewController) -> (ChatPresentationInterfaceState, NSAttributedString?) {\nvar updatedChatPresentationInterfaceState=state\n' + update[start:end] + '\nreturn (updatedChatPresentationInterfaceState, editingUrlPreviewText)\n}')
    for name, marker, finish in [
        ('lateCompose', '                    guard $0.interfaceState.composeInputState.content.allMedia.isEmpty', '                })'),
        ('lateEdit', '                    guard !nagramiXHasNamedLink($0.interfaceState.editMessage?', '                })'),
    ]:
        start = update.index(marker); end = update.index(finish, start)
        parts.append('func ' + name + '(_ state: ChatPresentationInterfaceState) -> ChatPresentationInterfaceState {\nlet result:(TelegramMediaWebpage?)->(TelegramMediaWebpage,String)? = {_ in (TelegramMediaWebpage(), "https://t.me/example")}\nlet apply:(ChatPresentationInterfaceState)->ChatPresentationInterfaceState = {\n' + update[start:end] + '\n}\nreturn apply(state)\n}')
    parts.append(block(menu, 'func updatedChatEditInterfaceMessageState('))
    # Exact send attribute branches in a small wrapper; peer/payment/enqueue UI
    # and the actual network are outside this focused decision regression.
    rich = block(node, '                    if !composeContent.allMedia.isEmpty || nagramiXDisableNamedLinkPreview {')
    plain = block(node, '                            if nagramiXDisableNamedLinkPreview || nagramiXHasNamedLinkEntities(entities) {')
    parts.append('final class SendAdapter {\nlet chatPresentationInterfaceState: ChatPresentationInterfaceState\ninit(_ state: ChatPresentationInterfaceState){chatPresentationInterfaceState=state}\nfunc attributes(_ input: NSAttributedString, entities: [MessageTextEntity], rich: Bool, attached: Bool) -> [MessageAttribute] {\nlet nagramiXDisableNamedLinkPreview=nagramiXHasNamedLink(input)\nlet composeContent=Content(allMedia:attached ? [1]:[])\nvar attributes:[MessageAttribute]=[]\nif rich {\n' + rich + '\n} else {\n' + plain + '\n}\nreturn attributes\n}\n}')
    start = save.index('                var disableUrlPreview = nagramiXHasNamedLink(')
    end = save.index('                var invertedMediaAttribute:', start)
    parts.append('final class SaveAdapter {\nlet presentationInterfaceState:ChatPresentationInterfaceState\ninit(_ s:ChatPresentationInterfaceState){presentationInterfaceState=s}\nfunc preview(_ editMessage: EditMessage) -> (Bool,TelegramMediaWebpage?,WebpagePreviewMessageAttribute?) {\nlet strongSelf=self\n' + save[start:end] + '\nreturn(disableUrlPreview,webpage,webpagePreviewAttribute)\n}\n}')
    start = edit.index('    let disableUrlPreview = disableUrlPreview || nagramiXHasNamedLinkEntities(')
    end = edit.index('    let uploadedMedia:', start)
    api_flag = block(edit, '                if disableUrlPreview {')
    parts.append('func normalizedEdit(media:RequestEditMessageMedia,entities:TextEntitiesMessageAttribute?,webpagePreviewAttribute:WebpagePreviewMessageAttribute?,disableUrlPreview:Bool) -> (Bool,RequestEditMessageMedia,WebpagePreviewMessageAttribute?,Int32) {\n' + edit[start:end] + '\nvar flags:Int32=0\n' + api_flag + '\nreturn(disableUrlPreview,nagramiXEditMedia,webpagePreviewAttribute,flags)\n}')
    parts.append((ROOT / 'scripts/tests/NagramiXNamedLinkTests.swift').read_text())
    return '\n'.join(parts)


def copy_fixture(source):
    # This imports the real full copy builder, common authorless planner,
    # recipient batch, staging code and native EnqueueMessage. Existing model
    # adapters are reused; the old test main (preview-preserving contract) is not.
    code = authorless_fixture(source)
    code = code[:code.index('\nimport Foundation\n\nprivate var checks = 0')]
    return code + '\n' + (ROOT / 'scripts/tests/NagramiXNamedLinkCopyTests.swift').read_text()
