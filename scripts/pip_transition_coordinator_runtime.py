"""Исполнение production переходов; AVKit/DOM/отрисовка — явные границы."""
from pathlib import Path
from validate_quick_format import block
from validate_pip_swipe_handoff import U,G,N,clean
from pip_preview_continuity_runtime import POSTER_BOUNDARY
ROOT=Path(__file__).resolve().parents[1]

def entry_fixture(source):
    t=(source/U).read_text();n=(source/N).read_text()
    code=(ROOT/'scripts/tests/NagramiXPiPCoordinatorBoundary.swift').read_text()
    code=code.replace('// PRODUCTION_STATE',clean(block(t,'private enum NagramiXPiPVideoGeometry'))+'\n'+clean(block(t,'private struct NagramiXNativePiPVisualState'))+'\n'+clean(block(t,'private final class NagramiXNativePiPPresentationAcknowledgement')))
    reset='\n'.join(clean(block(n,m)) for m in ['    func nagramiXResetNativePictureInPictureSwipe(', '    func nagramiXLockNativePictureInPictureSwipe()'])
    code=code.replace('// PRODUCTION_RESET',reset)
    markers=['    private func nagramiXCancelPiPEntryTimer()', '    private func nagramiXAbortPiPEntry()', '    private func nagramiXRequestPictureInPicture()', '    private func nagramiXTryStartPictureInPicture()', '    private func nagramiXCommitPiPHandoff(', '    private func nagramiXApplyVideoDimensions(', '    private func nagramiXBeginNativePiPVisualTransition()', '    private func nagramiXFinishNativePiPVisualTransition(', '    private func nagramiXCanUsePiPSourceLayer(', '    private func nagramiXNativePiPRendererReady()', '    private func nagramiXTryFinishNativePiPRestore()', '    private func nagramiXAwaitNativePiPPresentation(', '    private func nagramiXBeginWebPictureInPicture()', '    private func nagramiXRestoreSystemWebPiP(', '    private func nagramiXFinishSystemWebPiP(', '    @objc func pictureInPictureButtonPressed()', '    func expandPIP()', '    fileprivate func nagramiXHasAnotherActiveNativePictureInPictureContent(']
    methods='\n'.join(clean(block(t,m)).replace('fileprivate func','func').replace('private func','func') for m in markers)
    assert '@discardableResult\n    private func nagramiXRequestPictureInPicture' in t
    methods=methods.replace('func nagramiXRequestPictureInPicture()', '@discardableResult\n    func nagramiXRequestPictureInPicture()',1)
    code=code.replace('// PRODUCTION_COORDINATOR',methods)
    setup=block(t,'    private func setupNativePictureInPicture()')
    callbacks={name:clean(block(setup,name+': {')).removeprefix(name+': ') for name in ['willBegin','didBegin','didEnd','expand','failedToBegin']}
    for name,value in callbacks.items():code=code.replace('// PRODUCTION_'+name,value)
    return (code+'\n'+(ROOT/'scripts/tests/NagramiXPiPCoordinatorTests.swift').read_text()).replace('fileprivate ','').replace('private ','')

