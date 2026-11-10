"""Production-ветви единого видеоплеера в явных адаптерах без UIKit/декодера."""
import re
from validate_quick_format import block
from temporary_playback_identity_runtime import UI_BOUNDARY

UI='submodules/TelegramUI/'
ROUND=UI+'Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift'
BUBBLE=UI+'Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift'
SHARED=UI+'Sources/SharedMediaPlayer.swift'
NATIVE='submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift'
MANAGER='submodules/TelegramUniversalVideoContent/Sources/UniversalVideoContentManager.swift'
POLICY='submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift'
CONTROLLER=UI+'Sources/ChatController.swift'
OPEN=UI+'Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift'

CHECK=r'''
var checks=0
func check(_ value:@autoclosure()->Bool,_ reason:String){if !value(){FileHandle.standardError.write(Foundation.Data(("Round native regression: "+reason+"\n").utf8));exit(91)};checks+=1}
'''

def ownership(source):
    native=(source/NATIVE).read_text();shared=(source/SHARED).read_text();row=(source/ROUND).read_text();manager=(source/MANAGER).read_text()
    shared_id=re.search(r'nagramiXArchivedMessageId: (.+)\), close:',shared).group(1)
    row_id=re.search(r'nagramiXArchivedMessageId: (.+)\), priority:',row).group(1)
    flag=next(line for line in row.splitlines() if 'let nagramiXArchivedInstantVideo = item.message.attributes.contains' in line)
    initial=native[native.index('        if let messageId = nagramiXArchivedMessageId,'):native.index('        self.userLocation = userLocation')]
    subscriber=block(manager,'private final class UniversalVideoContentSubscriber {').replace('private final','final')
    methods='\n'.join(block(manager,m).replace('public func','func') for m in ['    public func attachUniversalVideoContent(', '    public func detachUniversalVideoContent('])
    holder_methods='\n'.join(block(manager,m) for m in ['    func addSubscriber(', '    func removeSubscriberAndUpdate(', '    func update(forceUpdateId:'])
    return r'''
import Foundation
typealias MessageId=Int64
public typealias MediaId=Int64
typealias MediaResourceId=Int64
protocol MessageAttribute{}
struct NagramiXArchivedMessageAttribute:MessageAttribute{}
struct Message {var id:Int64;var stableId:UInt32;var temporary:Bool;var attributes:[MessageAttribute]}
struct Item {let message:Message}
struct File {var fileId:Int64=77;var isInstantVideo=true;var resource=Resource()}
struct Resource {var id:Int64=90}
struct Reference {var media=File()}
func nagramiXCanUseTemporaryMediaActions(_ message:Message)->Bool{message.temporary}
protocol UniversalVideoContent {var id:AnyHashable{get};func isEqual(to other:UniversalVideoContent)->Bool}
protocol UniversalVideoContentNode:AnyObject{}
class ASDisplayNode {var owner:String?}
final class Decoder:ASDisplayNode,UniversalVideoContentNode{}
enum UniversalVideoPriority:Int,Comparable {case secondaryOverlay=1,embedded=2;static func <(a:Self,b:Self)->Bool{a.rawValue<b.rawValue}}
final class Queue {static func mainQueue()->Queue{Queue()};func isCurrent()->Bool{true}}
final class Bag<T> {func copyItems()->[T]{[]}}
final class UniversalVideoContentHolderCallbacks {
let status=Bag<(Int?)->Void>(),bufferingStatus=Bag<(Int?)->Void>(),playbackCompleted=Bag<()->Void>(),isNativePictureInPictureActive=Bag<(Bool)->Void>()
}
'''+block(native,'public enum NativeVideoContentId:')+'\n'+block(native,'private struct NagramiXArchivedInstantVideoId:').replace('private ','')+r'''
final class Content:UniversalVideoContent {
var id:AnyHashable;var nativeId:NativeVideoContentId;var nagramiXArchivedInstantVideo:Bool
init(id:NativeVideoContentId,fileReference:Reference,nagramiXArchivedMessageId:MessageId?){
'''+initial+r'''
}
func isEqual(to other:UniversalVideoContent)->Bool{self.id==other.id}
}
func content(_ item:Item,_ reference:Reference,_ embedded:Bool)->Content{
'''+flag+r'''
return Content(id:.message(item.message.stableId,reference.media.fileId),fileReference:reference,nagramiXArchivedMessageId:embedded ? ('''+row_id+''') : ('''+shared_id+'''))
}
'''+subscriber+r'''
final class UniversalVideoContentHolder {
private var nextId:Int32=0;private var subscribers:[UniversalVideoContentSubscriber]=[]
let content:UniversalVideoContent;let contentNode:ASDisplayNode & UniversalVideoContentNode
var isEmpty:Bool{subscribers.isEmpty}
init(content:UniversalVideoContent,contentNode:ASDisplayNode & UniversalVideoContentNode,statusUpdated:@escaping(Int?)->Void,bufferingStatusUpdated:@escaping(Int?)->Void,playbackCompleted:@escaping()->Void,isNativePictureInPictureActiveUpdated:@escaping(Bool)->Void){self.content=content;self.contentNode=contentNode}
'''+holder_methods+r'''
}
final class Manager {
private var holders:[AnyHashable:UniversalVideoContentHolder]=[:];private var holderCallbacks:[AnyHashable:UniversalVideoContentHolderCallbacks]=[:]
'''+methods+r'''
}
'''+CHECK+r'''
@main struct OwnershipTests {static func main(){
for archived in [false,true] {for temporary in [false,true] {for overlayFirst in [false,true] {
 let item=Item(message:Message(id:11,stableId:3,temporary:temporary,attributes:archived ? [NagramiXArchivedMessageAttribute()]:[]))
 let reference=Reference(),manager=Manager();let embedded=content(item,reference,true),overlay=content(item,reference,false)
 check(embedded.id==overlay.id,"both subscribers use one content id")
 var creates=0;let decoder=Decoder()
 func attach(_ name:String,_ c:Content,_ priority:UniversalVideoPriority)->(AnyHashable,Int32){
 manager.attachUniversalVideoContent(content:c,priority:priority,create:{creates+=1;return decoder},update:{value in if let value{value.0.owner=name}else if decoder.owner==name{decoder.owner=nil}})
 }
 var embeddedToken:(AnyHashable,Int32),overlayToken:(AnyHashable,Int32)
 if overlayFirst {overlayToken=attach("overlay",overlay,.secondaryOverlay);embeddedToken=attach("row",embedded,.embedded)}
 else {embeddedToken=attach("row",embedded,.embedded);overlayToken=attach("overlay",overlay,.secondaryOverlay)}
 check(creates==1 && decoder.owner=="row","exactly one native surface; visible row owns playback")
 manager.detachUniversalVideoContent(id:embeddedToken.0,index:embeddedToken.1)
 check(decoder.owner=="overlay","scrolling out moves the same decoder to overlay")
 embeddedToken=attach("row",embedded,.embedded)
 check(creates==1 && decoder.owner=="row","returning hands back the same decoder")
 manager.detachUniversalVideoContent(id:overlayToken.0,index:overlayToken.1)
 check(decoder.owner=="row","detaching inactive overlay preserves row ownership")
 manager.detachUniversalVideoContent(id:embeddedToken.0,index:embeddedToken.1)
 check(decoder.owner==nil,"last owner detaches cleanly")
 if archived {
  let changedStable=Item(message:Message(id:11,stableId:99,temporary:temporary,attributes:[NagramiXArchivedMessageAttribute()]))
  check(content(changedStable,reference,true).id==embedded.id,"legacy archive does not depend on synthetic stable id")
  var changedReference=reference;changedReference.media.resource.id+=1
  check(content(item,changedReference,true).id != embedded.id,"independent archive resource retains distinct decoder identity")
 }
}}}
print("PASS native ownership checks: \(checks)")
}}
'''

