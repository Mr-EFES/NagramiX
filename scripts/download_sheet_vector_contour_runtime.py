"""Execute the complete production group with explicit UIKit/Texture adapters.

The analytical path adapter checks containment and layer ancestry, not iOS pixels.
No production class body is replaced with a test implementation.
"""
from validate_download_sheet_edge import clean

GROUP = 'submodules/Display/Source/ActionSheetItemGroupNode.swift'


def fixture(source):
    code = (source / GROUP).read_text().replace('import UIKit\nimport AsyncDisplayKit', '')
    return BOUNDARY + clean(code) + TESTS


def negatives(text):
    cases = [
        ('missing-common-mask', 'self.clippingNode.layer.mask = self.nagramiXTopCornersOnly ? self.nagramiXTopCornerContentMask : nil',
         'self.clippingNode.layer.mask = nil', 'common ancestor clips blur, rows and highlights'),
        ('nonzero-dim-fill', 'self.nagramiXTopCornerDimLayer.fillRule = .evenOdd',
         'self.nagramiXTopCornerDimLayer.fillRule = .nonZero', 'dim is the exact complement of content'),
        ('inverted-content', 'path: paths.content)', 'path: paths.dim)', 'common ancestor clips blur, rows and highlights'),
        ('stale-size', 'size: self.clippingNode.bounds.size)', 'size: CGSize(width: 320, height: 400))', 'resized mask and dim use current bounds'),
        ('floating-mask-leak', 'self.nagramiXTopCornersOnly ? self.nagramiXTopCornerContentMask : nil',
         'self.nagramiXTopCornerContentMask', 'floating reuse restores native corners and image'),
        ('double-dim', '? nil\n                : generateStretchableFilledCircleImage',
         '? generateStretchableFilledCircleImage(radius: 16, color: nil, backgroundColor: self.theme.dimColor)\n                : generateStretchableFilledCircleImage',
         'attached mode removes the legacy raster dim image'),
    ]
    for name, old, new, diagnostic in cases:
        assert text.count(old) == 1, (name, text.count(old))
        yield name, text.replace(old, new), diagnostic


