#!/usr/bin/env python3
"""Проверить настоящее медиа в ответе на сохранённую одноразку и штатное действие Reply."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PANEL = 'submodules/TelegramUI/Components/Chat/ReplyAccessoryPanelNode/Sources/ReplyAccessoryPanelNode.swift'
INFO = 'submodules/TelegramUI/Components/Chat/ChatMessageReplyInfoNode/Sources/ChatMessageReplyInfoNode.swift'
MENU = 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift'
ARCHIVE = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
HELPER = 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift'


def source_contract(source, baseline=None):
    texts = {p: (source / p).read_text() for p in [PANEL, INFO, MENU]}
    plan_path = OVERLAY / 'temporary_message_interaction_patches.json'
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        for name in texts:
            assert hashlib.sha256((source/name).read_bytes()).hexdigest() == plan['outputs'][name], name
        before = {name: (OVERLAY/plan['previous'][name]).read_text() for name in texts}
    else:
        assert baseline is not None, 'A reviewed baseline is required before the stage manifest exists'
        before = {name: (baseline/name).read_text() for name in texts}
    panel, info, menu = texts[PANEL], texts[INFO], texts[MENU]
    archive = (source/ARCHIVE).read_text()
    assert 'public func temporaryInteractionMessage(id: MessageId, liveMessage: Message?) -> Message?' in archive
    assert 'public func nagramiXCanUseTemporaryMediaActions(_ message: Message) -> Bool' in (source/HELPER).read_text()
    assert 'context.account.postbox.messageView(messageId),' in panel
    assert 'context.account.nagramiXMessageArchive.updates' in panel
    assert 'startStrict(next: { [weak self] messageView, _ in' in panel
    assert 'let message = context.account.nagramiXMessageArchive.temporaryInteractionMessage(id: messageId, liveMessage: messageView.message)' in panel
    assert 'let message = messageView.message' not in panel
    assert 'self.nagramiXReplyMessageGeneration == generation' in panel
    assert 'self.dismiss?()' in panel
    assert 'strongSelf.interfaceInteraction?.setupReplyMessage(nil, nil, { _, _ in })' not in panel
    assert '(!message.containsSecretMedia || nagramiXCanUseTemporaryMediaActions(message))' in panel
    assert '(!message.containsSecretMedia || nagramiXCanUseTemporaryMediaActions(message))' in info
    assert 'self.message = nagramiXReplyInfoMessage(context: context, parentMessage: parentMessage, message: message)' in info
    assert 'message?.id ?? parentMessage.attributes.compactMap { $0 as? ReplyMessageAttribute }.first?.messageId' in info
    assert 'if !hasRateTranscription && message.minAutoremoveOrClearTimeout == nil && !nagramiXCanUseTemporaryMediaActions(message) {' in menu
    reply = block(menu, '        if !isPinnedMessages, !isReplyThreadHead, data.canReply {')
    assert 'interfaceInteraction.setupReplyMessage(messages[0].id, nil,' in reply
    assert 'updateTextInputStateAndMode' not in reply and 'descriptionStringForMessage' not in reply
    assert 'nagramiXArchivedSaveMediaActions(context: context' in menu
    retained_delete=block(menu,'        if nagramiXRetainedTemporary,\n')
    assert 'containsArchivedMessage(id: message.id)' in retained_delete
    assert 'isLocallyDeletedMessage(id: message.id)' in retained_delete
    assert 'NagramiXTabSettings.current.showDeletedMessages' not in retained_delete
    assert '!data.messageActions.options.contains(.deleteLocally)' in retained_delete
    assert '!data.messageActions.options.contains(.deleteGlobally)' in retained_delete
    # The requested reply already resolves from the visible history, including
    # retained MessageEntry/MessageGroupEntry values; it does not need a server fetch.
    history = (source/'submodules/TelegramUI/Sources/ChatHistoryListNode.swift').read_text()
    current = block(history, '    public func messageInCurrentHistoryView(_ id: EngineMessage.Id)')
    assert 'historyView.filteredEntries' in current and '.MessageGroupEntry' in current and 'return EngineMessage(message)' in current
    load = (source/'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift').read_text()
    assert 'strongSelf.chatDisplayNode.historyNode.messageInCurrentHistoryView(messageId)?._asMessage()' in load
    assert '.updatedReplyMessage(message).updatedSearch(nil).updatedShowCommands(false)' in load
    native_dismiss = (source/'submodules/TelegramUI/Sources/ChatControllerNode.swift').read_text()
    assert 'strongSelf.accessoryPanelNode === accessoryPanelNode' in native_dismiss
    for name, text in texts.items():
        old=before[name]
        assert text.count('descriptionStringForMessage(') == old.count('descriptionStringForMessage(') - (1 if name == MENU else 0)
        if name != MENU:
            for forbidden in ['.captureTemporaryBeforeViewing(', '.markTemporaryExpired(', '.archiveTemporaryExpiration(', '.markMessageContentAsConsumedInteractively(', '.storeMessage(', '.sendMessages(']:
                assert text.count(forbidden) == old.count(forbidden), (name,forbidden)
    return texts


def fixture(texts, mode='current'):
    panel,info,menu = texts[PANEL],texts[INFO],texts[MENU]
    resolver=block(info,'private func nagramiXReplyInfoMessage(')
    cancel=block(panel,'                    Queue.mainQueue().justDispatch { [weak self] in')[len('                    Queue.mainQueue().justDispatch '):]
    panel_predicate='(!message.containsSecretMedia || nagramiXCanUseTemporaryMediaActions(message))'
    info_predicate=panel_predicate
    # Both guards are actual source predicates; this prevents a test-only gate
    # from passing when the real call site still rejects a temporary attachment.
    assert 'if let message = message, '+panel_predicate+' {' in panel
    assert '} else if let message = arguments.message, '+info_predicate+' {' in info
    reply=block(menu,'        if !isPinnedMessages, !isReplyThreadHead, data.canReply {')
    start=reply.index('action: { c, _ in')
    action=block(reply[start:],'action: { c, _ in')[len('action: '):]
    sound_condition='!hasRateTranscription && message.minAutoremoveOrClearTimeout == nil && !nagramiXCanUseTemporaryMediaActions(message)'
    retained_delete=block(menu,'        if nagramiXRetainedTemporary,\n').split('{',1)[0]
    assert 'if '+sound_condition+' {' in menu
    if mode=='old-panel-gate': panel_predicate='!message.containsSecretMedia'
    elif mode=='old-info-gate': info_predicate='!message.containsSecretMedia'
    elif mode=='no-parent-target': resolver=resolver.replace('message?.id ?? parentMessage.attributes.compactMap { $0 as? ReplyMessageAttribute }.first?.messageId','message?.id')
    elif mode=='stale-generation': cancel=cancel.replace('self.nagramiXReplyMessageGeneration == generation,','true,')
    elif mode=='no-cancel-recheck': cancel=cancel.replace('context.account.nagramiXMessageArchive.temporaryInteractionMessage(id: messageId, liveMessage: messageView.message) == nil','true')
    elif mode=='strong-cancel': cancel=cancel.replace('[weak self]','[self]').replace('guard let self,','guard true,')
    elif mode=='duplicate-sound': sound_condition=sound_condition.replace(' && !nagramiXCanUseTemporaryMediaActions(message)','')
    elif mode=='text-only-reply': action='{ _, _ in interfaceInteraction.textOnlyFallbacks += 1 }'
    elif mode=='no-retained-delete': retained_delete=retained_delete.replace('if nagramiXRetainedTemporary,','if false && nagramiXRetainedTemporary,')
    elif mode=='unowned-delete': retained_delete=retained_delete.replace('(context.account.nagramiXMessageArchive.isLocallyDeletedMessage(id: message.id) || context.account.nagramiXMessageArchive.containsArchivedMessage(id: message.id))','true')
    elif mode=='duplicate-delete': retained_delete=retained_delete.replace('!data.messageActions.options.contains(.deleteLocally)','true')
    return '''import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
// Source-level UI projection and nil-cancellation bodies execute below. UIKit,
// the Signal scheduler, and the separately tested readonly archive/policy are adapters.
typealias MessageId = Int64
protocol MessageAttribute {}
final class ReplyMessageAttribute: MessageAttribute { let messageId: Int64; init(_ id: Int64) { messageId=id } }
final class OtherAttribute: MessageAttribute {}
final class Message {
    let id: Int64
    let containsSecretMedia: Bool
    let temporaryEligible: Bool
    let minAutoremoveOrClearTimeout: Int?
    let attributes: [MessageAttribute]
    let media: String
    init(_ id: Int64, secret: Bool=false, temporary: Bool=false, ttl: Int?=nil, attributes: [MessageAttribute]=[], media: String="original file") { self.id=id;containsSecretMedia=secret;temporaryEligible=temporary;minAutoremoveOrClearTimeout=ttl;self.attributes=attributes;self.media=media }
}
typealias EngineRawMessage = Message
var enabled=true
func nagramiXCanUseTemporaryMediaActions(_ message: Message) -> Bool { enabled && message.temporaryEligible }
final class Archive {
    var records: [Int64:Message]=[:]
    var calls: [Int64]=[]
    var locallyDeleted:Set<Int64>=[]
    func isLocallyDeletedMessage(id:MessageId)->Bool {locallyDeleted.contains(id)}
    func containsArchivedMessage(id:MessageId)->Bool {enabled && records[id] != nil}
    func temporaryInteractionMessage(id: MessageId, liveMessage: Message?) -> Message? {
        calls.append(id)
        guard liveMessage == nil || liveMessage?.id == id else { return nil }
        guard enabled else { return liveMessage }
        if let record=records[id], record.id==id, record.temporaryEligible { return record }
        return liveMessage
    }
}
final class Account { let nagramiXMessageArchive=Archive() }
final class AccountContext { let account=Account() }
struct MessageView { let message: Message? }
final class Panel {
    var nagramiXReplyMessageGeneration: UInt64=0
    var dismiss: (() -> Void)?
    func missingAction(context: AccountContext, messageId: MessageId, messageView: MessageView, generation: UInt64) -> () -> Void { return '''+cancel+''' }
}
final class WeakPanel { weak var value: Panel?; init(_ value: Panel) { self.value=value } }
'''+resolver+'''
func panelHasThumbnail(_ value: Message?) -> Bool { if let message=value, '''+panel_predicate+''' { return true };return false }
func infoHasThumbnail(_ value: Message?) -> Bool { if let message=value, '''+info_predicate+''' { return true };return false }
func soundActions(_ message: Message, hasRateTranscription: Bool=false) -> Int {
    var count=0
    if '''+sound_condition+''' { count += 1 }
    if nagramiXCanUseTemporaryMediaActions(message) { count += 1 }
    return count
}
struct DeleteOptions:OptionSet {let rawValue:Int;static let deleteLocally=Self(rawValue:1);static let deleteGlobally=Self(rawValue:2)}
struct MessageActions {let options:DeleteOptions}
struct MenuData {let messageActions:MessageActions}
func retainedDelete(context:AccountContext,message:Message,nagramiXRetainedTemporary:Bool,options:DeleteOptions)->Bool {
    let data=MenuData(messageActions:MessageActions(options:options))
    '''+retained_delete+''' { return true }
    return false
}
enum Transition { case immediate }
enum DismissResult { case custom(Transition) }
final class MenuController {
    var dismisses=0
    func dismiss(result: DismissResult, completion: @escaping () -> Void) { dismisses += 1;completion() }
}
final class Interaction {
    var textOnlyFallbacks=0
    var ids: [Int64?]=[]
    var completions=0
    func setupReplyMessage(_ id: Int64?, _ inner: Int?, _ completion: @escaping (Transition,@escaping () -> Void) -> Void) { ids.append(id);completion(.immediate,{self.completions += 1}) }
}
func replyAction(messages: [Message], interfaceInteraction: Interaction) -> (MenuController?,Int) -> Void { return '''+action+''' }
var checks=0
func check(_ value: @autoclosure () -> Bool,_ label: String) { if !value() { FileHandle.standardError.write(Data(("reply UI regression: "+label+"\\n").utf8));exit(91) };checks += 1 }
@main struct Main {
    static func main() {
        let context=AccountContext()
        let original=Message(42,secret:true,temporary:true,ttl:Int.max)
        let retained=Message(42,temporary:true,media:"retained voice bytes")
        let parent=Message(100,attributes:[OtherAttribute(),ReplyMessageAttribute(42)])
        let ordinary=Message(99)
        let protectedOther=Message(66,secret:true)
        enabled=true
        check(panelHasThumbnail(original),"ON original panel thumbnail")
        check(infoHasThumbnail(original),"ON original sent reply thumbnail")
        check(panelHasThumbnail(ordinary) && infoHasThumbnail(ordinary),"ordinary thumbnail unchanged")
        check(!panelHasThumbnail(protectedOther) && !infoHasThumbnail(protectedOther),"other secret media remains protected")
        context.account.nagramiXMessageArchive.records[42]=retained
        check(nagramiXReplyInfoMessage(context:context,parentMessage:parent,message:original) === retained,"retained projection resolves actual media")
        check(nagramiXReplyInfoMessage(context:context,parentMessage:parent,message:nil) === retained,"missing associated reply resolved by parent ID")
        check(context.account.nagramiXMessageArchive.calls.last==42,"existing target ID preserved")
        check(nagramiXReplyInfoMessage(context:context,parentMessage:parent,message:ordinary) === ordinary,"explicit non-temporary target unchanged")
        let before=context.account.nagramiXMessageArchive.calls.count
        check(nagramiXReplyInfoMessage(context:context,parentMessage:ordinary,message:nil)==nil,"no invented missing target")
        check(context.account.nagramiXMessageArchive.calls.count==before,"no target needs no lookup")
        check(panelHasThumbnail(retained) && infoHasThumbnail(retained),"retained file thumbnail")
        check(retained.id==original.id && retained.media=="retained voice bytes","real ID and file unchanged")
        check(soundActions(retained)==1,"one save sound for retained voice")
        check(soundActions(original)==1,"one save sound for original voice")
        check(retainedDelete(context:context,message:retained,nagramiXRetainedTemporary:true,options:[]),"TEMP-only retained record can be deleted without Deleted Messages")
        check(!retainedDelete(context:context,message:retained,nagramiXRetainedTemporary:false,options:[]),"ordinary message does not acquire local purge")
        check(!retainedDelete(context:context,message:retained,nagramiXRetainedTemporary:true,options:[.deleteLocally]),"native local delete not duplicated")
        check(!retainedDelete(context:context,message:retained,nagramiXRetainedTemporary:true,options:[.deleteGlobally]),"native global delete not duplicated")
        check(!retainedDelete(context:context,message:ordinary,nagramiXRetainedTemporary:true,options:[]),"unowned temporary-looking message cannot purge")
        enabled=false
        check(!panelHasThumbnail(original) && !infoHasThumbnail(original),"OFF native secret media policy")
        check(nagramiXReplyInfoMessage(context:context,parentMessage:parent,message:original) === original,"OFF original identity preserved")
        check(nagramiXReplyInfoMessage(context:context,parentMessage:parent,message:nil)==nil,"OFF archive invisible")
        check(soundActions(ordinary)==1,"OFF native sound action")
        check(soundActions(original)==0,"OFF view-once sound hidden")
        enabled=true
        let panel=Panel()
        var dismisses=0
        panel.dismiss={dismisses += 1}
        panel.nagramiXReplyMessageGeneration=1
        let stale=panel.missingAction(context:context,messageId:404,messageView:MessageView(message:nil),generation:1)
        panel.nagramiXReplyMessageGeneration=2
        stale()
        check(dismisses==0,"stale nil cannot cancel newer reply")
        let restored=panel.missingAction(context:context,messageId:42,messageView:MessageView(message:nil),generation:2)
        restored()
        check(dismisses==0,"late archive availability prevents cancellation")
        let missing=panel.missingAction(context:context,messageId:404,messageView:MessageView(message:nil),generation:2)
        missing()
        check(dismisses==1,"current missing reply dismisses native panel")
        let pending: () -> Void
        let probe: WeakPanel
        do { let gone=Panel();probe=WeakPanel(gone);pending=gone.missingAction(context:context,messageId:404,messageView:MessageView(message:nil),generation:0) }
        check(probe.value==nil,"queued cancel does not retain panel")
        pending()
        check(dismisses==1,"released panel cannot cancel reply")
        let interaction=Interaction(), menu=MenuController()
        replyAction(messages:[retained],interfaceInteraction:interaction)(menu,0)
        check(interaction.ids.count==1 && interaction.ids.first! == 42,"native real Reply target for retained file")
        check(interaction.textOnlyFallbacks==0,"no description-only replacement")
        check(menu.dismisses==1 && interaction.completions==1,"native context dismissal and completed action preserved")
        replyAction(messages:[original],interfaceInteraction:interaction)(menu,0)
        check(interaction.ids.count==2 && interaction.ids.last! == 42,"native original Reply unchanged")
        print("PASS temporary reply UI checks: \\(checks)")
    }
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--baseline',type=Path)
    p.add_argument('--swiftc',type=Path,required=True)
    p.add_argument('--report',type=Path)
    args=p.parse_args()
    texts=source_contract(args.source,args.baseline)
    runs=[];negative=[]
    with tempfile.TemporaryDirectory(prefix='temporary-reply-ui-') as folder:
        root=Path(folder)
        for mode in ['current','old-panel-gate','old-info-gate','no-parent-target','stale-generation','no-cancel-recheck','strong-cancel','duplicate-sound','text-only-reply','no-retained-delete','unowned-delete','duplicate-delete']:
            source=root/(mode+'.swift');source.write_text(fixture(texts,mode))
            for optimized in [False,True]:
                binary=root/(mode+('-O' if optimized else '-debug'))
                command=[str(args.swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(root/'module-cache')]
                if optimized:command+=['-O']
                subprocess.run([*command,str(source),'-o',str(binary)],check=True)
                result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
                if mode=='current':
                    assert result.returncode==0,result.stdout+result.stderr
                    runs.append(result.stdout.strip())
                else:
                    assert result.returncode==91 and 'reply UI regression:' in result.stderr,(mode,result.returncode,result.stdout,result.stderr)
                    negative.append({'mode':mode,'optimized':optimized,'diagnostic':result.stderr.strip()})
        for name in [PANEL,INFO,MENU]:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/name)],check=True)
    report={'production_runs':runs,'semantic_negatives':negative,'parse_files':3,'source_hashes':{name:hashlib.sha256((args.source/name).read_bytes()).hexdigest() for name in texts},'boundaries':'Actual reply-info resolver, native Reply action, thumbnail predicates, nil-cancel closure and Save Sound gate execute. UIKit, signal scheduling, archive and shared eligibility are bounded adapters tested separately. Live IDs/quotes/server attributes are unchanged; no receipt or RPC added.','native_sdk':'not run','physical_device':'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
