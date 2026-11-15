// Recording UIKit edge for executing the actual button/cell source on Linux.
// It records constraints and typography requests; it does not render pixels.
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

struct UIEdgeInsets { var top:CGFloat=0,left:CGFloat=0,bottom:CGFloat=0,right:CGFloat=0 }
struct UIColor:Equatable { let id:Int;func withAlphaComponent(_ value:CGFloat)->Self{self};var cgColor:Self{self} }
struct UILayoutPriority { static let required=Self() }
struct AccessibilityTraits:OptionSet {
 let rawValue:Int
 static let button=Self(rawValue:1),selected=Self(rawValue:2),notEnabled=Self(rawValue:4)
}
struct Anchor:Equatable {
 let owner:Int,name:String
 func constraint(equalTo other:Anchor,constant:CGFloat=0)->NSLayoutConstraint{NSLayoutConstraint(self,"=",other,constant)}
 func constraint(equalToConstant value:CGFloat)->NSLayoutConstraint{NSLayoutConstraint(self,"=",nil,value)}
 func constraint(greaterThanOrEqualToConstant value:CGFloat)->NSLayoutConstraint{NSLayoutConstraint(self,">=",nil,value)}
}
final class NSLayoutConstraint {
 enum Axis {case horizontal,vertical}
 let first:Anchor,relation:String,second:Anchor?,constant:CGFloat
 init(_ first:Anchor,_ relation:String,_ second:Anchor?,_ constant:CGFloat){self.first=first;self.relation=relation;self.second=second;self.constant=constant}
 static var active:[NSLayoutConstraint]=[]
 static func activate(_ values:[NSLayoutConstraint]){active+=values}
}
final class CALayer {
 enum Curve {case continuous}
 var cornerCurve=Curve.continuous,borderWidth:CGFloat=0,cornerRadius:CGFloat=0
 var borderColor:UIColor?
}
class UIView {
 static func performWithoutAnimation(_ body:()->Void){body()}
 static var serial=0
 let id:Int
 var frame:CGRect
 var bounds:CGRect{get{CGRect(origin:.zero,size:frame.size)}set{frame.size=newValue.size}}
 weak var superview:UIView?
 var subviews:[UIView]=[]
 let layer=CALayer()
 var isUserInteractionEnabled=true,isAccessibilityElement=false,accessibilityElementsHidden=false,clipsToBounds=false,translatesAutoresizingMaskIntoConstraints=true,isHidden=false
 var backgroundColor:UIColor?,alpha:CGFloat=1
 var accessibilityLabel:String?,accessibilityValue:String?,accessibilityTraits:AccessibilityTraits=[]
 struct Traits {var displayScale:CGFloat=2}
 let traitCollection=Traits()
 var invalidations=0,layoutRequests=0,fittings=0
 init(frame:CGRect = .zero){UIView.serial+=1;id=UIView.serial;self.frame=frame}
 func addSubview(_ view:UIView){view.superview=self;subviews.append(view)}
 func insertSubview(_ view:UIView,belowSubview:UIView){addSubview(view)}
 func anchor(_ name:String)->Anchor{Anchor(owner:id,name:name)}
 var leadingAnchor:Anchor{anchor("leading")};var trailingAnchor:Anchor{anchor("trailing")}
 var topAnchor:Anchor{anchor("top")};var bottomAnchor:Anchor{anchor("bottom")}
 var centerXAnchor:Anchor{anchor("centerX")};var centerYAnchor:Anchor{anchor("centerY")}
 var widthAnchor:Anchor{anchor("width")};var heightAnchor:Anchor{anchor("height")}
 var intrinsicContentSize:CGSize{.zero}
 func setContentCompressionResistancePriority(_ value:UILayoutPriority,for axis:NSLayoutConstraint.Axis){}
 func setNeedsLayout(){layoutRequests+=1}
 func invalidateIntrinsicContentSize(){invalidations+=1}
 func layoutSubviews(){}
 func systemLayoutSizeFitting(_ targetSize:CGSize,withHorizontalFittingPriority:UILayoutPriority,verticalFittingPriority:UILayoutPriority)->CGSize{fittings+=1;return targetSize}
}
class UIButton:UIView {
 enum Event {case touchUpInside}
 var isEnabled=true,isSelected=false,isHighlighted=false
 func addTarget(_ target:AnyObject,action:String,for event:Event){}
}
final class UILabel:UIView {
 enum Alignment {case center}
 var text:String?,font:CGFloat=17,textColor:UIColor?,numberOfLines=1,textAlignment=Alignment.center,adjustsFontForContentSizeCategory=false
 override var intrinsicContentSize:CGSize{CGSize(width:CGFloat(text?.count ?? 0)*font*0.6,height:ceil(font*1.2))}
}
final class UIImage {
 init?(systemName:String){}
 struct SymbolConfiguration {enum Weight{case semibold};init(pointSize:CGFloat,weight:Weight){}}
}
final class UIImageView:UIView {
 enum Mode {case scaleAspectFit}
 var image:UIImage?,contentMode=Mode.scaleAspectFit,tintColor:UIColor?,preferredSymbolConfiguration:UIImage.SymbolConfiguration?
 init(image:UIImage?){self.image=image;super.init()}
}
class UIVisualEffect {}
final class UIGlassEffect:UIVisualEffect {
 enum Style {case clear};var isInteractive=false
 init(style:Style){}
}
final class UIBlurEffect:UIVisualEffect {
 enum Style {case systemUltraThinMaterialDark,systemUltraThinMaterialLight}
 init(style:Style){}
}
final class UIVisualEffectView:UIView {
 let contentView=UIView()
 init(effect:UIVisualEffect){super.init()}
}
final class UIStackView:UIView {
 enum Distribution{case fillEqually};enum Alignment{case fill,center}
 var axis=NSLayoutConstraint.Axis.horizontal,distribution=Distribution.fillEqually,alignment=Alignment.fill,spacing:CGFloat=0
 let arrangedSubviews:[UIView]
 init(arrangedSubviews:[UIView]){self.arrangedSubviews=arrangedSubviews;super.init();for view in arrangedSubviews{addSubview(view)}}
}
class UITableViewCell:UIView {
 enum Style{case `default`};enum Selection{case none}
 let contentView=UIView();var selectionStyle=Selection.none
 init(style:Style,reuseIdentifier:String?){super.init();addSubview(contentView)}
}
struct ListTheme {
 let itemAccentColor=UIColor(id:1),itemPrimaryTextColor=UIColor(id:2),itemSecondaryTextColor=UIColor(id:3),itemBlocksBackgroundColor=UIColor(id:4),itemBlocksSeparatorColor=UIColor(id:5)
}
struct Theme {let list=ListTheme(),overallDarkAppearance=true}
struct ListFontSize {let itemListBaseFontSize:CGFloat}
struct PresentationData {let theme=Theme();let listsFontSize:ListFontSize;init(_ font:CGFloat=17){listsFontSize=ListFontSize(itemListBaseFontSize:font)}}
enum Font {static func regular(_ value:CGFloat)->CGFloat{value}}
struct PresentationStrings {func nagramiXUILocalized(_ key:String)->String{key}}
