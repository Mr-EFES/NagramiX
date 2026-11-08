#!/usr/bin/env python3
"""Проверить выбор native/signed репоста и наличие фото в контекстных действиях."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block

ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
FILE='submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift'
HELPER='submodules/TelegramUI/Sources/Chat/NagramiXTemporaryReplySend.swift'


def verify(source):
    text=(source/FILE).read_text()
    path=OVERLAY/'temporary_message_interaction_patches.json'
    if path.exists():
        plan=json.loads(path.read_text())
        assert hashlib.sha256((source/FILE).read_bytes()).hexdigest()==plan['outputs'][FILE]
        assert set(plan['copies'])=={HELPER}
        assert hashlib.sha256((source/HELPER).read_bytes()).hexdigest()==plan['copies'][HELPER]['sha256']
    assert 'let nagramiXReplayCopy = ' not in text
    assert 'chatCopyProtected: chatPresentationInterfaceState.copyProtectionEnabled' in text
    assert 'if nagramiXTemporarySelection, !nagramiXNativeRepost, nagramiXCanCopySelection {' in text
    native=block(text,'            if nagramiXNativeRepost {')
    assert 'interfaceInteraction.forwardMessages(messagesToForward)' in native
    signed=block(text,'        if nagramiXTemporarySelection, !nagramiXNativeRepost, nagramiXCanCopySelection {')
    assert 'controller.presentAccountFrozenInfoIfNeeded(delay: true)' in signed
    assert 'controller.commitPurposefulAction()' in signed
    assert signed.index('presentAccountFrozenInfoIfNeeded') < signed.index('commitPurposefulAction') < signed.index('controller.forwardMessages(messages: copies.sorted')
    assert 'transferMode: .copyToSingleRecipient, nagramiXTransferTitle: chatPresentationInterfaceState.strings.nagramiXForwardWithAuthor' in signed
    assert 'interfaceInteraction.forwardMessages(copies)' not in signed
    assert 'return nagramiXTemporaryReplySignedSource(original, authorName: author)' in signed
    helper=(source/HELPER).read_text()
    sign=block(helper,'func nagramiXTemporaryReplySignedSource(')
    assert 'page.rawMedia' not in sign and 'rawMedia:' not in sign
    assert 'media: page.media' in sign
    page=(source/'submodules/TelegramCore/Sources/SyncCore/SyncCore_InstantPage.swift').read_text()
    assert 'public let media: [EngineMedia.Id: EngineMedia]' in page
    assert 'public convenience init(blocks: [InstantPageBlock], media: [EngineMedia.Id: EngineMedia], isComplete: Bool, rtl: Bool, url: String, views: Int32?)' in page
    assert 'if !messages[0].containsSecretMedia || nagramiXCanUseTemporaryMediaActions(messages[0]) {' in text
    actual=(source/'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift').read_text()
    assert 'func forwardMessages(messages: [EngineRawMessage]' in actual
    assert 'nagramiXTransferTitle: String? = nil)' in actual
    assert 'case copyToSingleRecipient' in actual
    return text,helper


def fixture(text,helper,mode='current'):
    sign=block(helper,'func nagramiXTemporaryReplySignedSource(')
    ordinary=block(text,'private func nagramiXCanRepostMessages(')
    native=block(text,'private func nagramiXCanUseNativeRepost(')
    signed=block(text,'        if nagramiXTemporarySelection, !nagramiXNativeRepost, nagramiXCanCopySelection {')
    marker='action: { _, f in'
    signed_action=block(signed[signed.index(marker):],marker)[len('action: '):]
    native_action=block(block(text,'            if nagramiXNativeRepost {'),marker)[len('action: '):]
    photo=block(text,'                if !messages[0].containsSecretMedia || nagramiXCanUseTemporaryMediaActions(messages[0]) {')
    if mode=='old-native-routing': native=native.replace('return hasForwardPermission','return !messages.contains(where: { nagramiXCanUseTemporaryMediaActions($0) }) && hasForwardPermission')
    elif mode=='generic-signed-callback':
        old='''controller.forwardMessages(messages: copies.sorted(by: { $0.id < $1.id }), resetCurrent: false,
                    transferMode: .copyToSingleRecipient, nagramiXTransferTitle: chatPresentationInterfaceState.strings.nagramiXForwardWithAuthor)'''
        assert old in signed_action
        signed_action=signed_action.replace(old,'interfaceInteraction.forwardMessages(copies)')
    elif mode=='old-photo-gate': photo=photo.replace(' || nagramiXCanUseTemporaryMediaActions(messages[0])','')
    elif mode=='wrong-entity-offset': sign=sign.replace('prefix.utf16.count','prefix.count')
    elif mode=='missing-rich-signature': sign=sign.replace('[.paragraph(.plain(authorName + ":"))] + page.blocks','page.blocks')
    elif mode=='lost-rich-media': sign=sign.replace('media: page.media','media: [:]')
    elif mode=='no-frozen-check': signed_action=signed_action.replace('guard !controller.presentAccountFrozenInfoIfNeeded(delay: true) else { f(.default); return }','')
    return '''import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
// Actual source predicates, image-resource lookup and both menu action closures
// execute. Message storage, presentation strings, UI dismissal and the send API
// are explicit adapters; the actual copy transport is tested separately.
enum Namespaces { enum Message { static let Cloud=0;static let SecretIncoming=2 } }
struct MessageId:Equatable,Comparable,Hashable,ExpressibleByIntegerLiteral {
    let namespace:Int
    let value:Int64
    init(integerLiteral:Int64){namespace=0;value=integerLiteral}
    init(namespace:Int,value:Int64){self.namespace=namespace;self.value=value}
    static func <(lhs:Self,rhs:Self)->Bool {lhs.namespace==rhs.namespace ? lhs.value<rhs.value : lhs.namespace<rhs.namespace}
}
protocol MessageAttribute:AnyObject {}
final class NagramiXArchivedMessageAttribute:MessageAttribute {}
final class OtherAttribute:MessageAttribute {}
indirect enum RichText:Equatable {case plain(String),bold(RichText)}
enum InstantPageBlock:Equatable {case paragraph(RichText)}
final class InstantPage {
    let blocks:[InstantPageBlock];let media:[Int:String];let isComplete:Bool;let rtl:Bool;let url:String;let views:Int32?
    init(blocks:[InstantPageBlock],media:[Int:String],isComplete:Bool,rtl:Bool,url:String,views:Int32?) {self.blocks=blocks;self.media=media;self.isComplete=isComplete;self.rtl=rtl;self.url=url;self.views=views}
}
final class RichTextMessageAttribute:MessageAttribute {let instantPage:InstantPage;let fullInstantPage:InstantPage?;init(instantPage:InstantPage,fullInstantPage:InstantPage?) {self.instantPage=instantPage;self.fullInstantPage=fullInstantPage}}
struct MessageTextEntity:Equatable {let range:Range<Int>;let type:String}
final class TextEntitiesMessageAttribute:MessageAttribute {let entities:[MessageTextEntity];init(entities:[MessageTextEntity]){self.entities=entities}}
struct Peer {let name:String}
struct EnginePeer {let peer:Peer;init(_ peer:Peer){self.peer=peer};func displayTitle(strings:Strings,displayOrder:Int)->String {peer.name}}
final class Message {
    let id:MessageId
    let containsSecretMedia:Bool
    let temporary:Bool
    let protected:Bool
    let nagramiXRequiresFreeContentCopy:Bool
    let attributes:[MessageAttribute]
    let author:Peer?
    let text:String
    let media:String
    init(_ id:MessageId,secret:Bool=false,temporary:Bool=false,protected:Bool=false,requiresFree:Bool=false,attributes:[MessageAttribute]=[],author:Peer?=nil,text:String="caption",media:String="original media") {self.id=id;containsSecretMedia=secret;self.temporary=temporary;self.protected=protected;nagramiXRequiresFreeContentCopy=requiresFree;self.attributes=attributes;self.author=author;self.text=text;self.media=media}
    func isCopyProtected()->Bool {protected}
    func withUpdatedText(_ value:String)->Message {Message(id,secret:containsSecretMedia,temporary:temporary,protected:protected,requiresFree:nagramiXRequiresFreeContentCopy,attributes:attributes,author:author,text:value,media:media)}
    func withUpdatedAttributes(_ value:[MessageAttribute])->Message {Message(id,secret:containsSecretMedia,temporary:temporary,protected:protected,requiresFree:nagramiXRequiresFreeContentCopy,attributes:value,author:author,text:text,media:media)}
}
typealias EngineRawMessage=Message
var temporaryEnabled=true
var copiesAllowed=true
func nagramiXCanUseTemporaryMediaActions(_ message:Message)->Bool {temporaryEnabled && message.temporary}
func nagramiXCanCopyMessagesAsNew(_ messages:[Message],accountPeerId:Int64)->Bool {copiesAllowed && !messages.isEmpty}
'''+ordinary+'\n'+native+'\n'+sign+'''
struct Strings {let nagramiXForwardWithAuthor="Repost";let User_DeletedAccount="Deleted Account"}
struct Presentation {let strings=Strings();let nameDisplayOrder=0}
struct Account {let peerId:Int64=1}
struct Context {let account=Account()}
enum Mode:Equatable {case copyToSingleRecipient}
class ViewController {}
final class ChatControllerImpl:ViewController {
    var frozen=false
    var purposes=0
    var batches:[[Message]]=[]
    var titles:[String]=[]
    var reset:[Bool]=[]
    var modes:[Mode]=[]
    func presentAccountFrozenInfoIfNeeded(delay:Bool)->Bool {frozen}
    func commitPurposefulAction(){purposes += 1}
    func forwardMessages(messages:[Message],resetCurrent:Bool,transferMode:Mode,nagramiXTransferTitle:String){batches.append(messages);reset.append(resetCurrent);modes.append(transferMode);titles.append(nagramiXTransferTitle)}
}
final class Interaction {
    var controller:ViewController?
    var nativeBatches:[[Message]]=[]
    init(_ controller:ViewController?){self.controller=controller}
    func chatController()->ViewController? {controller}
    func forwardMessages(_ messages:[Message]){nativeBatches.append(messages)}
}
enum Dismiss:Equatable {case `default`,dismissWithoutContent}
typealias MenuAction=(Int,(Dismiss)->Void)->Void
func signedAction(messagesToForward:[Message],copyMessagesToForward:[Message],context:Context,chatPresentationInterfaceState:Presentation,interfaceInteraction:Interaction)->MenuAction {return '''+signed_action+''' }
func nativeAction(messagesToForward:[Message],interfaceInteraction:Interaction)->MenuAction {return '''+native_action+''' }
func choices(_ originals:[Message],hasForwardPermission:Bool=true,chatCopyProtected:Bool=false,ownViewOnceCopy:Bool=false)->(Bool,Bool) {
    let nagramiXNativeRepost=nagramiXCanUseNativeRepost(originals,hasForwardPermission:hasForwardPermission,chatCopyProtected:chatCopyProtected,ownViewOnceCopy:ownViewOnceCopy)
    let nagramiXTemporarySelection=originals.contains(where:{nagramiXCanUseTemporaryMediaActions($0)})
    let nagramiXCanCopySelection=nagramiXCanCopyMessagesAsNew(originals,accountPeerId:1)
    var signed=false
    if nagramiXTemporarySelection, !nagramiXNativeRepost, nagramiXCanCopySelection { signed=true }
    return (nagramiXNativeRepost,signed)
}
struct Representation {let resource:Int}
struct Image {let representations:[Representation]}
func largestImageRepresentation(_ representations:[Representation])->Representation? {representations.last}
func photoResource(messages:[Message],image:Image)->Int? {var loadCopyMediaResource:Int?
'''+photo+'''
    return loadCopyMediaResource
}
var checks=0
func check(_ value:@autoclosure ()->Bool,_ label:String){if !value(){FileHandle.standardError.write(Data(("temporary repost regression: "+label+"\\n").utf8));exit(91)};checks += 1}
@main struct Main {
    static func main(){
        let alive=Message(7,temporary:true)
        let oneShot=Message(8,secret:true,temporary:true)
        let retained=Message(8,temporary:true,attributes:[NagramiXArchivedMessageAttribute()])
        let secret=Message(MessageId(namespace:2,value:9),temporary:true)
        let ordinary=Message(6)
        check(choices([alive]).0 && !choices([alive]).1,"live TTL text keeps native repost even with retention")
        check(!choices([oneShot]).0 && choices([oneShot]).1,"one-shot uses signed copy only")
        check(!choices([retained]).0 && choices([retained]).1,"retained copy never forwards old ID")
        check(!choices([secret]).0 && choices([secret]).1,"secret source uses signed copy")
        check(!choices([ordinary,oneShot]).0 && choices([ordinary,oneShot]).1,"mixed selection has signed fallback")
        check(choices([ordinary]).0 && !choices([ordinary]).1,"ordinary native route unchanged")
        check(!choices([]).0 && !choices([]).1,"empty source hidden")
        check(!choices([alive],hasForwardPermission:false).0,"forward permission required")
        check(!choices([alive],chatCopyProtected:true).0,"real chat protection respected")
        check(!choices([alive],ownViewOnceCopy:true).0,"own recording exception not native repost")
        check(!choices([Message(1,protected:true)]).0,"real message protection respected")
        check(!choices([Message(1,requiresFree:true)]).0,"private source restriction respected")
        let controller=ChatControllerImpl(),interaction=Interaction(nil)
        interaction.controller=controller
        var dismissals:[Dismiss]=[]
        nativeAction(messagesToForward:[alive],interfaceInteraction:interaction)(0,{dismissals.append($0)})
        check(interaction.nativeBatches.count==1 && interaction.nativeBatches[0][0] === alive,"native action preserves exact original")
        check(controller.batches.isEmpty,"native action never duplicates signed send")
        let author="Юра 👨‍👩‍👧"
        let caption="A😊B"
        let range=(caption as NSString).range(of:"😊")
        let entity=MessageTextEntity(range:range.location..<(range.location+range.length),type:"custom")
        let other=OtherAttribute()
        let source=Message(12,temporary:true,attributes:[TextEntitiesMessageAttribute(entities:[entity]),other],author:Peer(name:author),text:caption,media:"playable voice resource")
        let first=Message(2,temporary:true,author:nil,text:"earlier")
        signedAction(messagesToForward:[oneShot],copyMessagesToForward:[source,first],context:Context(),chatPresentationInterfaceState:Presentation(),interfaceInteraction:interaction)(0,{dismissals.append($0)})
        check(controller.batches.count==1 && interaction.nativeBatches.count==1,"signed action calls actual copy-mode controller directly")
        check(controller.purposes==1 && controller.modes==[.copyToSingleRecipient] && controller.reset==[false],"copy mode and purpose preserved")
        check(controller.titles==["Repost"],"selection title stays Repost")
        let batch=controller.batches[0]
        check(batch.map{$0.id}==[2,12],"source ordering preserved")
        let signed=batch[1]
        let prefix=author+":\\n"
        check(signed.text==prefix+caption,"author signature precedes exact caption")
        let signedEntities=(signed.attributes.compactMap{$0 as? TextEntitiesMessageAttribute}.first?.entities) ?? []
        check(signedEntities==[MessageTextEntity(range:(range.location+prefix.utf16.count)..<(range.location+range.length+prefix.utf16.count),type:"custom")],"entity offsets use UTF16 author length")
        check(signed.media==source.media && signed.id==source.id,"actual source media and ID not replaced by description")
        check(signed.attributes.contains{$0 === other},"non-entity attributes retained")
        check(source.text==caption && (source.attributes[0] as? TextEntitiesMessageAttribute)?.entities==[entity],"original source unmodified")
        check(batch[0].text=="Deleted Account:\\nearlier","missing author uses existing localized fallback")
        check(dismissals==[.dismissWithoutContent,.dismissWithoutContent],"both valid actions dismiss once")
        controller.frozen=true
        signedAction(messagesToForward:[oneShot],copyMessagesToForward:[source],context:Context(),chatPresentationInterfaceState:Presentation(),interfaceInteraction:interaction)(0,{dismissals.append($0)})
        check(controller.batches.count==1 && controller.purposes==1 && dismissals.last == .default,"frozen account cannot enqueue signed copy")
        controller.frozen=false;temporaryEnabled=false
        signedAction(messagesToForward:[oneShot],copyMessagesToForward:[source],context:Context(),chatPresentationInterfaceState:Presentation(),interfaceInteraction:interaction)(0,{dismissals.append($0)})
        check(controller.batches.count==1 && controller.purposes==1,"late OFF cancels signed action")
        let image=Image(representations:[Representation(resource:4),Representation(resource:8)])
        check(photoResource(messages:[oneShot],image:image)==nil,"OFF secret photo keeps native resource policy")
        check(photoResource(messages:[ordinary],image:image)==8,"ordinary photo resource unchanged")
        temporaryEnabled=true
        check(photoResource(messages:[oneShot],image:image)==8,"ON temporary photo resource lookup available")
        check(photoResource(messages:[Message(1,secret:true)],image:image)==nil,"unrelated secret photo stays gated")
        copiesAllowed=false
        signedAction(messagesToForward:[oneShot],copyMessagesToForward:[source],context:Context(),chatPresentationInterfaceState:Presentation(),interfaceInteraction:interaction)(0,{dismissals.append($0)})
        check(controller.batches.count==1,"copy eligibility rechecked at action")
        copiesAllowed=true
        signedAction(messagesToForward:[oneShot],copyMessagesToForward:[source],context:Context(),chatPresentationInterfaceState:Presentation(),interfaceInteraction:Interaction(nil))(0,{dismissals.append($0)})
        check(controller.batches.count==1,"missing controller cannot send")
        let richPage=InstantPage(blocks:[.paragraph(.bold(.plain("full content")))],media:[35:"retained actual attachment"],isComplete:true,rtl:true,url:"https://original",views:37)
        let partialPage=InstantPage(blocks:[.paragraph(.plain("partial"))],media:[:],isComplete:false,rtl:false,url:"",views:nil)
        let richSource=Message(20,temporary:true,attributes:[TextEntitiesMessageAttribute(entities:[entity]),other,RichTextMessageAttribute(instantPage:partialPage,fullInstantPage:richPage)],author:Peer(name:author),text:caption,media:"retained file")
        let richController=ChatControllerImpl(),richInteraction=Interaction(nil)
        richInteraction.controller=richController
        signedAction(messagesToForward:[oneShot],copyMessagesToForward:[richSource],context:Context(),chatPresentationInterfaceState:Presentation(),interfaceInteraction:richInteraction)(0,{_ in})
        check(richController.batches.count==1,"rich signed callback uses same actual builder")
        let richSigned=richController.batches[0][0]
        let richAttribute=richSigned.attributes.compactMap{$0 as? RichTextMessageAttribute}.first
        check(richAttribute?.instantPage.blocks == [.paragraph(.plain(author+":"))] + richPage.blocks,"rich visible page has author paragraph before full original blocks")
        check(richAttribute?.instantPage.media == richPage.media,"rich attachment media map preserved")
        check(richAttribute?.instantPage.rtl == richPage.rtl && richAttribute?.instantPage.url == richPage.url && richAttribute?.instantPage.isComplete == true,"rich metadata uses complete page")
        check(richAttribute?.instantPage.views == nil && richAttribute?.fullInstantPage == nil,"new standalone page clears source views and duplicate page")
        check(richSigned.text==prefix+caption && richSigned.media==richSource.media,"rich caption and actual file preserved")
        let richEntities=richSigned.attributes.compactMap{$0 as? TextEntitiesMessageAttribute}.first?.entities
        check(richEntities==signedEntities,"rich UTF16 entity offsets match signed caption")
        check(richSource.attributes.contains{$0===other} && richPage.blocks==[.paragraph(.bold(.plain("full content")))],"rich source remains immutable")
        print("PASS temporary repost checks: \\(checks)")
    }
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path)
    args=p.parse_args();text,helper=verify(args.source)
    runs=[];negative=[]
    with tempfile.TemporaryDirectory(prefix='temporary-repost-') as folder:
        root=Path(folder)
        for mode in ['current','old-native-routing','generic-signed-callback','old-photo-gate','wrong-entity-offset','missing-rich-signature','lost-rich-media','no-frozen-check']:
            source=root/(mode+'.swift');source.write_text(fixture(text,helper,mode))
            for opt in [False,True]:
                binary=root/(mode+('-O' if opt else '-debug'))
                command=[str(args.swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(root/'cache')]
                if opt:command+=['-O']
                subprocess.run([*command,str(source),'-o',str(binary)],check=True)
                result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
                if mode=='current':
                    assert result.returncode==0,result.stdout+result.stderr;runs.append(result.stdout.strip())
                else:
                    assert result.returncode==91 and 'temporary repost regression:' in result.stderr,(mode,result.stdout,result.stderr)
                    negative.append({'mode':mode,'optimized':opt,'diagnostic':result.stderr.strip()})
        for path in [FILE,HELPER]:
            subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/path)],check=True)
    report={'production_runs':runs,'semantic_negatives':negative,'source_sha256':hashlib.sha256((args.source/FILE).read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256((args.source/HELPER).read_bytes()).hexdigest(),'parse_files':2,'boundaries':'Actual signing helper, native-source classifier, signed/native menu callbacks and photo resource lookup execute; shared eligibility, immutable Message wrappers, UIKit strings/dismiss and copy transport are adapters. Source and callback modes are checked against actual declarations.','native_sdk':'not run','physical_device':'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
