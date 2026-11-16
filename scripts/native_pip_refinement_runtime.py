"""Execute actual changed handlers. UIKit/AVKit delivery and clocks are explicit IO hosts."""
from pathlib import Path
from validate_quick_format import block
from validate_pip_swipe_handoff import U, N, clean
from pip_transition_coordinator_runtime import entry_fixture

ROOT = Path(__file__).resolve().parent
GEOMETRY_IMPORTS = 'import Foundation\n#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n'


def lifecycle(source):
    text = (source / U).read_text()
    code = entry_fixture(source).split('var checks=0', 1)[0]
    code = code.replace(' func removeAnimation(forKey:String){}', '''
 func removeAnimation(forKey:String){}
 func animateAlpha(from:Double,to:Double,duration:Double,completion:@escaping(Bool)->Void){
  DispatchQueue.main.asyncAfter(deadline:clock+duration){completion(true)}
 }
''')
    code = code.replace(' var nagramiXPiPEntryGeneration=0', '''
 var nagramiXPiPHandoffStarted=false,nagramiXPiPHandoffFadeFinished=false,nagramiXPiPHandoffCompleted=false
 var detached=0
 var nagramiXPiPEntryGeneration=0''')
    code = code.replace('func completeCustomDismiss(_ pip:Bool){controller?.view.window=nil}',
                        'func completeCustomDismiss(_ pip:Bool){detached+=1;controller?.view.window=nil}')
    methods = '\n'.join(clean(block(text, m)).replace('private func', 'func') for m in [
        '    private func nagramiXBeginPiPHandoff(', '    private func nagramiXCompletePiPHandoff('])
    code = code.replace('    func nagramiXCommitPiPHandoff(', methods + '\n    func nagramiXCommitPiPHandoff(', 1)
    return code + (ROOT / 'tests/NagramiXNativePiPRefinementTests.swift').read_text()


def clipping(source):
    text = (source / U).read_text()
    return '''import Foundation
class CALayer {
 weak var superlayer:CALayer?
 var masksToBounds=false
 var mask:CALayer?
}
enum CATransaction {static func begin(){};static func commit(){};static func setDisableActions(_ value:Bool){}}
''' + clean(block(text, 'private final class NagramiXNativePiPSourceClipping')) + '''
var checks=0
func check(_ ok:@autoclosure()->Bool,_ message:String){if !ok(){FileHandle.standardError.write(Data(("PiP clip: "+message+"\\n").utf8));exit(96)};checks+=1}
@main struct Tests {static func main(){
 for rootClips in [false,true] {for parentClips in [false,true] {for masked in [false,true] {
  let root=CALayer(),parent=CALayer(),source=CALayer(),mask=CALayer(),outer=CALayer()
  root.superlayer=outer;parent.superlayer=root;source.superlayer=parent
  root.masksToBounds=rootClips;parent.masksToBounds=parentClips
  if masked{root.mask=mask;parent.mask=mask}
  source.masksToBounds=true;source.mask=mask
  var lease=NagramiXNativePiPSourceClipping(source:source,root:root)
  check(lease != nil,"owned chain admitted")
  check(!root.masksToBounds && root.mask==nil && !parent.masksToBounds && parent.mask==nil,"root and inner upper/lower edges use the same unclipped path")
  check(source.masksToBounds && source.mask===mask,"AVKit source mask is never modified")
  root.superlayer=nil
  lease?.restore();lease?.restore();lease=nil
  check(root.masksToBounds==rootClips && root.mask===(masked ? mask:nil),"root restored even after gallery reparenting")
  check(parent.masksToBounds==parentClips && parent.mask===(masked ? mask:nil),"inner mask restored exactly")
 }}}
 do {
  let root=CALayer(),parent=CALayer(),source=CALayer(),other=CALayer(),newMask=CALayer()
  parent.superlayer=root;source.superlayer=parent;parent.masksToBounds=true;root.masksToBounds=true
  let lease=NagramiXNativePiPSourceClipping(source:source,root:root)!
  parent.superlayer=other;root.mask=newMask
  lease.restore()
  check(!parent.masksToBounds,"recycled inner ancestor is not overwritten")
  check(root.mask===newMask,"newly installed root mask is not overwritten")
 }
 let source=CALayer(),root=CALayer()
 check(NagramiXNativePiPSourceClipping(source:source,root:root)==nil,"foreign chain refused without mutation")
 print("\\(checks) actual clipping checks passed")
}}
'''


