#!/usr/bin/env python3
"""Проверить подготовку и окончательную отправку ответа на временное медиа.

Исполняются реальные enum/Core preflight, private Node helpers, весь send lease,
подпись rich source и группировка очереди. Scheduler/Postbox/UI/object resolver
ограничены адаптерами; доступность InstantPage API дополнительно проверяется
клиентом раздельных Core/Postbox модулей. Это не UIKit/Apple SDK или проверка доставки Telegram.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile

from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
NODE = 'submodules/TelegramUI/Sources/ChatControllerNode.swift'
LOAD = 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift'
HELPER = 'submodules/TelegramUI/Sources/Chat/NagramiXTemporaryReplySend.swift'
CORE = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXLocalMessageData.swift'
ENQUEUE = 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift'
COPY = 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift'
RESOURCE = 'submodules/TelegramCore/Sources/TelegramEngine/Resources/NagramiXResourceAccess.swift'
OBJECTS = 'submodules/TelegramUI/Sources/Chat/NagramiXCopyDelivery.swift'
PAGE = 'submodules/TelegramCore/Sources/SyncCore/SyncCore_InstantPage.swift'
ENGINE_MEDIA = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Media.swift'
RICH_ATTRIBUTE = 'submodules/TelegramCore/Sources/SyncCore/SyncCore_RichTextMessageAttribute.swift'
TEXT_ATTRIBUTE = 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TextEntitiesMessageAttribute.swift'
POSTBOX_MESSAGE = 'submodules/Postbox/Sources/Message.swift'
ENGINE_ALIAS = 'submodules/TelegramCore/Sources/TelegramEngine/Utils/EnginePostboxCoding.swift'
RICH_TEXT = 'submodules/TelegramCore/Sources/SyncCore/SyncCore_RichText.swift'


def clean(text):
    return '\n'.join(line for line in text.splitlines() if not line.startswith(('import ', 'internal import '))).replace('public ', '')


def function_block(text, marker):
    assert text.count(marker) == 1, marker
    start = text.index(marker)
    parenthesis = text.index('(', start)
    depth = 1
    end = parenthesis + 1
    while depth:
        if text[end] == '(': depth += 1
        elif text[end] == ')': depth -= 1
        end += 1
    opening = text.index('{', end)
    depth = 1
    end = opening + 1
    while depth:
        if text[end] == '{': depth += 1
        elif text[end] == '}': depth -= 1
        end += 1
    return text[start:end]


def read(source, name, support):
    path = source / name
    if not path.is_file() and support is not None:
        path = support / name
    assert path.is_file(), path
    return path.read_text()


def instant_page_surface(texts):
    """Keep native fields, access levels and both factory bodies verbatim.

    Coding/equality conformances and their unrelated implementations are outside
    this adapter. In particular the raw storage/factory stay internal.
    """
    text = texts[PAGE]
    start = text.index('public final class InstantPage: PostboxCoding, Equatable {')
    end = text.index('    public init(decoder:', start)
    surface = text[start:end].replace(': PostboxCoding, Equatable {', ' {', 1) + '}\n'
    assert '    let rawMedia: [MediaId: Media]' in surface
    assert '    public let media: [EngineMedia.Id: EngineMedia]' in surface
    assert '    public convenience init(blocks: [InstantPageBlock], media: [EngineMedia.Id: EngineMedia]' in surface
    assert '    init(blocks: [InstantPageBlock], rawMedia: [MediaId: Media]' in surface
    return surface


def check_native_public_fields(text, fields):
    for field in fields:
        assert field in text, 'Adapter API missing from native declarations: ' + field


def module_boundary(texts, swiftc, folder):
    """Compile the exact UI helper as a client of separate Core/Postbox modules.

    This checks actual access control, not merely Swift grammar in a single
    combined fixture. Only the unrelated constructors/implementations of boundary
    types are bounded; no internal native member is promoted to public.
    """
    folder.mkdir(exist_ok=True)
    check_native_public_fields(texts[POSTBOX_MESSAGE], (
        'public let peerId: PeerId',
        'public let text: String', 'public let attributes: [MessageAttribute]',
        'public func withUpdatedText(_ text: String) -> Message',
        'public func withUpdatedAttributes(_ attributes: [MessageAttribute]) -> Message',
    ))
    check_native_public_fields(texts[TEXT_ATTRIBUTE], (
        'public var range: Range<Int>', 'public var type: MessageTextEntityType',
        'public init(range: Range<Int>, type: MessageTextEntityType)',
        'public let entities: [MessageTextEntity]',
        'public init(entities: [MessageTextEntity])',
    ))
    check_native_public_fields(texts[RICH_ATTRIBUTE], (
        'public let instantPage: InstantPage', 'public var fullInstantPage: InstantPage?',
        'public init(instantPage: InstantPage, fullInstantPage: InstantPage?)',
    ))
    check_native_public_fields(texts[ENGINE_MEDIA], (
        'public typealias Id = MediaId', 'case custom(EngineCustomMedia)',
        '    init(_ media: Media)', '    func _asMedia() -> Media',
    ))
    assert 'public typealias EngineRawMessage = Message' in texts[ENGINE_ALIAS]
    assert 'case Bold' in texts[TEXT_ATTRIBUTE]
    assert 'case paragraph(RichText)' in texts[PAGE]
    assert 'case plain(String)' in texts[RICH_TEXT]
    postbox = '''
public typealias MediaId = Int64
public protocol Media {}
public protocol MessageAttribute {}
public struct PeerId: Equatable {}
public struct MessageId { public let peerId: PeerId }
public struct StoryId {}
public struct ItemCollectionId {}
public final class Message {
    public let text: String
    public let attributes: [MessageAttribute]
    init(text: String, attributes: [MessageAttribute]) { self.text = text; self.attributes = attributes }
    public func withUpdatedText(_ text: String) -> Message { Message(text: text, attributes: self.attributes) }
    public func withUpdatedAttributes(_ attributes: [MessageAttribute]) -> Message { Message(text: self.text, attributes: attributes) }
}
'''
    core = '''
import Postbox
public typealias EngineRawMessage = Message
public protocol EngineCustomMedia: Media {}
public enum EngineMedia {
    public typealias Id = MediaId
    case custom(EngineCustomMedia)
    init(_ media: Media) { self = .custom(media as! EngineCustomMedia) }
    func _asMedia() -> Media { switch self { case let .custom(value): return value } }
}
public enum RichText { case plain(String) }
public enum InstantPageBlock { case paragraph(RichText) }
public enum MessageTextEntityType { case Bold }
public struct MessageTextEntity {
    public var range: Range<Int>
    public var type: MessageTextEntityType
    public init(range: Range<Int>, type: MessageTextEntityType) { self.range = range; self.type = type }
}
public final class TextEntitiesMessageAttribute: MessageAttribute {
    public let entities: [MessageTextEntity]
    public init(entities: [MessageTextEntity]) { self.entities = entities }
}
public final class RichTextMessageAttribute: MessageAttribute {
    public let instantPage: InstantPage
    public var fullInstantPage: InstantPage?
    public init(instantPage: InstantPage, fullInstantPage: InstantPage?) { self.instantPage = instantPage; self.fullInstantPage = fullInstantPage }
}
''' + instant_page_surface(texts)
    # The UI helper only sees public Core declarations. Enqueue cases retain
    # native associated labels/types; unused payload implementations are bounded.
    assert 'public struct EngineMessageReplySubject:' in texts[ENQUEUE]
    assert 'public final class NagramiXArchivedMediaCopy {' in texts[COPY]
    grouping = block(texts[ENQUEUE], 'public enum EnqueueMessageGrouping {')
    start = texts[ENQUEUE].index('public enum EnqueueMessage {')
    end = texts[ENQUEUE].index('    public func withUpdatedReplyToMessageId(', start)
    native_cases = texts[ENQUEUE][start:end] + '\n}\n'
    core += '''
public enum AnyMediaReference {}
public struct EngineMessageReplySubject {}
public final class NagramiXArchivedMediaCopy {
    private var committed = false
''' + block(texts[COPY], '    public func commit(') + '\n}\n' + grouping + '\n' + native_cases
    postbox_path = folder/'Postbox.swift'; postbox_path.write_text(postbox)
    core_path = folder/'TelegramCore.swift'; core_path.write_text(core)
    for name, path in (('Postbox', postbox_path), ('TelegramCore', core_path)):
        compiled = subprocess.run([str(swiftc), '-warnings-as-errors', '-emit-module', '-module-name', name,
                                   '-I', str(folder), '-module-cache-path', str(folder/'cache'), str(path),
                                   '-emit-module-path', str(folder/(name+'.swiftmodule'))], capture_output=True, text=True)
        assert compiled.returncode == 0, compiled.stderr
    helper = texts[HELPER]
    assert re.search(r'(?m)^.*\bimport\s+Postbox\b', helper) is None, 'New UI helper must not directly import Postbox'
    sources = {
        'public-surface': (helper, None),
        'old-internal-storage': (helper.replace('media: page.media', 'rawMedia: page.rawMedia', 1), "'rawMedia' is inaccessible due to 'internal' protection level"),
        'old-internal-factory': (helper.replace('media: page.media', 'rawMedia: [:]', 1), 'incorrect argument label in call'),
    }
    assert sources['old-internal-storage'][0] != helper and sources['old-internal-factory'][0] != helper
    for name, (content, diagnostic) in sources.items():
        path = folder/(name+'.swift'); path.write_text(content)
        checked = subprocess.run([str(swiftc), '-warnings-as-errors', '-typecheck', '-I', str(folder),
                                  '-module-cache-path', str(folder/'cache'), str(path)], capture_output=True, text=True)
        if diagnostic is None:
            assert checked.returncode == 0, checked.stderr
        else:
            assert checked.returncode != 0 and diagnostic in checked.stderr, (name, checked.returncode, checked.stderr)
        (folder/(name+'.diagnostics.txt')).write_text(checked.stderr)
    return {'full_exact_ui_helper_typecheck': 'passed without direct Postbox import', 'old_internal_api_compiler_rejections': 2,
            'native_instant_page_surface_sha256': hashlib.sha256(instant_page_surface(texts).encode()).hexdigest(),
            'scope': 'exact full helper imports public TelegramCore API backed by a separate Postbox module; native InstantPage fields/factories and Enqueue cases; bounded other implementations'}


def verify(source, support, baseline):
    texts = {n: read(source, n, support) for n in (NODE, LOAD, HELPER, CORE, ENQUEUE, COPY, RESOURCE, OBJECTS)}
    for name in (PAGE, ENGINE_MEDIA, RICH_ATTRIBUTE, TEXT_ATTRIBUTE, POSTBOX_MESSAGE, ENGINE_ALIAS, RICH_TEXT):
        texts[name] = read(source, name, support or baseline)
    node, load = texts[NODE], texts[LOAD]
    assert 'convenience init(account: Account)' in texts[RESOURCE]
    assert 'self.init(mediaBox: account.postbox.mediaBox)' in texts[RESOURCE]
    assert 'public func commit() {\n        self.committed = true\n    }' in texts[COPY]
    assert 'func nagramiXResolveTemporaryReply(messageId: EngineMessage.Id, expectedTemporary: Bool = false)' in texts[CORE]
    for declaration in (
        'case message(text: String, attributes: [MessageAttribute], inlineStickers: [MediaId: Media], mediaReference: AnyMediaReference?, threadId: Int64?, replyToMessageId: EngineMessageReplySubject?, replyToStoryId: StoryId?, localGroupingKey: Int64?, correlationId: Int64?, bubbleUpEmojiOrStickersets: [ItemCollectionId])',
        'case forward(source: MessageId, threadId: Int64?, grouping: EnqueueMessageGrouping, attributes: [MessageAttribute], correlationId: Int64?)',
    ):
        assert declaration in texts[ENQUEUE], declaration
    assert 'rawMedia:' not in texts[HELPER] and '.rawMedia' not in texts[HELPER], 'UI helper may only use public InstantPage media API'
    assert re.search(r'(?m)^.*\bimport\s+Postbox\b', texts[HELPER]) is None, 'New UI helper must not directly import Postbox'
    send = function_block(node, '    func sendCurrentMessage(')
    assert 'if self.nagramiXPrepareTemporaryReplySend(' in send
    assert 'let nagramiXReplySubject = nagramiXTemporaryReplySource == nil ? self.chatPresentationInterfaceState.interfaceState.replyMessageSubject?.subjectModel : nil' in send
    assert 'if nagramiXTemporaryReplySource == nil, let replyMessageSubject' in send
    assert 'let signed = (nagramiXResolvedTemporaryReplyObjects ?? [source]).map' in send
    assert 'nagramiXCopyMessagesAsNew(signed, account: self.context.account, forceLocalMedia: true, accountPeerId: self.context.account.peerId, mediaCopy: staging)' in send
    assert 'messages = copies.map { $0.withUpdatedThreadId(self.chatLocation.threadId).withUpdatedReplyToMessageId(nil) } + messages.map { $0.withUpdatedReplyToMessageId(nil) }' in send
    assert 'source.id == self.chatPresentationInterfaceState.interfaceState.replyMessageSubject?.messageId' in send
    assert 'nagramiXTemporaryReplyRetried: true' in send
    assert 'nagramiXTemporaryReplyStaging?.commit()' not in send
    assert node.count('func nagramiXTakeTemporaryReplySend(') == 1
    assert 'let temporaryReplySend = self?.chatDisplayNode.nagramiXTakeTemporaryReplySend(messages)' in load
    queue = block(load, '                    let performEnqueue: () -> Void =')
    assert 'if forwardSourcePeerIds.count > 1 && temporaryReplySend?.includesLocalCopy == true' in queue
    assert 'nagramiXTemporaryReplyEnqueueGroups(transformedMessages)' in queue
    assert 'if let temporaryReplySend {\n                        temporaryReplySend.beforeEnqueue { allowed in\n                            guard allowed else { return }\n                            performEnqueue()' in load
    assert 'guard temporaryReplySend == nil else { return }' in load
    assert 'self?.controller?.presentPaidMessageAlertIfNeeded(count: count, completion: confirmation)' in send
    assert 'nagramiXTemporaryReplySource != nil)' in send
    # The ordinary media upload/parser/object resolver paths are not reimplemented
    # here: they must remain the established implementation from checkpoint08.
    if baseline is not None:
        for name in (OBJECTS,):
            actual = read(source, name, support)
            assert actual == (baseline/name).read_text(), 'Object resolver changed outside this task: '+name
        old_load = (baseline/LOAD).read_text()
        for marker in ('if forwardSourcePeerIds.count > 1 {',):
            old = block(old_load, '                '+marker)
            current = block(load, '                        } else '+marker)
            # The new local-copy branch is before this ordinary branch. Ignore
            # whitespace and the equivalent leading else introduced by wrapping.
            current = current[current.index(marker):]
            assert ''.join(old.split()) == ''.join(current.split()), 'Native ordinary multi-source forward branch changed'
    return texts


def fixture(texts):
    node = texts[NODE]
    enum = clean(block(texts[CORE], 'public enum NagramiXTemporaryReplyResolution {'))
    resolve = clean(block(texts[CORE], '    func nagramiXResolveTemporaryReply('))
    enqueue = texts[ENQUEUE]
    start = enqueue.index('public enum EnqueueMessage {')
    end = enqueue.index('    public func withUpdatedReplyToMessageId(', start)
    cases = clean(enqueue[start:end])
    methods = '\n'.join(clean(block(enqueue, marker)) for marker in (
        '    public func withUpdatedReplyToMessageId(', '    public func withUpdatedThreadId(', '    public func withUpdatedCorrelationId('))
    full_enqueue = cases + methods + '\n}\n'
    helper = clean(texts[HELPER])
    native_commit = clean(block(texts[COPY], '    public func commit('))
    native_rollback = block(texts[COPY], '    deinit {').replace('deinit {', 'deinit {\n        defer { if self.committed { self.probe.commits += 1 } else { self.probe.rollbacks += 1 } }', 1)
    functions = '\n'.join(block(node, marker).replace('private ', '', 1) for marker in (
        '    private func nagramiXPrepareTemporaryReplySend(',
        '    private func nagramiXMakeTemporaryReplySend(',
        '    func nagramiXTakeTemporaryReplySend(',
    ))
    fee_line = next(line for line in node.splitlines() if 'guard (!nagramiXForwardPaymentRequired && nagramiXResolvedTemporaryReply == nil)' in line)
    submit = block(node, 'private func nagramiXSubmitComposerForwardMessages(').replace('private ', '', 1)
    return ADAPTERS.replace('// NATIVE_COMMIT', native_commit).replace('// NATIVE_ROLLBACK', native_rollback).replace('// NATIVE_INSTANT_PAGE', clean(instant_page_surface(texts))) + '\n' + enum + '\nextension TelegramEngine.Messages {\n' + resolve + '\n}\n' + full_enqueue + helper + '\n' + submit + '\n' + NODE_HEADER + functions + FEE_TEST_METHOD.replace('// FEE_GUARD', fee_line) + '\n}\n' + TESTS


ADAPTERS = r'''
import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
struct MessageId: Hashable { let peerId: Int64; let id: Int32 }
typealias MediaId = Int64
typealias StoryId = Int64
typealias ItemCollectionId = Int64
struct EngineMessageReplySubject: Equatable { let messageId: MessageId }
enum EngineMessage { typealias Id = MessageId }
enum EnqueueMessageGrouping { case none, auto }
protocol MessageAttribute {}
protocol Media {}
final class TelegramMediaExpiredContent: Media {}
final class Payload: Media { let bytes: Data; init(_ bytes: Data) { self.bytes=bytes } }
struct AnyMediaReference { let media: Media }
enum RichText: Equatable { case plain(String) }
enum InstantPageBlock: Equatable { case paragraph(RichText) }
protocol EngineCustomMedia: Media {}
extension Payload: EngineCustomMedia {}
enum EngineMedia {
    typealias Id = MediaId
    case custom(EngineCustomMedia)
    init(_ media: Media) { self = .custom(media as! EngineCustomMedia) }
    func _asMedia() -> Media { switch self { case let .custom(value): return value } }
}
// NATIVE_INSTANT_PAGE
func mediaPayload(_ media:EngineMedia?)->Payload?{guard case let .custom(value)?=media else{return nil};return value as? Payload}
struct MessageTextEntity: Equatable { enum Kind: Equatable { case bold, italic }; let range: Range<Int>; let type: Kind }
final class TextEntitiesMessageAttribute: MessageAttribute { let entities:[MessageTextEntity];init(entities:[MessageTextEntity]){self.entities=entities} }
final class RichTextMessageAttribute: MessageAttribute { let instantPage:InstantPage;let fullInstantPage:InstantPage?;init(instantPage:InstantPage,fullInstantPage:InstantPage?){self.instantPage=instantPage;self.fullInstantPage=fullInstantPage} }
final class OtherAttribute: MessageAttribute { let token:String;init(_ token:String){self.token=token} }
final class Message {
    let id:MessageId;let text:String;let media:[Media];let attributes:[MessageAttribute];let temporary:Bool;let approved:Bool
    init(_ id:MessageId,text:String="voice",media:[Media]=[],attributes:[MessageAttribute]=[],temporary:Bool=true,approved:Bool=true){self.id=id;self.text=text;self.media=media;self.attributes=attributes;self.temporary=temporary;self.approved=approved}
    func withUpdatedText(_ text:String)->Message{Message(id,text:text,media:media,attributes:attributes,temporary:temporary,approved:approved)}
    func withUpdatedAttributes(_ attributes:[MessageAttribute])->Message{Message(id,text:text,media:media,attributes:attributes,temporary:temporary,approved:approved)}
}
typealias EngineRawMessage = Message
var tempEnabled=true
func nagramiXTemporaryMessagesEnabled()->Bool{tempEnabled}
func nagramiXIsTemporaryMessage(_ message:Message)->Bool{message.temporary}
func nagramiXCanRetainTemporaryMessage(_ message:Message)->Bool{message.approved && message.temporary}
func nagramiXCanUseTemporaryMediaActions(_ message:Message)->Bool{tempEnabled && nagramiXCanRetainTemporaryMessage(message)}
enum NoError: Error {}
final class Disposable {}
final class Signal<T,E:Error>{
    let subscribe:(@escaping(T)->Void)->Void
    init(_ subscribe:@escaping(@escaping(T)->Void)->Void){self.subscribe=subscribe}
    @discardableResult func startStandalone(next:@escaping(T)->Void)->Disposable{subscribe(next);return Disposable()}
}
infix operator |> : AdditionPrecedence
func |> <T,U>(value:T, f:(T)->U)->U{f(value)}
func take<T,E>(_ count:Int)->(Signal<T,E>)->Signal<T,E>{ { signal in Signal { next in var remaining=count;signal.subscribe { value in if remaining>0 {remaining-=1;next(value)} } } } }
func deliverOnMainQueue<T,E>(_ signal:Signal<T,E>)->Signal<T,E>{signal}
final class Transaction { let owner:Postbox;init(_ owner:Postbox){self.owner=owner};func getMessage(_ id:MessageId)->Message?{owner.reads+=1;return owner.live[id]} }
final class Postbox {
    var live:[MessageId:Message]=[:];var archive:NagramiXMessageArchive?=NagramiXMessageArchive();var pending:[()->Void]=[];var deferred=true;var reads=0
    func transaction<T>(_ f:@escaping(Transaction)->T)->Signal<T,NoError>{Signal { next in let run={next(f(Transaction(self)))};if self.deferred {self.pending.append(run)}else{run()} } }
    func flush(){let next=pending.removeFirst();next()}
}
final class NagramiXMessageArchive {
    var retained:[MessageId:Message]=[:];var lookups=0
    static func forPostbox(_ postbox:Postbox)->NagramiXMessageArchive?{postbox.archive}
    func temporaryInteractionMessage(id:MessageId,liveMessage:Message?)->Message?{lookups+=1;return retained[id]}
}
final class Account { let postbox=Postbox() }
final class TelegramEngine {final class Messages {let account:Account;init(_ a:Account){account=a}};let messages:Messages;init(_ a:Account){messages=Messages(a)} }
final class Context {let account:Account;let engine:TelegramEngine;init(){account=Account();engine=TelegramEngine(account)} }
struct ChatLocation:Equatable{var peerId:Int64?;var threadId:Int64?}
struct InputState:Equatable{var text:String="draft";var generation:Int=0}
struct ChatInterfaceState:Equatable{
    struct ReplyMessageSubject:Equatable{var messageId:MessageId}
    var editMessage:Int?=nil;var replyMessageSubject:ReplyMessageSubject?=ReplyMessageSubject(messageId:MessageId(peerId:10,id:1));var token:Int=0
}
struct PresentationState{var interfaceState=ChatInterfaceState();var replyMessage:Message?=nil;var sendPaidMessageStars:Int?=nil}
final class ChatTextInputPanelNode{var inputTextState=InputState()}
final class Interaction{var alerts=0;func presentController(_ value:Int,_ other:Int?){alerts+=1}}
func nagramiXArchivedCopyAlert(context:Context)->Int{1}
final class Controller{
    var objectCallbacks:[([Message]?)->Void]=[];var richCallbacks:[([Message])->Void]=[];var objectCalls:[[Message]]=[]
    func nagramiXResolveCopyObjects(messages:[Message],completion:@escaping([Message]?)->Void){objectCalls.append(messages);objectCallbacks.append(completion)}
    func nagramiXPrepareRichTextCopy(messages:[Message],completion:@escaping([Message])->Void){richCallbacks.append(completion)}
}
final class LeaseProbe{var commits=0;var rollbacks=0}
final class NagramiXArchivedMediaCopy{
    private var committed=false
    let path:String;let paths:[String];let probe:LeaseProbe
    init(_ path:String,_ probe:LeaseProbe){self.path=path;self.paths=[path];self.probe=probe;try! Data([1,2,3]).write(to:URL(fileURLWithPath:path))}
    // NATIVE_COMMIT
    func committedForTest()->Bool{committed}
    // NATIVE_ROLLBACK
}
'''

NODE_HEADER = '''
final class Node {
    let context:Context
    var inputPanelNode:AnyObject?=ChatTextInputPanelNode()
    var textInputPanelNode:ChatTextInputPanelNode?{inputPanelNode as? ChatTextInputPanelNode}
    var chatPresentationInterfaceState=PresentationState()
    var chatLocation=ChatLocation(peerId:20,threadId:3)
    weak var controller:Controller?
    var interfaceInteraction:Interaction?=Interaction()
    var nagramiXResolvingTemporaryReplySend=false
    var nagramiXTemporaryReplyGeneration:UInt64=0
    var nagramiXPendingTemporaryReplySend:NagramiXTemporaryReplySend?
    init(_ context:Context){self.context=context}
'''

FEE_TEST_METHOD = '''
    func feeGuard(required:Bool,resolved:NagramiXTemporaryReplyResolution?,state:ChatInterfaceState,location:ChatLocation,fee:Int?)->Bool{
        let nagramiXForwardPaymentRequired=required
        let nagramiXResolvedTemporaryReply=resolved
        let nagramiXPreparedForwardState=state
        let nagramiXPreparedForwardLocation=location
        let nagramiXPreparedForwardFee=fee
        var permitted=false
        let run={ [self] in
            // FEE_GUARD
            permitted=true
        }
        run();return permitted
    }
'''

TESTS = r'''
var checks=0
func check(_ condition:@autoclosure()->Bool,_ label:String){guard condition()else{FileHandle.standardError.write(Data(("TEMP SEND REGRESSION: "+label+"\n").utf8));exit(91)};checks+=1}
let tempRoot=CommandLine.arguments[1]
let id=MessageId(peerId:10,id:1), otherId=MessageId(peerId:10,id:2)
let bytes=Data([0,1,2,255,8,9]), payload=Payload(Data([0,1,2,255,8,9]))
func message(_ text:String="voice",id:MessageId=id,approved:Bool=true,media:[Media]?=nil,attributes:[MessageAttribute]=[])->Message{Message(id,text:text,media:media ?? [payload],attributes:attributes,approved:approved)}
func isNative(_ value:NagramiXTemporaryReplyResolution)->Bool{if case .native=value{return true};return false}
func isUnavailable(_ value:NagramiXTemporaryReplyResolution)->Bool{if case .unavailable=value{return true};return false}
func enqueue(_ text:String,_ marker:Int64?=nil,_ group:Int64?=nil)->EnqueueMessage{.message(text:text,attributes:[OtherAttribute("native-attr")],inlineStickers:[5:payload],mediaReference:AnyMediaReference(media:payload),threadId:3,replyToMessageId:EngineMessageReplySubject(messageId:id),replyToStoryId:8,localGroupingKey:group,correlationId:marker,bubbleUpEmojiOrStickersets:[9])}
func token(_ message:EnqueueMessage)->String{switch message{case let .message(text,_,_,_,_,_,_,_,_,_):return text;case let .forward(source,_,_,_,_):return "f\(source.peerId):\(source.id)"}}
func resolve(_ context:Context,expected:Bool)->NagramiXTemporaryReplyResolution{var result:NagramiXTemporaryReplyResolution?;context.engine.messages.nagramiXResolveTemporaryReply(messageId:id,expectedTemporary:expected).startStandalone{result=$0};context.account.postbox.flush();return result!}
let c=Context(),box=c.account.postbox
let live=message();box.live[id]=live
check(isNative(resolve(c,expected:true)),"live target retains native reply")
tempEnabled=false
check(isNative(resolve(c,expected:true)),"live target stays native after TEMP OFF")
box.live.removeAll()
check(isUnavailable(resolve(c,expected:true)),"OFF missing temporary source cannot be invented")
check(isNative(resolve(c,expected:false)),"ordinary missing target preserves native behavior")
tempEnabled=true
let retained=message("retained");box.archive!.retained[id]=retained
if case let .copy(copy)=resolve(c,expected:true){check(copy === retained,"approved retained source actual identity")}else{check(false,"approved retained source actual identity")}
box.live[id]=message(media:[TelegramMediaExpiredContent()])
if case let .copy(copy)=resolve(c,expected:true){check(copy === retained,"expired placeholder resolves retained attachment")}else{check(false,"expired placeholder resolves retained attachment")}
box.archive!.retained[id]=message(approved:false)
check(isUnavailable(resolve(c,expected:true)),"unapproved retained source cannot send")
box.archive!.retained[id]=message(media:[TelegramMediaExpiredContent()])
check(isUnavailable(resolve(c,expected:true)),"expired retained placeholder cannot replace file")
box.archive=nil
check(isUnavailable(resolve(c,expected:true)),"missing archive refuses temporary source")
check(box.reads==9,"preflight only reads one snapshot per request")

// Initial preparation observes current draft/input/recipient/topic and only one lookup.
let nctx=Context(),node=Node(nctx),controller=Controller();node.controller=controller
nctx.account.postbox.live[id]=message();node.chatPresentationInterfaceState.replyMessage=message()
var resolutions=0
let done:(NagramiXTemporaryReplyResolution,[Message]?,Bool)->Void={_,_,_ in resolutions+=1}
check(node.nagramiXPrepareTemporaryReplySend(nagramiXResolvedTemporaryReply:nil,nagramiXResolvedTemporaryReplyObjects:nil,nagramiXExpectedTemporaryReply:false,completion:done),"preflight intercepts reply send")
check(node.nagramiXPrepareTemporaryReplySend(nagramiXResolvedTemporaryReply:nil,nagramiXResolvedTemporaryReplyObjects:nil,nagramiXExpectedTemporaryReply:false,completion:done) && nctx.account.postbox.pending.count==1,"double tap performs one initial lookup")
nctx.account.postbox.flush();check(resolutions==1 && !node.nagramiXResolvingTemporaryReplySend,"unchanged native draft proceeds once")
for mode in 0..<4{
    check(node.nagramiXPrepareTemporaryReplySend(nagramiXResolvedTemporaryReply:nil,nagramiXResolvedTemporaryReplyObjects:nil,nagramiXExpectedTemporaryReply:false,completion:done),"initial draft captured")
    if mode==0{node.chatPresentationInterfaceState.interfaceState.token+=1}
    if mode==1{node.textInputPanelNode!.inputTextState.generation+=1}
    if mode==2{node.chatLocation.peerId=99}
    if mode==3{node.chatLocation.threadId=44}
    nctx.account.postbox.flush()
    check(resolutions==1,"stale initial draft input recipient or topic cannot continue")
}
node.chatLocation=ChatLocation(peerId:20,threadId:3)
check(node.nagramiXPrepareTemporaryReplySend(nagramiXResolvedTemporaryReply:.native,nagramiXResolvedTemporaryReplyObjects:nil,nagramiXExpectedTemporaryReply:true,completion:done)==false,"already resolved native source bypasses async preparation")
node.chatPresentationInterfaceState.interfaceState.editMessage=1
check(!node.nagramiXPrepareTemporaryReplySend(nagramiXResolvedTemporaryReply:nil,nagramiXResolvedTemporaryReplyObjects:nil,nagramiXExpectedTemporaryReply:false,completion:done),"ordinary edit is not converted into retained send")
node.chatPresentationInterfaceState.interfaceState.editMessage=nil

// Resolver completion is an engine boundary: fixed dice image/card retain source ID.
let source=message("dice")
for value in ["fixed dice image","source object card"]{
    var objects:[Message]?=nil
    check(node.nagramiXPrepareTemporaryReplySend(nagramiXResolvedTemporaryReply:.copy(source),nagramiXResolvedTemporaryReplyObjects:nil,nagramiXExpectedTemporaryReply:true,completion:{_,result,_ in objects=result}),"retained special object invokes common resolver")
    let transformed=message(value);controller.objectCallbacks.removeFirst()([transformed])
    check(objects?.first === transformed,"resolved image or card is used instead of raw unsupported source")
}
var objectsCalls=0
_ = node.nagramiXPrepareTemporaryReplySend(nagramiXResolvedTemporaryReply:.copy(source),nagramiXResolvedTemporaryReplyObjects:nil,nagramiXExpectedTemporaryReply:true,completion:{_,_,_ in objectsCalls+=1})
node.chatLocation.threadId=45;controller.objectCallbacks.removeFirst()([message("late card")]);check(objectsCalls==0,"late object callback cannot send into new topic")
node.chatLocation.threadId=3
let alerts=node.interfaceInteraction!.alerts
_ = node.nagramiXPrepareTemporaryReplySend(nagramiXResolvedTemporaryReply:.copy(source),nagramiXResolvedTemporaryReplyObjects:nil,nagramiXExpectedTemporaryReply:true,completion:{_,_,_ in objectsCalls+=1})
controller.objectCallbacks.removeFirst()([message(id:otherId)])
check(objectsCalls==0 && node.interfaceInteraction!.alerts==alerts+1,"resolver cannot switch source identity")
let partialPage=InstantPage(blocks:[.paragraph(.plain("preview"))],media:[7:.custom(payload)],isComplete:false,rtl:true,url:"source",views:5)
let partial=message("rich",attributes:[RichTextMessageAttribute(instantPage:partialPage,fullInstantPage:nil)])
var rich:[Message]?=nil
check(node.nagramiXPrepareTemporaryReplySend(nagramiXResolvedTemporaryReply:.copy(source),nagramiXResolvedTemporaryReplyObjects:[partial],nagramiXExpectedTemporaryReply:true,completion:{_,result,_ in rich=result}),"partial rich source requires full page")
let page=InstantPage(blocks:[.paragraph(.plain("full"))],media:[7:.custom(payload)],isComplete:true,rtl:true,url:"source",views:5)
let full=message("rich",attributes:[RichTextMessageAttribute(instantPage:page,fullInstantPage:nil)])
controller.richCallbacks.removeFirst()([full]);check(rich?.first === full,"full rich object completes preparation")

// Attribution moves UTF16 entities and retains all rich blocks/media.
let entity=MessageTextEntity(range:0..<2,type:.bold)
let signed=nagramiXTemporaryReplySignedSource(message("😀 voice",attributes:[TextEntitiesMessageAttribute(entities:[entity]),RichTextMessageAttribute(instantPage:page,fullInstantPage:nil)]),authorName:"Å😀")
let shifted=signed.attributes.compactMap{$0 as? TextEntitiesMessageAttribute}.first!.entities
check(signed.text=="Å😀:\n😀 voice" && shifted[0].range==5..<7,"author prefix shifts source UTF16 entities correctly")
let signedPage=signed.attributes.compactMap{$0 as? RichTextMessageAttribute}.first!.instantPage
check(signedPage.blocks==[.paragraph(.plain("Å😀:"))]+page.blocks && mediaPayload(signedPage.media[7]) === payload && signedPage.isComplete && signedPage.rtl && mediaPayload(signedPage.media[7])?.bytes == bytes,"rich attribution preserves all blocks and media")

// Actual batching keeps comments and the whole copied album around mixed forwards.
let f1:EnqueueMessage = .forward(source:MessageId(peerId:1,id:1),threadId:3,grouping:.auto,attributes:[],correlationId:nil)
let f2:EnqueueMessage = .forward(source:MessageId(peerId:1,id:2),threadId:3,grouping:.auto,attributes:[],correlationId:nil)
let f3:EnqueueMessage = .forward(source:MessageId(peerId:2,id:3),threadId:3,grouping:.auto,attributes:[],correlationId:77)
let messages=[enqueue("copy caption",44,99),enqueue("copy media",nil,99),enqueue("user comment"),f1,f2,f3,enqueue("trailing")]
let groups=nagramiXTemporaryReplyEnqueueGroups(messages)
check(groups.map{$0.count}==[3,2,1,1],"mixed forward grouping preserves contiguous copied album and comment")
check(groups.flatMap{$0}.map(token)==messages.map(token),"queue grouping never drops or reorders any native payload")
if case let .message(_,attrs,stickers,ref,thread,reply,story,group,corr,up)=groups[0][0]{
 check((attrs[0] as! OtherAttribute).token=="native-attr" && (stickers[5] as? Payload) === payload && (ref?.media as? Payload) === payload && thread==3 && reply?.messageId==id && story==8 && group==99 && corr==44 && up==[9] && (ref?.media as? Payload)?.bytes == bytes,"ordinary associated native payload bytes and metadata preserved")
}

// The one-time guard also handles a provider erroneously completing twice.
var duplicateReady=0,duplicateAllowed:[Bool]=[]
let duplicateLease=NagramiXTemporaryReplySend(correlationId:9,mediaCopy:nil,prepare:{complete in complete(true);complete(true)},ready:{duplicateReady+=1})
duplicateLease.beforeEnqueue{duplicateAllowed.append($0)}
check(duplicateReady==1 && duplicateAllowed==[true,false],"duplicate preparation cannot commit twice")

// Fee confirmation retains ownership; commit is delayed until final source check.
func makeLease(_ label:String,_ probe:LeaseProbe)->NagramiXArchivedMediaCopy{NagramiXArchivedMediaCopy(tempRoot+"/"+label,probe)}
let feeContext=Context(),feeNode=Node(feeContext);feeContext.account.postbox.archive!.retained[id]=source
let probe=LeaseProbe();var local:NagramiXArchivedMediaCopy?=makeLease("paid",probe)
var readyCalls=0,retries=0,outcomes:[Bool]=[]
var pending:NagramiXTemporaryReplySend?=feeNode.nagramiXMakeTemporaryReplySend(marker:44,replySubject:.init(messageId:id),nagramiXReplyGeneration:0,nagramiXTemporaryReplySource:source,nagramiXExpectedTemporaryReply:true,nagramiXTemporaryReplyRetried:false,mediaCopy:local,retry:{_ in retries+=1},ready:{readyCalls+=1})
local=nil
var confirm:((Bool)->Void)?
nagramiXSubmitComposerForwardMessages(messageCount:messages.count,requiresPayment:true,postpone:false,present:{count,callback in check(count==7,"fee sees final output cardinality");confirm=callback},send:{_ in pending!.beforeEnqueue{outcomes.append($0)}})
check(FileManager.default.fileExists(atPath:tempRoot+"/paid") && readyCalls==0 && outcomes.isEmpty,"copy remains uncommitted before fee confirmation")
confirm!(false)
check(readyCalls==0 && outcomes.isEmpty,"copy remains uncommitted during final lookup")
feeContext.account.postbox.flush()
check(outcomes==[true] && readyCalls==1 && retries==0,"authoritative approved source releases queue once")
pending!.beforeEnqueue{outcomes.append($0)};check(outcomes==[true,false],"send lease cannot commit twice")
pending=nil;confirm=nil
check(probe.commits==1 && probe.rollbacks==0 && FileManager.default.fileExists(atPath:tempRoot+"/paid"),"accepted local resource ownership survives original lease release")
try! FileManager.default.removeItem(atPath:tempRoot+"/paid")
let canceledProbe=LeaseProbe();var canceled:NagramiXTemporaryReplySend?=feeNode.nagramiXMakeTemporaryReplySend(marker:44,replySubject:.init(messageId:id),nagramiXReplyGeneration:0,nagramiXTemporaryReplySource:source,nagramiXExpectedTemporaryReply:true,nagramiXTemporaryReplyRetried:false,mediaCopy:makeLease("cancel",canceledProbe),retry:{_ in},ready:{check(false,"canceled fee cannot send")})
check(canceled!.includesLocalCopy,"retained batch owns its lease")
canceled=nil
check(canceledProbe.rollbacks==1 && !FileManager.default.fileExists(atPath:tempRoot+"/cancel"),"fee cancellation rolls back uncommitted files")

// Final lookup must reject any draft/location/topic/input/fee/generation drift.
for mode in 0..<6{
 let context=Context(),current=Node(context);context.account.postbox.archive!.retained[id]=source
 let own=LeaseProbe();var operation:NagramiXTemporaryReplySend?=current.nagramiXMakeTemporaryReplySend(marker:44,replySubject:.init(messageId:id),nagramiXReplyGeneration:0,nagramiXTemporaryReplySource:source,nagramiXExpectedTemporaryReply:true,nagramiXTemporaryReplyRetried:false,mediaCopy:makeLease("drift\(mode)",own),retry:{_ in check(false,"drift cannot retry")},ready:{check(false,"stale final context cannot enqueue")})
 var allowed:[Bool]=[];operation!.beforeEnqueue{allowed.append($0)}
 if mode==0{current.chatPresentationInterfaceState.interfaceState.token+=1}
 if mode==1{current.chatLocation.peerId=21}
 if mode==2{current.chatLocation.threadId=9}
 if mode==3{current.textInputPanelNode!.inputTextState.generation+=1}
 if mode==4{current.chatPresentationInterfaceState.sendPaidMessageStars=5}
 if mode==5{current.nagramiXTemporaryReplyGeneration+=1}
 context.account.postbox.flush();operation=nil
 check(allowed==[false] && own.rollbacks==1 && !FileManager.default.fileExists(atPath:tempRoot+"/drift\(mode)"),"stale final context cannot enqueue")
}
let preparedState=feeNode.chatPresentationInterfaceState.interfaceState,preparedLocation=feeNode.chatLocation
check(feeNode.feeGuard(required:true,resolved:.copy(source),state:preparedState,location:preparedLocation,fee:nil),"unchanged fee recipient context proceeds")
feeNode.chatLocation.peerId=21
check(!feeNode.feeGuard(required:true,resolved:.copy(source),state:preparedState,location:preparedLocation,fee:nil),"fee callback rejects recipient switch")
feeNode.chatLocation=preparedLocation

// Source can disappear during Stars/schedule. Retry once using its new resolution.
let transition=Context(),transitionNode=Node(transition);transition.account.postbox.archive!.retained[id]=source
var retryKinds=0,transitionReady=0,transitionAllowed:[Bool]=[]
let first=transitionNode.nagramiXMakeTemporaryReplySend(marker:4,replySubject:.init(messageId:id),nagramiXReplyGeneration:0,nagramiXTemporaryReplySource:nil,nagramiXExpectedTemporaryReply:true,nagramiXTemporaryReplyRetried:false,mediaCopy:nil,retry:{value in if case .copy=value{retryKinds+=1}},ready:{transitionReady+=1})
first.beforeEnqueue{transitionAllowed.append($0)};transition.account.postbox.flush()
check(transitionAllowed==[false] && retryKinds==1 && transitionReady==0,"native to retained expiration retries preparation once")
transition.account.postbox.live[id]=source
let second=transitionNode.nagramiXMakeTemporaryReplySend(marker:4,replySubject:.init(messageId:id),nagramiXReplyGeneration:0,nagramiXTemporaryReplySource:source,nagramiXExpectedTemporaryReply:true,nagramiXTemporaryReplyRetried:true,mediaCopy:nil,retry:{_ in retryKinds+=1},ready:{transitionReady+=1})
second.beforeEnqueue{transitionAllowed.append($0)};transition.account.postbox.flush()
check(retryKinds==1 && transitionReady==0 && transitionAllowed==[false,false],"resolution oscillation cannot retry indefinitely")
let successfulRetry=transitionNode.nagramiXMakeTemporaryReplySend(marker:5,replySubject:.init(messageId:id),nagramiXReplyGeneration:0,nagramiXTemporaryReplySource:nil,nagramiXExpectedTemporaryReply:true,nagramiXTemporaryReplyRetried:true,mediaCopy:nil,retry:{_ in check(false,"successful retry must not recurse")},ready:{transitionReady+=1})
successfulRetry.beforeEnqueue{transitionAllowed.append($0)};transition.account.postbox.flush()
check(transitionAllowed==[false,false,true] && transitionReady==1,"rebuilt native reply commits once after a resolution retry")
transition.account.postbox.live.removeAll()
let copyRetry=transitionNode.nagramiXMakeTemporaryReplySend(marker:6,replySubject:.init(messageId:id),nagramiXReplyGeneration:0,nagramiXTemporaryReplySource:source,nagramiXExpectedTemporaryReply:true,nagramiXTemporaryReplyRetried:true,mediaCopy:nil,retry:{_ in check(false,"rebuilt retained reply must not recurse")},ready:{transitionReady+=1})
copyRetry.beforeEnqueue{transitionAllowed.append($0)};transition.account.postbox.flush()
check(transitionAllowed==[false,false,true,true] && transitionReady==2,"rebuilt retained reply commits once after a resolution retry")
let unavailableContext=Context(),unavailableNode=Node(unavailableContext)
var unavailableAllowed:[Bool]=[]
let unavailable=unavailableNode.nagramiXMakeTemporaryReplySend(marker:4,replySubject:.init(messageId:id),nagramiXReplyGeneration:0,nagramiXTemporaryReplySource:source,nagramiXExpectedTemporaryReply:true,nagramiXTemporaryReplyRetried:false,mediaCopy:nil,retry:{_ in check(false,"purged source cannot retry")},ready:{check(false,"purged source cannot enqueue")})
unavailable.beforeEnqueue{unavailableAllowed.append($0)};unavailableContext.account.postbox.flush()
check(unavailableAllowed==[false] && unavailableNode.interfaceInteraction!.alerts==1,"purged source refuses enqueue and reports failure")

// Correlation claim is exact, single-use, and absent for ordinary sends.
let claim=Node(Context());claim.nagramiXPendingTemporaryReplySend=first
check(claim.nagramiXTakeTemporaryReplySend([enqueue("unrelated",100)])==nil && claim.nagramiXPendingTemporaryReplySend != nil,"unrelated callback cannot take another pending lease")
check(claim.nagramiXTakeTemporaryReplySend([enqueue("correct",4)]) === first && claim.nagramiXPendingTemporaryReplySend==nil,"correlation owner claims lease once")
check(claim.nagramiXTakeTemporaryReplySend([enqueue("correct",4)])==nil,"ordinary send without pending lease stays native")
let weakContext=Context();var weakNode:Node?=Node(weakContext);weak var weakReference=weakNode
var weakAllowed:[Bool]=[]
let weakOperation=weakNode!.nagramiXMakeTemporaryReplySend(marker:4,replySubject:.init(messageId:id),nagramiXReplyGeneration:0,nagramiXTemporaryReplySource:source,nagramiXExpectedTemporaryReply:true,nagramiXTemporaryReplyRetried:false,mediaCopy:nil,retry:{_ in},ready:{check(false,"released node cannot enqueue")})
weakOperation.beforeEnqueue{weakAllowed.append($0)};weakNode=nil
check(weakReference==nil,"asynchronous source lookup does not retain node")
weakContext.account.postbox.flush();check(weakAllowed==[false],"released node rejects late completion")
print("PASS temporary reply send production checks: \(checks)")
'''


def execute(texts, swiftc, folder):
    code = fixture(texts)
    mutations = {
        'missing-begin-guard': (code.replace('guard !self.began else { completion(false); return }', 'if false { completion(false); return }', 1), 'send lease cannot commit twice'),
        'missing-commit-guard': (code.replace('guard allowed, !self.committed else', 'guard allowed else', 1), 'duplicate preparation cannot commit twice'),
        'dropped-message-groups': (code.replace('case (.message, .message):\n                appendToLast = true', 'case (.message, .message):\n                appendToLast = false', 1), 'mixed forward grouping preserves contiguous copied album and comment'),
        'late-source-skipped': (code.replace('case .unavailable:\n                    ready(false)', 'case .unavailable:\n                    ready(true)', 1), 'purged source cannot enqueue'),
        'draft-check-dropped': (code.replace('self.chatPresentationInterfaceState.interfaceState == preparedState,', '({ _ = preparedState; return true })(),', 1), 'stale final context cannot enqueue'),
    }
    assert all(value[0] != code for value in mutations.values()), 'A semantic mutation no longer matches the real body'
    results = []
    for name, (content, failure) in [('current', (code, None)), *mutations.items()]:
        path = folder/(name+'.swift'); path.write_text(content)
        for optimized in (False, True):
            label = name+('-O' if optimized else '-debug'); binary = folder/label; files = folder/(label+'-files'); files.mkdir(exist_ok=True)
            command = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder/'cache'), *(['-O'] if optimized else []), str(path), '-o', str(binary)]
            compiled = subprocess.run(command, capture_output=True, text=True)
            assert compiled.returncode == 0, compiled.stdout+compiled.stderr
            completed = subprocess.run([str(binary), str(files)], capture_output=True, text=True, timeout=45, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if failure is None:
                assert completed.returncode == 0, completed.stdout+completed.stderr
                results.append(completed.stdout.strip())
            else:
                assert completed.returncode == 91 and 'TEMP SEND REGRESSION: '+failure in completed.stderr, (label,completed.returncode,completed.stdout,completed.stderr)
    boundary = module_boundary(texts, swiftc, folder/'module-boundary')
    return results, len(mutations)*2, boundary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--support-source',type=Path)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--artifacts',type=Path)
    args=parser.parse_args()
    texts=verify(args.source,args.support_source,args.baseline)
    if args.artifacts:
        args.artifacts.mkdir(parents=True,exist_ok=True);folder=args.artifacts
        runs,negative,boundary=execute(texts,args.swiftc,folder)
    else:
        with tempfile.TemporaryDirectory(prefix='nagramix-temporary-send-') as temporary:
            runs,negative,boundary=execute(texts,args.swiftc,Path(temporary))
    report={'production_runs':runs,'semantic_negative_runs':negative,'module_boundary':boundary,'source_bodies':{n:hashlib.sha256(value.encode()).hexdigest() for n,value in texts.items()},'native_ordinary_queue':'unchanged ordinary branch; exact associated media/attributes preserved','object_resolver':'unchanged common resolver; fixed image/card continuation covered through bounded callback','ownership':'real temporary files; native commit and rollback bodies with release counters; staging constructor is bounded','apple_sdk':'pending','device':'pending','live_delivery':'not exercised'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