def recording(source):
    policy=(source/POLICY).read_text();controller=(source/CONTROLLER).read_text();opening=(source/OPEN).read_text()
    helper=block(policy,'public func nagramiXShouldBlockViewOnceScreenCapture(').replace('public ','')
    permission=block(policy,'    var nagramiXAllowsScreenshotBypass: Bool {')
    gate=block(controller,'                        if (file.isVoice || file.isInstantVideo) && message.minAutoremoveOrClearTimeout == viewOnceTimeout')
    alert=re.search(r'        if (self.screenCaptureManager\?\.isRecordingActive.+) \{',opening).group(1)
    stop=block(controller,'                                if let item = state.item as? MessageMediaPlaylistItem,').replace('return','return false')
    return r'''
import Foundation
let viewOnceTimeout:Int32 = .max
struct Peer {var isVerificationCodes=false}
struct Id {var peerId=Peer()}
struct Message {var id=Id();var paidContent:Int?;var retained=true;var minAutoremoveOrClearTimeout:Int32?=viewOnceTimeout
'''+permission+r'''
func _asMessage()->Message{self}}
struct File {var isVoice=false;var isInstantVideo=true}
struct NagramiXPrivacySettings {static var current=NagramiXPrivacySettings();var bypassScreenshots=false}
func nagramiXCanUseTemporaryMediaActions(_ message:Message)->Bool{message.retained}
struct EngineMessage{init(_ message:Message){}}
final class Capture {var isRecordingActive=false}
final class MessageMediaPlaylistItem {let message:Message;init(_ message:Message){self.message=message}}
struct State {let item:Any}
'''+helper+r'''
final class Router {let screenCaptureManager:Capture?=Capture();var disposable=0
func openViewOnceMediaMessage(_ message:EngineMessage){disposable+=1}
func opensNormal(_ message:Message,_ file:File)->Bool {
'''+gate+r'''
return true
}
func showsAlert(_ message:Message)->Bool{if '''+alert+r''' {return true};return false}
func recordingStops(_ state:State)->Bool {
'''+stop+r'''
return true
}}
'''+CHECK+r'''
@main struct RecordingTests {static func main(){
for free in [false,true] {for retained in [false,true] {for captured in [false,true] {for paid in [false,true] {for codes in [false,true] {
 NagramiXPrivacySettings.current.bypassScreenshots=free
 let router=Router();router.screenCaptureManager?.isRecordingActive=captured
 let message=Message(id:Id(peerId:Peer(isVerificationCodes:codes)),paidContent:paid ? 1:nil,retained:retained)
 let blocked = !free || paid || codes
 check(nagramiXShouldBlockViewOnceScreenCapture(message)==blocked,"capture permission matrix")
 check(router.opensNormal(message,File()) == (retained && !(captured && blocked)),"retained recording route stays in native chat player")
 check(router.showsAlert(message)==(captured && blocked),"free content does not show recording alert")
 check(router.recordingStops(State(item:MessageMediaPlaylistItem(message)))==blocked,"recording detector respects live capture policy")
 check(router.recordingStops(State(item:0)),"unknown playlist item keeps native capture policy")
}}}}}
print("PASS recording route checks: \(checks)")
}}
'''

