"""Production draft/model/send helpers; adapters name the unavailable platform boundaries."""
from pathlib import Path
from validate_quick_format import block

UI = 'submodules/TelegramUI/Sources/'
MENU = UI + 'ChatControllerOpenAttachmentMenu.swift'
NODE = UI + 'ChatControllerNode.swift'
SCAN = UI + 'Chat/ChatControllerOpenDocumentScanner.swift'
RICH = 'submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextAttachmentScreen.swift'
CORE = 'submodules/TelegramCore/Sources/ChatInputContent/'
MODEL = CORE + 'ChatInputContentModel.swift'
ACCOUNT = 'submodules/AccountContext/Sources/ChatController.swift'
SEND = 'submodules/TextFormat/Sources/ChatComposerSendPlan.swift'
ROOT = Path(__file__).resolve().parents[1]


def without_imports(text):
    return '\n'.join(line for line in text.splitlines() if not line.startswith('import '))


def function(text, marker):
    """The function header may itself contain a default closure `{}`."""
    assert text.count(marker) == 1
    start = text.index(marker)
    brace = text.rindex('{', start, text.index('\n', start))
    depth = 1
    for index in range(brace + 1, len(text)):
        depth += (text[index] == '{') - (text[index] == '}')
        if depth == 0:
            return text[start:index + 1]
    raise AssertionError(marker)


def fixture(source):
    model = without_imports((source / MODEL).read_text())
    state = block((source / ACCOUNT).read_text(), 'public struct ChatTextInputState:')
    state = state[:state.index('    public init(from decoder:')] + '}\n'
    state = state.replace(': Codable, Equatable', ': Equatable', 1)
    production = [model, state]
    for name in ['ChatInputContentButton.swift', 'ChatInputContentRuns.swift', 'ChatInputContentReplaceRange.swift', 'ChatInputContentMedia.swift']:
        production.append(without_imports((source / (CORE + name)).read_text()))
    production.append(without_imports((source / SEND).read_text()))
    menu = (source / MENU).read_text()
    for name in ['nagramiXComposerFileDraft', 'nagramiXComposerCaptionFiles', 'nagramiXComposerSendContent', 'nagramiXComposerFileMessages']:
        production.append(block(menu, 'func ' + name + '('))
    attach = block(menu, '    func nagramiXAttachFilesToComposer(')
    alert = next(line for line in attach.splitlines() if 'self.present(textAlertController(' in line)
    assert attach.count(alert) == 1
    attach = attach.replace(alert, '            self.errors += 1')
    production.append('extension ChatControllerImpl {\n@discardableResult\n' + attach + '\n}')
    boundary = (ROOT / 'scripts/tests/NagramiXComposerFilesBoundary.swift').read_text()
    tests = (ROOT / 'scripts/tests/NagramiXComposerFilesTests.swift').read_text()
    return boundary + '\n' + '\n'.join(production) + '\n' + tests


def negatives(text):
    mutations = [
        ('flatten_draft', 'var updated = state', 'var updated = ChatTextInputState(inputText: state.inputText)', 'structure preserved'),
        ('omit_files', 'updated.content.blocks.append(.media(ChatInputMedia(media: file, kind: kind, naturalSize: size)))', '_ = (file, kind, size)', 'all files attached'),
        ('overwrite_changed_draft', 'guard state == initialState else', 'guard true else', 'stale caption rejected'),
        ('truncate_long_post', 'text.length <= maxCaptionLength', 'text.length >= 0 && maxCaptionLength >= 0', 'long caption stays rich'),
        ('extra_text_message', 'var messages: [EnqueueMessage] = []', 'var messages: [EnqueueMessage] = [.message(text: caption.string, attributes: [], inlineStickers: [:], mediaReference: nil, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: nil, bubbleUpEmojiOrStickersets: [])]', 'one file one post'),
        ('lose_caption', 'text: last ? (piece?.0.string ?? "") : ""', 'text: ""', 'caption retained'),
        ('lose_reply', 'replyToMessageId: replyTo', 'replyToMessageId: nil', 'reply retained'),
        ('reorder_media', 'guard !reachedFiles else', 'guard !reachedFiles || reachedFiles else', 'inline order stays rich'),
        ('flatten_loses_media', '    return draft.content\n}', '    _ = draft\n    return ChatTextInputState(inputText: fallbackText).content\n}', 'format removal retains files'),
    ]
    for name, old, new, diagnostic in mutations:
        assert text.count(old) == 1, (name, text.count(old))
        yield name, text.replace(old, new, 1), diagnostic
