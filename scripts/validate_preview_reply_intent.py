#!/usr/bin/env python3
"""Проверить передачу ответа из preview через восстановление черновика и замену экрана."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'preview_reply_intent_patches.json').read_text())
L = 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift'
C = 'submodules/TelegramUI/Sources/ChatController.swift'
INTERFACE = 'submodules/ChatInterfaceState/Sources/ChatInterfaceState.swift'
PRESENTATION = 'submodules/ChatPresentationInterfaceState/Sources/ChatPresentationInterfaceState.swift'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(source):
    for name, expected in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha(source / name) == expected, name
    for name, expected in PLAN['templates'].items():
        assert sha(OVERLAY / name) == expected, name
    load = (source / L).read_text()
    chat = (source / C).read_text()
    old_load = (OVERLAY / PLAN['previous'][L]).read_text()
    for marker in ['        let interfaceInteraction = ChatPanelInterfaceInteraction(setupReplyMessage:', '            guard !strongSelf.presentAccountFrozenInfoIfNeeded(delay: true) else {']:
        assert marker in load
    marker = '            guard !strongSelf.presentAccountFrozenInfoIfNeeded(delay: true) else {'
    end = '        }, setupEditMessage:'
    assert load[load.index(marker, load.index('let interfaceInteraction =')):load.index(end)] == old_load[old_load.index(marker, old_load.index('let interfaceInteraction =')):old_load.index(end)]
    reply = load[load.index('        let interfaceInteraction = ChatPanelInterfaceInteraction(setupReplyMessage:'):load.index(end)]
    preview = block(reply, '            if strongSelf.nagramiXReadHistoryDisabled {')
    assert preview.index('completion(.immediate, { [weak self]') < preview.index('nagramiXStagePreviewReply(') < preview.index('self.context.sharedContext.navigateToChatController(')
    assert 'activateInput: .text, keepStack: .always, useExisting: false' in preview
    assert 'active.nagramiXKeepFullChatForPreviewReply = true' in preview
    assert 'navigationController.viewControllers.last === self' in preview
    assert 'completion: { [weak active]' in preview and 'committed === active' in preview
    assert 'navigationController.viewControllers.last === active' in preview
    assert 'let nagramiXReadHistoryDisabled: Bool' in chat
    navigation = (source / 'submodules/TelegramUI/Sources/NavigateToChatController.swift').read_text()
    assert navigation.index('if requiresAgeVerification,') < navigation.index('if let pushController = params.pushController')
    assert 'params.completion(controller)' in navigation
    api = (source / 'submodules/AccountContext/Sources/AccountContext.swift').read_text()
    assert 'pushController: ((ChatController, Bool, @escaping () -> Void) -> Void)? = nil,' in api
    native = (source / PRESENTATION).read_text()
    for signature in ['public func updatedInterfaceState(_ f: (ChatInterfaceState) -> ChatInterfaceState)', 'public func updatedReplyMessage(_ replyMessage: Message?)', 'public func updatedEditMessageState(_ editMessageState: ChatEditInterfaceMessageState?)', 'public func updatedSearch(_ search: ChatSearchData?)', 'public func updatedShowCommands(_ showCommands: Bool)']:
        assert signature in native, signature
    assert 'self.contentDataUpdated(synchronous: true' in load
    first = load.index('self.contentDataUpdated(synchronous: true')
    assert first < load.index('self.contentDataReady.set(true)', first)


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('preview_reply_intent', OVERLAY / 'preview_reply_intent.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []
    def seed(label):
        target = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            origin = OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(origin.read_bytes())
        return target
    def reject(target, label, overlay=OVERLAY):
        before = manifest(target)
        try:
            module.apply_preview_reply_intent(target, overlay)
        except (SystemExit, OSError, KeyError):
            pass
        else:
            raise AssertionError('Неверный вход принят: ' + label)
        assert before == manifest(target), 'Частичная запись: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_preview_reply_intent(valid, OVERLAY)
    assert all(sha(valid / name) == expected for name, expected in PLAN['outputs'].items())
    reject(valid, 'повторное применение')
    for name in {**PLAN['inputs'], **PLAN['guards']}:
        for kind in ['missing', 'drift']:
            target = seed(str(len(rejected)))
            if kind == 'missing': (target / name).unlink()
            else: (target / name).write_bytes((target / name).read_bytes() + b'\n// drift\n')
            reject(target, kind + ':' + name)
    mutations = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        mutations.append((field, bad))
    for key, value in [('required_previous_stage', 'upstream_13_2_release_string_compile'), ('target_pin', '0' * 40)]:
        bad = copy.deepcopy(PLAN); bad[key] = value; mutations.append((key, bad))
    bad = copy.deepcopy(PLAN); bad['previous'][L] = '../outside'; mutations.append(('template-traversal', bad))
    bad = copy.deepcopy(PLAN)
    for field in ['inputs', 'outputs', 'previous', 'replacements']:
        bad[field]['../outside'] = bad[field].pop(L)
    mutations.append(('source-traversal', bad))
    for label, bad in mutations:
        overlay = temp / ('bad-' + label)
        overlay.mkdir()
        for name in PLAN['templates']:
            path = overlay / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / name).read_bytes())
        (overlay / 'preview_reply_intent_patches.json').write_text(json.dumps(bad))
        reject(seed('root-' + label), label, overlay)
    return rejected


def fixture(source, mode='current'):
    chat = (source / C).read_text()
    load = (source / L).read_text()
    native = (source / INTERFACE).read_text()
    subject = block(native, '    public struct ReplyMessageSubject:').replace('public ', '')
    getters = '\n'.join(block(native, marker).replace('public ', '') for marker in ['    public func withUpdatedReplyMessageSubject(', '    public func withUpdatedEditMessage('])
    stage = block(chat, '    func nagramiXStagePreviewReply(')
    hydrate = block(load, '            if let pendingPreviewReply, !self.nagramiXReadHistoryDisabled, self.chatLocation == pendingPreviewReply.location {')
    commit = block(load[load.index('pushController: { [weak self] controller, animated, completion in'):], 'pushController: { [weak self] controller, animated, completion in')[len('pushController: '):]
    pending = '''let pendingPreviewReply = self.nagramiXPendingPreviewReply
        self.nagramiXPendingPreviewReply = nil'''
    if mode == 'no-pending':
        stage = stage.replace('self.nagramiXPendingPreviewReply = (location: self.chatLocation, message: message, subject: subject)', 'self.nagramiXPendingPreviewReply = nil')
    elif mode == 'late-only':
        start = stage.index('        self.updateChatPresentationInterfaceState(')
        stage = stage[:start] + '        return true\n    }'
    elif mode == 'wrong-location':
        hydrate = hydrate.replace(', self.chatLocation == pendingPreviewReply.location', '')
    elif mode == 'repeat-intent':
        pending = 'let pendingPreviewReply = self.nagramiXPendingPreviewReply'
    elif mode == 'old-stack':
        commit = '{ controller, animated, completion in navigationController.replaceControllersAndPush(controllers: navigationController.viewControllers, controller: controller, animated: animated, completion: completion) }'
    elif mode == 'stale-commit':
        commit = commit.replace('guard let self, navigationController.viewControllers.last === self else { return }', 'guard let self else { return }')
    fields = [('timestamp','Int32','1'), ('composeInputState','String','""'), ('composeDisableUrlPreviews','[String]','[]'), ('replyMessageSubject','ReplyMessageSubject?','nil'), ('forwardMessageIds','[EngineMessage.Id]?','nil'), ('forwardOptionsState','Int?','nil'), ('editMessage','ChatEditMessageState?','nil'), ('selectionState','Int?','nil'), ('messageActionsState','Int','0'), ('historyScrollState','Int?','nil'), ('mediaRecordingMode','Int','0'), ('mediaDraftState','Int?','nil'), ('silentPosting','Bool','false'), ('inputLanguage','String?','nil'), ('sendMessageEffect','Int64?','nil'), ('postSuggestionState','Int?','nil')]
    declarations = '\n'.join('let '+name+': '+typ for name,typ,_ in fields)
    initializer = 'init('+', '.join(name+': '+typ+' = '+default for name,typ,default in fields)+') {\n'+'\n'.join('self.'+name+' = '+name for name,_,_ in fields)+'\n}'
    return '''import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
// AVKit/UIKit, loading, full presentation layout and navigation are explicit adapters.
// The stage helper, intent hydration, preview commit, ReplySubject, and two native
// immutable ChatInterfaceState getters below are extracted from guarded source.
struct MessageId: Codable, Equatable { var peerId: Int64; var id: Int32 }
enum EngineMessage { typealias Id = MessageId }
struct EngineMessageReplyQuote: Codable, Equatable { var text: String }
struct EngineMessageReplyInnerSubject: Codable, Equatable { var value: String }
struct EngineMessageReplySubject { var messageId: MessageId; var quote: EngineMessageReplyQuote?; var innerSubject: EngineMessageReplyInnerSubject? }
struct Message: Equatable { var id: MessageId; var text: String }
typealias ChatEditMessageState = Int
final class ChatInterfaceState {
'''+subject+'\n'+declarations+'\n'+initializer+'\n'+getters+'''
}
struct ChatPresentationInterfaceState {
    var interfaceState = ChatInterfaceState()
    var replyMessage: Message?
    var editMessageState: Int?
    var search: String? = "search"
    var showCommands = true
    func updatedInterfaceState(_ f: (ChatInterfaceState) -> ChatInterfaceState) -> Self { var r=self;r.interfaceState=f(r.interfaceState);return r }
    func updatedReplyMessage(_ value: Message?) -> Self { var r=self;r.replyMessage=value;return r }
    func updatedEditMessageState(_ value: Int?) -> Self { var r=self;r.editMessageState=value;return r }
    func updatedSearch(_ value: String?) -> Self { var r=self;r.search=value;return r }
    func updatedShowCommands(_ value: Bool) -> Self { var r=self;r.showCommands=value;return r }
}
struct ChatLocation: Equatable { var peerId: Int64?; var threadId: Int64? }
class ViewController {}
final class NavigationController {
    var viewControllers: [ViewController]
    var commits = 0
    init(_ controllers: [ViewController]) { viewControllers=controllers }
    func replaceControllersAndPush(controllers: [ViewController], controller: ViewController, animated: Bool, completion: @escaping () -> Void) { viewControllers=controllers+[controller];commits += 1;completion() }
}
typealias PreviewCommit = (ViewController, Bool, @escaping () -> Void) -> Void
final class ChatControllerImpl: ViewController {
    let nagramiXReadHistoryDisabled: Bool
    var chatLocation: ChatLocation
    var nagramiXPendingPreviewReply: (location: ChatLocation, message: Message, subject: ChatInterfaceState.ReplyMessageSubject)?
    var presentationInterfaceState = ChatPresentationInterfaceState()
    var loads = 0
    var saved = 0
    var nativeEditRestorations = 0
    var displayNode: Int { loads += 1; return 0 }
    init(readonly: Bool = false, peerId: Int64 = 7, threadId: Int64? = nil) { nagramiXReadHistoryDisabled=readonly;chatLocation=ChatLocation(peerId:peerId,threadId:threadId) }
    func updateChatPresentationInterfaceState(animated: Bool, interactive: Bool, saveInterfaceState: Bool, _ f: (ChatPresentationInterfaceState) -> ChatPresentationInterfaceState) { presentationInterfaceState=f(presentationInterfaceState);if saveInterfaceState { saved += 1 } }
'''+stage+'''
    func hydrate(_ initialInterfaceState: ChatInterfaceState?) {
        '''+pending+'''
        var presentationInterfaceState = self.presentationInterfaceState
        presentationInterfaceState = presentationInterfaceState.updatedInterfaceState { interfaceState in
            var interfaceState = interfaceState
            if let initialInterfaceState { interfaceState = initialInterfaceState }
            return interfaceState
        }
'''+hydrate+'''
        else if initialInterfaceState?.editMessage != nil { nativeEditRestorations += 1 }
        self.presentationInterfaceState = presentationInterfaceState
    }
    func makeCommit(_ navigationController: NavigationController) -> PreviewCommit { return '''+commit+''' }
}
final class WeakProbe { weak var value: ChatControllerImpl?; init(_ value: ChatControllerImpl) { self.value=value } }
var checks=0
func check(_ value: @autoclosure () -> Bool, _ label: String) {
    if !value() { FileHandle.standardError.write(Data(("preview regression: "+label+"\\n").utf8));exit(91) };checks += 1
}
@main struct Main {
    static func main() {
        let message=Message(id: MessageId(peerId:7,id:42),text:"chosen")
        let subject=ChatInterfaceState.ReplyMessageSubject(messageId:message.id,quote:EngineMessageReplyQuote(text:"quote"),innerSubject:EngineMessageReplyInnerSubject(value:"inner"))
        let draftSubject=ChatInterfaceState.ReplyMessageSubject(messageId:MessageId(peerId:7,id:2),quote:nil,innerSubject:nil)
        for thread in [nil,Int64(99)] {
            let active=ChatControllerImpl(threadId:thread)
            check(active.nagramiXStagePreviewReply(message:message,subject:subject),"stage")
            check(active.loads==1,"stage loads node")
            check(active.saved==0,"staging must not save before hydration")
            check(active.presentationInterfaceState.interfaceState.replyMessageSubject==subject,"reply visible before push")
            check(active.presentationInterfaceState.replyMessage==message,"message visible before push")
            check(active.presentationInterfaceState.search==nil && !active.presentationInterfaceState.showCommands,"clear search and commands")
            let draft=ChatInterfaceState(composeInputState:"saved draft",replyMessageSubject:draftSubject,editMessage:73,silentPosting:true,inputLanguage:"ru")
            active.hydrate(draft)
            check(active.presentationInterfaceState.interfaceState.replyMessageSubject==subject,"reply survives saved draft")
            check(active.presentationInterfaceState.replyMessage==message,"chosen reply message survives")
            check(active.presentationInterfaceState.interfaceState.editMessage==nil,"old edit cannot replace reply")
            check(active.presentationInterfaceState.editMessageState==nil && active.nativeEditRestorations==0,"old edit layout is not restored")
            check(active.presentationInterfaceState.interfaceState.composeInputState=="saved draft","draft text preserved")
            check(active.presentationInterfaceState.interfaceState.silentPosting && active.presentationInterfaceState.interfaceState.inputLanguage=="ru","other draft settings preserved")
            check(active.nagramiXPendingPreviewReply==nil,"intent consumed exactly once")
            active.presentationInterfaceState.interfaceState=active.presentationInterfaceState.interfaceState.withUpdatedReplyMessageSubject(nil)
            active.hydrate(nil)
            check(active.presentationInterfaceState.interfaceState.replyMessageSubject==nil,"later update does not restore cancelled reply")
        }
        let ordinary=ChatControllerImpl()
        ordinary.hydrate(ChatInterfaceState(composeInputState:"ordinary",replyMessageSubject:draftSubject,editMessage:19))
        check(ordinary.presentationInterfaceState.interfaceState.replyMessageSubject==draftSubject,"ordinary saved reply unchanged")
        check(ordinary.nativeEditRestorations==1,"ordinary edit restoration unchanged")
        let readonly=ChatControllerImpl(readonly:true)
        check(!readonly.nagramiXStagePreviewReply(message:message,subject:subject),"readonly never activated")
        check(readonly.loads==0 && readonly.nagramiXPendingPreviewReply==nil,"readonly policy unchanged")
        let other=ChatControllerImpl(peerId:8)
        check(!other.nagramiXStagePreviewReply(message:message,subject:subject),"cross-peer rejected")
        let mismatched=ChatControllerImpl()
        check(!mismatched.nagramiXStagePreviewReply(message:message,subject:draftSubject),"mismatched subject rejected")
        let changed=ChatControllerImpl()
        check(changed.nagramiXStagePreviewReply(message:message,subject:subject),"stage before location change")
        changed.chatLocation=ChatLocation(peerId:8,threadId:nil)
        changed.hydrate(ChatInterfaceState(replyMessageSubject:draftSubject,editMessage:31))
        check(changed.presentationInterfaceState.interfaceState.replyMessageSubject==draftSubject,"changed location cancels reply intent")
        check(changed.nativeEditRestorations==1 && changed.nagramiXPendingPreviewReply==nil,"changed location keeps native restoration")
        let root=ViewController(), folder=ViewController(), preview=ChatControllerImpl(readonly:true)
        let nav=NavigationController([root,folder,preview])
        let active=ChatControllerImpl()
        check(active.nagramiXStagePreviewReply(message:message,subject:subject),"stage before navigation")
        let commit=preview.makeCommit(nav)
        var completions=0
        commit(active,true,{completions += 1})
        check(nav.commits==1 && completions==1,"one committed navigation")
        check(nav.viewControllers.count==3 && nav.viewControllers[0]===root && nav.viewControllers[1]===folder && nav.viewControllers.last===active,"replace only preview preserving prior stack")
        active.hydrate(ChatInterfaceState(replyMessageSubject:draftSubject))
        check(active.presentationInterfaceState.interfaceState.replyMessageSubject==subject,"delayed content load after navigation completion")
        commit(ChatControllerImpl(),true,{completions += 1})
        check(nav.commits==1 && completions==1,"duplicate commit ignored")
        _=nav.viewControllers.popLast()
        check(nav.viewControllers.last===folder,"one Back reaches previous menu")
        commit(ChatControllerImpl(),true,{completions += 1})
        check(nav.viewControllers.last===folder && nav.commits==1,"stale commit after Back ignored")
        let nav2=NavigationController([root])
        let deferred: PreviewCommit
        let weakProbe: WeakProbe
        do { let gone=ChatControllerImpl(readonly:true);weakProbe=WeakProbe(gone);deferred=gone.makeCommit(nav2) }
        check(weakProbe.value==nil,"deferred closure does not retain preview")
        deferred(ChatControllerImpl(),true,{completions += 1})
        check(nav2.viewControllers.count==1 && nav2.commits==0,"released preview cannot navigate")
        let last=ChatControllerImpl()
        check(last.nagramiXStagePreviewReply(message:message,subject:subject),"first intent")
        let newMessage=Message(id:MessageId(peerId:7,id:99),text:"latest")
        let newSubject=ChatInterfaceState.ReplyMessageSubject(messageId:newMessage.id,quote:nil,innerSubject:nil)
        check(last.nagramiXStagePreviewReply(message:newMessage,subject:newSubject),"latest intent")
        last.hydrate(ChatInterfaceState(replyMessageSubject:draftSubject))
        check(last.presentationInterfaceState.interfaceState.replyMessageSubject==newSubject && last.presentationInterfaceState.replyMessage==newMessage,"latest staged action wins")
        print("PASS preview reply production checks: \\(checks)")
    }
}
'''


def runtime_checks(source, swiftc, temp):
    runs, negatives = [], []
    for mode in ['current', 'no-pending', 'late-only', 'wrong-location', 'repeat-intent', 'old-stack', 'stale-commit']:
        suite = temp / (mode + '.swift')
        suite.write_text(fixture(source, mode))
        for optimized in [False, True]:
            binary = temp / (mode + ('-O' if optimized else '-debug'))
            cmd = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp/'cache')]
            if optimized: cmd += ['-O']
            subprocess.run([*cmd, str(suite), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0,0)))
            if mode == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                runs.append(result.stdout.strip())
            else:
                assert result.returncode == 91 and 'preview regression:' in result.stderr, mode + ':' + result.stdout + result.stderr
                negatives.append({'mode':mode, 'optimized':optimized, 'diagnostic':result.stderr.strip()})
    return runs, negatives


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='preview-reply-intent-') as folder:
        temp=Path(folder)
        rejected=guard_checks(args.source,temp)
        runs, negatives=runtime_checks(args.source,args.swiftc,temp) if args.swiftc else ([],[])
        if args.swiftc:
            for name in PLAN['outputs']:
                subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/name)],check=True)
    result={'outputs':PLAN['outputs'],'guards':len(PLAN['guards']),'fail_closed':rejected,'production_runs':runs,'semantic_negatives':negatives,'swift_parse_files':2 if args.swiftc else 0,'boundaries':'Actual stage helper, hydration branch, preview commit, native reply subject and immutable ChatInterfaceState getters execute; UIKit/loading/full presentation/navigation are adapters. Native APIs are checked against 12 exact guards.','apple_sdk':'not run','physical_device':'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