def gesture(source):
    text = (source / U).read_text()
    node = (source / N).read_text()
    recognizer = clean(block(text, 'private final class NagramiXUpwardPiPGestureRecognizer:'))
    handler = clean(block(text, '    @objc private func nagramiXUpwardPiPSwipe(')).replace('private func', 'func')
    return GEOMETRY_IMPORTS + '''typealias Selector=String
protocol UIGestureRecognizerDelegate:AnyObject {}
class UIView {weak var superview:UIView?}
class UIControl:UIView {}
class UITouch {let view:UIView?;init(_ view:UIView?){self.view=view}}
class UIGestureRecognizer {
 enum State {case possible,began,changed,ended,cancelled,failed}
 var state=State.possible
 weak var view:UIView?
 weak var delegate:(any UIGestureRecognizerDelegate)?
 init(target:Any?,action:Selector?){}
}
class UIPanGestureRecognizer:UIGestureRecognizer {
 var maximumNumberOfTouches=2,cancelsTouchesInView=true,delaysTouchesBegan=true,delaysTouchesEnded=true
 var movement=CGPoint.zero,speed=CGPoint.zero
 func translation(in view:UIView?)->CGPoint{movement}
 func velocity(in view:UIView?)->CGPoint{speed}
}
class UIScrollView:UIView {
 var zoomScale:CGFloat=1,minimumZoomScale:CGFloat=1
 lazy var panGestureRecognizer:UIPanGestureRecognizer={let g=UIPanGestureRecognizer(target:nil,action:nil);g.view=self;return g}()
}
''' + recognizer + '\n' + clean(block(node, 'func nagramiXShouldBeginFastPictureInPictureSwipe(')) + '''
final class Scroll {let view=UIScrollView()}
final class Host {
 let scrollNode=Scroll()
 var usesNativePictureInPictureSwipe=true,preparations=0,requests=0
 func prepareForNativePictureInPictureSwipe(){preparations+=1}
 func nagramiXRequestPictureInPicture()->Bool{requests+=1;return true}
''' + handler + '''
}
var checks=0
func check(_ ok:@autoclosure()->Bool,_ message:String){if !ok(){FileHandle.standardError.write(Data(("PiP gesture: "+message+"\\n").utf8));exit(96)};checks+=1}
@main struct Tests {static func main(){
 let g=NagramiXUpwardPiPGestureRecognizer(target:nil,action:nil),surface=UIView()
 g.view=surface;g.canBegin={true}
 check(g.maximumNumberOfTouches==1 && !g.cancelsTouchesInView && !g.delaysTouchesBegan && !g.delaysTouchesEnded,"one-finger observer does not cancel native touches")
 for v in [CGPoint(x:0,y:-400),CGPoint(x:100,y:-400)] {g.speed=v;check(g.gestureRecognizerShouldBegin(g),"upward vertical pan admitted")}
 for v in [CGPoint.zero,CGPoint(x:0,y:400),CGPoint(x:400,y:-100),CGPoint(x:CGFloat.nan,y:-400),CGPoint(x:0,y:-CGFloat.infinity)] {g.speed=v;check(!g.gestureRecognizerShouldBegin(g),"down/horizontal/nonfinite pan refused")}
 g.speed=CGPoint(x:0,y:-400);g.canBegin={false};check(!g.gestureRecognizerShouldBegin(g),"owner/zoom/setting admission respected")
 let button=UIControl(),label=UIView();button.superview=surface;label.superview=button
 check(!g.gestureRecognizer(g,shouldReceive:UITouch(label)),"native button descendants excluded")
 check(g.gestureRecognizer(g,shouldReceive:UITouch(surface)),"video surface admitted")
 let scroll=UIScrollView(),other=UIPanGestureRecognizer(target:nil,action:nil);other.view=scroll
 check(g.gestureRecognizer(g,shouldRecognizeSimultaneouslyWith:scroll.panGestureRecognizer),"inner and outer scroll pans can coexist")
 check(!g.gestureRecognizer(g,shouldRecognizeSimultaneouslyWith:other),"unrelated recognizers not admitted")
 for state in [UIGestureRecognizer.State.changed,.ended] {
  let h=Host();g.requested=false;g.state=state;g.movement=CGPoint(x:1,y:-36);g.speed=CGPoint(x:0,y:-400)
  h.nagramiXUpwardPiPSwipe(g);check(h.requests==1,"surface swipe invokes shared request even when outer offset did not move")
  h.nagramiXUpwardPiPSwipe(g);check(h.requests==1,"one pan submits at most one request even after failed start")
  h.scrollNode.view.zoomScale=2;h.nagramiXUpwardPiPSwipe(g);check(h.requests==1,"zoomed media remains native")
 }
 for state in [UIGestureRecognizer.State.cancelled,.failed,.possible] {let h=Host();g.state=state;h.nagramiXUpwardPiPSwipe(g);check(h.requests==0,"cancelled gesture cannot start")}
 for v in [CGPoint(x:0,y:36),CGPoint(x:100,y:-36),CGPoint(x:0,y:-3)] {let h=Host();g.requested=false;g.state = .changed;g.movement=v;g.speed=CGPoint(x:0,y:-20);h.nagramiXUpwardPiPSwipe(g);check(h.requests==0,"down/horizontal/jitter stays native")}
 let h=Host();g.state = .began;h.nagramiXUpwardPiPSwipe(g);check(h.preparations==1 && h.requests==0,"began prepares without starting")
 h.usesNativePictureInPictureSwipe=false;g.state = .changed;g.movement=CGPoint(x:0,y:-36);h.nagramiXUpwardPiPSwipe(g);check(h.requests==0,"swipe OFF affects only shortcut")
 print("\\(checks) actual gesture checks passed")
}}
'''


