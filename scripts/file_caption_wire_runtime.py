"""Настоящие пути caption send/edit и native trim; сеть/media/UI — явные IO-hosts."""
from pathlib import Path
from validate_quick_format import block
import file_caption_consistency_runtime as sends
import file_caption_edit_runtime as edits

ROOT = Path(__file__).resolve().parents[1]
T = 'submodules/TextFormat/Sources/ChatComposerSendPlan.swift'
M = sends.MENU
N = 'submodules/TelegramUI/Sources/ChatControllerNode.swift'
E = edits.EDIT
F = sends.FILE
ATTRS = 'submodules/TextFormat/Sources/ChatTextInputAttributes.swift'


def native_text(source, code):
    # The inherited fixtures identify these text functions as hosts.109 executes
    # the actual native trimming, splitting and Markdown conversion instead.
    text = (source / ATTRS).read_text()
    for name in ['trimChatInputText', 'breakChatInputText', 'convertMarkdownToAttributes']:
        marker = 'func ' + name + '('
        start = code.index(marker)
        if code[start-7:start] == 'public ':
            start -= 7
        old = block(code, marker)
        stop = code.index(old) + len(old)
        code = code[:start] + block(text, 'public ' + marker) + code[stop:]
    code += '\n' + block(text, 'private func trimRangesForChatInputText(') + '\n'
    code += '\n'.join(l for l in text.splitlines() if l.startswith(('private let markdownRegexFormat =', 'private let markdownRegex ='))) + '\n'
    code = code.replace('public var isVideo = false', 'public var isVideo = false\n    public var isAnimated = false, isSticker = false', 1)
    code = code.replace('result.isVideo = isVideo;', 'result.isVideo = isVideo; result.isAnimated = isAnimated; result.isSticker = isSticker;', 1)
    return code


def send_fixture(source):
    code = sends.fixture(source).split('@main struct FileCaptionChecks', 1)[0]
    code = native_text(source, code)
    node = (source / N).read_text()
    call = next(l.strip() for l in node.splitlines() if 'let nagramiXFileMessages: [EnqueueMessage] = nagramiXComposerFileMessages(' in l)
    code += '''
final class OrdinaryCaptionHost {
 let context = FixtureCaption.context
 let chatLocation = FixtureChatLocation()
 func send(_ files: [TelegramMediaFile], _ effectiveInputText: NSAttributedString) -> [EnqueueMessage] {
  let nagramiXCaptionFiles = files
  let inlineStickers: [MediaId: Media] = [:]
  let nagramiXReplySubject: EngineMessageReplySubject? = EngineMessageReplySubject(id:47)
''' + call + '''
  return nagramiXFileMessages
 }
}
'''
    return code + (ROOT / 'scripts/tests/NagramiXFileCaptionWireSendTests.swift').read_text()


def edit_fixture(source):
    code = edits.fixture(source).split('@main', 1)[0]
    code = native_text(source, code)
    code = code.replace('struct EditSource {let attributes:[MessageAttribute]}', 'struct EditSource {let attributes:[MessageAttribute];let media:[Media]}', 1)
    code = code.replace('originalRich:RichTextMessageAttribute?=nil)->EditPlan', 'originalRich:RichTextMessageAttribute?=nil,existingFile:TelegramMediaFile?=nil,captionAbove:Bool=false)->EditPlan', 1)
    code = code.replace('let message=EditSource(attributes:originalRich.map{[$0]} ?? [])', 'let message=EditSource(attributes:originalRich.map{[$0]} ?? [],media:existingFile.map{[$0]} ?? [])\n let invertedMediaAttribute:Int? = captionAbove ? 1:nil', 1)
    code = code.replace('struct EditPlan {', 'struct EditPlan {\n let text:NSAttributedString,entities:[MessageTextEntity]', 1)
    actual = next(l.strip() for l in (source / E).read_text().splitlines() if 'let entities = generateTextEntities(text.string, enabledTypes: .all, currentEntities: generateChatInputTextEntities(text))' in l)
    code = code.replace(' return EditPlan(rich:', ' ' + actual + '\n return EditPlan(text:text,entities:entities,rich:', 1)
    return code + (ROOT / 'scripts/tests/NagramiXFileCaptionWireEditTests.swift').read_text()


def geometry_fixture(source):
    # Retain the actual compact constants and text top-inset switch from98.
    # Source109's file switch also reads the actual pending caption selection.
    code = edits.geometry_fixture(source).split('@main enum FileEdges', 1)[0]
    code = code.replace('struct File {let isMusic:Bool}', '''struct File {
 let isMusic:Bool
 var isVoice=false,isInstantVideo=false,isVideo=false,isAnimated=false,isSticker=false
}
typealias TelegramMediaFile = File
struct CaptionMessage {let text:String}
struct PendingCaption {let text:String}
struct CaptionAttributes {let updatingMedia:PendingCaption?}
struct CaptionItem {let message:CaptionMessage,attributes:CaptionAttributes}
''', 1)
    # Both current and historical measure functions get the same IO data.
    code = code.replace('pixel:CGFloat)->(CGSize,CGFloat,CGFloat)', 'pixel:CGFloat,wire:String="",pending:String?=nil)->(CGSize,CGFloat,CGFloat)')
    code = code.replace(' let layoutConstants=constants(pixel),fileInsets=layoutConstants.file.bubbleInsets', ' let item=CaptionItem(message:CaptionMessage(text:wire),attributes:CaptionAttributes(updatingMedia:pending.map{PendingCaption(text:$0)}))\n _ = item\n let layoutConstants=constants(pixel),fileInsets=layoutConstants.file.bubbleInsets')
    code += '\n' + block((source / F).read_text(), 'private func nagramiXFileCaptionHasWireSpacing(') + '\n'
    return code + (ROOT / 'scripts/tests/NagramiXFileCaptionWireGeometryTests.swift').read_text()