def presentation(source):
    row=(source/ROUND).read_text();bubble=(source/BUBBLE).read_text()
    flags=row[row.index('            let isViewOnceMessage ='):row.index('            if isSecretMedia {')]
    flags=flags.replace('            let theme = item.presentationData.theme\n','')
    idle_start=row.index('            self.videoNode?.isHidden = isSecretMedia || isViewOnceMessage')
    idle_end=row.index('\n        }\n    }',idle_start)
    idle=row[idle_start:idle_end]
    playing=block(row,'            if let dustNode = self.dustNode {') if row.count('            if let dustNode = self.dustNode {')==1 else ''
    assert playing
    footer=bubble[bubble.index('            let statusFrame = CGRect(',bubble.index('        if nagramiXIsArchived {\n            let nagramiXStatusWasVisible')):bubble.index('\n        } else {\n            strongSelf.nagramiXDeletedStatusNode?.removeFromSupernode()')]
    return r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
struct Message {var once=true;var retained=true;var containsSecretMedia=true}
struct Data {var isPreview=false}
struct Interaction {var enableFullTranslucency=true}
struct Item {var message=Message();var presentationData=Data();var controllerInteraction=Interaction()}
func nagramiXIsViewOnceMessage(_ message:Message)->Bool{message.once}
func nagramiXCanUseTemporaryMediaActions(_ message:Message)->Bool{message.retained}
struct Color {static let white=Color()}
enum Transition {case immediate}
class Surface {var isHidden=false;var clipsToBounds=false;var cornerRadius:CGFloat=0;var frame:CGRect = .zero;var removed=false;var layer:Surface{self}
 func removeFromSupernode(){removed=true}
}
final class MediaDustNode:Surface {init(enableAnimations:Bool){};func update(size:CGSize,color:Color,transition:Transition){}}
final class Node {
 var videoNode:Surface?=Surface();var secretVideoPlaceholderBackground=Surface(),secretVideoPlaceholder=Surface(),dateAndStatusNode=Surface();var dustNode:MediaDustNode?
 func insertSubnode(_ node:MediaDustNode,belowSubnode:Surface){}
 func idle(_ item:Item,_ videoFrame:CGRect){
'''+flags+idle+r'''
 _ = requiresDisposableViewOnce
 }
 func playing(){videoNode?.isHidden=false;secretVideoPlaceholderBackground.isHidden=true;secretVideoPlaceholder.isHidden=true
'''+playing+r'''
 }
}
final class Animator {var updates=0;func updateFrame(layer:Surface,frame:CGRect,completion:((Bool)->Void)?){updates+=1;layer.frame=frame}}
struct Animation {let animator=Animator()}
func footer(_ statusNode:Surface,_ iconNode:Surface,_ backgroundFrame:CGRect,_ statusSize:CGSize,_ nagramiXStatusWasVisible:Bool,_ animation:Animation){
'''+footer+r'''
}
'''+CHECK+r'''
@main struct PresentationTests {static func main(){
let node=Node();let frame=CGRect(x:0,y:0,width:404,height:404)
for retained in [true,false] {for once in [true,false] {
 let item=Item(message:Message(once:once,retained:retained,containsSecretMedia:once))
 node.idle(item,frame)
 check(node.videoNode!.isHidden==once,"view-once cover is independent of retention")
 check((node.dustNode != nil)==once,"stock dust exists while idle")
 if once {check(node.dustNode!.frame==frame && node.dustNode!.cornerRadius==202,"dust follows circle geometry")}
 node.playing()
 check(!node.videoNode!.isHidden && node.dustNode==nil,"playing reveals the native surface and removes dust")
 node.idle(item,frame)
 check((node.dustNode != nil)==once,"replay restores original idle presentation")
}}
node.idle(Item(),frame);node.idle(Item(message:Message(once:false,retained:true,containsSecretMedia:false)),frame)
check(node.dustNode==nil,"reused ordinary row cannot retain old dust")
for height in [80.0,220.0,404.0] {for width in [200.0,320.0] {for existing in [false,true] {
 let status=Surface(),icon=Surface(),animation=Animation();let size=CGSize(width:150,height:30)
 footer(status,icon,CGRect(x:9,y:20,width:width,height:height),size,existing,animation)
 check(animation.animator.updates==(existing ? 2:0),"existing deletion footer uses native animator")
 check(status.frame.maxY==20+height-4 && icon.frame.maxX==status.frame.minX-4,"footer/icon stay aligned with message height")
}}}
print("PASS round cover and footer checks: \(checks)")
}}
'''

def activation(source):
    row=(source/ROUND).read_text();activate=block(row,'    private func activateVideoPlayback()')
    activate=activate[:activate.index('        if self.infoBackgroundNode.alpha.isZero {')]+'        nativeFetchOnly += 1\n    }'
    return UI_BOUNDARY+r'''
