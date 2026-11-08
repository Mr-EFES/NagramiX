#!/usr/bin/env python3
"""Check ordinary archive payloads without an SDK or application build."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_temporary_interaction_archive import (
    ARCHIVE, CORE, archive_fixture, body, clean, resource_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'ios/temporary_message_interaction/After15.inc'


def verify(source):
    text = (source / ARCHIVE).read_text()
    record = body(text, '    private static func makeRecord(message: StoreMessage,')
    assert 'type(of: decoded) == type(of: item)' in record
    assert 'let contentAttributes = Self.retainedContentAttributes(message.attributes)' in record
    assert 'contentAttributes: contentAttributes' in record
    assert '$0 is TelegramMediaExpiredContent || $0 is TelegramMediaAction' in record
    assert 'record.wasTemporary' in body(text, '    public func deletedMessages(')
    # The new payload coverage must not turn into a change to receipt/TTL policy.
    old = OLD.read_text()
    for marker in [
        '    public func temporaryInteractionMessage(',
        '    public func shouldSuppressTemporaryContentReceipt(id:',
        '    public func shouldSuppressTemporaryContentReceipt(peerId:',
        '    public func postDeletionPlan(', '    public func deleteArchivedPosts(',
        '    private func mediaRequests(', '    private func localMedia(_ media: Media, depth:',
    ]:
        assert body(text, marker) == body(old, marker), marker
    account = (source / (CORE + 'Account/AccountManager.swift')).read_text()
    for kind in ['Contact', 'Map', 'Dice', 'Game', 'Webpage']:
        assert 'declareEncodable(TelegramMedia' + kind + '.self,' in account, kind
    return hashlib.sha256(text.encode()).hexdigest()


def fixture(source, mode='current'):
    text = (source / ARCHIVE).read_text()
    original = archive_fixture(source)
    original = original[:original.index('@main struct TemporaryArchiveTests')]
    if mode == 'old-media':
        old = OLD.read_text()
        original = original.replace(clean(body(text, '    private static func makeRecord(message: StoreMessage,')),
                                    clean(body(old, '    private static func makeRecord(message: StoreMessage,')))
    if mode == 'old-attributes':
        original = original.replace('contentAttributes: contentAttributes',
                                    'contentAttributes: retainedTemporary ? contentAttributes : nil')
    if mode == 'partial-media':
        original = original.replace('type(of: decoded) == type(of: item) else { return nil }',
                                    'type(of: decoded) == type(of: item) else { continue }')
    if mode == 'wrong-kind':
        original = original.replace('type(of: decoded) == type(of: item)', 'type(of: decoded) == type(of: decoded)')
    if mode == 'partial-attributes':
        original = original.replace('guard contentAttributes.allSatisfy({ Self.decodedRootObject($0) is MessageAttribute }) else { return nil }', '')
    if mode == 'service':
        original = original.replace('$0 is TelegramMediaExpiredContent || $0 is TelegramMediaAction', '$0 is TelegramMediaExpiredContent')

    # Native Contact/Map/Dice use their real fields, constructors, coding and
    # equality. Other framework models remain the existing explicit boundary.
    base = body(original, 'class Media {')
    original = original.replace(base, '''protocol Media: AnyObject {var name:String {get};var peerIds:[PeerId] {get}}
extension Media {var name:String {String(describing:type(of:self))};var peerIds:[PeerId] {[]}}
class BoundaryMedia:Media {let name:String;init(_ name:String){self.name=name};var peerIds:[PeerId]{[]}}''')
    import re
    original = re.sub(r'(final class \w+):Media', r'\1:BoundaryMedia', original)
    for kind in ['Contact', 'Map']:
        original = original.replace('final class TelegramMedia' + kind + ':BoundaryMedia {}', '')
    old_codec = body(original, 'final class Codec {')
    original = original.replace(old_codec, CODEC)
    original = original.replace('Codec.values[data]', 'Codec.decode(data)')
    original = original.replace('Codec.values[$0]', 'Codec.decode($0)')
    original += '\nstruct MediaId:Hashable {let namespace:Int32;let id:Int64}\n'
    original += '\nfinal class TelegramMediaGame:BoundaryMedia {}\n'
    for filename in ['SyncCore_TelegramMediaContact.swift', 'SyncCore_TelegramMediaMap.swift', 'SyncCore_TelegramMediaDice.swift']:
        native = (source / (CORE + 'SyncCore/' + filename)).read_text()
        original += clean(native).replace(': PostboxCoding, Equatable', ': Equatable')
    return original + CODING_BOUNDARY + TESTS


CODEC = r'''
final class Codec {
    static var values:[Data:Any]=[:]
    static var blocked=Set<String>()
    static func encode(_ object:Any)->Data {
        let name=String(describing:type(of:object))
        let key=Data(UUID().uuidString.utf8)
        if blocked.contains(name) || object is UnregisteredMedia {return key}
        if object is WrongDecodedMedia {values[key]=TelegramMediaImage("wrong-kind");return key}
        let encoder=PostboxEncoder()
        switch object {
        case let value as TelegramMediaContact:value.encode(encoder)
        case let value as TelegramMediaMap:value.encode(encoder)
        case let value as TelegramMediaDice:value.encode(encoder)
        default: values[key]=object;return key
        }
        return try! JSONSerialization.data(withJSONObject:["kind":name,"fields":encoder.fields],options:[.sortedKeys])
    }
    static func decode(_ data:Data)->Any? {
        if let envelope=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let name=envelope["kind"] as? String,let fields=envelope["fields"] as? [String:Any] {
            let decoder=PostboxDecoder(fields)
            switch name {
            case "TelegramMediaContact":return TelegramMediaContact(decoder:decoder)
            case "TelegramMediaMap":return TelegramMediaMap(decoder:decoder)
            case "TelegramMediaDice":return TelegramMediaDice(decoder:decoder)
            default:return nil
            }
        }
        return values[data]
    }
}
'''

CODING_BOUNDARY = r'''
final class UnregisteredMedia:BoundaryMedia {}
final class WrongDecodedMedia:BoundaryMedia {}
final class PostboxEncoder {
    var fields:[String:Any]=[:]
    func encodeString(_ value:String,forKey key:String){fields[key]=value}
    func encodeInt32(_ value:Int32,forKey key:String){fields[key]=value}
    func encodeInt64(_ value:Int64,forKey key:String){fields[key]=value}
    func encodeDouble(_ value:Double,forKey key:String){fields[key]=value}
    func encodeNil(forKey key:String){fields[key]=NSNull()}
    func encodeData(_ value:Data,forKey key:String){fields[key]=["data":value.base64EncodedString()]}
    func encodeObject(_ object:Any,forKey key:String){let encoder=PostboxEncoder();switch object{case let value as MapVenue:value.encode(encoder);case let value as MapGeoAddress:value.encode(encoder);default:fatalError("Unsupported native test coding branch")};fields[key]=encoder.fields}
}
final class PostboxDecoder {
    let fields:[String:Any];init(_ fields:[String:Any]){self.fields=fields}
    func decodeStringForKey(_ key:String,orElse:String)->String{fields[key] as? String ?? orElse}
    func decodeOptionalStringForKey(_ key:String)->String?{fields[key] as? String}
    func decodeOptionalInt64ForKey(_ key:String)->Int64?{(fields[key] as? NSNumber)?.int64Value}
    func decodeOptionalInt32ForKey(_ key:String)->Int32?{(fields[key] as? NSNumber)?.int32Value}
    func decodeOptionalDoubleForKey(_ key:String)->Double?{(fields[key] as? NSNumber)?.doubleValue}
    func decodeDoubleForKey(_ key:String,orElse:Double)->Double{decodeOptionalDoubleForKey(key) ?? orElse}
    func decodeDataForKey(_ key:String)->Data?{guard let value=fields[key] as? [String:String],let base64=value["data"] else{return nil};return Data(base64Encoded:base64)}
    func decodeObjectForKey(_ key:String,decoder:(PostboxDecoder)->Any)->Any?{guard let fields=fields[key] as? [String:Any] else{return nil};return decoder(PostboxDecoder(fields))}
}
'''

TESTS = r'''
@main struct OrdinaryArchiveTests {
    static func main() throws {
        var checks=0
        func check(_ value:@autoclosure()->Bool,_ label:String){if !value(){FileHandle.standardError.write(Data(("Ordinary archive regression: "+label+"\n").utf8));exit(93)};checks+=1}
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
        defer{try? FileManager.default.removeItem(at:directory);UserDefaults.standard.removeVolatileDomain(forName:UserDefaults.argumentDomain)}
        func archive(_ name:String)->Archive{Archive(directory.appendingPathComponent(name+".json").path)}
        configure(false,true)
        let contact=TelegramMediaContact(firstName:"Юра",lastName:"Зуев",phoneNumber:"+70000000",peerId:PeerId(77),vCardData:"BEGIN:VCARD\nEND:VCARD")
        let map=TelegramMediaMap(latitude:51.5,longitude:-0.12,heading:123,accuracyRadius:4.5,venue:MapVenue(title:"Venue",address:"Address",provider:"Provider",id:"venue-id",type:"cafe"),address:MapGeoAddress(country:"GB",state:"State",city:"City",street:"Street"),liveBroadcastingTimeout:900,liveProximityNotificationRadius:30)
        let dice=TelegramMediaDice(emoji:"🎰",tonAmount:40,value:64,gameOutcome:TelegramMediaDice.GameOutcome(seed:Data([1,2,3]),tonAmount:50))
        let medias:[Media]=[contact,map,dice,TelegramMediaGame("Game title and payload"),TelegramMediaWebpage("https://example.org/preview"),TelegramMediaImage("photo"),TelegramMediaFile("document"),TelegramMediaPoll("poll")]
        let saved=archive("known")
        var messages:[Message]=[]
        let attrs:[MessageAttribute]=[TextEntitiesMessageAttribute(entities:[MessageTextEntity(text:"bold/link")]),MediaSpoilerMessageAttribute(),WebpagePreviewMessageAttribute(),InvertMediaMessageAttribute(),ReplyMessageAttribute(),OutgoingContentInfoMessageAttribute(),RichTextMessageAttribute(instantPage:InstantPage("rich preview"),fullInstantPage:InstantPage("rich body"))]
        for (index,media) in medias.enumerated() {
            let (store,peers)=sample(Int32(100+index),ttl:nil,text:"Caption 😀 https://example.org",media:[media],attributes:attrs)
            let live=locallyRenderedMessage(message:store,peers:peers)!;messages.append(live)
            saved.captureIncoming(store,peers:peers);saved.queue.drain()
            let record=saved.saved.records.values.first{$0.messageId==live.id}!
            check(record.content.media.count==1,"ordinary registered media is retained instead of silently dropped")
            saved.archiveMessagesBeforeDeletion([live],deletedAt:500);saved.queue.drain()
            let rendered=saved.deletedMessage(id:live.id)
            check(rendered?.media.count==1 && rendered?.media.first?.name==media.name,"first deletion materializes whole native media object")
            check(rendered?.text==store.text && rendered?.attributes.compactMap{$0 as? TextEntitiesMessageAttribute}.first?.entities==[MessageTextEntity(text:"bold/link")],"ordinary caption and entities survive")
            check(rendered?.attributes.contains{$0 is MediaSpoilerMessageAttribute}==true && rendered?.attributes.contains{$0 is InvertMediaMessageAttribute}==true && rendered?.attributes.contains{$0 is WebpagePreviewMessageAttribute}==true,"ordinary presentation attributes survive")
            check(rendered?.attributes.compactMap{$0 as? RichTextMessageAttribute}.first?.fullInstantPage?.text=="rich body","ordinary rich payload survives with temporary feature OFF")
            check(record.contentAttributes?.count==6,"only existing six safe display attributes are retained")
        }
        let renderedContact=saved.deletedMessage(id:messages[0].id)!.media[0] as! TelegramMediaContact
        check(renderedContact !== contact && renderedContact.isEqual(to:contact),"actual Contact coder restores independent full contact")
        let renderedMap=saved.deletedMessage(id:messages[1].id)!.media[0] as! TelegramMediaMap
        check(renderedMap !== map && renderedMap.isEqual(to:map),"actual Map coder restores native location fields")
        check(renderedMap.venue?.title=="Venue" && renderedMap.address?.country=="GB" && renderedMap.address?.city=="City" && renderedMap.address?.street=="Street","venue title and geographical address survive beyond native shallow equality")
        let renderedDice=saved.deletedMessage(id:messages[2].id)!.media[0] as! TelegramMediaDice
        check(renderedDice !== dice && renderedDice.isEqual(to:dice) && renderedDice.value==64 && renderedDice.gameOutcome?.seed==Data([1,2,3]),"actual Dice coder preserves original outcome instead of a new roll")
        let restarted=Archive(saved.path);restarted.restore()
        check(restarted.saved.records.count==medias.count && restarted.deletedMessage(id:messages[0].id)?.media.first is TelegramMediaContact,"archive JSON restart retains native structured objects")
        check(restarted.deletedMessage(id:messages[1].id)?.media.first is TelegramMediaMap && restarted.deletedMessage(id:messages[2].id)?.media.first is TelegramMediaDice,"native codec payload survives persisted restart")

        let multi=archive("whole")
        let (whole,wholePeers)=sample(300,ttl:nil,media:medias,attributes:attrs)
        let liveWhole=locallyRenderedMessage(message:whole,peers:wholePeers)!
        multi.captureIncoming(whole,peers:wholePeers);multi.queue.drain();multi.archiveMessagesBeforeDeletion([liveWhole],deletedAt:600);multi.queue.drain()
        let wholeRendered=multi.deletedMessage(id:liveWhole.id)!
        check(wholeRendered.media.map{$0.name}==medias.map{$0.name},"mixed post preserves every media part in original order")
        let transaction=Transaction();transaction.messages[liveWhole.id]=liveWhole
        let first=multi.postDeletionPlan(transaction:transaction,messageIds:[liveWhole.id],localCandidates:[])
        check(first.nativeMessageIds==[liveWhole.id] && first.localMessageIds.isEmpty,"live first deletion keeps native phase")
        transaction.messages.removeValue(forKey:liveWhole.id)
        let second=multi.postDeletionPlan(transaction:transaction,messageIds:[liveWhole.id],localCandidates:[liveWhole.id])
        check(second.nativeMessageIds.isEmpty && second.localMessageIds==[liveWhole.id],"second delete targets complete local post")
        _=multi.deleteArchivedPosts(messageIds:second.localMessageIds).startStandalone();multi.queue.drain()
        check(multi.saved.records.isEmpty && multi.mediaStore.files.isEmpty,"second delete releases complete local ownership")

        for bad in [UnregisteredMedia("unregistered"),WrongDecodedMedia("wrong-kind")] as [Media] {
            let badArchive=archive("bad-"+bad.name);let (store,peers)=sample(400,ttl:nil,media:[contact,bad,TelegramMediaFile("tail")])
            badArchive.captureIncoming(store,peers:peers);badArchive.queue.drain()
            check(badArchive.saved.records.isEmpty && badArchive.mediaStore.reservations.isEmpty,"undecodable or wrong-kind media rejects whole snapshot before reservations")
        }
        let badAttribute=archive("bad-attribute");Codec.blocked.insert("MediaSpoilerMessageAttribute")
        let (badAttrs,badAttrsPeers)=sample(401,ttl:nil,media:[contact],attributes:[MediaSpoilerMessageAttribute()])
        badAttribute.captureIncoming(badAttrs,peers:badAttrsPeers);badAttribute.queue.drain();Codec.blocked.removeAll()
        check(badAttribute.saved.records.isEmpty,"undecodable required presentation attribute rejects whole snapshot")
        for excluded in [TelegramMediaAction("service"),TelegramMediaExpiredContent("expired"),TelegramMediaPaidContent("paid")] as [Media] {
            let denied=archive("deny-"+excluded.name);let (store,peers)=sample(402,ttl:nil,media:[contact,excluded])
            denied.captureIncoming(store,peers:peers);denied.queue.drain()
            check(denied.saved.records.isEmpty,"service expired and paid objects stay excluded")
        }
        let denied=archive("denied")
        let (secret,secretPeers)=sample(410,secret:true,ttl:nil,media:[contact]);denied.captureIncoming(secret,peers:secretPeers)
        let (temporary,temporaryPeers)=sample(411,ttl:900,media:[contact]);denied.captureIncoming(temporary,peers:temporaryPeers)
        denied.queue.drain();check(denied.saved.records.isEmpty,"ordinary expansion does not bypass secret or disabled-temporary policy")
        let off=archive("off");configure(false,false)
        let (ordinary,ordinaryPeers)=sample(420,ttl:nil,media:medias,attributes:attrs);off.captureIncoming(ordinary,peers:ordinaryPeers);off.queue.drain()
        check(off.saved.records.isEmpty,"showDeleted OFF stops new ordinary capture")
        check(saved.deletedMessages(peerId:messages[0].id.peerId,threadId:nil,minIndex:nil,maxIndex:nil).isEmpty,"showDeleted OFF hides old ordinary snapshots")
        configure(false,true)
        check(saved.deletedMessages(peerId:messages[0].id.peerId,threadId:nil,minIndex:nil,maxIndex:nil).count==medias.count,"reenabling shows same intact snapshots without recreating them")
        print("Ordinary archive actual-method checks: \(checks)")
    }
}
'''


def run(source, swiftc, directory):
    results = []
    for mode in ['current', 'old-media', 'old-attributes', 'partial-media', 'wrong-kind', 'partial-attributes', 'service']:
        path = directory / (mode + '.swift');path.write_text(fixture(source, mode))
        for optimized in [False, True]:
            binary = directory / (mode + ('-O' if optimized else '-debug'))
            args = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(directory / 'cache')]
            if optimized: args.append('-O')
            subprocess.run([*args,str(path),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            assert result.returncode==(0 if mode=='current' else 93),result.stdout+result.stderr
            if mode!='current':assert 'Ordinary archive regression:' in result.stderr
            results.append(binary.name+': '+(result.stdout.strip() if mode=='current' else result.stderr.strip()));print(results[-1],flush=True)
    # Exercise the unchanged native resource collector/remapper in ordinary mode,
    # against real native constructor fields and primary-byte completeness checks.
    value=resource_fixture(source).replace('incoming:true,wasTemporary:true','incoming:true,wasTemporary:false')
    assert 'incoming:true,wasTemporary:true' not in value
    value=value.replace('requests.allSatisfy{$0.temporary && $0.replay}','requests.allSatisfy{!$0.temporary && !$0.replay}')
    value=value.replace('retained-only mode owns every resource independent of deleted setting','ordinary mode owns resources without enabling temporary replay')
    value=value.replace('        print("Temporary native constructor/resource checks: \\(checks)")', '        check(archive.complete(TelegramMediaContact()) && archive.complete(TelegramMediaMap()),"ordinary contacts and maps are metadata-complete without primary resources")\n        print("Temporary native constructor/resource checks: \\(checks)")')
    path=directory/'ordinary-resources.swift';path.write_text(value)
    for optimized in [False,True]:
        binary=directory/('ordinary-resources'+('-O' if optimized else '-debug'))
        args=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(directory/'resource-cache')]
        if optimized:args.append('-O')
        subprocess.run([*args,str(path),'-o',str(binary)],check=True)
        result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60)
        assert result.returncode==0,result.stdout+result.stderr
        results.append(binary.name+': '+result.stdout.strip());print(results[-1],flush=True)
    return results


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args();sha=verify(args.source)
    with tempfile.TemporaryDirectory(prefix='preflight-archive-media-') as work:
        results=run(args.source,args.swiftc,Path(work)) if args.swiftc else []
        if args.swiftc:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/ARCHIVE)],check=True)
    report={'output_sha256':sha,'executions':results,'swift_parse':1 if args.swiftc else 0,'boundaries':'Actual record serialization, capture, deletion planner/purge, materializer, Foundation JSON/restart and resource collectors/remappers. Contact/Map/Dice constructors/coders/equality and Game/Webpage/resource constructor fields come from native source. Postbox object container/registration, media store ownership, Signals and UIKit are explicit bounded adapters. No SDK, network or physical-device claim.'}
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Ordinary archive media preflight passed')


if __name__=='__main__':main()