def youtube(source):
    from youtube_background_continuity_runtime import fixture
    from system_web_picture_in_picture_runtime import WEB
    text = (source / WEB).read_text()
    code = fixture(source)
    code = code.replace('enum NagramiXTabSettings {static var backgroundVideoPlaybackEnabled=true}', '''
enum NagramiXTabSettings {
 static var backgroundVideoPlaybackEnabled=true,videoPiPSwipeEnabled=true
 static let changedNotification=Notification.Name("fixture-youtube-policy")
}''')
    assignment = next(l.strip() for l in text.splitlines() if 'self.nagramiXSystemPiP = NagramiXWebSystemPictureInPicture(' in l)
    call = next(l.strip() for l in text.splitlines() if 'self.nagramiXSystemPiP.setYouTubePolicy(self.impl' in l)
    observer = block(text, '        self.nagramiXPolicyObserver = NotificationCenter.default.addObserver(')
    host = '''
final class CapabilityHost {
 let impl:EmbedImplementation
 let nagramiXSystemPiP:NagramiXWebSystemPictureInPicture
 let webView=WKWebView()
 var nagramiXPolicyObserver:NSObjectProtocol?
 init(youtube:Bool){
  impl=youtube ? YoutubeEmbedImplementation():EmbedImplementation()
  let userContentController=WKUserContentController()
''' + assignment + '\nself.nagramiXSystemPiP.webView=self.webView\n' + call + '\n' + observer + '''
 }
 deinit{if let observer=nagramiXPolicyObserver{NotificationCenter.default.removeObserver(observer)}}
}
'''
    code = code.replace('@main struct Tests {', host + '\n@main struct Tests {', 1)
    scenarios = '''
  for swipe in [false,true] {for isYouTube in [false,true] {
   NagramiXTabSettings.videoPiPSwipeEnabled=swipe
   let h=CapabilityHost(youtube:isYouTube)
   check(h.nagramiXSystemPiP.begin(),"button starts a request regardless of swipe setting")
   func lastPolicy()->[String:Any]?{h.webView.calls.last(where:{$0.0["command"] as? String == "policy"})?.0}
   check(lastPolicy()?["enabled"] as? Bool == isYouTube,"only YouTube receives client PiP override and swipe OFF cannot revoke button")
   NagramiXTabSettings.videoPiPSwipeEnabled = !swipe
   NotificationCenter.default.post(name:NagramiXTabSettings.changedNotification,object:nil)
   check(lastPolicy()?["enabled"] as? Bool == isYouTube,"live swipe toggle leaves active button capability intact")
   h.nagramiXSystemPiP.stop()
  }}
'''
    return code.replace('  for pip in [false,true]', scenarios + '\n  for pip in [false,true]', 1)


