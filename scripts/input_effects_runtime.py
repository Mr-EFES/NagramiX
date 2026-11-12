"""Действующие настройки, CA-аниматор и список строк с явной UIKit-границей."""
from validate_quick_format import block
SETTINGS='submodules/NagramiXCore/Sources/NagramiXTypingSettings.swift'
ANIMATION='submodules/NagramiXCore/Sources/NagramiXTypingAnimation.swift'
UI='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'
CHAT='submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/ChatTextInputPanelNode.swift'
ATTACHMENT='submodules/AttachmentTextInputPanelNode/Sources/AttachmentTextInputPanelNode.swift'


def fixture(source):
    settings=(source/SETTINGS).read_text()
    animation=(source/ANIMATION).read_text().replace('import UIKit\n','')
    entries=block((source/UI).read_text(),'private func nagramiXInputEffectEntries(')
    return settings+'\n'+BOUNDARY+'\n'+animation+'\n'+ENTRY_BOUNDARY+'\n'+entries+'\n'+TESTS


def negatives(code):
    for name,old,new,label in [
        ('default-on','value.enabled = stored["enabled"] as? Bool ?? false','value.enabled = stored["enabled"] as? Bool ?? true','fresh setting is OFF'),
        ('no-power-gate','!ProcessInfo.processInfo.isLowPowerModeEnabled','true','low power stops animation'),
        ('no-reduce-motion','!UIAccessibility.isReduceMotionEnabled','true','reduce motion stops animation'),
        ('no-throttle','guard timestamp - self.lastTimestamp >= value.minimumInterval else { return }','guard timestamp >= 0 else { return }','rapid typing does not stack animations'),
        ('model-transform','animation.isAdditive = true','animation.isAdditive = false','decorative transforms are additive'),
        ('missing-parameters','if value.preset == .custom {','if value.preset == .pulse {','custom has five named parameter sliders'),
    ]:
        assert code.count(old)==1,(name,code.count(old))
        yield name,code.replace(old,new,1),label