BOUNDARY = r'''
import Foundation
struct UIRectCorner:OptionSet {
    let rawValue:Int
    static let topLeft=Self(rawValue:1),topRight=Self(rawValue:2)
}
struct CACornerMask:OptionSet {
    let rawValue:Int
    static let layerMinXMinYCorner=Self(rawValue:1),layerMaxXMinYCorner=Self(rawValue:2)
    static let layerMinXMaxYCorner=Self(rawValue:4),layerMaxXMaxYCorner=Self(rawValue:8)
}
struct CGColor:Equatable {let alpha:CGFloat}
final class UIColor {
    let cgColor:CGColor
    init(_ alpha:CGFloat){cgColor=CGColor(alpha:alpha)}
    static let black=UIColor(1)
}
struct CGPath:Equatable {
    struct Contour:Equatable {let rect:CGRect;let radius:CGFloat}
    var contours:[Contour]
    func contains(_ p:CGPoint,evenOdd:Bool)->Bool {
        let count=contours.filter{c in
            guard c.rect.contains(p) else{return false}
            let r=min(c.radius,min(c.rect.width,c.rect.height)/2)
            if r>0 && p.y<c.rect.minY+r {
                if p.x<c.rect.minX+r {return hypot(p.x-c.rect.minX-r,p.y-c.rect.minY-r)<=r}
                if p.x>c.rect.maxX-r {return hypot(p.x-c.rect.maxX+r,p.y-c.rect.minY-r)<=r}
            }
            return true
        }.count
        return evenOdd ? count%2==1 : count>0
    }
}
final class UIBezierPath {
    var cgPath:CGPath
    init(rect:CGRect){cgPath=CGPath(contours:[.init(rect:rect,radius:0)])}
    init(roundedRect:CGRect,byRoundingCorners:UIRectCorner,cornerRadii:CGSize){
        precondition(byRoundingCorners == [.topLeft,.topRight])
        cgPath=CGPath(contours:[.init(rect:roundedRect,radius:cornerRadii.width)])
    }
    func append(_ other:UIBezierPath){cgPath.contours += other.cgPath.contours}
}
struct CATransform3D {let x:CGFloat,y:CGFloat,z:CGFloat}
func CATransform3DMakeTranslation(_ x:CGFloat,_ y:CGFloat,_ z:CGFloat)->CATransform3D{.init(x:x,y:y,z:z)}
class CALayer {
    var frame=CGRect.zero,mask:CALayer?,isHidden=false
    var maskedCorners:CACornerMask=[.layerMinXMinYCorner,.layerMaxXMinYCorner,.layerMinXMaxYCorner,.layerMaxXMaxYCorner]
    var sublayerTransform=CATransform3DMakeTranslation(0,0,0)
    var sublayers:[CALayer]=[]
    var frameTransitions:[String]=[],pathTransitions:[String]=[],alphaAnimations:[CGFloat]=[]
    func addSublayer(_ layer:CALayer){sublayers.append(layer)}
    func animateAlpha(from:CGFloat,to:CGFloat,duration:Double){alphaAnimations.append(to)}
}
final class CAShapeLayer:CALayer {
    enum FillRule {case evenOdd,nonZero}
    var path:CGPath?,fillColor:CGColor?,fillRule=FillRule.nonZero
    func alpha(at p:CGPoint)->CGFloat {
        guard !isHidden,let path=path,path.contains(p,evenOdd:fillRule == .evenOdd) else{return 0}
        return fillColor?.alpha ?? 0
    }
}
class UIView {
    var frame=CGRect.zero
    var bounds:CGRect {CGRect(origin:.zero,size:frame.size)}
    var backgroundColor:UIColor?,isUserInteractionEnabled=true,accessibilityElementsHidden=false
    var clipsToBounds=false
    var subviews:[UIView]=[];weak var superview:UIView?
    let layer=CALayer()
    func addSubview(_ v:UIView){subviews.append(v);v.superview=self}
    func removeFromSuperview(){superview?.subviews.removeAll{$0 === self};superview=nil}
    // Model only clipping ancestry. Blur and row colors are intentionally opaque.
    func contentAlpha(at p:CGPoint)->CGFloat {
        if let mask=layer.mask as? CAShapeLayer,mask.alpha(at:p)==0{return 0}
        return superview?.contentAlpha(at:p) ?? 1
    }
}
final class UIImage {}
final class UIImageView:UIView {var image:UIImage?}
final class UIBlurEffect {enum Style {case light,dark};init(style:Style){}}
final class UIVisualEffectView:UIView {init(effect:UIBlurEffect){super.init()}}
class UIScrollView:UIView {
    enum Adjustment {case never}
    var bounces=true,delaysContentTouches=true,canCancelContentTouches=false,showsVerticalScrollIndicator=true
    var showsHorizontalScrollIndicator=true,scrollsToTop=true,contentInsetAdjustmentBehavior=Adjustment.never
    var contentSize=CGSize.zero,contentOffset=CGPoint.zero,contentInset=UIEdgeInsets()
    weak var delegate:AnyObject?
}
struct UIEdgeInsets:Equatable {var top:CGFloat=0,left:CGFloat=0,bottom:CGFloat=0,right:CGFloat=0}
class UIEvent {}
protocol ASScrollViewDelegate:AnyObject {}
class ASDisplayNode {
    let view=UIScrollView()
    var layer:CALayer{view.layer}
    var frame:CGRect{get{view.frame}set{view.frame=newValue}}
    var bounds:CGRect{view.bounds}
    var clipsToBounds:Bool{get{view.clipsToBounds}set{view.clipsToBounds=newValue}}
    var cornerRadius:CGFloat=0,alpha:CGFloat=1
    var wrappedScrollViewDelegate:AnyObject{self}
    func addSubnode(_ node:ASDisplayNode){view.addSubview(node.view)}
    func removeFromSupernode(){view.removeFromSuperview()}
    func invalidateCalculatedLayout(){}
    func hitTest(_ point:CGPoint,with event:UIEvent?)->UIView?{view}
}
final class ASScrollNode:ASDisplayNode {var canCancelAllTouchesInViews=false}
final class ActionSheetGroupOverlayNode:ASDisplayNode {func updateLayout(size:CGSize,transition:ContainedViewLayoutTransition){}}
final class ActionSheetItemNode:ASDisplayNode {
    let height:CGFloat;var hasSeparator=false
    let highlight=UIView()
    init(_ height:CGFloat){self.height=height;super.init();view.addSubview(highlight)}
    func updateLayout(constrainedSize:CGSize,transition:ContainedViewLayoutTransition)->CGSize{CGSize(width:constrainedSize.width,height:height)}
}
struct ActionSheetControllerTheme {
    enum Background {case light,dark}
    var dimColor:UIColor,itemBackgroundColor=UIColor(1),backgroundType=Background.dark
}
enum ContainedViewLayoutTransition {
    enum Curve {case linear}
    case immediate,animated(duration:Double,curve:Curve)
    var label:String{if case .immediate=self{return "immediate"};return "animated"}
    func updateFrame(node:ASDisplayNode,frame:CGRect){node.frame=frame}
    func updateFrame(view:UIView,frame:CGRect){view.frame=frame}
    func updateFrame(layer:CALayer,frame:CGRect){layer.frame=frame;layer.frameTransitions.append(label)}
    func updatePath(layer:CAShapeLayer,path:CGPath){layer.path=path;layer.pathTransitions.append(label)}
    func updateAlpha(node:ASDisplayNode,alpha:CGFloat){node.alpha=alpha}
}
let UIScreenPixel:CGFloat=0.5
func floorToScreenPixels(_ x:CGFloat)->CGFloat{floor(x*2)/2}
func generateStretchableFilledCircleImage(radius:CGFloat,color:UIColor?,backgroundColor:UIColor)->UIImage?{UIImage()}
extension CGRect{func equalTo(_ r:CGRect)->Bool{self==r}}
extension CGSize{func equalTo(_ s:CGSize)->Bool{self==s}}
'''