def eligibility(source):
    text = (source / U).read_text()
    return '''import Foundation
class WebEmbedVideoContent {}
class SystemVideoContent {}
class PlatformVideoContent {}
struct MessageId {let namespace:Int32}
struct Message {var paidContent:Int?,adAttribute:Int?;let id:MessageId}
enum Namespaces {enum Message {static let allNonRegular:[Int32]=[7,8];static let Local:Int32=9}}
enum Info {case message(Message,Int?);case webPage(Int,Int,Int?)}
class UniversalVideoGalleryItem {let content:AnyObject;var isSecret=false;var contentInfo:Info?
 init(_ content:AnyObject){self.content=content}}
''' + clean(block(text, 'private func nagramiXUsesEmbeddedPictureInPicture(')) + '\n' + clean(block(text, 'private func nagramiXCanOfferWebPictureInPicture(')) + '''
var checks=0
func check(_ ok:@autoclosure()->Bool,_ message:String){if !ok(){FileHandle.standardError.write(Data(("PiP eligibility: "+message+"\\n").utf8));exit(96)};checks+=1}
@main struct Tests {static func main(){
 for content in [WebEmbedVideoContent() as AnyObject,SystemVideoContent(),PlatformVideoContent()] {
  let item=UniversalVideoGalleryItem(content)
  item.contentInfo = .message(Message(paidContent:nil,adAttribute:nil,id:MessageId(namespace:0)),nil)
  check(nagramiXCanOfferWebPictureInPicture(item),"regular video button independent of swipe and remote YouTube flag")
  item.isSecret=true;check(!nagramiXCanOfferWebPictureInPicture(item),"secret restriction retained");item.isSecret=false
  for ns:Int32 in [7,8,9] {item.contentInfo = .message(Message(paidContent:nil,adAttribute:nil,id:MessageId(namespace:ns)),nil);check(!nagramiXCanOfferWebPictureInPicture(item),"nonregular/local restriction retained")}
  for paid in [false,true] {item.contentInfo = .message(Message(paidContent:paid ? 1:nil,adAttribute:paid ? nil:1,id:MessageId(namespace:0)),nil);check(!nagramiXCanOfferWebPictureInPicture(item),"paid/ad restriction retained")}
  item.contentInfo = .webPage(0,0,1);check(nagramiXCanOfferWebPictureInPicture(item),"restorable web page admitted")
  item.contentInfo = .webPage(0,0,nil);check(!nagramiXCanOfferWebPictureInPicture(item),"unrestorable page refused")
  item.contentInfo=nil;check(!nagramiXCanOfferWebPictureInPicture(item),"unknown owner refused")
 }
 let native=UniversalVideoGalleryItem(NSObject());native.contentInfo = .webPage(0,0,1)
 check(!nagramiXCanOfferWebPictureInPicture(native),"native videos keep their own AVKit route")
 print("\\(checks) actual embedded eligibility checks passed")
}}
'''
