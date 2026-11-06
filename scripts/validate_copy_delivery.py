#!/usr/bin/env python3
"""Проверить отправку копий, владение загрузками и стабильный выбор адресатов."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile
from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
STAGE = 'copy_delivery'
PLAN = json.loads((OVERLAY / (STAGE + '_patches.json')).read_text())
CORE = 'submodules/TelegramCore/Sources/'
POLICY = CORE + 'Utils/NagramiXContentCopy.swift'
COPIER = CORE + 'Utils/NagramiXOutgoingCopy.swift'
INFO = CORE + 'SyncCore/SyncCore_OutgoingContentInfoMessageAttribute.swift'
FORWARD = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
NODE = 'submodules/TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionControllerNode.swift'
CONTACT = 'submodules/ContactListUI/Sources/ContactListNode.swift'
SK = 'submodules/SSignalKit/SwiftSignalKit/Source/'

def clean(text):
    return '\n'.join(l for l in text.splitlines() if not re.match(r'^(?:(?:internal|public|private|fileprivate|package) )?import ', l)).replace('public ', '')

def sha(data): return hashlib.sha256(data).hexdigest()

def verify(source):
    for n, h in {**PLAN['outputs'], **PLAN['guards']}.items(): assert sha((source/n).read_bytes()) == h, n
    for n, item in PLAN['copies'].items(): assert sha((source/n).read_bytes()) == item['sha256'], n
    for n, h in PLAN['templates'].items(): assert sha((OVERLAY/n).read_bytes()) == h, n
    text = (source/FORWARD).read_text()
    assert 'forceLocalMedia: false' in text and 'nagramiXPrepareCopyUpload(' in text
    assert 'nagramiXProtectedOriginal' not in text
    assert 'nagramiXObserveCopyDelivery' in text and 'lookupReceived.swap(true)' in text
    assert 'timeout(20.0, queue: Queue.mainQueue(), alternate: .complete())' in text
    pending = (source/(CORE+'State/PendingMessageManager.swift')).read_text()
    assert pending.count('nagramiXCopyShouldReupload(') == 2
    assert 'forcedReuploadOnce' in pending and 'nagramiXCopyServerFallbackText(' in pending
    upload = (source/(CORE+'PendingMessages/PendingMessageUploadedContent.swift')).read_text()
    assert 'if !forceReupload, peerId.namespace != Namespaces.Peer.SecretChat, let reference = image.reference' in upload
    assert 'if forceReupload && attributes.contains(where:' in upload
    assert 'if !forceReupload, let uploaded = uploadedRichMedia(from: media)' in upload
    assert 'isGrouped: true' in upload and 'let attachments = ([poll.attachedMedia, poll.results.solution?.media]' in upload
    assert 'let inputGame = Api.InputGame.inputGameID' in upload
    multipart = (source/(CORE+'Network/MultipartUpload.swift')).read_text()
    assert 'dataSignal = postbox.mediaBox.resourceData(resource.resource, option: .incremental' in multipart
    assert 'fetchedResource = fetchedMediaResource(' in multipart
    ui = (source/'submodules/TelegramUI/Sources/Chat/NagramiXCopyDelivery.swift').read_text()
    assert 'synchronouslyLookupCorrelationId' in ui and 'nagramiXCopiedMessageDeliveryState(message, acknowledged:' in ui
    assert 'nagramiXRetryCopiedMessages' in ui and 'resendMessages(' not in ui
    assert 'exportMessageLink' in ui and 'exportStoryLink' in ui
    assert 'story.music == nil, story.mediaAreas.isEmpty' in ui
    assert 'todo.completions.isEmpty' in ui and 'peer?.isPremium == true' in ui
    assert 'poll.correctAnswers?.isEmpty != false' in ui
    assert 'inputMediaDice(' not in ui and 'tonAmount:' not in ui
    assert 'case .full = $0' in ui
    panel = (source/'submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift').read_text()
    assert 'let copyBlocked = !self.nagramiXCanCopySelection\n' in panel
    assert 'TelegramSecretChat, !ContentSettings.default.nagramiXAllowsFreeContent' not in panel
    menu = (source/'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift').read_text()
    assert 'let messagesToForward = selectAll || isImage ? messages : (groupedCopyMessages.isEmpty ? [message] : groupedCopyMessages)' in menu
    assert '&& !nagramiXTemporaryActions && !isCopyProtected && !nagramiXOwnViewOnceCopy' in menu
    assert 'if nagramiXTemporaryActions, nagramiXCanCopySelection {' in menu
    assert 'interfaceInteraction.forwardMessages(copies)' in menu
    assert 'prefix.utf16.count' in menu
    assert 'guard nagramiXCanUseTemporaryMediaActions(message), nagramiXCanCopyMessagesAsNew(copyMessagesToForward' in menu
    assert text.count('}) == nagramiXOwnViewOnceCopy) else {') == 3
    load=(source/'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift').read_text()
    assert 'transferMode: .copyToSingleRecipient, nagramiXTransferTitle: strongSelf.presentationData.strings.nagramiXForwardWithAuthor' in load
    # Ordinary reposts remain native; retained temporary media keeps the agreed author-signature copy.
    assert 'interfaceInteraction.forwardMessages(messagesToForward)' in menu
    assert not set(PLAN['outputs']) & set(json.loads((OVERLAY/'upstream_13_2_post_patches.json').read_text())['outputs'])
    assert (OVERLAY/'apply_overlay.py').read_text().index('    apply_rich_draft_upload_retry(') < (OVERLAY/'apply_overlay.py').read_text().index('    apply_copy_delivery(')

def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location(STAGE, OVERLAY/(STAGE+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    apply = module.apply_copy_delivery
    rejected = []
    def seed(label):
        tree = temp/label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            p = tree/name; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((OVERLAY/PLAN['previous'][name] if name in PLAN['previous'] else source/name).read_bytes())
        return tree
    def reject(tree, label, overlay=OVERLAY):
        before = manifest(tree)
        try: apply(tree, overlay)
        except (SystemExit, OSError): pass
        else: raise AssertionError('Invalid input accepted: '+label)
        assert manifest(tree) == before, 'Partial write: '+label
        rejected.append(label)
    valid = seed('valid'); apply(valid, OVERLAY)
    for n in list(PLAN['outputs'])+list(PLAN['copies']): assert (valid/n).read_bytes() == (source/n).read_bytes(), n
    reject(valid, 'repeat')
    for index, name in enumerate({**PLAN['inputs'], **PLAN['guards']}):
        for kind in ['missing', 'drift']:
            tree = seed(str(index)+'-'+kind)
            if kind == 'missing': (tree/name).unlink()
            else: (tree/name).write_bytes(b'drift')
            reject(tree, kind+' '+name)
    first = next(iter(PLAN['inputs']))
    variants = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad=copy.deepcopy(PLAN);bad[field][next(iter(bad[field]))]='0'*64;variants.append((field,bad))
    for field in ['previous', 'replacements']:
        bad=copy.deepcopy(PLAN);bad[field][first]='../outside.swift';variants.append((field,bad))
    bad=copy.deepcopy(PLAN);bad['outputs'].clear();variants.append(('inconsistent',bad))
    name = next(iter(PLAN['copies']))
    bad=copy.deepcopy(PLAN);bad['copies']['../outside.swift']=bad['copies'].pop(name);variants.append(('copy-traversal',bad))
    for label,bad in variants:
        overlay=temp/('overlay-'+label)
        for n in PLAN['templates']:
            p=overlay/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OVERLAY/n).read_bytes())
        (overlay/(STAGE+'_patches.json')).write_text(json.dumps(bad))
        reject(seed('source-'+label),label,overlay)
    for index,n in enumerate([first,next(iter(PLAN['guards']))]):
        tree=seed('symlink-'+str(index));p=tree/n;external=temp/('outside-'+str(index));external.write_bytes(p.read_bytes());p.unlink();p.symlink_to(external);reject(tree,'external symlink '+n)
    tree=seed('existing-copy');p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'existing');reject(tree,'existing-copy')
    return rejected


def model_boundary(source, real_signals=False):
    from validate_message_copy_availability import poll_boundary
    base=(ROOT/'scripts/tests/NagramiXContentCopyTests.swift').read_text().split('@main struct ContentCopyTests')[0]
    if real_signals: base='import Foundation\n'+base[base.index('enum Namespaces'):]
    base=base.replace('    var id = MessageId(); var text', '    var peers: [PeerId: Any] = [:]\n    var id = MessageId(); var text')
    base=base.replace('struct NagramiXArchivedMessageAttribute: MessageAttribute {}', 'struct NagramiXArchivedMessageAttribute: MessageAttribute { var isTemporary=false }')
    base=base.replace('struct TelegramMediaPaidContent: Media {}','enum PaidPart { case full(Media), preview }; struct TelegramMediaPaidContent: Media { var extendedMedia: [PaidPart] = [] }')
    base=base.replace('static let Failed = Self(rawValue: 1);', 'static let Failed = Self(rawValue: 1); static let Unsent = Self(rawValue: 8);')
    base=base.replace('    var isVoice: Bool {', '    var isVideo: Bool { attributes.contains("video") }\n    var isVoice: Bool {')
    base=base.replace('    func isCopyProtected() -> Bool { protected }','    var paidContent: Media? { media.first { $0 is TelegramMediaPaidContent } }; var isSelfExpiring: Bool { minAutoremoveOrClearTimeout != nil }\n    func isCopyProtected() -> Bool { protected }\n    func withUpdatedText(_ text: String) -> Self { var r=self; r.text=text; return r }\n    func withUpdatedMedia(_ media: [Media]) -> Self { var r=self; r.media=media; return r }\n    func withUpdatedAttributes(_ attributes: [MessageAttribute]) -> Self { var r=self; r.attributes=attributes; return r }')
    rich=(ROOT/'scripts/tests/NagramiXRichContentCopyTests.swift').read_text().split('@main struct RichContentCopyTests')[0]
    base += rich + poll_boundary(source)
    base += '''
struct TelegramMediaTodo: Media {}
struct TelegramMediaGame: Media {}
struct ForwardSourceInfoAttribute: MessageAttribute {}
struct WebpagePreviewMessageAttribute: MessageAttribute { var leadingPreview: Bool; var forceLargeMedia: Bool? }
struct InvertMediaMessageAttribute: MessageAttribute {}
struct NotificationInfoMessageAttribute: MessageAttribute { var muted: Bool }
struct OutgoingScheduleInfoMessageAttribute: MessageAttribute { var time: Int32 }
extension AnyMediaReference { var media: Media { switch self { case let .standalone(media), let .message(_, media): return media } } }
extension EngineMessage { typealias Id = MessageId }
extension EnqueueMessage {
    func withUpdatedAttributes(_ f: ([MessageAttribute]) -> [MessageAttribute]) -> Self {
        .message(text: text, attributes: f(attributes), inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: threadId, replyToMessageId: replyToMessageId, replyToStoryId: replyToStoryId, localGroupingKey: localGroupingKey, correlationId: correlationId, bubbleUpEmojiOrStickersets: bubbleUpEmojiOrStickersets)
    }
    func withUpdatedGroupingKey(_ f: (Int64?) -> Int64?) -> Self {
        .message(text: text, attributes: attributes, inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: threadId, replyToMessageId: replyToMessageId, replyToStoryId: replyToStoryId, localGroupingKey: f(localGroupingKey), correlationId: correlationId, bubbleUpEmojiOrStickersets: bubbleUpEmojiOrStickersets)
    }
}
class PostboxDecoder { func decodeOptionalStringForKey(_ key: String) -> String? { nil }; func decodeInt32ForKey(_ key: String, orElse: Int32) -> Int32 { orElse } }
class PostboxEncoder { func encodeString(_ value: String, forKey: String) {}; func encodeNil(forKey: String) {}; func encodeInt32(_ value: Int32, forKey: String) {} }
'''
    from validate_temporary_media_actions import P
    base+=clean(block((source/P).read_text(),'public func nagramiXCanUseTemporaryMediaActions('))
    base+=clean((source/INFO).read_text())
    return base


def payload_fixture(source):
    copier=(source/COPIER).read_text().split('/// Retrying a rejected copy')[0]
    policy=(source/POLICY).read_text().split('private enum NagramiXContentCopyFetchError')[0]
    return model_boundary(source)+clean(policy)+clean(copier)+clean((source/(CORE+'Utils/NagramiXArchivedMediaCopy.swift')).read_text())+'\n'+(ROOT/'scripts/tests/NagramiXCopyDeliveryTests.swift').read_text()


def preparation_fixture(source):
    parts=['import Foundation']
    for n in ['Atomic','Disposable','Subscriber']:
        parts.append((source/(SK+n+'.swift')).read_text())
    s=(source/(SK+'Signal.swift')).read_text();parts.append(s[:s.index('@available(iOS 13.0')])
    s=(source/(SK+'Signal_Mapping.swift')).read_text()
    parts.extend(block(s,a) for a in ['private class DistinctUntilChangedContext<T>', 'public func map<T, E, R>(', 'public func filter<T, E>(', 'public func distinctUntilChanged<T: Equatable, E>('])
    parts.append(block((source/(SK+'Signal_Single.swift')).read_text(),'public func single<T, E>('))
    parts.append(block((source/(SK+'Signal_Take.swift')).read_text(),'public func take<T, E>(_ count:'))
    s=(source/(SK+'Signal_Combine.swift')).read_text()
    parts.extend(block(s,a) for a in ['private struct SignalCombineState','private func combineLatestAny<','private func signalOfAny<','public func combineLatest<T, E>('])
    parts.append('''
enum Scheduler {
    static var now=0.0; static var tasks:[(Double,()->Void)]=[]
    static func advance(_ seconds:Double) {
        let end=now+seconds
        while let i=tasks.indices.filter({tasks[$0].0<=end}).min(by:{tasks[$0].0<tasks[$1].0}) { let task=tasks.remove(at:i); now=task.0;task.1() }
        now=end
    }
}
final class Queue {
    static func concurrentDefaultQueue()->Queue {Queue()}
    func after(_ seconds:Double,_ f:@escaping()->Void) {Scheduler.tasks.append((Scheduler.now+seconds,f))}
}
func deliverOn<T,E>(_ queue:Queue)->(Signal<T,E>)->Signal<T,E> {{ $0 }}
enum ResourceStatus: Equatable { case Remote(Float), Paused(Float), Fetching(Bool,Float), Local }
extension MediaBox {
    func resourceStatus(_ resource:MediaResource)->Signal<ResourceStatus,NoError> {
        Signal { out in let name=resource.id.stringRepresentation;self.statusObservers[name]=out.putNext;out.putNext(.Remote(0));return ActionDisposable {self.statusObservers.removeValue(forKey:name)} }
    }
    func status(_ name:String,_ value:ResourceStatus){statusObservers[name]?(value)}
}
''')
    base=model_boundary(source,True).replace('    var paths: [String: String] = [:];','    var statusObservers: [String: (ResourceStatus)->Void] = [:]\n    var paths: [String: String] = [:];')
    parts.append(base)
    text=(source/POLICY).read_text()
    parts.append(text[:text.index('/// Fetch only primary attachments')])
    parts.append(text[text.index('/// Pins original cache resources'):])
    parts.append((ROOT/'scripts/tests/NagramiXCopyPreparationTests.swift').read_text())
    return 'import Foundation\n'+clean('\n'.join(parts))



def selection_fixture(source):
    n=(source/NODE).read_text()
    fixture=(ROOT/'scripts/tests/NagramiXTransferConsistencyBoundary.swift').read_text()
    fixture=fixture[:fixture.index('struct PresentationStrings')]
    fixture=fixture.replace('    var editing=false','    var nagramiXCopyMode=0\n    var nagramiXCopySearchAnchors:[Int:Set<Int>]=[:]\n    var editing=false')
    # Unused UIKit send handlers are not part of this state boundary.
    fixture=fixture.replace('        node.requestSend = // PRODUCTION_SEND_REQUEST_BRIDGE','        node.requestSend = nil')
    fixture=fixture.replace('        textInputPanelNode!.sendMessage = // PRODUCTION_SEND_BUTTON_CALLBACK','        textInputPanelNode!.sendMessage = nil')
    start=n.index('    var nagramiXCopySelection = false')
    props=n[start:n.index(' = ([], [:])',start)+len(' = ([], [:])')].replace('private ','')
    select=block(n,'    func nagramiXSelectCopyRecipient(')
    select=select[:select.index('        if self.forwardedMessageIds.isEmpty')]+"        self.textInputPanelNode?.updateSendButtonEnabled(!self.selectedPeers.0.isEmpty, animated: true)\n    }"
    select=block(n,'    func nagramiXRecordFoundCopyRecipient(')+'\n'+block(n,'    private func nagramiXCopyContactState(').replace('private ','')+'\n'+select
    start=n.index('    private var selectedPeers:')
    selected=n[start:n.index('    func beginSelection()',start)].replace('private ','')
    begin=block(n,'    func beginSelection()');begin=begin[begin.index('        if self.nagramiXCopySelection {'):begin.index('        guard let controller')]
    begin+='\n        self.mainContainerNode?.currentItemNode.updateState { state in var state=state;state.nagramiXCopyMode=self.controller?.multipleSelectionLimit == 1 ? 1:2;return state }'
    fixture=fixture.replace('if contactListActive {contactListNode?.state=ContactListNodeGroupSelectionState()}', 'if contactListActive {contactListNode?.state=nagramiXCopyContactState()}')
    search=n.index('openPeer: { [weak self] peer, chatPeer, threadId, _ in')
    chats=block(n[search:],'                        chatListNode?.updateState { state in').replace('chatListNode?.updateState','self.mainContainerNode?.currentItemNode.updateState')
    search=n.index('contentNode: ContactsSearchContainerNode(')
    contacts=block(n[search:],'                    strongSelf.contactListNode?.updateSelectionState { state -> ContactListNodeGroupSelectionState? in')
    for marker,body in [('CONTACT_STATE',block((source/CONTACT).read_text(),'public struct ContactListNodeGroupSelectionState:').replace('public ','')),('SELECTION_PROPERTIES',props),('SELECT_RECIPIENT',select),('SELECTED_PROPERTIES',selected),('BEGIN_SELECTION',begin),('CHAT_SEARCH_SELECTION',chats),('CONTACT_SEARCH_SELECTION',contacts)]:
        assert '// PRODUCTION_'+marker in fixture,marker
        fixture=fixture.replace('// PRODUCTION_'+marker,body)
    entries=(source/'submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift').read_text()
    rank=block(entries,'    if state.nagramiXCopyMode != 0 {')
    comparator=block(entries,'    static func <(lhs: ChatListNodeEntry, rhs: ChatListNodeEntry)')
    comparator=comparator[:comparator.index('        if case let .PeerEntry(left) = lhs, case let .PeerEntry(right) = rhs,\n           left.nagramiXInlineParentIndex')]+"        return lhs.nativeOrder < rhs.nativeOrder\n    }"
    fixture+='\nstruct RenderedPeer {var peerId:Int}\nstruct Thread {var id:Int}\nstruct ViewItem {var renderedPeer:RenderedPeer}\nstruct RankView {var items:[ViewItem]}\nenum RankIdentity: Hashable {case peer(Int),thread(Int),header}\nenum ChatListNodeEntry: Comparable {\n    struct PeerEntryData:Equatable {\n        var peer:RenderedPeer;var order:Int;var threadInfo:Thread?\n        var nagramiXCopyRank:Int?;var nagramiXCopySingleSelection=false\n        static func ==(a:Self,b:Self)->Bool {a.peer.peerId==b.peer.peerId && a.order==b.order}\n    }\n    case PeerEntry(PeerEntryData),HeaderEntry,ArchiveIntro,EmptyIntro,GroupReferenceEntry\n    static func peer(id:Int,order:Int,thread:Int?)->Self {.PeerEntry(.init(peer:.init(peerId:id),order:order,threadInfo:thread.map{Thread(id:$0)}))}\n    var nativeOrder:Int {if case let .PeerEntry(p)=self{return p.order};return 10000}\n    var stableId:RankIdentity {if case let .PeerEntry(p)=self {if let t=p.threadInfo{return .thread(t.id)};return .peer(p.peer.peerId)};return .header}\n    // COMPARATOR\n}\nfunc arrange(_ input:[ChatListNodeEntry],state:ListState,found:[(EnginePeer,EnginePeer?)],native:[ChatListNodeEntry])->[Int] {\n    var result=input\n    let foundPeers=found\n    let savedMessagesPeer:EnginePeer?=nil\n    let view=RankView(items:native.compactMap{if case let .PeerEntry(p)=$0{return .init(renderedPeer:p.peer)};return nil})\n    // RANK\n    return result.reversed().compactMap{if case let .PeerEntry(p)=$0{return p.peer.peerId};return nil}\n}\n'
    fixture += '''
enum ContactListNodeEntry {
    case header(Int)
    case peer(Int64,ContactListPeer,Int?,Int?,Int,Int,Int,Int,Int,Int,Bool,Bool,Bool,Int?,Bool,String?)
    static func row(_ id:Int)->Self {.peer(0,.peer(peer:.user(User(id:id)),isGlobal:false,participantCount:nil),nil,nil,0,0,0,0,0,0,false,false,true,nil,false,nil)}
}
'''+block((source/CONTACT).read_text(),'private func nagramiXArrangeCopyContacts(')
    fixture=fixture.replace('// COMPARATOR',comparator).replace('// RANK',rank)
    return fixture+'\n'+(ROOT/'scripts/tests/NagramiXCopySelectionTests.swift').read_text()


def temporary_fixture(source):
    # Reuse current production copier/policy/stager, not a historical snapshot.
    base=payload_fixture(source).split('@main struct CopyDeliveryTests')[0]
    base=base.replace('struct TestUser { var id: PeerId; var botInfo: Int? = nil }','struct TestUser { var id: PeerId; var botInfo: Int? = nil; var name="Юра 😀" }')
    base=base.replace('enum EngineMessage { typealias Attribute = MessageAttribute }','enum EngineMessage { case raw(Message); typealias Attribute = MessageAttribute }')
    old='struct Entity { let value: String; var associatedMediaIds: [MediaId] = [] }'
    new='struct Entity { let value: String; var associatedMediaIds: [MediaId] = []; var range: Range<Int> = 0..<2; var type: String {value}; init(value: String, associatedMediaIds: [MediaId] = []) {self.value=value;self.associatedMediaIds=associatedMediaIds}; init(range: Range<Int>, type: String) {self.value=type;self.range=range} }'
    assert base.count(old)==1; base=base.replace(old,new)
    menu=(source/'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift').read_text()
    author=block(menu,'                let copies = copyMessagesToForward.map { original -> EngineRawMessage in')
    reply=block(menu,'                if nagramiXCanUseTemporaryMediaActions(messages[0]), context.account.nagramiXMessageArchive.isLocallyDeletedMessage(id: messages[0].id) {')
    boundary=(ROOT/'scripts/tests/NagramiXTemporaryRepostBoundary.swift').read_text().replace('// PRODUCTION_AUTHOR_MAP',author).replace('// PRODUCTION_REPLY_BRANCH',reply)
    tests=(ROOT/'scripts/tests/NagramiXTemporaryCopyTests.swift').read_text()
    tests=tests.replace('precondition(value(),label)', 'if !value() { fatalError("Temporary copy regression: "+label) }')
    extra=(ROOT/'scripts/tests/NagramiXTemporaryRepostTests.swift').read_text()
    marker='  print("PASS: '
    assert tests.count(marker)==1;tests=tests.replace(marker,extra+'\n'+marker)
    return base+'\n'+boundary+'\n'+tests

def execute(source, swiftc, temp):
    retry=(ROOT/'scripts/tests/NagramiXCopyRetryBoundary.swift').read_text().replace('// PRODUCTION_RETRY', clean(block((source/COPIER).read_text(),'public func nagramiXRetryCopiedMessages(')))
    ui=(source/'submodules/TelegramUI/Sources/Chat/NagramiXCopyDelivery.swift').read_text()
    progress=block(ui,'private final class NagramiXCopyProgressController:').replace('@objc ', '').replace('#selector(self.cancelPressed)','self.cancelPressed')
    progress=(ROOT/'scripts/tests/NagramiXCopyProgressBoundary.swift').read_text().replace('// PRODUCTION_PROGRESS',progress)
    variants = {'payloads':payload_fixture(source), 'preparation':preparation_fixture(source), 'selection':selection_fixture(source), 'retry':retry, 'progress':progress, 'temporary':temporary_fixture(source)}
    variants['ui-title-collision']=progress.replace('cancelTitle','title')
    variants['forced-download']=variants['preparation'].replace('for message in messages where message.nagramiXCopyNeedsLocalMedia {','for message in messages {')
    variants['premature-unpin']=variants['preparation'].replace('if !transferred.with({ $0 }) { lease.dispose() }','lease.dispose()')
    variants['shared-paid-group']=variants['payloads'].replace('let groupingKey = copiedGroupingKeys[sourceGroup] ?? Int64.random(in: 1 ... Int64.max)','let groupingKey = sourceGroup')
    variants['missing-upload-fallback']=variants['payloads'].replace('return error == "CHAT_FORWARDS_RESTRICTED" || error == "MEDIA_EMPTY" || error == "MEDIA_INVALID"','return false')
    variants['free-content-gate']=variants['payloads'].replace('return (!retainedTemporary || temporary)','return (!self.nagramiXRequiresFreeContentCopy || ContentSettings.default.nagramiXAllowsFreeContent) && (!retainedTemporary || temporary)')
    variants['first-contact-promoted']=variants['selection'].replace('if self.nagramiXCopyFoundPeers.contains(where: { $0.id == peer.id }),', 'if true,')
    variants['enqueue-means-delivered']=variants['payloads'].replace('guard let message else { return .queued }','guard let message else { return .accepted }')
    variants['retry-random-id-lost']=variants['retry'].replace('attributes: message.attributes', 'attributes: []')
    variants['temporary-author-lost']=variants['temporary'].replace('original.withUpdatedText(prefix + original.text)', 'original.withUpdatedText(original.text)')
    variants['temporary-own-restricted']=variants['temporary'].replace('guard !nagramiXCanUseTemporaryMediaActions(self), let accountPeerId,', 'guard let accountPeerId,')
    assert all(v != variants['payloads'] and v != variants['preparation'] for n,v in variants.items() if n not in ['payloads','preparation','selection','retry','progress','temporary'])
    results=[]
    for label,code in variants.items():
        file=temp/(label+'.swift');file.write_text(code)
        for optimized in [False,True]:
            binary=temp/(label+('-O' if optimized else '-debug'))
            built=subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),str(file),'-o',str(binary)],capture_output=True,text=True)
            if label=='ui-title-collision':
                assert built.returncode!=0 and ('title' in built.stderr and 'override' in built.stderr),built.stderr
                results.append(binary.name+': UIKit inherited-property conflict rejected');print(results[-1],flush=True);continue
            assert built.returncode==0,built.stderr[-12000:]
            run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if label in ['payloads','preparation','selection','retry','progress','temporary']: assert run.returncode==0,run.stdout+run.stderr;status=run.stdout.strip()
            else:
                expected={'temporary-author-lost':'Original author included', 'temporary-own-restricted':'Temporary ON routes own recordings'}.get(label, 'Copy ')
                assert run.returncode!=0 and expected in run.stderr,run.stdout+run.stderr
                status='regression reproduced and rejected'
            results.append(binary.name+': '+status);print(results[-1],flush=True)
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_playback_commands'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'round_caption_transport'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'repost_copy_integrity'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'native_pip_baseline'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-copy-delivery-check-') as folder:
        temp=Path(folder);rejected=guard_checks(args.source,temp/'guards');runtime=temp/'runtime';runtime.mkdir()
        results=execute(args.source,args.swiftc,runtime) if args.swiftc else []
        if args.swiftc:
            for n in list(PLAN['outputs'])+list(PLAN['copies']): subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/n)],check=True)
    report={'replacements':len(PLAN['outputs']),'copies':len(PLAN['copies']),'guards':len(PLAN['guards']),'fail_closed':len(rejected),'executions':results,'native_sdk':'pending; not authorized in source task','device':'pending','boundaries':'Production copy builder, file staging and policy; real Foundation file IO. Production fetch/preparation using pinned real Signal/Subscriber/Atomic/Disposable/filter/take/combineLatest; network/mediaBox and clock are boundaries. Source SHA/API/wiring contracts, whole Swift syntax; no UIKit or Telegram server execution.'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
