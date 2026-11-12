"""Actual Snow settings/view/conditional rows with explicit UIKit/CA adapters."""
from validate_quick_format import block
SETTINGS='submodules/NagramiXCore/Sources/NagramiXSnowSettings.swift'
VIEW='submodules/NagramiXCore/Sources/NagramiXSnowView.swift'
UI='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'
DENSITY='submodules/SettingsUI/Sources/NagramiXSnowDensityItem.swift'
LIST='submodules/ChatListUI/Sources/ChatListControllerNode.swift'
CONTROLLER='submodules/ChatListUI/Sources/ChatListController.swift'
CHAT='submodules/TelegramUI/Sources/ChatControllerNode.swift'


def fixture(source):
    return (source/SETTINGS).read_text()+'\n'+BOUNDARY+'\n'+(source/VIEW).read_text().replace('import UIKit\n','')+'\n'+ENTRY+'\n'+block((source/UI).read_text(),'private enum NagramiXSettingsSection:')+'\n'+block((source/UI).read_text(),'private func nagramiXSnowEntries(')+'\n'+TESTS


def negatives(code):
    for name,old,new,label in [
        ('master-ignored','let allowed = config.enabled &&','let allowed = true &&','master OFF has no particles'),
        ('chat-gate-ignored','(self.scope == .header || config.inChats)','true','chat toggle leaves header running and hides messages'),
        ('power-ignored','!ProcessInfo.processInfo.isLowPowerModeEnabled','true','power stops both emitters'),
        ('motion-ignored','!UIAccessibility.isReduceMotionEnabled','true','motion stops both emitters'),
        ('offscreen-ignored','self.window != nil','true','offscreen stops emitter'),
        ('children-visible','if value.enabled {','if true {','OFF exposes only header and master'),
        ('wrong-restart-clock','self.layer.convertTime(CACurrentMediaTime(), from: nil)','self.particles.convertTime(CACurrentMediaTime(), from: nil)','resume uses parent clock without catch-up'),
    ]:
        assert code.count(old)==1,(name,code.count(old));yield name,code.replace(old,new,1),label

