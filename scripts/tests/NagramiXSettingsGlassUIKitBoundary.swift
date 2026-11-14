// Linux-only UIKit dispatch/layout metrics. No claim of Apple rendering.
enum UIUserInterfaceLayoutDirection {case leftToRight,rightToLeft}
extension UIColor {func withAlphaComponent(_ alpha:CGFloat)->UIColor{UIColor(white:0.5,alpha:alpha)}}
class NSLayoutConstraint {
 enum Axis{case horizontal,vertical}
 var isActive=false
 static func activate(_ constraints:[NSLayoutConstraint]){}
}
struct UILayoutPriority {static let defaultLow=Self()}
class FixtureAnchor {
 func constraint(equalTo:FixtureAnchor,constant:CGFloat=0)->NSLayoutConstraint{NSLayoutConstraint()}
 func constraint(greaterThanOrEqualToConstant:CGFloat)->NSLayoutConstraint{NSLayoutConstraint()}
}
class FixtureLayoutGuide {let leadingAnchor=FixtureAnchor(),trailingAnchor=FixtureAnchor()}
extension UIView {
 var leadingAnchor:FixtureAnchor{FixtureAnchor()};var trailingAnchor:FixtureAnchor{FixtureAnchor()}
 var topAnchor:FixtureAnchor{FixtureAnchor()};var bottomAnchor:FixtureAnchor{FixtureAnchor()}
 var heightAnchor:FixtureAnchor{FixtureAnchor()};var layoutMarginsGuide:FixtureLayoutGuide{FixtureLayoutGuide()}
 var translatesAutoresizingMaskIntoConstraints:Bool{get{false}set{}}
 func addGestureRecognizer(_ gesture:UITapGestureRecognizer){}
}
class UITableViewCell:UIView {
 enum CellStyle{case `default`,value1};enum SelectionStyle{case none}
 let contentView=UIView();let textLabel:UILabel?=UILabel();var selectionStyle=SelectionStyle.none
 init(style:CellStyle,reuseIdentifier:String?){super.init(frame:.zero);addSubview(contentView)}
 required init?(coder:NSCoder){super.init(coder:coder)}
}
class UIStackView:UIView {
 var axis=NSLayoutConstraint.Axis.horizontal;var spacing:CGFloat=0;var arrangedSubviews:[UIView]=[]
 convenience init(arrangedSubviews:[UIView]){self.init(frame:.zero);for view in arrangedSubviews{addArrangedSubview(view)}}
 func addArrangedSubview(_ view:UIView){arrangedSubviews.append(view);addSubview(view)}
}
class UITapGestureRecognizer {
 enum State{case ended,began};var state=State.ended;var cancelsTouchesInView=true;var locationValue:CGPoint = .zero
 init(target:AnyObject,action:String){}
 func location(in view:UIView)->CGPoint{locationValue}
}
class UISlider:UIControl {
 struct State:OptionSet{let rawValue:Int;static let normal=Self(rawValue:1),highlighted=Self(rawValue:2),disabled=Self(rawValue:4)}
 var minimumValue:Float=0,maximumValue:Float=1,value:Float=0
 var isTracking=false;var isContinuous=true;var tintColor:UIColor?
 var minimumTrackTintColor:UIColor?;var maximumTrackTintColor:UIColor?;var images:[Int:UIImage]=[:]
 func setThumbImage(_ image:UIImage?,for state:State){images[state.rawValue]=image}
 func setValue(_ value:Float,animated:Bool){self.value=min(maximumValue,max(minimumValue,value))}
 func trackRect(forBounds b:CGRect)->CGRect{CGRect(x:0,y:b.midY-2,width:b.width,height:4)}
 func thumbRect(forBounds b:CGRect,trackRect t:CGRect,value:Float)->CGRect{
  let width=images[State.normal.rawValue]?.size.width ?? 31
  let fraction=CGFloat((value-minimumValue)/(maximumValue-minimumValue))
  let x=(b.width-width)*(effectiveUserInterfaceLayoutDirection == .rightToLeft ? 1-fraction:fraction)
  return CGRect(x:x,y:(b.height-width)/2,width:width,height:width)
 }
}
