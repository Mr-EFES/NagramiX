// UIKit, text measurement, ListView and theme boundaries. The complete actual
// density node, geometry, glass/control classes and normalizer execute unchanged.
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

#if !canImport(UIKit)
var fixtureGlassAvailable = true
struct UIEdgeInsets {var top:CGFloat=0,left:CGFloat=0,bottom:CGFloat=0,right:CGFloat=0}
enum NSTextAlignment {case left,right,center}
enum UIUserInterfaceStyle {case unspecified,light,dark}
struct UIAccessibilityTraits:OptionSet {let rawValue:Int;static let adjustable=Self(rawValue:1)}
class UIEvent {}
class UIColor {
 let alpha:CGFloat
 init(white:CGFloat,alpha:CGFloat){self.alpha=alpha}
 static let clear=UIColor(white:0,alpha:0),black=UIColor(white:0,alpha:1)
 var cgColor:UIColor{self}
}
class CALayer {
 var frame:CGRect = .zero;var cornerRadius:CGFloat=0;var masksToBounds=false
 var shadowColor:UIColor?;var shadowOffset:CGSize = .zero;var shadowRadius:CGFloat=0;var shadowOpacity:Float=0;var shadowPath:CGRect?
 var sublayers:[CALayer]=[]
 func addSublayer(_ l:CALayer){sublayers.append(l)}
}
class CAGradientLayer:CALayer {var colors:[Any]?;var locations:[NSNumber]?;var startPoint:CGPoint = .zero;var endPoint:CGPoint = .zero}
class CAShapeLayer:CALayer {var fillColor:UIColor?;var strokeColor:UIColor?;var lineWidth:CGFloat=0;var path:CGRect?}
enum CATransaction {static func begin(){};static func commit(){};static func setDisableActions(_ b:Bool){}}
class UIBezierPath {let cgPath:CGRect;init(ovalIn r:CGRect){cgPath=r}}
class UIView:NSObject {
 var frame:CGRect {didSet{bounds=CGRect(origin:.zero,size:frame.size)}}
 var bounds:CGRect;let layer=CALayer();var isOpaque=true;var isUserInteractionEnabled=true
 var isAccessibilityElement=false;var accessibilityElementsHidden=false;var accessibilityTraits:UIAccessibilityTraits=[]
 var overrideUserInterfaceStyle=UIUserInterfaceStyle.unspecified
 var accessibilityLabel:String?;var accessibilityValue:String?;var backgroundColor:UIColor?;var clipsToBounds=false;var isHidden=false
 var subviews:[UIView]=[]
 override convenience init(){self.init(frame:.zero)}
 init(frame:CGRect){self.frame=frame;self.bounds=CGRect(origin:.zero,size:frame.size);super.init()}
 required init?(coder:NSCoder){frame = .zero;bounds = .zero;super.init()}
 func addSubview(_ v:UIView){subviews.append(v)}
 func insertSubview(_ v:UIView,at i:Int){subviews.insert(v,at:i)}
 func layoutSubviews(){}
 func point(inside p:CGPoint,with e:UIEvent?)->Bool{bounds.contains(p)}
 func accessibilityIncrement(){};func accessibilityDecrement(){}
}
class UIControl:UIView {
 struct Event:OptionSet {let rawValue:Int;static let valueChanged=Self(rawValue:1)}
 var action:(()->Void)?
 func addTarget(_ target:AnyObject,action:String,for event:Event){self.action = { [weak target] in (target as? NagramiXSnowDensityItemNode)?.sliderValueChanged() }}
 func sendActions(for event:Event){action?()}
}
class UIImage {let size:CGSize;let isOpaque:Bool;init(size:CGSize=CGSize(width:1,height:1),opaque:Bool=false){self.size=size;isOpaque=opaque}}
class UIImageView:UIView {var image:UIImage?}
class UIFont {let pointSize:CGFloat;init(_ p:CGFloat){pointSize=p};static func systemFont(ofSize p:CGFloat)->UIFont{UIFont(p)}}
class UILabel:UIView {var text:String?;var font:UIFont?;var textColor:UIColor?;var numberOfLines=1;var textAlignment=NSTextAlignment.left}
extension NSAttributedString.Key {static let font=Self("fixture-font")}
struct NSStringDrawingOptions:OptionSet {let rawValue:Int;static let usesLineFragmentOrigin=Self(rawValue:1),usesFontLeading=Self(rawValue:2)}
extension NSString {
 func size(withAttributes a:[NSAttributedString.Key:Any])->CGSize{let s=(a[.font] as! UIFont).pointSize;return CGSize(width:CGFloat(self.length)*s*0.5,height:s*1.3)}
 func boundingRect(with s:CGSize,options:NSStringDrawingOptions,attributes a:[NSAttributedString.Key:Any],context:Any?)->CGRect{
  let one=self.size(withAttributes:a);return CGRect(x:0,y:0,width:min(s.width,one.width),height:ceil(one.width/max(1,s.width))*one.height)
 }
}
class UIVisualEffect {}
class UIGlassEffect:UIVisualEffect {enum Style{case clear};let style:Style;var isInteractive=true;init(style:Style){self.style=style}}
class UIVisualEffectView:UIView {let effect:UIVisualEffect?;init(effect:UIVisualEffect?){self.effect=effect;super.init(frame:.zero)};required init?(coder:NSCoder){return nil}}
class UIGraphicsImageRendererFormat {var opaque=true}
class FixtureCGContext {var cleared=false;func clear(_ r:CGRect){cleared=true}}
class FixtureRendererContext {let cgContext=FixtureCGContext()}
class UIGraphicsImageRenderer {
 let size:CGSize;let format:UIGraphicsImageRendererFormat
 init(size:CGSize,format:UIGraphicsImageRendererFormat){self.size=size;self.format=format}
 func image(_ draw:(FixtureRendererContext)->Void)->UIImage{let c=FixtureRendererContext();draw(c);return UIImage(size:size,opaque:format.opaque || !c.cgContext.cleared)}
}
class TGPhotoEditorSliderView:UIControl {
 var interactionBegan:(()->Void)?;var interactionEnded:(()->Void)?
 var minimumValue:CGFloat=0,maximumValue:CGFloat=1,startValue:CGFloat=0,value:CGFloat=0
 var enablePanHandling=false;var trackCornerRadius:CGFloat=0,lineSize:CGFloat=0
 var disablesInteractiveTransitionGestureRecognizer=false
 var backColor:UIColor?;var trackColor:UIColor?;var startColor:UIColor?
 var knobImage:UIImage? {didSet{knobView?.image=knobImage}}
 let knobView:UIImageView?=UIImageView(frame:.zero)
 override init(frame:CGRect){super.init(frame:frame);addSubview(knobView!)}
 required init?(coder:NSCoder){super.init(coder:coder);addSubview(knobView!)}
 override func layoutSubviews(){
  super.layoutSubviews();guard let k=knobView,let image=knobImage else{return}
  let position=7+nativePositiveMinimumPosition(value:value,totalLength:bounds.width-14,minimum:minimumValue,maximum:maximumValue)
  k.frame=CGRect(x:position-image.size.width/2,y:(bounds.height-image.size.height)/2,width:image.size.width,height:image.size.height)
 }
}
#else
import UIKit
extension UIView {var disablesInteractiveTransitionGestureRecognizer:Bool{get{false}set{}}}
#endif

