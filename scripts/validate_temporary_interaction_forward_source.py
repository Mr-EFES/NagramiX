#!/usr/bin/env python3
"""Execute the native-source classifier and the two real forwarding mappers.

Only source selection is exercised: immutable Message/Engine snapshots and the
archive are bounded adapters. No Apple SDK, network send or physical playback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
FORWARD = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
NODE = 'submodules/TelegramUI/Sources/ChatControllerNode.swift'
ALIAS = 'submodules/TelegramCore/Sources/TelegramEngine/Utils/EnginePostboxCoding.swift'
LOADER = '            let sortedMessages = messageIds.compactMap { id -> EngineRawMessage? in'
PREVIEW = '                    var messages = messageIds.compactMap { id -> Message? in'
OUTER = '                |> map { messages, accountPeer, options -> ([Message], Int32, Bool) in'
HELPER = 'func nagramiXNativeForwardSource('
DOC = '/// Native forwarding must keep a live server identity. Copy preparation can\n/// still prefer its retained resource; the two choices are separate intents.\n'


def read(source, name, support=None):
    path = source / name
    if not path.is_file() and support is not None:
        path = support / name
    assert path.is_file(), str(path)
    return path.read_text()


def verify(source, support, baseline):
    forward = read(source, FORWARD, support)
    node = read(source, NODE, support)
    helper = block(forward, HELPER)
    loader = block(forward, LOADER)
    preview = block(node, PREVIEW)
    plan_path = ROOT / 'ios/temporary_message_interaction_patches.json'
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else None
    if plan is not None and all(name in plan['outputs'] for name in (FORWARD, NODE)):
        for name, text in [(FORWARD, forward), (NODE, node)]:
            assert hashlib.sha256(text.encode()).hexdigest() == plan['outputs'][name], name
        if baseline is None:
            prior_forward = (ROOT / 'ios' / plan['previous'][FORWARD]).read_text()
            prior_node = (ROOT / 'ios' / plan['previous'][NODE]).read_text()
        else:
            prior_forward = (baseline / FORWARD).read_text()
            prior_node = (baseline / NODE).read_text()
    else:
        assert baseline is not None, 'Reviewed baseline required before the manifest exists'
        prior_forward = (baseline / FORWARD).read_text()
        prior_node = (baseline / NODE).read_text()
    # The whole source-selector file contains exactly the reviewed helper and
    # mapper changes. Node's native preview map reverses exactly; its independent
    # send-body changes are covered by validate_temporary_interaction_send.py.
    helper_region = DOC + helper + '\n\n'
    assert forward.count(helper_region) == 1, 'Unexpected native helper boundary'
    old_loader = block(prior_forward, LOADER)
    reversed_forward = forward.replace(helper_region, '', 1).replace(loader, old_loader, 1)
    assert reversed_forward == prior_forward, 'Forward source changed outside helper/mapper'
    old_preview = block(prior_node, '                    var messages = messageIds.compactMap {')
    outer = block(node, OUTER)
    assert outer.replace(preview, old_preview, 1) == block(prior_node, OUTER), 'Native preview changed outside source mapper'
    assert 'let messages = combineLatest(context.account.postbox.messagesAtIds(messageIds), accountPeerSignal, forward.options)' in node
    assert 'messageIds.map(TelegramEngine.EngineData.Item.Messages.Message.init)' in forward
    assert 'let live = (messages[id] ?? nil)?._asMessage()' in loader
    assert 'if transferMode == .forwardWithSource, let native = nagramiXNativeForwardSource(live)' in loader
    assert 'if !options.hideNames, let native = nagramiXNativeForwardSource(messagesById[id])' in preview
    assert 'public typealias EngineRawMessage = Message' in read(baseline or source, ALIAS, support)
    return forward, node, helper, loader, preview


def fixture(helper, loader, preview, mode):
    if mode == 'unconditional-archive-loader':
        start = loader.index('                let live =')
        loader = loader[:start] + '                return self.context.account.nagramiXMessageArchive.interactionMessage(id: id, liveMessage: (messages[id] ?? nil)?._asMessage())\n            }'
    elif mode == 'unconditional-archive-preview':
        start = preview.index('                        if !options.hideNames,')
        preview = preview[:start] + '                        return context.account.nagramiXMessageArchive.interactionMessage(id: id, liveMessage: messagesById[id])\n                    }'
    elif mode == 'wrong-native-eligibility':
        assert '!live.containsSecretMedia, ' in helper
        helper = helper.replace('!live.containsSecretMedia, ', '', 1)
    return '''import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
enum Namespaces { enum Message {static let Cloud=0;static let SecretIncoming=2;static let Local=1} }
struct MessageId:Hashable,Comparable {
    let namespace:Int;let value:Int
    init(_ value:Int,_ namespace:Int=Namespaces.Message.Cloud){self.namespace=namespace;self.value=value}
    static func <(lhs:Self,rhs:Self)->Bool {lhs.namespace==rhs.namespace ? lhs.value<rhs.value : lhs.namespace<rhs.namespace}
}
struct MessageFlags:OptionSet {
    let rawValue:Int
    static let Sending=Self(rawValue:1);static let Failed=Self(rawValue:2)
    var isSending:Bool {contains(.Sending)}
}
protocol Media:AnyObject {}
final class TelegramMediaExpiredContent:Media {}
final class Payload:Media {let name:String;init(_ name:String){self.name=name}}
protocol MessageAttribute:AnyObject {}
final class NagramiXArchivedMessageAttribute:MessageAttribute {}
final class Lifetime:MessageAttribute {let seconds:Int;init(_ seconds:Int){self.seconds=seconds}}
final class Message {
    let id:MessageId;let flags:MessageFlags;let containsSecretMedia:Bool
    let nagramiXRequiresFreeContentCopy:Bool;let media:[Media];let attributes:[MessageAttribute]
    let author:String;let text:String
    init(_ id:MessageId,flags:MessageFlags=[],secret:Bool=false,requiresFree:Bool=false,media:[Media]=[],attributes:[MessageAttribute]=[],author:String="original author",text:String="original caption") {
        self.id=id;self.flags=flags;containsSecretMedia=secret;nagramiXRequiresFreeContentCopy=requiresFree;self.media=media;self.attributes=attributes;self.author=author;self.text=text
    }
}
typealias EngineRawMessage=Message
struct EngineMessage {
    let value:Message
    init(_ value:Message){self.value=value}
    func _asMessage()->Message {value}
}
enum NagramiXMessageTransferMode:CaseIterable {case forwardWithSource,copyAsNew,forwardWithoutSource,copyToSingleRecipient}
final class Archive {
    var records:[MessageId:Message]=[:];var calls:[MessageId]=[]
    func interactionMessage(id:MessageId,liveMessage:Message?)->Message? {
        calls.append(id)
        return records[id] ?? liveMessage
    }
}
struct Account {let nagramiXMessageArchive:Archive}
struct Context {let account:Account}
struct Options {let hideNames:Bool}
''' + helper + '''
final class Controller {
    let context:Context
    init(_ archive:Archive){context=Context(account:Account(nagramiXMessageArchive:archive))}
    func load(_ messageIds:[MessageId],messages:[MessageId:EngineMessage?],transferMode:NagramiXMessageTransferMode)->[Message] {
''' + loader + '''.sorted {$0.id < $1.id}
        return sortedMessages
    }
}
func previewSources(_ messageIds:[MessageId],messagesById:[MessageId:Message],context:Context,options:Options)->[Message] {
''' + preview.replace('var messages =', 'let messages =', 1) + '''
    return messages
}
var checks=0
func check(_ value:@autoclosure()->Bool,_ diagnostic:String) {
    checks += 1
    if !value(){fputs("forward source regression: "+diagnostic+"\\n",stderr);exit(91)}
}
@main struct Tests {
    static func main() {
        let photo=Payload("actual photo"),video=Payload("actual video"),ttl=Lifetime(86400)
        let text=Message(MessageId(1),attributes:[ttl],text:"live auto-delete text")
        let group=Message(MessageId(2),media:[photo,video],attributes:[ttl],text:"live group album")
        let retained=Message(text.id,media:[Payload("retained snapshot")],attributes:[NagramiXArchivedMessageAttribute()],author:"retained author",text:"retained text")
        let archivedGroup=Message(group.id,media:[Payload("retained album")],attributes:[NagramiXArchivedMessageAttribute()],text:"retained group")
        check(nagramiXNativeForwardSource(nil)==nil,"nil source is ineligible")
        check(nagramiXNativeForwardSource(text)===text,"alive TTL text stays native")
        check(nagramiXNativeForwardSource(group)===group,"alive TTL group stays native")
        let secret=Message(MessageId(3),secret:true,media:[video],attributes:[ttl])
        let protected=Message(MessageId(4),requiresFree:true,media:[photo],attributes:[ttl])
        let expired=Message(MessageId(5),media:[TelegramMediaExpiredContent()])
        let secretNamespace=Message(MessageId(6,Namespaces.Message.SecretIncoming),requiresFree:true,media:[video],attributes:[ttl])
        let local=Message(MessageId(7,Namespaces.Message.Local),media:[photo])
        let sending=Message(MessageId(8),flags:.Sending)
        let failed=Message(MessageId(9),flags:.Failed)
        check(nagramiXNativeForwardSource(secret)==nil,"secret-media source is ineligible")
        for source in [protected,expired,secretNamespace,local,sending,failed,retained] {
            check(nagramiXNativeForwardSource(source)==nil,"restricted/expired/archived source is ineligible")
        }
        let archive=Archive(),controller=Controller(Archive())
        let nativeController=Controller(archive)
        archive.records=[text.id:retained,group.id:archivedGroup]
        let engine:[MessageId:EngineMessage?]=[text.id:EngineMessage(text),group.id:EngineMessage(group)]
        let loaded=nativeController.load([group.id,text.id],messages:engine,transferMode:.forwardWithSource)
        check(loaded.count==2 && loaded[0]===text && loaded[1]===group,"native loader preserves live ID/author without retained query")
        check(archive.calls.isEmpty,"native loader never queries available retained snapshot")
        check(loaded[0].attributes.first===ttl && loaded[1].media[0]===photo && loaded[1].media[1]===video,"native loader preserves TTL and actual immutable media")
        check(loaded[0].author=="original author" && loaded[0].text=="live auto-delete text","native loader keeps original authorship/caption")
        for mode in [NagramiXMessageTransferMode.copyAsNew,.forwardWithoutSource,.copyToSingleRecipient] {
            archive.calls=[]
            let values=nativeController.load([text.id,group.id],messages:engine,transferMode:mode)
            check(values.count==2 && values[0]===retained && values[1]===archivedGroup,"copy mode resolves retained payload")
            check(archive.calls==[text.id,group.id],"copy mode calls archive for every source")
        }
        for source in [secret,protected,expired,secretNamespace,local,sending,failed,retained] {
            let copy=Message(source.id,attributes:[NagramiXArchivedMessageAttribute()],text:"resolved retained")
            archive.records[source.id]=copy;archive.calls=[]
            let values=nativeController.load([source.id],messages:[source.id:EngineMessage(source)],transferMode:.forwardWithSource)
            check(values.count==1 && values[0]===copy && archive.calls==[source.id],"ineligible native loader still resolves retained payload")
        }
        let missing=MessageId(99)
        archive.records[missing]=Message(missing,attributes:[NagramiXArchivedMessageAttribute()]);archive.calls=[]
        check(nativeController.load([missing],messages:[:],transferMode:.forwardWithSource).first===archive.records[missing],"missing live ID resolves retained payload")
        check(archive.calls==[missing],"missing loader asks archive")
        check(controller.load([missing],messages:[:],transferMode:.forwardWithSource).isEmpty,"missing source without retained data remains absent")
        // Restore colliding text record overwritten by the archived-source case.
        archive.records[text.id]=retained;archive.records[group.id]=archivedGroup;archive.calls=[]
        let liveById=[text.id:text,group.id:group]
        let nativePreview=previewSources([group.id,text.id],messagesById:liveById,context:nativeController.context,options:Options(hideNames:false))
        check(nativePreview.count==2 && nativePreview[0]===group && nativePreview[1]===text,"native preview preserves live ID/author without retained query")
        check(archive.calls.isEmpty,"native preview never queries available retained snapshot")
        check(nativePreview[0].media[0]===photo && nativePreview[1].attributes.first===ttl,"native preview keeps actual media and original TTL")
        archive.calls=[]
        let copiedPreview=previewSources([text.id,group.id],messagesById:liveById,context:nativeController.context,options:Options(hideNames:true))
        check(copiedPreview.count==2 && copiedPreview[0]===retained && copiedPreview[1]===archivedGroup,"hideNames preview resolves retained copies")
        check(archive.calls==[text.id,group.id],"hideNames preview asks archive for both sources")
        for source in [secret,protected,expired,secretNamespace,local,sending,failed] {
            archive.calls=[]
            let values=previewSources([source.id],messagesById:[source.id:source],context:nativeController.context,options:Options(hideNames:false))
            check(values.count==1 && values[0]===archive.records[source.id] && archive.calls==[source.id],"ineligible preview resolves retained payload")
        }
        archive.calls=[]
        check(previewSources([missing],messagesById:[:],context:nativeController.context,options:Options(hideNames:false)).first===archive.records[missing],"missing preview resolves retained payload")
        check(archive.calls==[missing],"missing preview asks archive")
        check(previewSources([MessageId(100)],messagesById:[:],context:nativeController.context,options:Options(hideNames:false)).isEmpty,"missing preview without archive stays absent")
        print("PASS forward source checks: \\(checks)")
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--support', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    forward, node, helper, loader, preview = verify(args.source, args.support, args.baseline)
    expected = {
        'unconditional-archive-loader': 'native loader preserves live ID/author without retained query',
        'unconditional-archive-preview': 'native preview preserves live ID/author without retained query',
        'wrong-native-eligibility': 'secret-media source is ineligible',
    }
    runs, negatives = [], []
    with tempfile.TemporaryDirectory(prefix='temporary-forward-source-') as folder:
        folder = Path(folder)
        for mode in ['current', *expected]:
            source = folder / (mode + '.swift')
            source.write_text(fixture(helper, loader, preview, mode))
            for optimized in [False, True]:
                binary = folder / (mode + ('-O' if optimized else '-debug'))
                command = [str(args.swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(folder / 'cache')]
                if optimized: command.append('-O')
                subprocess.run([*command, str(source), '-o', str(binary)], check=True)
                result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                    preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
                if mode == 'current':
                    assert result.returncode == 0, result.stdout + result.stderr
                    runs.append({'optimized': optimized, 'result': result.stdout.strip()})
                else:
                    assert result.returncode == 91 and expected[mode] in result.stderr, (mode, result.stdout, result.stderr)
                    negatives.append({'mode': mode, 'optimized': optimized, 'diagnostic': result.stderr.strip()})
        for name, text in [(FORWARD, forward), (NODE, node)]:
            path = folder / Path(name).name
            path.write_text(text)
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(path)], check=True)
    report = {'production_runs': runs, 'semantic_negatives': negatives,
        'source_sha256': {FORWARD: hashlib.sha256(forward.encode()).hexdigest(), NODE: hashlib.sha256(node.encode()).hexdigest()},
        'source_boundaries': 'Forward whole file reverses exactly to stage 8; Node enclosing native forward-preview map reverses exactly to stage 8.',
        'runtime_boundaries': 'Actual helper and both compactMap closures execute. Engine snapshots, immutable Message flags/media/attributes, archive preference and transfer options are adapters; sender and server are not executed.',
        'parse_files': 2, 'native_sdk': 'not run', 'physical_device': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