BOUNDARY=r'''
var deviceLowPower=false
var now:Double=100
extension ProcessInfo {var isLowPowerModeEnabled:Bool {deviceLowPower}}
extension Notification.Name {static let NSProcessInfoPowerStateDidChange=Notification.Name("power")}
enum UIAccessibility {static var isReduceMotionEnabled=false;static let reduceMotionStatusDidChangeNotification=Notification.Name("motion")}
enum UIApplication {static let willResignActiveNotification=Notification.Name("resign");static let didBecomeActiveNotification=Notification.Name("active")}
func CACurrentMediaTime()->Double {now}
class CALayer {
 var frame:CGRect = .zero;var speed:Float=1;var timeOffset:Double=0;var beginTime:Double=0
 var children:[CALayer]=[]
 func addSublayer(_ value:CALayer){children.append(value)}
 func convertTime(_ value:Double,from:CALayer?)->Double {(value-self.beginTime)*Double(self.speed)+self.timeOffset}
}
final class CAEmitterLayer:CALayer {
 enum Shape {case rectangle};enum Mode {case volume};enum Render {case unordered}
 var emitterShape:Shape = .rectangle;var emitterMode:Mode = .volume;var renderMode:Render = .unordered
 var birthRate:Float=1;var seed:UInt32=0;var emitterPosition:CGPoint = .zero;var emitterSize:CGSize = .zero
 var cellUpdates=0;var emitterCells:[CAEmitterCell]? {didSet {cellUpdates+=1}}
}
final class CAEmitterCell {
 var contents:Any?;var contentsScale:CGFloat=1;var color:Int=0;var birthRate:Float=0;var lifetime:Float=0;var lifetimeRange:Float=0
 var velocity:CGFloat=0;var velocityRange:CGFloat=0;var emissionLongitude:CGFloat=0;var emissionRange:CGFloat=0;var alphaSpeed:Float=0
}
enum CATransaction {static var balance=0;static func begin(){balance+=1};static func commit(){balance-=1};static func setDisableActions(_ value:Bool){}}
struct UIViewAutoresizing:OptionSet {let rawValue:Int;static let flexibleWidth=Self(rawValue:1);static let flexibleHeight=Self(rawValue:2)}
final class Traits {var displayScale:CGFloat=2}
final class UIWindow {var bounds=CGRect(x:0,y:0,width:390,height:844)}
public class UIView:NSObject {
 var frame:CGRect {didSet {bounds=CGRect(origin:.zero,size:frame.size)}};var bounds:CGRect;let layer=CALayer();var window:UIWindow?;weak var superview:UIView?
 var children:[UIView]=[];var isHidden=false;var isUserInteractionEnabled=true;var isAccessibilityElement=true;var accessibilityElementsHidden=false;var clipsToBounds=false
 var autoresizingMask:UIViewAutoresizing=[];var traitCollection=Traits()
 public init(frame:CGRect){self.frame=frame;self.bounds=CGRect(origin:.zero,size:frame.size);super.init()}
 public required init?(coder:NSCoder){self.frame = .zero;self.bounds = .zero;super.init()}
 public func didMoveToWindow(){}
 public func layoutSubviews(){}
 func removeFromSuperview(){superview?.children.removeAll {$0 === self};superview=nil;window=nil;didMoveToWindow()}
 func addSubview(_ view:UIView){view.removeFromSuperview();children.append(view);view.superview=self;view.window=window;view.didMoveToWindow()}
 func insertSubview(_ view:UIView,aboveSubview background:UIView){addSubview(view);children.removeAll {$0 === view};let i=children.firstIndex {$0 === background}!;children.insert(view,at:i+1)}
 func insertSubview(_ view:UIView,at index:Int){addSubview(view);children.removeAll {$0 === view};children.insert(view,at:index)}
 func bringSubviewToFront(_ view:UIView){children.removeAll {$0 === view};children.append(view)}
}
final class UIColor {static let white=UIColor();init(){};init(white:CGFloat,alpha:CGFloat){};var cgColor:Int {1}}
final class UIImage {var cgImage:Int {1}}
final class GraphicsContext {func setFillColor(_ color:Int){};func fillEllipse(in rect:CGRect){}}
final class RendererContext {var cgContext=GraphicsContext()}
final class UIGraphicsImageRendererFormat {var opaque=true;var scale:CGFloat=1}
var rasterized=0
final class UIGraphicsImageRenderer {init(size:CGSize,format:UIGraphicsImageRendererFormat){};func image(_ draw:(RendererContext)->Void)->UIImage {rasterized+=1;draw(RendererContext());return UIImage()}}
'''
ENTRY='''private enum NagramiXSettingsEntry:Equatable {case snowHeader,snowEnabled(Bool),snowInChats(Bool),snowDensity(Int)}'''
TESTS=r'''
@main struct SnowTests {
 static func main(){
  let key="nagramix.atmosphere.snowfall",defaults=UserDefaults.standard,old=UserDefaults.standard.object(forKey:"nagramix.atmosphere.snowfall")
  defaults.removeObject(forKey:key);defer {defaults.set(old,forKey:key)}
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data(("Snowfall regression: "+why+"\n").utf8));exit(96)};checks+=1}
  check(NagramiXSettingsSection.atmosphere.rawValue > NagramiXSettingsSection.inputEffects.rawValue+5,"sections do not merge")
  check(!NagramiXSnowSettings.current.enabled && NagramiXSnowSettings.current.inChats && NagramiXSnowSettings.current.density==100,"fresh values")
  check(nagramiXSnowEntries(NagramiXSnowSettings.current).count==2,"OFF exposes only header and master")
  for input in [Int.min] + Array(-10...120) + [Int.max] {
   NagramiXSnowSettings.update {$0.density=input}
   let value=NagramiXSnowSettings.current
   check((10...100).contains(value.density) && value.density%5==0,"bounded stepped density")
   check(NagramiXSnowSettings.read(in:defaults)==value,"cold read preserves values")
  }
  let parent=UIView(frame:CGRect(x:0,y:0,width:390,height:120));parent.window=UIWindow()
  let background=UIView(frame:parent.bounds),content=UIView(frame:parent.bounds);parent.addSubview(background);parent.addSubview(content)
  let wall=UIView(frame:CGRect(x:0,y:0,width:390,height:844));wall.window=parent.window
  var header:NagramiXSnowView?=NagramiXSnowView(scope:.header)
  let chat=NagramiXSnowView(scope:.messages)
  header!.setVisible(true);chat.setVisible(true);header!.bind(to:parent,above:background);chat.bind(to:wall)
  let he=header!.layer.children.first as! CAEmitterLayer,ce=chat.layer.children.first as! CAEmitterLayer
  check(he.birthRate==0 && he.speed==0 && he.emitterCells==nil && ce.birthRate==0,"master OFF has no particles")
  check(parent.children[1] === header && parent.children[2] === content,"header is above background below controls")
  check(!header!.isUserInteractionEnabled && !header!.isAccessibilityElement && header!.accessibilityElementsHidden,"snow is decorative and touch transparent")
  for density in stride(from:10,through:100,by:5) {
   NagramiXSnowSettings.update {$0.enabled=true;$0.inChats=true;$0.density=density}
   check(nagramiXSnowEntries(NagramiXSnowSettings.current).count==4,"ON shows exactly two children")
   check(he.birthRate==1 && ce.birthRate==1 && he.speed==1,"both scopes enabled")
   check(he.emitterCells?.count==2 && ce.emitterCells?.count==2,"only two white flake sizes")
   let headerRate=he.emitterCells!.reduce(Float(0)) {$0+$1.birthRate};let chatRate=ce.emitterCells!.reduce(Float(0)) {$0+$1.birthRate}
   check(abs(headerRate-18*Float(density)/100)<0.001 && abs(chatRate-75*Float(density)/100)<0.001,"density changes rate in each scope")
   check(ce.emitterCells!.allSatisfy {$0.contentsScale==2 && $0.velocity==44 && $0.alphaSpeed<0 && $0.lifetime==4},"flakes drift down and fade with correct raster scale")
   let old=he.cellUpdates,renders=rasterized
   header!.layoutSubviews();header!.bind(to:parent,above:background)
   check(he.cellUpdates==old && renders==rasterized,"unchanged layout does not rebuild emitter or images")
  }
  NagramiXSnowSettings.update {$0.inChats=false}
  check(he.birthRate==1 && !header!.isHidden && ce.birthRate==0 && chat.isHidden,"chat toggle leaves header running and hides messages")
  NagramiXSnowSettings.update {$0.inChats=true}
  deviceLowPower=true;NotificationCenter.default.post(name:.NSProcessInfoPowerStateDidChange,object:nil)
  check(he.birthRate==0 && ce.birthRate==0 && he.speed==0 && ce.speed==0,"power stops both emitters")
  now=200;deviceLowPower=false;NotificationCenter.default.post(name:.NSProcessInfoPowerStateDidChange,object:nil)
  check(he.birthRate==1 && ce.birthRate==1 && he.beginTime==200,"resume uses parent clock without catch-up")
  UIAccessibility.isReduceMotionEnabled=true;NotificationCenter.default.post(name:UIAccessibility.reduceMotionStatusDidChangeNotification,object:nil)
  check(he.birthRate==0 && ce.birthRate==0,"motion stops both emitters")
  UIAccessibility.isReduceMotionEnabled=false;NotificationCenter.default.post(name:UIAccessibility.reduceMotionStatusDidChangeNotification,object:nil)
  NotificationCenter.default.post(name:UIApplication.willResignActiveNotification,object:nil)
  check(he.birthRate==0 && ce.birthRate==0,"inactive app pauses")
  NotificationCenter.default.post(name:UIApplication.didBecomeActiveNotification,object:nil)
  check(he.birthRate==1 && ce.birthRate==1,"active app restores allowed state")
  header!.window=nil;header!.didMoveToWindow();check(he.birthRate==0,"offscreen stops emitter")
  header!.window=parent.window;header!.didMoveToWindow()
  header!.setVisible(false);check(he.birthRate==0,"covered controller stops emitter")
  header!.setVisible(true);check(he.birthRate==1,"visible controller restores emitter")
  let before=rasterized;header!.traitCollection.displayScale=3;header!.layoutSubviews();check(rasterized==before+2,"raster scale gets matching cached flakes")
  check(CATransaction.balance==0,"every disabled-actions transaction is balanced")
  NagramiXSnowSettings.update {$0.enabled=false}
  check(he.birthRate==0 && ce.birthRate==0 && he.emitterCells==nil,"OFF clears particles immediately")
  check(NagramiXSnowSettings.current.inChats && NagramiXSnowSettings.current.density==100,"OFF retains child values")
  header!.removeFromSuperview();weak var released=header;header=nil
  check(released==nil,"observers do not retain view")
  print("Snowfall production checks: \(checks)")
 }
}
'''