// The host models below are explicit boundaries, also used by the Apple API
// probe. Apple UIKit, CoreGraphics and the actual Legacy header are not mocked.
enum Font {static func regular(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size)}}
let UIScreenPixel:CGFloat=0.5
struct FixtureFontSize {var baseDisplaySize:CGFloat=17}
class FixtureTheme {
 var overallDarkAppearance=true
 struct SwitchColors {let frameColor=UIColor(white:0.3,alpha:1)}
 struct List {let itemBlocksBackgroundColor=UIColor(white:0.1,alpha:1),itemPrimaryTextColor=UIColor(white:1,alpha:1),itemSecondaryTextColor=UIColor(white:0.5,alpha:1),itemAccentColor=UIColor(white:0.7,alpha:1),itemBlocksSeparatorColor=UIColor(white:0.3,alpha:1);let itemSwitchColors=SwitchColors()}
 let list=List()
}
struct FixturePresentation {var fontSize=FixtureFontSize();let theme=FixtureTheme()}
class NagramiXSnowDensityItem {
 let presentationData:FixturePresentation,title:String,value:Int,updated:(Int)->Void
 var theme:FixtureTheme{presentationData.theme}
 init(title:String,value:Int,fontSize:CGFloat=17,updated:@escaping(Int)->Void){var p=FixturePresentation();p.fontSize.baseDisplaySize=fontSize;presentationData=p;self.title=title;self.value=value;self.updated=updated}
}
class ASDisplayNode:NSObject {
 let view=UIView(frame:.zero);var isLayerBacked=false;weak var supernode:ASDisplayNode?
 var layer:CALayer{view.layer};var frame:CGRect{get{view.frame}set{view.frame=newValue}}
 var backgroundColor:UIColor?{get{view.backgroundColor}set{view.backgroundColor=newValue}}
 var isHidden:Bool{get{view.isHidden}set{view.isHidden=newValue}}
 func insertSubnode(_ n:ASDisplayNode,at i:Int){n.supernode=self}
}
class ASImageNode:ASDisplayNode {var image:UIImage?}
struct ListViewItemLayoutParams {let width:CGFloat,leftInset:CGFloat,rightInset:CGFloat}
enum Neighbor {case sameSection(Bool),other}
struct ItemListNeighbors {var top=Neighbor.sameSection(false),bottom=Neighbor.other}
struct ListViewItemNodeLayout {let contentSize:CGSize,insets:UIEdgeInsets;var size:CGSize{contentSize}}
struct ListViewItemAnimationOptions:OptionSet {let rawValue:Int}
class ListViewItemNode:ASDisplayNode {
 var contentSize:CGSize = .zero;var insets=UIEdgeInsets()
 init(layerBacked:Bool){super.init()}
 func didLoad(){}
 func animateInsertion(_ timestamp:Double,duration:Double,options:ListViewItemAnimationOptions){}
 func animateRemoved(_ timestamp:Double,duration:Double){}
}
enum PresentationResourcesItemList {static func cornersImage(_ theme:FixtureTheme,top:Bool,bottom:Bool)->UIImage?{UIImage()}}
func itemListNeighborsGroupedInsets(_ n:ItemListNeighbors,_ p:ListViewItemLayoutParams)->UIEdgeInsets{UIEdgeInsets()}
func itemListHasRoundedBlockLayout(_ p:ListViewItemLayoutParams)->Bool{true}
extension CALayer {func animateAlpha(from:Double,to:Double,duration:Double,removeOnCompletion:Bool=true){}}