def poster_fixture(source):
    t=(source/U).read_text();g=(source/G).read_text()
    b=POSTER_BOUNDARY.replace('struct MediaPlayerStatus {}','struct MediaPlayerStatus {let dimensions:CGSize}')
    b=b.replace('final class UIView {','''final class UIView {
 var alpha:Double=1;var window:AnyObject?=NSObject();var bounds:CGRect{CGRect(origin:.zero,size:frame.size)}
 var isUserInteractionEnabled=true,accessibilityElementsHidden=false
 static var snapshots=0
 func snapshotView(afterScreenUpdates:Bool)->UIView?{Self.snapshots+=1;return UIView()}
 static func animate(withDuration:Double,animations:()->Void,completion:(Bool)->Void){animations();completion(true)}
''')
    b=b.replace('let cgColor=0}','let cgColor=0;func withAlphaComponent(_ value:Double)->UIColor{self}}')
    code=b+'\n'+clean(block(t,'private enum NagramiXPiPVideoGeometry'))+'\n'+clean(block(t,'private struct NagramiXNativePiPVisualState'))+'\n'+clean(block(t,'private final class UniversalVideoGalleryItemPictureInPictureNode:'))
    code+='''
final class PosterHost:ASDisplayNode {
 var item:UniversalVideoGalleryItem?,videoNode:ASDisplayNode?,playerStatusValue:MediaPlayerStatus?
 var nagramiXPiPDeferredDimensions:CGSize?
 var nagramiXPiPVisualState=NagramiXNativePiPVisualState()
 weak var controller:GalleryController?
 func galleryController()->GalleryController?{controller}
'''+clean(block(t,'    func nagramiXMakePiPPreviewPoster()'))+'''
}
typealias UniversalVideoGalleryItemNode=PosterHost
final class Pager {var item:PosterHost?;func centralItemNode()->ASDisplayNode?{item}}
final class GalleryNode {let pager=Pager();var suppressed=false;func nagramiXSetNativePictureInPictureChatTransitionSuppressed(_ value:Bool){suppressed=value}}
final class ChatController {func updatePushedTransition(_ value:Double,transition:ContainedViewLayoutTransition){}}
final class Navigation {var topViewController:AnyObject?=ChatController()}
final class GalleryController {
 let view=UIView(),galleryNode=GalleryNode()
 let baseNavigationController:Navigation?=Navigation()
 var nagramiXNativePiPBackdrop:UIView?,nagramiXNativePiPBackdropPoster:ASDisplayNode?
 weak var nagramiXNativePiPBackdropSource:UIView?
 var nagramiXNativePiPBackdropBounds:CGRect?
 var nagramiXNativePiPBackdropActive=false,nagramiXNativePiPBackdropPreparing=false
 var nagramiXNativePiPBackdropGeneration=0,restores=0
 func nagramiXRestoreHiddenMediaAfterPiP(){restores+=1}
'''
    for m in ['    func nagramiXPrepareNativePiPBackdrop()', '    func nagramiXShowNativePiPBackdrop()', '    func nagramiXFinishNativePiPBackdrop(', '    private func nagramiXUpdateNativePiPBackdropLayout()']:
        code+='\n'+clean(block(g,m)).replace('private func','func')
    return code+'\n}\n'+(ROOT/'scripts/tests/NagramiXPiPCoordinatorPosterTests.swift').read_text()

def native_fixture(source):
    t=(source/U).read_text()
    code='''import Foundation
final class AVSampleBufferDisplayLayer {}
final class AVPictureInPictureController {
 var isPictureInPicturePossible=true,isPictureInPictureActive=false,starts=0,stops=0
 func startPictureInPicture(){starts+=1}
 func stopPictureInPicture(){stops+=1;isPictureInPictureActive=false}
}
final class Node {var layer:AVSampleBufferDisplayLayer?=AVSampleBufferDisplayLayer();func getVideoLayer()->AVSampleBufferDisplayLayer?{layer}}
final class WorkQueue {var jobs:[()->Void]=[];func async(_ f:@escaping()->Void){jobs.append(f)}}
enum DispatchQueue {static let main=WorkQueue()}
final class NativeLifecycle {
 let node=Node();var pictureInPictureController:AVPictureInPictureController?=AVPictureInPictureController()
 weak var nagramiXOriginalSourceLayer:AVSampleBufferDisplayLayer?
 var nagramiXStartCancelled=false,isStarting=false,hasExplicitStart=false,nagramiXExpandWhenStarted=false
 var leaseReleases=0,restoreCancels=0,begins=0,expands=0
 init(){nagramiXOriginalSourceLayer=node.layer}
 func nagramiXReleaseHierarchyPlayback(){leaseReleases+=1}
 func nagramiXCancelInterfaceRestore(){restoreCancels+=1}
 func didBegin(_ own:NativeLifecycle){precondition(own===self);begins+=1}
 func requestExpand(){expands+=1}
'''
    for m in ['    var matchesSourceLayer:', '    var canBeginPictureInPicture:', '    func beginPictureInPicture()', '    func cancelPendingStart()', '    public func pictureInPictureControllerDidStartPictureInPicture(']:
        code+='\n'+clean(block(t,m))
    code=code.replace('    func beginPictureInPicture()', '    @discardableResult func beginPictureInPicture()')
    return code+'\n}\n'+(ROOT/'scripts/tests/NagramiXPiPCoordinatorNativeTests.swift').read_text()