TESTS = r'''
@main struct ContourTests {
    static func main(){
        var checks=0
        func check(_ v:@autoclosure()->Bool,_ s:String){if !v(){FileHandle.standardError.write(Data(("Contour regression: "+s+"\n").utf8));exit(91)};checks+=1}
        for width:CGFloat in [320,393,430,852,834] {for safe:CGFloat in [0,21,34] {for alpha:CGFloat in [0.2,0.5,0.8] {
            let g=ActionSheetItemGroupNode(theme:ActionSheetControllerTheme(dimColor:UIColor(alpha)))
            let rows=[88,84,84,64].map{ActionSheetItemNode(CGFloat($0))}
            g.updateItemNodes(rows)
            check(g.clippingNode.layer.mask==nil && g.centerDimView.image != nil,"native floating initialization unchanged")
            g.nagramiXBottomPadding=safe;g.nagramiXTopCornersOnly=true
            let size=g.updateLayout(constrainedSize:CGSize(width:width,height:900),transition:.immediate)
            check(g.centerDimView.image==nil,"attached mode removes the legacy raster dim image")
            check(g.centerDimView.layer.sublayers.contains{$0 === g.nagramiXTopCornerDimLayer},"dim follows existing center-view animation")
            check(size==CGSize(width:width,height:320+safe) && g.nagramiXBottomPaddingView.frame.maxY==size.height,"safe-area fill reaches bottom unchanged")
            check(!g.scrollNode.view.bounces && g.clippingNode.cornerRadius==0,"one clipping contour without inner bounce")
            check(g.backgroundEffectView.superview === g.clippingNode.view && g.scrollNode.view.superview === g.clippingNode.view,"blur and rows share a clipping ancestor")
            check(g.clippingNode.layer.mask === g.nagramiXTopCornerContentMask,"common ancestor clips blur, rows and highlights")
            for scale:CGFloat in [1,2,3] {
                for x:CGFloat in [0.25,2,5,9,14,18,width/2] {for y:CGFloat in [0.25,2,5,9,14,18,size.height-0.25] {
                    let p=CGPoint(x:x/scale,y:y/scale)
                    // Independent expected geometry of a radius-16 top corner.
                    let inside=p.x>=16 || p.y>=16 || hypot(p.x-16,p.y-16)<=16
                    let expected:CGFloat=inside ? 1:0
                    for v in [g.backgroundEffectView,g.scrollNode.view,rows[0].highlight,g.nagramiXBottomPaddingView] {
                        check(v.contentAlpha(at:p)==expected,"common ancestor clips blur, rows and highlights")
                    }
                    let c=g.nagramiXTopCornerContentMask.alpha(at:p),d=g.nagramiXTopCornerDimLayer.alpha(at:p)
                    check(c==expected && abs(d-(1-expected)*alpha)<0.00001,"dim is the exact complement of content")
                    let right=CGPoint(x:width-p.x,y:p.y)
                    check(g.nagramiXTopCornerContentMask.alpha(at:right)==expected,"top corners are symmetric")
                }}
            }
            for p in [CGPoint(x:0.25,y:size.height-0.25),CGPoint(x:width-0.25,y:size.height-0.25)] {
                check(g.nagramiXTopCornerContentMask.alpha(at:p)==1 && g.nagramiXTopCornerDimLayer.alpha(at:p)==0,"bottom edge and safe-area fill stay square and attached")
            }
            let oldCalls=g.nagramiXTopCornerContentMask.pathTransitions.count
            _=g.updateLayout(constrainedSize:CGSize(width:width,height:900),transition:.immediate)
            check(g.nagramiXTopCornerContentMask.pathTransitions.count>oldCalls,"path refresh does not depend on outer frame changing")
            let wider=CGSize(width:width+47,height:240)
            _=g.updateLayout(constrainedSize:wider,transition:.animated(duration:0.3,curve:.linear))
            for layer in [g.nagramiXTopCornerContentMask,g.nagramiXTopCornerDimLayer] {
                check(layer.frame==CGRect(origin:.zero,size:wider) && layer.path?.contours.allSatisfy{$0.rect==layer.frame}==true,"resized mask and dim use current bounds")
                check(layer.frameTransitions.last=="animated" && layer.pathTransitions.last=="animated","frame and contour share native transition")
            }
            g.animateDimViewsAlpha(from:0,to:1,duration:0.3)
            check(g.centerDimView.layer.alphaAnimations==[1],"existing dim fade includes vector dim child")
            g.nagramiXTopCornersOnly=false;g.nagramiXBottomPadding=0
            _=g.updateLayout(constrainedSize:CGSize(width:width,height:900),transition:.immediate)
            check(g.clippingNode.layer.mask==nil && g.clippingNode.cornerRadius==16 && g.centerDimView.image != nil && g.nagramiXTopCornerDimLayer.isHidden,"floating reuse restores native corners and image")
            check(g.scrollNode.view.bounces && g.nagramiXBottomPaddingView.frame.height==0,"floating reuse restores padding and scroll behavior")
            g.nagramiXTopCornersOnly=true
            _=g.updateLayout(constrainedSize:CGSize(width:width,height:900),transition:.immediate)
            check(g.clippingNode.layer.mask === g.nagramiXTopCornerContentMask && !g.nagramiXTopCornerDimLayer.isHidden,"attached reuse reinstalls one contour")
        }}}
        print("Production group contour checks: \(checks)")
    }
}
'''