BOUNDARY=r'''
#if canImport(CoreGraphics)
import CoreGraphics
#endif
final class NagramiXFixtureWeakProbe<T:AnyObject> {weak var value:T?;init(_ value:T?){self.value=value}}
var clockTime:Double=1
var deviceLowPower=false
extension ProcessInfo {var isLowPowerModeEnabled:Bool {deviceLowPower}}
extension Notification.Name {static let NSProcessInfoPowerStateDidChange=Notification.Name("power")}
enum UIAccessibility {static var isReduceMotionEnabled=false;static let reduceMotionStatusDidChangeNotification=Notification.Name("motion")}
enum UIApplication {static let didEnterBackgroundNotification=Notification.Name("background")}
func CACurrentMediaTime()->Double {clockTime}
final class CGColor {}
final class CGPath {}
final class CGContext {func setShadow(offset:CGSize,blur:CGFloat,color:CGColor){};func setFillColor(_ color:CGColor){};func addPath(_ path:CGPath){};func fillPath(){}}
public final class UIColor:NSObject {
 let value:Int;init(_ value:Int){self.value=value};var cgColor:CGColor {CGColor()}
 func withAlphaComponent(_ value:CGFloat)->UIColor {self}
 public override func isEqual(_ object:Any?)->Bool {(object as? UIColor)?.value==self.value}
}
final class CAKeyframeAnimation {
 let keyPath:String;var values:[Any]?;var duration:Double=0;var isAdditive=false;var timingFunction:CAMediaTimingFunction?
 init(keyPath:String){self.keyPath=keyPath}
}
struct CAMediaTimingFunctionName {static let easeInEaseOut=CAMediaTimingFunctionName()}
final class CAMediaTimingFunction {init(name:CAMediaTimingFunctionName){}}
final class CALayer {
 weak var superlayer:CALayer?;var children:[CALayer]=[];var opacity:Float=1;var contents:Any?;var contentsScale:CGFloat=1;var frame:CGRect = .zero
 var animations:[String:CAKeyframeAnimation]=[:];var adds=0
 func add(_ value:CAKeyframeAnimation,forKey key:String){animations[key]=value;adds+=1}
 func removeAnimation(forKey key:String){animations.removeValue(forKey:key)}
 func removeFromSuperlayer(){superlayer?.children.removeAll {$0 === self};superlayer=nil}
 func insertSublayer(_ layer:CALayer,below:CALayer){layer.superlayer=self;children.append(layer)}
}
final class TraitCollection {var displayScale:CGFloat=2}
public final class UIView {
 let layer=CALayer();var window:Int?=1;var bounds=CGRect(x:0,y:0,width:320,height:44);var frame=CGRect(x:20,y:15,width:320,height:44)
 let traitCollection=TraitCollection();weak var superview:UIView?
}
final class UIBezierPath {init(roundedRect:CGRect,cornerRadius:CGFloat){};var cgPath:CGPath {CGPath()}}
final class UIGraphicsImageRendererFormat {var scale:CGFloat=1;var opaque=true}
final class Image {var cgImage:Int {1}}
final class RenderContext {var cgContext:CGContext {CGContext()}}
var renderedImages=0
final class UIGraphicsImageRenderer {
 init(size:CGSize,format:UIGraphicsImageRendererFormat){}
 func image(_ draw:(RenderContext)->Void)->Image {renderedImages+=1;draw(RenderContext());return Image()}
}
'''
ENTRY_BOUNDARY=r'''
private enum NagramiXSettingsEntry:Equatable {
 case inputEffectsHeader,inputEffectsEnabled(Bool),inputEffectsPreset(NagramiXTypingPreset),inputEffectsParameterHeader(NagramiXTypingParameter),inputEffectsParameter(NagramiXTypingParameter,Int)
}
'''
TESTS=r'''
@main struct InputEffectsTests {
 static func main(){
  let storageKey="nagramix.input.typingEffects",defaults=UserDefaults.standard,old=UserDefaults.standard.object(forKey:"nagramix.input.typingEffects")
  defaults.removeObject(forKey:storageKey)
  defer {defaults.set(old,forKey:storageKey)}
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data(("Input effects regression: "+why+"\n").utf8));exit(96)};checks+=1}
  check(!NagramiXTypingSettings.current.enabled,"fresh setting is OFF")
  check(NagramiXTypingSettings.current.preset == .wave,"default wave")
  let isolated=UserDefaults(suiteName:"input-effects-fixture")!;isolated.removePersistentDomain(forName:"input-effects-fixture")
  defer {isolated.removePersistentDomain(forName:"input-effects-fixture")}
  isolated.set(["enabled":false,"preset":100,"0":-50.0,"1":200.0,"2":Double.nan],forKey:storageKey)
  let invalid=NagramiXTypingSettings.read(in:isolated)
  check(!invalid.enabled && invalid.preset == .wave && invalid.intensity==0 && invalid.speed==100 && invalid.scale==45,"stored malformed values normalized")
  for parameter in NagramiXTypingParameter.allCases {for input in [-200.0,0,45,100,200,Double.nan,Double.infinity] {
   NagramiXTypingSettings.update {$0[parameter]=input}
   let current=NagramiXTypingSettings.current
   check(current[parameter].isFinite && (0...100).contains(current[parameter]),"each parameter bounded")
   check(NagramiXTypingSettings.read(in:defaults)==current,"each setting persists across cold read")
  }}
  check(nagramiXInputEffectEntries(NagramiXTypingConfiguration()).count==2,"OFF hides effect controls")
  for preset in NagramiXTypingPreset.allCases {
   var v=NagramiXTypingConfiguration();v.enabled=true;v.preset=preset
   let entries=nagramiXInputEffectEntries(v)
   check(entries.count == (preset == .custom ? 13:3),"custom has five named parameter sliders")
   if preset == .custom {for parameter in NagramiXTypingParameter.allCases {
    check(entries.contains(.inputEffectsParameterHeader(parameter)) && entries.contains(.inputEffectsParameter(parameter,Int(v[parameter]))),"parameters have distinct labels")
   }}
  }
  let target=UIView(),companion=UIView(),parent=UIView();target.superview=parent;companion.superview=parent
  let frame=target.frame,bounds=target.bounds
  target.layer.animations["native.selection"]=CAKeyframeAnimation(keyPath:"native")
  var animator:NagramiXTypingAnimation?=NagramiXTypingAnimation()
  for preset in NagramiXTypingPreset.allCases {for level in [0.0,25,55,100] {
   NagramiXTypingSettings.update {$0=NagramiXTypingConfiguration();$0.enabled=true;$0.preset=preset;for p in NagramiXTypingParameter.allCases {$0[p]=level}}
   clockTime+=1;animator!.play(target:target,companions:[companion],color:UIColor(1))
   let ours=(Array(target.layer.animations.values) + parent.layer.children.flatMap {Array($0.animations.values)}).filter {$0.keyPath != "native"}
   check(!ours.isEmpty,"all presets animate original field")
   for animation in ours {
    check(animation.duration >= 0.15-0.0001 && animation.duration <= 0.64,"bounded duration")
    check(animation.keyPath == "opacity" || animation.isAdditive,"decorative transforms are additive")
    check((animation.values as? [Double])?.allSatisfy {$0.isFinite} == true,"finite keyframes")
   }
   check(target.frame==frame && target.bounds==bounds,"animation leaves layout intact")
   check((companion.layer.animations.isEmpty) == (preset != .panelWave),"only panel wave touches companion")
   let adds=target.layer.adds;animator!.play(target:target,companions:[companion],color:UIColor(1))
   check(target.layer.adds==adds,"rapid typing does not stack animations")
   animator!.stop()
   check(target.layer.animations.count==1 && target.layer.animations["native.selection"] != nil && companion.layer.animations.isEmpty,"stop removes only owned animations")
  }}
  NagramiXTypingSettings.update {$0.enabled=true;$0.preset = .pulse}
  deviceLowPower=true;clockTime+=1;animator!.play(target:target,color:UIColor(1));check(target.layer.animations.count==1,"low power stops animation");deviceLowPower=false
  UIAccessibility.isReduceMotionEnabled=true;clockTime+=1;animator!.play(target:target,color:UIColor(1));check(target.layer.animations.count==1,"reduce motion stops animation");UIAccessibility.isReduceMotionEnabled=false
  target.window=nil;clockTime+=1;animator!.play(target:target,color:UIColor(1));check(target.layer.animations.count==1,"offscreen does not animate");target.window=1
  for name in [NagramiXTypingSettings.changedNotification,.NSProcessInfoPowerStateDidChange,UIAccessibility.reduceMotionStatusDidChangeNotification,UIApplication.didEnterBackgroundNotification] {
   clockTime+=1;animator!.play(target:target,color:UIColor(1));NotificationCenter.default.post(name:name,object:nil)
   check(target.layer.animations.count==1,"live policy changes clear effect")
  }
  NagramiXTypingSettings.update {$0.preset = .neon}
  target.bounds.size.width += 1
  let count=renderedImages
  clockTime+=1;animator!.play(target:target,color:UIColor(1));let first=renderedImages
  clockTime+=1;animator!.play(target:target,color:UIColor(1));check(first==count+1 && renderedImages==first,"glow bitmap cached at same size color and scale")
  clockTime+=1;animator!.play(target:target,color:UIColor(2));check(renderedImages==first+1,"theme change refreshes glow")
  target.traitCollection.displayScale=3;clockTime+=1;animator!.play(target:target,color:UIColor(2));check(renderedImages==first+2,"display scale refreshes glow")
  let released=NagramiXFixtureWeakProbe(animator);animator=nil;check(released.value==nil,"notification observers do not retain animator")
  check(target.layer.animations.count==1,"deinit clears only owned animations")
  NagramiXTypingSettings.update {$0.enabled=false}
  check(!NagramiXTypingSettings.read(in:defaults).enabled,"saved OFF survives cold read")
  print("Input effects production checks: \(checks)")
 }
}
'''