final class Node {var item:Item?;var media:File?=File();var nativeFetchOnly=0;var allow=true;var status:Status?
let nagramiXArchivedPlaybackAction=NagramiXArchivedPlaybackAction();func shouldOpen()->Bool{allow}
'''+block(row,'    private var nagramiXIsArchivedInstantVideo: Bool {').replace('private ','')+'\n'+block(row,'    private var nagramiXUsesRetainedPlayback: Bool {').replace('private ','')+'\n'+activate.replace('private ','')+'\n}\n'+CHECK+r'''
@main struct ActivationTests {static func main(){
for archived in [false,true] {for staleStatus in [false,true] {
 let item=Item(message:Message(retained:true,archived:archived));let node=Node();node.item=item
 node.status=Status(mediaStatus:staleStatus ? .playbackStatus:.fetchStatus)
 node.activateVideoPlayback()
 check(item.context.sharedContext.mediaManager.toggles==0,"stale row state never toggles a different selected player")
 check(node.nagramiXArchivedPlaybackAction.pending.count==1,"live and archive activation resolve exact native playlist")
 node.nagramiXArchivedPlaybackAction.drain();check(item.controllerInteraction.opens==1,"one tap opens selected message")
 node.activateVideoPlayback();node.item=Item(message:Message(id:2,retained:true,archived:archived));node.nagramiXArchivedPlaybackAction.drain()
 check(item.controllerInteraction.opens==1,"reused row cancels stale asynchronous activation")
}}
print("PASS selected playback activation checks: \(checks)")
}}
'''

def negatives(fixtures):
    def changed(name,key,old,new,reason):
        text=fixtures[key];assert old in text,name
        return name,text.replace(old,new,1),reason
    return [
        changed('split-live-surface','ownership','item.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) ? item.message.id : nil','(item.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) || nagramiXCanUseTemporaryMediaActions(item.message)) ? item.message.id : nil','both subscribers use one content id'),
        changed('recording-alert-ignores-free','recording','if self.screenCaptureManager?.isRecordingActive == true && nagramiXShouldBlockViewOnceScreenCapture(message._asMessage())','if self.screenCaptureManager?.isRecordingActive == true','free content does not show recording alert'),
        changed('recording-route-ignores-free','recording','self.screenCaptureManager?.isRecordingActive == true && nagramiXShouldBlockViewOnceScreenCapture(message)','self.screenCaptureManager?.isRecordingActive == true','retained recording route'),
        changed('cover-lost','presentation','if isViewOnceMessage {\n                let dustNode:','if requiresDisposableViewOnce {\n                let dustNode:','stock dust exists while idle'),
        changed('footer-jumps','presentation','if nagramiXStatusWasVisible {','if nagramiXStatusWasVisible && false {','existing deletion footer uses native animator'),
        changed('live-skips-exact-player','activation','if self.nagramiXUsesRetainedPlayback || nagramiXCanUseTemporaryMediaActions(item.message) {','if self.nagramiXUsesRetainedPlayback {','live and archive activation resolve exact native playlist'),
    ]
