#!/usr/bin/env python3
"""Check retained round playback without dispatching an SDK or IPA build.

Execute production archive/playlist/activation/layout bodies in explicit
storage, signals and UI adapters. Historical snapshots remain immutable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_temporary_interaction_archive import ARCHIVE, archive_fixture, clean
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'round_video_replay_stability'
IV = 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift'
BUBBLE = 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift'
NATIVE = 'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift'
PLAYLIST = 'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift'
ACTION = 'submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift'
API = 'submodules/AccountContext/Sources/MediaManager.swift'
SHARED = 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift'
OPEN = 'submodules/TelegramUI/Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift'
POSTBOX = 'submodules/Postbox/Sources/Message.swift'


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, **kwargs)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def archive_tests(source):
    fixture = archive_fixture(source)
    # Extend the existing boundary with the real public Postbox method, rather
    # than inventing a new method in a test double that the SDK may not export.
    method = clean(block((source / POSTBOX).read_text(), '    public func withUpdatedStableId('))
    fixture += '\nextension Message {\n' + method + '\n}\n'
    fixture = fixture.replace('@main struct TemporaryArchiveTests', 'struct HistoricalTemporaryArchiveTests')
    fixture += '\n' + clean(block((source / ARCHIVE).read_text(), 'public extension Message {'))
    return fixture + ARCHIVE_TESTS


ARCHIVE_TESTS = r'''
@main struct RoundArchiveTests {
    static func main() throws {
        // The unchanged historical suite also runs against the modified bodies.
        try HistoricalTemporaryArchiveTests.main()
        var checks=0
        func check(_ v:@autoclosure()->Bool,_ s:String){if !v(){FileHandle.standardError.write(Data(("Round archive regression: "+s+"\n").utf8));exit(94)};checks+=1}
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
        defer{try? FileManager.default.removeItem(at:directory);UserDefaults.standard.removeVolatileDomain(forName:UserDefaults.argumentDomain)}
        for secret in [false,true] { for once in [false,true] { for incoming in [false,true] {
            configure(true,true)
            let saved=Archive(directory.appendingPathComponent("\(secret)-\(once)-\(incoming).json").path)
            let (store,peers)=sample(910,secret:secret,incoming:incoming,ttl:once ? viewOnceTimeout:900,media:[TelegramMediaFile("round")])
            let live=locallyRenderedMessage(message:store,peers:peers)!.withUpdatedStableId(stableId:197)
            saved.captureIncoming(store,peers:peers);saved.queue.drain()
            let before=saved.saved
            let interaction=saved.temporaryInteractionMessage(id:live.id,liveMessage:live)!
            check(interaction.stableId==197,"live row keeps Postbox stableId before asynchronous capture")
            check(saved.saved==before,"interaction is readonly; no receipt, expiry or archive mutation")
            check(!interaction.nagramiXShowsArchiveNotice,"retaining a live temporary message is not deletion")
            check((interaction.attributes.first{$0 is NagramiXArchivedMessageAttribute} as? NagramiXArchivedMessageAttribute)?.deletedAt==0,"live snapshot has no fake deletion timestamp")
            saved.captureTemporaryBeforeViewing(message:live);saved.queue.drain()
            check(saved.saved.records.values.first?.stableId==197,"existing replay record enriched with native row identity")
            saved.archiveMessagesBeforeDeletion([live],deletedAt:1000);saved.queue.drain()
            let deleted=saved.deletedMessage(id:live.id)!
            check(deleted.stableId==197,"native first deletion does not reinsert a different stable row")
            check(deleted.nagramiXShowsArchiveNotice,"deleted temporary/once round gets deleted notice")
            check(deleted.nagramiXIsViewOnceReplay,"replay eligibility remains independent of deleted presentation")
            check(deleted.media.count==1 && (deleted.media.first as? TelegramMediaFile)?.isInstantVideo==true,"whole round retained")
            let reload=Archive(saved.path);reload.restore()
            check(reload.deletedMessage(id:live.id)?.stableId==197,"stable identity survives archive restart")
            saved.captureIncoming(store,peers:peers);saved.queue.drain()
            check(saved.deletedMessage(id:live.id)?.stableId==197,"ingestion without custom stableId cannot erase known identity")
            let data=try Data(contentsOf:URL(fileURLWithPath:saved.path))
            var json=try JSONSerialization.jsonObject(with:data) as! [String:Any]
            var records=json["records"] as! [String:[String:Any]]
            for key in records.keys {records[key]?.removeValue(forKey:"stableId")}
            json["records"]=records
            try JSONSerialization.data(withJSONObject:json).write(to:URL(fileURLWithPath:saved.path))
            let legacy=Archive(saved.path);legacy.restore()
            check(legacy.deletedMessage(id:live.id)?.id==live.id,"pre-fix archive schema remains readable")
        } } }
        configure(false,true)
        let ordinary=Archive(directory.appendingPathComponent("ordinary.json").path)
        let (store,peers)=sample(911,ttl:nil,media:[TelegramMediaFile("round")])
        let live=locallyRenderedMessage(message:store,peers:peers)!.withUpdatedStableId(stableId:198)
        ordinary.archiveMessagesBeforeDeletion([live],deletedAt:1000);ordinary.queue.drain()
        check(ordinary.deletedMessage(id:live.id)?.stableId==198,"ordinary deleted round keeps native stableId")
        check(ordinary.deletedMessage(id:live.id)?.nagramiXShowsArchiveNotice==true,"ordinary deleted notice preserved")
        configure(true,true)
        let expiring=Archive(directory.appendingPathComponent("expiration.json").path)
        let (temporary,temporaryPeers)=sample(912,ttl:viewOnceTimeout,media:[TelegramMediaFile("round")])
        expiring.captureIncoming(temporary,peers:temporaryPeers);expiring.queue.drain()
        let expiredSnapshot=expiring.snapshotForExpiredMessage(id:MessageId(peerId:PeerId(8),namespace:0,id:912))
        check(expiredSnapshot?.nagramiXShowsArchiveNotice==true,"first expired frame is dimmed before asynchronous expiry persistence")
        expiring.queue.drain()
        configure(false,false)
        check(ordinary.deletedMessage(id:live.id)==nil,"OFF hides archive")
        check(ordinary.temporaryInteractionMessage(id:live.id,liveMessage:live)?.stableId==198,"OFF preserves original row")
        print("Round archive regression checks: \(checks)")
    }
}
'''


def ui_tests(source):
    iv = (source / IV).read_text()
    bubble = (source / BUBBLE).read_text()
    playlist = (source / PLAYLIST).read_text()
    native = (source / NATIVE).read_text()
    async_flags = iv[iv.index('            let isViewOnceMessage ='):iv.index('            if isSecretMedia {')]
    async_flags = async_flags.replace('            let theme = item.presentationData.theme\n', '')
    status_flags = iv[iv.index('        let isViewOnceMessage =', iv.index('    private func updateStatus(')):iv.index('//        var secretBeginTimeAndTimeout:')]
    playback = next(line.strip() for line in playlist.splitlines() if 'let source = SharedMediaPlaybackDataSource.telegramFile' in line)
    once = playback[playback.index('isViewOnce: ') + len('isViewOnce: '):-1].replace('self.message', 'item.message')
    alpha = next(line.strip() for line in bubble.splitlines() if 'let nagramiXContentAlpha:' in line)
    labels = [line.strip() for line in bubble.splitlines() if line.strip().startswith('let label =') and 'nagramiXDeleted' in line]
    assert len(labels) == 2 and labels[0] == labels[1]
    assert 'nagramiXViewOnceReplayLabel' not in bubble
    assert 'iconNode.image = generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Delete")' in bubble
    assert 'return self.view' in block(iv, '    override public func hitTest('), 'Retain single gesture owner'
    progress = block(iv, '    private func progressPressed(')
    marker = '        if let status = self.status {'
    prefix = progress[:progress.index(marker)]
    prefix = prefix.replace('guard let item = self.item, let file = self.media else', 'guard self.item != nil, self.media != nil else')
    prefix += '        self.nativeFetchOnly += 1\n    }'
    activate = block(iv, '    private func activateVideoPlayback(')
    activate = activate[:activate.index('        if self.infoBackgroundNode.alpha.isZero {')]
    # All retained activation and asynchronous lease checks are production code.
    activate += '        self.nativeFetchOnly += 1\n    }'
    handoff = block(native, '    func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition) {')
    handoff = handoff[:handoff.index('        self.validLayout = (size, actualSize)')] + '        self.validLayout = (size, actualSize)\n    }'
    identity = block(iv, '            if nagramiXArchivedInstantVideo || previouslyArchived {\n                updatedMedia =')
    return UI_BOUNDARY + '''
func needsNewIdentity(_ previouslyArchived:Bool,_ nagramiXArchivedInstantVideo:Bool,_ updatedMessageId:Bool)->Bool {
var updatedMedia=false
''' + identity + '\nreturn updatedMedia\n}\n' + '''
func flags(_ item:Item)->(Bool,Bool,Bool,Bool,Bool) {
''' + async_flags + '\nlet layoutOnce = isViewOnceMessage; let layoutSecret = isSecretMedia\ndo {\n' + status_flags + '\nreturn (layoutOnce,layoutSecret,isViewOnceMessage,isSecretMedia,' + once + ')\n}\n}\n' + '''
func notice(_ item:Item)->(CGFloat,String) {
let nagramiXIsArchived=item.content.firstMessage.nagramiXShowsArchiveNotice
let configuredLabel=""
''' + alpha + '\n' + labels[0] + '\nreturn (nagramiXContentAlpha,label)\n}\n' + '''
final class Node {
var item:Item?;var media:File?;let nagramiXArchivedPlaybackAction=NagramiXArchivedPlaybackAction();var nativeFetchOnly=0
var allow=true
func shouldOpen()->Bool {allow}
''' + block(iv, '    private var nagramiXIsArchivedInstantVideo: Bool {').replace('private ', '') + '\n' + block(iv, '    private var nagramiXUsesRetainedPlayback: Bool {').replace('private ', '') + '\n' + activate.replace('private ', '') + '\n' + prefix.replace('private ', '') + '''
}
final class Content {
var nagramiXArchivedInstantVideo=true
var validLayout:(size:CGSize,actualSize:CGSize)?
let playerNode=PlayerNode()
''' + handoff + '\n}\n' + UI_TESTS


UI_BOUNDARY = r'''
import Foundation
let viewOnceTimeout:Int32 = .max
protocol MessageAttribute {}
struct NagramiXArchivedMessageAttribute:MessageAttribute {}
struct Message {
    var id=1;var timeout:Int32? = viewOnceTimeout;var retained=true;var containsSecretMedia=true
    var attributes:[MessageAttribute]=[];var nagramiXShowsArchiveNotice=false
    var minAutoremoveOrClearTimeout:Int32? {timeout}
}
func nagramiXCanUseTemporaryMediaActions(_ message:Message)->Bool {message.retained}
struct File {var fileId=10;var resourceId=1}
struct Account {var id=1}
final class Context {var account=Account()}
struct OpenMessageParams {enum Mode {case `default`};let mode:Mode}
final class Interaction {
    var opens=0
    @discardableResult func openMessage(_ m:Message,_ p:OpenMessageParams)->Bool {opens+=1;return true}
}
struct Strings {var nagramiXDeleted="Это сообщение было удалено"}
struct Presentation {let strings=Strings()}
struct ContentItem {let firstMessage:Message}
struct Item {
    let message:Message;let context:Context;let controllerInteraction:Interaction
    var content:ContentItem {ContentItem(firstMessage:message)}
    var presentationData:Presentation {Presentation()}
}
final class NagramiXArchivedPlaybackAction {
    var pending:[()->Void]=[]
    func activate(context:Context,message:Message,isCurrent:@escaping()->Bool,open:@escaping()->Void) {pending.append{if isCurrent(){open()}}}
    func drain(){let work=pending;pending=[];work.forEach{$0()}}
}
enum ContainedViewLayoutTransition {case immediate;case animated}
final class Layer {var removed:[String]=[];func removeAnimation(forKey key:String){removed.append(key)}}
final class PlayerNode {let layer=Layer()}
'''

UI_TESTS = r'''
@main struct RoundUITests {
    static func main() {
        var checks=0
        func check(_ v:@autoclosure()->Bool,_ s:String){if !v(){FileHandle.standardError.write(Data(("Round UI regression: "+s+"\n").utf8));exit(95)};checks+=1}
        let context=Context(),interaction=Interaction()
        func item(_ message:Message)->Item {Item(message:message,context:context,controllerInteraction:interaction)}
        check(needsNewIdentity(false,true,false),"enabling retention rebuilds the actual previously native identity")
        check(needsNewIdentity(true,false,false),"disabling retention releases the actual retained identity")
        check(!needsNewIdentity(true,true,false),"same retained identity does not recreate player on relayout")
        for retained in [false,true] {for once in [false,true] {for secret in [false,true] {
            var m=Message();m.retained=retained;m.timeout=once ? viewOnceTimeout:nil;m.containsSecretMedia=secret
            let f=flags(item(m))
            check(f.0 == (once && !retained) && f.2 == f.0 && f.4 == f.0,"layout/status/playlist agree on effective once state")
            check(f.1 == ((secret || once) && !retained) && f.3 == (secret && !retained),"retained rounds expose video, OFF keeps native masks")
        } } }
        var m=Message();m.attributes=[NagramiXArchivedMessageAttribute()]
        check(notice(item(m)).0==1,"live retained round not dimmed")
        m.nagramiXShowsArchiveNotice=true
        check(notice(item(m)).0==0.5 && notice(item(m)).1=="Это сообщение было удалено","deleted once receives 50 percent and deleted label")
        m.nagramiXShowsArchiveNotice=false
        check(notice(item(m)).0==1,"reused live cell resets opacity")
        let node=Node();node.item=item(m);node.media=File()
        node.progressPressed();node.nagramiXArchivedPlaybackAction.drain()
        check(interaction.opens==1 && node.nativeFetchOnly==0,"central status tap opens retained player in one action instead of fetch-only")
        node.activateVideoPlayback();node.media?.resourceId=2;node.nagramiXArchivedPlaybackAction.drain()
        check(interaction.opens==2,"completed cache handoff does not invalidate same-file activation")
        node.activateVideoPlayback();node.media?.fileId=11;node.nagramiXArchivedPlaybackAction.drain()
        check(interaction.opens==2,"reused row with another file cannot open old request")
        node.activateVideoPlayback();var other=m;other.id=2;node.item=item(other);node.nagramiXArchivedPlaybackAction.drain()
        check(interaction.opens==2,"reused row with another message cannot open old request")
        node.item=item(m);node.activateVideoPlayback();context.account.id=2;node.nagramiXArchivedPlaybackAction.drain()
        check(interaction.opens==2,"another account cannot activate stale request")
        node.item=nil;node.progressPressed()
        check(node.nativeFetchOnly==0,"unbound row ignores status tap")
        var ordinary=Message();ordinary.retained=false;ordinary.attributes=[]
        node.item=item(ordinary);node.progressPressed()
        check(node.nativeFetchOnly==1,"ordinary native fetch handling untouched")
        let large=CGSize(width:348,height:348),small=CGSize(width:120,height:120)
        let video=Content();video.validLayout=(small,small)
        video.updateLayout(size:large,actualSize:large,transition:.immediate)
        check(video.playerNode.layer.removed==["position","bounds","transform"],"obsolete inner resize cleared on small-to-large ownership handoff")
        video.playerNode.layer.removed=[]
        video.updateLayout(size:large,actualSize:large,transition:.immediate)
        check(video.playerNode.layer.removed.isEmpty,"same-size updates do not cancel ongoing native animation")
        video.updateLayout(size:small,actualSize:small,transition:.animated)
        check(video.playerNode.layer.removed.isEmpty,"normal animated expansion/collapse remains native")
        video.updateLayout(size:large,actualSize:large,transition:.immediate)
        check(video.playerNode.layer.removed.count==3,"repeat reverse handoff remains bounded")
        video.playerNode.layer.removed=[];video.nagramiXArchivedInstantVideo=false
        video.updateLayout(size:small,actualSize:small,transition:.immediate)
        check(video.playerNode.layer.removed.isEmpty,"ordinary native video path never clears additional animations")
        print("Round UI regression checks: \(checks)")
    }
}
'''


def execute_fixture(swiftc, root, name, text, expected=0, diagnostic=None):
    path = root / (name + '.swift'); path.write_text(text)
    results = []
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        binary = root / (name + '-' + mode)
        run([swiftc, '-swift-version', '5', '-parse-as-library', '-warnings-as-errors', '-module-cache-path', root / 'cache', *flags, path, '-o', binary])
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
        assert result.returncode == expected and (diagnostic is None or diagnostic in result.stderr), result.stdout + result.stderr
        results.append({'name': name, 'mode': mode, 'exit_code': result.returncode, 'output': (result.stdout + result.stderr).strip()})
        binary.unlink()
    return results


def semantic_negatives(archive, ui):
    return [
        ('old-deleted-identity', archive.replace('return Message(stableId: record.stableId ?? rendered.stableId,', 'return Message(stableId: rendered.stableId,'), 94, 'native first deletion'),
        ('old-live-deletion-timestamp', archive.replace('deletedAt: record.deletedAt ?? 0,', 'deletedAt: record.deletedAt ?? record.timestamp,'), 94, 'retaining a live'),
        ('old-once-playlist', ui.replace('item.message.minAutoremoveOrClearTimeout == viewOnceTimeout && !nagramiXCanUseTemporaryMediaActions(item.message)', 'item.message.minAutoremoveOrClearTimeout == viewOnceTimeout', 1), 95, 'effective once'),
        ('old-fetch-only', ui.replace('if self.nagramiXUsesRetainedPlayback {\n            self.activateVideoPlayback()', 'if false {\n            self.activateVideoPlayback()'), 95, 'one action'),
        ('old-opacity', ui.replace('nagramiXIsArchived ? 0.5 : 1.0', '(nagramiXIsArchived && false) ? 0.5 : 1.0'), 95, '50 percent'),
        ('old-handoff-transform', ui.replace('self.playerNode.layer.removeAnimation(forKey: "transform")', ''), 95, 'ownership handoff'),
    ]


def playback_module_tests(source, swiftc, root):
    """Compile the unmodified helper against separate Core and signal modules.

    Engine aliases, playlist identities, lookup and player filter are taken
    from production. Only scheduling and the manager's backing state are adapters.
    """
    root.mkdir()
    postbox = '''
public struct PeerId: Hashable { public let value: Int; public init(_ value:Int){self.value=value} }
public struct MessageId: Hashable { public let peerId:PeerId;public let id:Int32;public init(_ peerId:PeerId,_ id:Int32){self.peerId=peerId;self.id=id} }
public struct MessageIndex: Equatable { public let id:MessageId;public init(_ id:MessageId){self.id=id} }
public protocol MessageAttribute {}
public struct Message {public let id:MessageId;public let index:MessageIndex;public let attributes:[MessageAttribute];public init(_ id:MessageId,_ attributes:[MessageAttribute]=[]){self.id=id;self.index=MessageIndex(id);self.attributes=attributes}}
'''
    engine = (source / 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Message.swift').read_text()
    coding = (source / 'submodules/TelegramCore/Sources/TelegramEngine/Utils/EnginePostboxCoding.swift').read_text()
    alias = next(line for line in coding.splitlines() if line == 'public typealias EngineRawMessage = Message')
    # Native declarations are exported through TelegramCore; the caller must
    # not accidentally rely on a locally visible Postbox.Message symbol.
    core = 'import Postbox\n' + alias + '\npublic final class EngineMessage {\nprivate let impl:Message\n'
    for name in ('Id', 'Index', 'Attribute'):
        core += next(line for line in engine.splitlines() if 'public typealias ' + name + ' = ' in line) + '\n'
    core += 'public init(_ message:Message){self.impl=message}\n'
    for marker in ('    public var id:', '    public var index:', '    public var attributes:'):
        core += block(engine, marker) + '\n'
    core += '}\npublic enum EnginePeer {public typealias Id = PeerId}\npublic final class NagramiXArchivedMessageAttribute:MessageAttribute {public init(){}}\n'
    signal = (ROOT / 'scripts/tests/RoundReplaySignalBoundary.swift').read_text()
    api = (source / API).read_text()
    ids = (source / 'submodules/AccountContext/Sources/SharedMediaPlayer.swift').read_text()
    module = 'import Foundation\nimport TelegramCore\nimport SwiftSignalKit\n'
    for marker in ('public protocol SharedMediaPlaylistId {', 'public protocol SharedMediaPlaylistItemId {',
                   'public protocol InstantPagePlaylistIdProviding {', 'public protocol InstantPagePlaylistItemIndexProviding {',
                   'public struct RichMessagePlaylistId:', 'public struct RichMessagePlaylistItemId:',
                   'public struct PeerMessagesMediaPlaylistItemId:'):
        module += block(ids, marker) + '\n'
    module += block(api, 'public enum PeerMessagesMediaPlaylistId:') + '\n'
    module += block(api, 'public func peerMessagesMediaPlaylistAndItemId(') + '\n'
    module += block(api, 'public enum MediaManagerPlayerType {') + '\n'
    boundary = (ROOT / 'scripts/tests/RoundReplayPlayerBoundary.swift').read_text()
    filtered = block((source / 'submodules/TelegramUI/Sources/MediaManager.swift').read_text(), '    public func filteredPlaylistState(')
    module += boundary.replace('// INSERT_NATIVE_FILTER', filtered)
    production_helper = source / ACTION
    common = [swiftc, '-swift-version', '5', '-warnings-as-errors', '-module-cache-path', root / 'cache']
    suffix = '.dylib' if sys.platform == 'darwin' else '.so'
    dependencies = {'Postbox': [], 'TelegramCore': ['-lPostbox'], 'SwiftSignalKit': [],
                    'AccountContext': ['-lPostbox', '-lTelegramCore', '-lSwiftSignalKit']}
    for name, text in [('Postbox', postbox), ('TelegramCore', core), ('SwiftSignalKit', signal), ('AccountContext', module)]:
        path = root / (name + '.swift'); path.write_text(text)
        inputs = [path, production_helper] if name == 'AccountContext' else [path]
        run(common + ['-emit-library', '-emit-module', '-module-name', name, '-I', root, '-L', root, *dependencies[name], *inputs,
                      '-emit-module-path', root / (name + '.swiftmodule'), '-o', root / ('lib' + name + suffix)])
    test = root / 'main.swift'
    test.write_text((ROOT / 'scripts/tests/RoundReplayPlayerTests.swift').read_text())
    results = []
    import os
    environment = dict(os.environ)
    library_path = 'DYLD_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
    environment[library_path] = str(root) + (os.pathsep + environment[library_path] if environment.get(library_path) else '')
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        binary = root / ('playback-' + mode)
        run(common + flags + ['-parse-as-library', '-I', root, '-L', root, '-lPostbox', '-lTelegramCore', '-lSwiftSignalKit', '-lAccountContext', test, '-o', binary])
        result = run([binary], env=environment)
        results.append({'mode': mode, 'case': 'production-helper-native-identities', 'output': result.stdout.strip()})
    # The pre-fix fixed recentActions ID must fail the real native-peer case.
    helper = production_helper.read_text()
    old_helper = helper.replace('playlistId: playlistId,\n            itemId: itemId,', 'playlistId: PeerMessagesMediaPlaylistId.recentActions(message.id.peerId),\n            itemId: itemId,')
    assert old_helper != helper
    path = root / 'OldHelper.swift'
    # Keep the binding used in the new helper from becoming a test-only warning.
    path.write_text(old_helper.replace('guard let (playlistId, itemId)', 'guard let (_, itemId)'))
    run(common + ['-emit-library', '-emit-module', '-module-name', 'AccountContext', '-I', root, '-L', root, *dependencies['AccountContext'], root / 'AccountContext.swift', path,
                  '-emit-module-path', root / 'AccountContext.swiftmodule', '-o', root / ('libAccountContext' + suffix)])
    result = subprocess.run([str(root / 'playback-debug')], capture_output=True, text=True, env=environment)
    assert result.returncode == 96 and 'native single-message playlist' in result.stderr, result.stdout + result.stderr
    results.append({'case': 'old-helper-wrong-playlist', 'exit_code': result.returncode, 'output': result.stderr.strip()})
    path.write_text(helper.replace('import TelegramCore\n', ''))
    result = subprocess.run(list(map(str, common + ['-typecheck', '-module-name', 'AccountContext', '-I', root, root / 'AccountContext.swift', path])), capture_output=True, text=True)
    assert result.returncode != 0 and "cannot find type 'EngineRawMessage'" in result.stderr, result.stderr
    results.append({'case': 'missing-helper-core-import', 'expected_compiler_rejection': True})
    return results


def source_contract(source):
    plan = checked_plan(STAGE)
    assert set(plan['inputs']) == {ARCHIVE, IV, BUBBLE, NATIVE, ACTION, PLAYLIST, SHARED, OPEN}
    for name, value in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == value, name
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    # Unedited standard geometry remains byte-for-byte intact below the handoff.
    native = (source / NATIVE).read_text()
    before = (ROOT / 'ios' / plan['previous'][NATIVE]).read_text()
    tail = '        self.validLayout = (size, actualSize)'
    assert block(native, '    func updateLayout(size:')[block(native, '    func updateLayout(size:').index(tail):] == block(before, '    func updateLayout(size:')[block(before, '    func updateLayout(size:').index(tail):]
    assert 'nagramiXCanUseTemporaryMediaActions' in block((source / OPEN).read_text(), '    func openViewOnceMediaMessage(')
    # Shared and embedded sides must select the exact same retained identity.
    assert '|| nagramiXCanUseTemporaryMediaActions(item.message)' in (source / SHARED).read_text()
    assert '|| nagramiXCanUseTemporaryMediaActions(item.message)' in (source / IV).read_text()
    for name in (IV, PLAYLIST, SHARED, OPEN, ACTION):
        assert 'import TelegramCore\n' in (source / name).read_text()
    iv = (source / IV).read_text()
    assert 'let previouslyArchived = self.nagramiXVideoUsesRetainedIdentity' in iv
    assert 'strongSelf.nagramiXVideoUsesRetainedIdentity = nagramiXArchivedInstantVideo' in iv
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = source_contract(args.source)
    before = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='round-video-replay-') as temporary:
        root = Path(temporary)
        rejects = guard_checks(args.source, STAGE, plan, root / 'guards')
        archive, ui = archive_tests(args.source), ui_tests(args.source)
        results = execute_fixture(args.swiftc, root, 'archive', archive)
        results += execute_fixture(args.swiftc, root, 'ui', ui)
        for name, contents, code, diagnostic in semantic_negatives(archive, ui):
            results += execute_fixture(args.swiftc, root, name, contents, code, diagnostic)
        api_results = playback_module_tests(args.source, args.swiftc, root / 'playback-modules')
        for name in plan['outputs']:
            run([args.swiftc, '-frontend', '-parse', args.source / name])
    assert manifest(args.source) == before
    run(['python3', args.source / 'build-system/Make/PostboxImportCheck.py', args.source])
    report = {'stage': STAGE, 'source_files': len(before), 'outputs': plan['outputs'], 'guards': len(plan['guards']),
              'fail_closed': len(rejects), 'executions': results, 'module_playback': api_results, 'swift_parse': len(plan['outputs']),
              'native_postbox_imports': 'passed', 'source_unchanged_by_checks': True,
              'boundaries': 'Production archive, row flags, retained activation and handoff guard execute in explicit storage/signals/UI adapters. No AVFoundation decoder or UIKit execution.',
              'apple_sdk': 'not_run', 'ipa': 'not_built', 'physical_iphone': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('executions', 'outputs')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
