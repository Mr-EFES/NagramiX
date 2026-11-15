"""Реальные UIKit/AVKit API всех новых переходов до долгой app-компиляции."""
from pathlib import Path
import subprocess,sys
from validate_quick_format import block
from validate_pip_swipe_handoff import U,G,clean
from pip_preview_continuity_apple import fixture as old_probe,public_contract
from pip_transition_coordinator_runtime import entry_fixture
from pip_texture_adapter_contract import check as texture_adapter_check
from pip_poster_animation_contract import check as poster_animation_check

def coordinator_probe(source):
    text=(source/U).read_text()
    code=entry_fixture(source).split('var checks=0',1)[0]
    code=code.replace('import Foundation','import Foundation\nimport UIKit\nimport AVKit',1)
    code=code.replace(block(code,'final class Layer {'),'typealias Layer=AVSampleBufferDisplayLayer')
    code=code.replace('typealias AVSampleBufferDisplayLayer=Layer','')
    code=code.replace(block(code,'class View {'),'typealias View=UIView')
    code=code.replace('var bounds:CGRect{view.bounds}','var bounds:CGRect{view.bounds}')
    code=code.replace('controller.view.window=attaches ? NSObject():nil;','')
    code=code.replace('view.window=nil;','').replace('controller?.view.window=nil','')
    code=code.replace('var sourceLayer:Layer?=Layer(),ownsContentNode=true,backgroundColor:Int?=1','var sourceLayer:Layer?=Layer(),ownsContentNode=true;var backgroundColor:UIColor? = .black')
    code=code.replace('var nagramiXPiPOriginalVideoBackground:Int?','var nagramiXPiPOriginalVideoBackground:UIColor?')
    code=code.replace('let view=View(),layer=Layer();','let view=View();var layer:CALayer{view.layer};')
    code=code.replace(block(code,'final class NagramiXNativePiPSourceClipping {'),clean(block(text,'private final class NagramiXNativePiPSourceClipping {')))
    # Runtime hosts use Bool readiness/event delivery; typecheck the actual new
    # AVKit calls and source-identity/cancellation implementation separately.
    code+='''
final class NativeAPIProbe {
 let node=UniversalVideoNode()
 var pictureInPictureController:AVPictureInPictureController?
 weak var nagramiXOriginalSourceLayer:AVSampleBufferDisplayLayer?
 var nagramiXStartCancelled=false,isStarting=false,hasExplicitStart=false,nagramiXExpandWhenStarted=false
 func nagramiXReleaseHierarchyPlayback(){}
 func nagramiXCancelInterfaceRestore(){}
 func didBegin(_ own:NativeAPIProbe){}
 func requestExpand(){}
'''
    for m in ['    var matchesSourceLayer:', '    var canBeginPictureInPicture:', '    func beginPictureInPicture()', '    func cancelPendingStart()', '    public func pictureInPictureControllerDidStartPictureInPicture(']:code+='\n'+clean(block(text,m))
    return code+'\n}\n'

def poster_probe(source):
    code=old_probe(source,source)
    t=(source/U).read_text();g=(source/G).read_text()
    code=code.replace('struct MediaPlayerStatus {}','struct MediaPlayerStatus {let dimensions:CGSize}')
    code=code.replace('final class Restorer:NSObject,AVPictureInPictureControllerDelegate {','final class Restorer:NSObject,AVPictureInPictureControllerDelegate {\n var nagramiXStartCancelled=false')
    code=clean(block(t,'private enum NagramiXPiPVideoGeometry'))+'\n'+clean(block(t,'private struct NagramiXNativePiPVisualState'))+'\n'+code
    code+='''
private final class UniversalVideoGalleryItemNode:ASDisplayNode {
 var item:UniversalVideoGalleryItem?,videoNode:ASDisplayNode?,playerStatusValue:MediaPlayerStatus?
 var nagramiXPiPDeferredDimensions:CGSize?
 var nagramiXPiPVisualState=NagramiXNativePiPVisualState()
 weak var controller:GalleryController?
 func galleryController()->GalleryController?{controller}
'''+clean(block(t,'    func nagramiXMakePiPPreviewPoster()'))+'''
}
private final class Pager {var item:UniversalVideoGalleryItemNode?;func centralItemNode()->ASDisplayNode?{item}}
private final class GalleryNode {let pager=Pager();func nagramiXSetNativePictureInPictureChatTransitionSuppressed(_ value:Bool){}}
private final class ChatController {func updatePushedTransition(_ value:Double,transition:ContainedViewLayoutTransition){}}
private final class Navigation {var topViewController:AnyObject?}
private final class GalleryController {
 let view=UIView(),galleryNode=GalleryNode()
 let baseNavigationController:Navigation?=Navigation()
 var nagramiXNativePiPBackdrop:UIView?,nagramiXNativePiPBackdropPoster:ASDisplayNode?
 weak var nagramiXNativePiPBackdropSource:UIView?
 var nagramiXNativePiPBackdropBounds:CGRect?
 var nagramiXNativePiPBackdropActive=false,nagramiXNativePiPBackdropPreparing=false
 var nagramiXNativePiPBackdropGeneration=0
 func nagramiXRestoreHiddenMediaAfterPiP(){}
'''
    for m in ['    func nagramiXPrepareNativePiPBackdrop()', '    func nagramiXShowNativePiPBackdrop()', '    func nagramiXFinishNativePiPBackdrop(', '    private func nagramiXUpdateNativePiPBackdropLayout()']:code+='\n'+clean(block(g,m))
    return code+'\n}\n'

def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    members=public_contract(source)
    texture=texture_adapter_check(source,swiftc,folder/'texture-adapter')
    animation=poster_animation_check(source,swiftc,folder/'poster-animation')
    probes={'coordinator':coordinator_probe(source),'poster':poster_probe(source)}
    for name,code in probes.items():
        p=folder/(name+'.swift');p.write_text(code)
        parsed=subprocess.run([str(swiftc),'-frontend','-parse',str(p)],capture_output=True,text=True);assert parsed.returncode==0,parsed.stdout+parsed.stderr
    result={'status':'not_run','reason':'Настоящие UIKit/AVKit требуют Apple SDK; Linux выполняет отдельные production fixtures.','probe_swift_parse':'passed','native_public_image_contract':members,'texture_adapter':texture,'poster_animation_clock':animation,'full_application_sdk':'not_run','physical_iphone':'pending'}
    if sys.platform!='darwin':return result
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    for name in probes:
        args=[str(swiftc),'-swift-version','5','-warnings-as-errors','-typecheck','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),str(folder/(name+'.swift'))]
        checked=subprocess.run(args,capture_output=True,text=True,timeout=180);assert checked.returncode==0,checked.stdout+checked.stderr
    result.update(status='passed',target='arm64-apple-ios15.0',scope='Actual shared request/commit/restore/rollback bodies, actual native cancellation/DidStart guards and full source poster/layout code with real UIKit/AVKit/CoreGraphics. Account/navigation/signal/timers and native event delivery are explicit graph hosts; PhotoResources/Display image declarations copied from canonical source. Native app link, live decoder and pixel rendering are separate.')
    result.pop('reason')
    return result
