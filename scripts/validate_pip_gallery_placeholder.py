#!/usr/bin/env python3
"""Check PiP frame continuity and unchanged native ownership/animation paths."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_pip_swipe_handoff import runtime, clean, U
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

ROOT=Path(__file__).resolve().parents[1]
STAGE='pip_gallery_placeholder'
D='submodules/GalleryUI/Sources/GalleryVideoDecoration.swift'
V='submodules/AccountContext/Sources/UniversalVideoNode.swift'


def run(command, **kwargs):
    result=subprocess.run(list(map(str,command)),capture_output=True,text=True,**kwargs)
    assert result.returncode==0,result.stdout+result.stderr
    return result


def handoff_fixture(source):
    text=runtime(source)
    u=(source/U).read_text()
    methods='\n'.join(clean(block(u,marker)) for marker in (
        '    private func updateDisplayPlaceholder() {',
        '    private func updateDisplayPlaceholder(_ displayPlaceholder: Bool) {',
    ))
    marker='    func updateControlsVisibility(_ visible: Bool) {}'
    assert text.count(marker)==1
    text=text.replace(marker, marker+'''
    var disablePictureInPicturePlaceholder = false
    var pictureInPictureNode: UniversalVideoGalleryItemPictureInPictureNode?
    let pictureInPictureButton: PictureButton? = PictureButton()
    let presentationData = PresentationData()
    let validLayout: (ContainerLayout, CGFloat)? = nil
    func insertSubnode(_ node: UniversalVideoGalleryItemPictureInPictureNode, aboveSubnode: ScrollNode) {}
'''+methods)
    text=text.replace('final class UniversalVideoNode {', 'final class UniversalVideoNode {\n    var backgroundColor: UIColor?')
    text=text.replace('@main enum PiPSwipeTests', 'enum PiPSwipeTests',1)
    # Execute the real ownership callback's restoration prefix as a separate
    # fixture method; the remainder is unchanged unrelated autoplay handling.
    marker='                    if value {\n                        strongSelf.nagramiXRestoreNativePictureInPicturePlaceholderIfOwned()\n                    }\n                    strongSelf.updateDisplayPlaceholder(!value)'
    assert u.count(marker)==1
    callback=marker.replace('strongSelf.','self.')
    text+='''
extension GalleryHarness {
    func ownershipChanged(_ value: Bool) {
        self.videoNode?.ownsContentNode=value
'''+callback+'''
    }
}
extension UIColor {static var black:Self {Self(white:0,alpha:1)}}
extension TestContent {var dimensions:CGSize {CGSize(width:320,height:180)}}
extension CGSize {func fitted(_ limit:CGSize)->CGSize {self}}
func floorToScreenPixels(_ value:CGFloat)->CGFloat {floor(value)}
final class PictureButton {var isEnabled=true}
final class UniversalVideoGalleryItemPictureInPictureNode {
    enum Mode {case pictureInPicture}
    static var created=0
    var frame=CGRect.zero
    var isUserInteractionEnabled=true
    init(strings:PresentationStrings,mode:Mode){Self.created+=1}
    func updateLayout(_ size:CGSize,transition:Transition){}
    func removeFromSupernode(){}
}
'''
    return text+HANDOFF_TESTS


HANDOFF_TESTS=r'''
@main enum PlaceholderTests {
    static func main() {
        PiPSwipeTests.main()
        let previousChecks=checks
        func cardCount()->Int {UniversalVideoGalleryItemPictureInPictureNode.created}
        for swipe in [false,true] {
            let owner=makeOwner()
            if swipe {owner.gallery.galleryNode.scrollViewWillBeginDragging(owner.gallery.galleryNode.scrollView);drag(owner,distance:12)}
            else {owner.pictureInPictureButtonPressed()}
            DispatchQueue.main.flush()
            let controller=AVPictureInPictureController.instances.last!
            check(owner.disablePictureInPicturePlaceholder,"native request suppresses technical card before handoff")
            let before=cardCount()
            owner.ownershipChanged(false)
            check(owner.pictureInPictureNode==nil && cardCount()==before,"ownership handoff cannot flash technical card")
            check(owner.gallery.view.alpha==1 && owner.dismissals==0,"source remains visible until native DidStart")
            controller.finishStart();AnimationClock.flush()
            check(owner.disablePictureInPicturePlaceholder && owner.dismissals==1,"active PiP retains suppression and native gallery dismissal")
            let content=owner.nativePictureInPictureContent as! NativePictureInPictureContentImpl
            var completions=0
            content.expand {completions+=1}
            check(completions==1 && owner.gallery.view.alpha==1 && owner.disablePictureInPicturePlaceholder,"expand restores gallery with continuity instead of technical card")
            owner.ownershipChanged(true)
            check(owner.disablePictureInPicturePlaceholder && cardCount()==before,"ownership before AVKit stop does not release suppression")
            controller.stopPictureInPicture()
            check(!owner.disablePictureInPicturePlaceholder && owner.pictureInPictureNode==nil,"completed restore returns ordinary placeholder policy")
            owner.ownershipChanged(false)
            check(owner.pictureInPictureNode != nil && cardCount()==before+1,"unrelated non-PiP ownership loss keeps native fallback")
            owner.ownershipChanged(true)
            check(owner.pictureInPictureNode==nil,"reacquisition removes unrelated fallback")
        }
        let failed=makeOwner();failed.pictureInPictureButtonPressed();DispatchQueue.main.flush()
        let controller=AVPictureInPictureController.instances.last!
        failed.ownershipChanged(false);let before=cardCount();controller.failStart()
        check(failed.disablePictureInPicturePlaceholder && failed.pictureInPictureNode==nil && cardCount()==before,"failed start without source cannot flash technical card")
        failed.ownershipChanged(true)
        check(!failed.disablePictureInPicturePlaceholder && failed.pictureInPictureNode==nil,"failed start recovers once actual source returns")
        print("PiP placeholder lifecycle checks: \(checks-previousChecks)")
    }
}
'''


def decoration_fixture(source):
    d=(source/D).read_text()
    # These four production methods own the snapshot lifecycle and layout.
    methods='\n'.join(clean(block(d,marker)) for marker in (
        '    public func updateContentNode(', '    public func updateContentNodeSnapshot(',
        '    public func updateLayout(',
    ))
    return DECORATION_BOUNDARY+'''
final class GalleryVideoDecoration {
    let contentContainerNode=ASDisplayNode()
    let backgroundNode:ASDisplayNode?=nil
    let foregroundNode:ASDisplayNode?=nil
    var contentNode:(ASDisplayNode & UniversalVideoContentNode)?
    var contentNodeSnapshot:UIView?
    var validLayout:(size:CGSize,actualSize:CGSize)?
'''+methods+'\n}\n'+DECORATION_TESTS


DECORATION_BOUNDARY=r'''
import Foundation
final class Layer {
    weak var view:UIView?
    var mask:Layer?
    var frame:CGRect {get{view?.frame ?? .zero}set{view?.frame=newValue}}
}
final class UIView {
    var frame=CGRect.zero
    lazy var layer:Layer={let layer=Layer();layer.view=self;return layer}()
    private(set) var subviews:[UIView]=[]
    weak var superview:UIView?
    func addSubview(_ view:UIView){view.removeFromSuperview();subviews.append(view);view.superview=self}
    func removeFromSuperview(){superview?.subviews.removeAll{$0===self};superview=nil}
}
class ASDisplayNode {
    let view=UIView()
    var layer:Layer {view.layer}
    var frame:CGRect {get{view.frame}set{view.frame=newValue}}
    weak var supernode:ASDisplayNode?
    var children:[ASDisplayNode]=[]
    func addSubnode(_ node:ASDisplayNode){node.removeFromSupernode();children.append(node);node.supernode=self;view.addSubview(node.view)}
    func removeFromSupernode(){supernode?.children.removeAll{$0===self};supernode=nil;view.removeFromSuperview()}
}
enum ContainedViewLayoutTransition {
    case immediate,animated
    func updateFrame(node:ASDisplayNode,frame:CGRect){node.frame=frame}
    func updateFrame(layer:Layer,frame:CGRect){layer.frame=frame}
}
protocol UniversalVideoContentNode:AnyObject {func updateLayout(size:CGSize,actualSize:CGSize,transition:ContainedViewLayoutTransition)}
final class Player:ASDisplayNode,UniversalVideoContentNode {
    var layouts=0
    func updateLayout(size:CGSize,actualSize:CGSize,transition:ContainedViewLayoutTransition){layouts+=1}
}
'''

DECORATION_TESTS=r'''
@main struct DecorationTests {
    static func main() {
        var checks=0
        func check(_ v:@autoclosure()->Bool,_ s:String){if !v(){FileHandle.standardError.write(Data(("Snapshot regression: "+s+"\n").utf8));exit(92)};checks+=1}
        let decoration=GalleryVideoDecoration()
        let frame=UIView()
        decoration.updateContentNodeSnapshot(frame)
        check(frame.superview===decoration.contentContainerNode.view,"snapshot attached without requiring valid layout")
        let landscape=CGSize(width:640,height:360),portrait=CGSize(width:360,height:640)
        decoration.updateLayout(size:landscape,actualSize:landscape,transition:.immediate)
        check(frame.frame==CGRect(origin:.zero,size:landscape),"snapshot follows first valid source layout")
        decoration.updateLayout(size:portrait,actualSize:portrait,transition:.animated)
        check(frame.frame==CGRect(origin:.zero,size:portrait),"snapshot follows native rotation/resize")
        decoration.updateContentNodeSnapshot(frame)
        check(decoration.contentContainerNode.view.subviews.count==1,"same snapshot does not duplicate views")
        let replacement=UIView();decoration.updateContentNodeSnapshot(replacement)
        check(frame.superview==nil && replacement.superview===decoration.contentContainerNode.view,"replacement releases previous snapshot")
        check(replacement.frame==CGRect(origin:.zero,size:portrait),"replacement uses current native bounds")
        decoration.updateContentNodeSnapshot(nil)
        check(replacement.superview==nil && decoration.contentNodeSnapshot==nil,"reacquisition releases frozen frame")
        decoration.updateContentNodeSnapshot(nil)
        check(decoration.contentContainerNode.view.subviews.isEmpty,"nil cleanup is idempotent")
        let player=Player();decoration.updateContentNode(player)
        check(player.supernode===decoration.contentContainerNode && player.layouts==1,"native decoder attachment/layout remains intact")
        decoration.updateContentNode(nil)
        check(player.supernode==nil,"native decoder detach remains intact")
        print("PiP frame snapshot checks: \(checks)")
    }
}
'''


def execute(swiftc,root,name,text,diagnostic=None):
    path=root/(name+'.swift');path.write_text(text);results=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        binary=root/(name+'-'+mode)
        run([swiftc,'-swift-version','5','-parse-as-library','-warnings-as-errors','-module-cache-path',root/'cache',*flags,path,'-o',binary])
        result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
        if diagnostic is None:assert result.returncode==0,result.stdout+result.stderr
        else:assert result.returncode in (91,92) and diagnostic in result.stderr,result.stdout+result.stderr
        results.append({'name':name,'mode':mode,'exit_code':result.returncode,'output':(result.stdout+result.stderr).strip()});binary.unlink()
    return results


def source_contract(source):
    plan=checked_plan(STAGE)
    assert set(plan['inputs'])=={U,D}
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,sha in {**plan['outputs'],**plan['guards']}.items():assert digest(source/name)==sha,name
    u=(source/U).read_text();before=(ROOT/'ios'/plan['previous'][U]).read_text()
    # The AVKit engine/delegate and all geometry/ownership commands are intact.
    assert block(u,'private final class NativePictureInPictureContentImpl:')==block(before,'private final class NativePictureInPictureContentImpl:')
    for marker in ('    override var usesNativePictureInPictureSwipe:', '    override func maybePerformActionForSwipeDismiss()', '    override func maybePerformActionForSwipeDownDismiss()'):
        assert block(u,marker)==block(before,marker),marker
    assert 'priority: .gallery, snapshotContentWhenGone: true)' in u
    node=(source/V).read_text()
    assert 'snapshotContentWhenGone: Bool = false' in node
    assert 'previous.view.snapshotView(afterScreenUpdates: false)' in node
    assert 'self.decoration.updateContentNodeSnapshot(nil)' in node
    assert 'self.snapshotContentWhenGone' in block(node,'    private func updateContentNode(')
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path,required=True);parser.add_argument('--report',type=Path)
    args=parser.parse_args();plan=source_contract(args.source);before=manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='pip-gallery-placeholder-') as temporary:
        root=Path(temporary);rejected=guard_checks(args.source,STAGE,plan,root/'guards')
        handoff,decoration=handoff_fixture(args.source),decoration_fixture(args.source)
        runs=execute(args.swiftc,root,'handoff',handoff)+execute(args.swiftc,root,'snapshot',decoration)
        variants=[
            ('technical-card',handoff.replace('self.disablePictureInPicturePlaceholder = suppressed','self.disablePictureInPicturePlaceholder = suppressed && false'),'native request suppresses technical card'),
            ('early-release',handoff.replace('guard self.videoNode?.ownsContentNode == true else { return }',''),'failed start without source cannot flash technical card'),
            ('lost-frame',decoration.replace('self.contentContainerNode.view.addSubview(snapshot)','_ = snapshot'),'snapshot attached'),
            ('stale-frame',decoration.replace('self.contentNodeSnapshot?.removeFromSuperview()',''),'replacement releases previous snapshot'),
        ]
        for name,text,diagnostic in variants:runs+=execute(args.swiftc,root,name,text,diagnostic)
        for name in plan['outputs']:run([args.swiftc,'-frontend','-parse',args.source/name])
    assert manifest(args.source)==before
    run(['python3',args.source/'build-system/Make/PostboxImportCheck.py',args.source])
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),'fail_closed':len(rejected),'executions':runs,'swift_parse':len(plan['outputs']),'source_files':len(before),'source_unchanged_by_checks':True,'native_postbox_imports':'passed','boundary':'Production PiP/delegate/swipe/placeholder bodies and snapshot attachment/layout execute in explicit AVKit/UIKit/scheduling adapters. The UIKit snapshot pixels and physical animation are not exercised.','apple_sdk':'not_run','ipa':'not_built','physical_iphone':'pending'}
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('executions','outputs')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
