import Foundation
import UIKit
import Display
// Display here exports only the exact production marker protocol; UIKit is real.
// Texture, presentation and app models are explicit standalone probe adapters.
class ASDisplayNode:NSObject,UIScrollViewDelegate {
 let view=UIScrollView()
 var layer:CALayer{view.layer}
 var frame:CGRect{get{view.frame}set{view.frame=newValue}}
 var bounds:CGRect{view.bounds}
 var backgroundColor:UIColor?{get{view.backgroundColor}set{view.backgroundColor=newValue}}
 var clipsToBounds:Bool{get{view.clipsToBounds}set{view.clipsToBounds=newValue}}
 var cornerRadius:CGFloat{get{view.layer.cornerRadius}set{view.layer.cornerRadius=newValue}}
 var alpha:CGFloat{get{view.alpha}set{view.alpha=newValue}}
 var wrappedScrollViewDelegate:UIScrollViewDelegate{self}
 func addSubnode(_ node:ASDisplayNode){view.addSubview(node.view)}
 func removeFromSupernode(){view.removeFromSuperview()}
 func invalidateCalculatedLayout(){}
 func hitTest(_ point:CGPoint,with event:UIEvent?)->UIView?{view.hitTest(point,with:event)}
}
protocol ASScrollViewDelegate:AnyObject{}
class ASScrollNode:ASDisplayNode{var canCancelAllTouchesInViews=false}
class ActionSheetGroupOverlayNode:ASDisplayNode{func updateLayout(size:CGSize,transition:ContainedViewLayoutTransition){}}
class ActionSheetItemNode:ASDisplayNode {
 let backgroundNode=ASDisplayNode();var hasSeparator=false
 init(theme:ActionSheetControllerTheme){super.init()}
 func updateLayout(constrainedSize:CGSize,transition:ContainedViewLayoutTransition)->CGSize{constrainedSize}
 func requestLayoutUpdate(){}
 func updateInternalLayout(_ size:CGSize,constrainedSize:CGSize){}
}
struct ActionSheetControllerTheme {
 enum Background{case light,dark}
 var dimColor=UIColor.black,itemBackgroundColor=UIColor.gray,itemHighlightedBackgroundColor=UIColor.gray
 var controlAccentColor=UIColor.blue,controlColor=UIColor.gray,secondaryTextColor=UIColor.gray,primaryTextColor=UIColor.white
 var backgroundType=Background.dark;var baseFontSize:CGFloat=17
}
enum ContainedViewLayoutTransition {
 enum Curve{case linear}
 case immediate,animated(duration:Double,curve:Curve)
 func updateFrame(node:ASDisplayNode,frame:CGRect){node.frame=frame}
 func updateFrame(view:UIView,frame:CGRect){view.frame=frame}
 func updateFrame(layer:CALayer,frame:CGRect){layer.frame=frame}
 func updatePath(layer:CAShapeLayer,path:CGPath){layer.path=path}
 func updateAlpha(node:ASDisplayNode,alpha:CGFloat){node.alpha=alpha}
}
extension CALayer{func animateAlpha(from:CGFloat,to:CGFloat,duration:Double){}}
class HighlightTrackingButton:UIButton {var highligthedChanged:((Bool)->Void)?}
enum Font{static func regular(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size)};static func semibold(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size,weight:.semibold)}}
let UIScreenPixel:CGFloat=0.5
let containerInsets=UIEdgeInsets(top:10,left:10,bottom:10,right:10)
func floorToScreenPixels(_ x:CGFloat)->CGFloat{floor(x*2)/2}
func generateStretchableFilledCircleImage(radius:CGFloat,color:UIColor?,backgroundColor:UIColor)->UIImage?{UIImage()}
