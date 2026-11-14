// UIKit/TextKit glyph metrics are explicit Linux adapters. Real Apple probe
// compiles all actual controller/view/formatter bodies with genuine UIKit.
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
#if canImport(UIKit)
import UIKit
#else
// Explicit attributed-run storage: swift-corelibs Foundation traps when its
// CF attribute equality sees fake UIKit font/style objects. Apple uses real
// NSAttributedString with real UIFont/NSMutableParagraphStyle instead.
class NSAttributedString {
 struct Key:Hashable{let rawValue:String;init(_ value:String){rawValue=value}}
 var string:String;var runs:[(NSRange,[Key:Any])]
 init(string:String,attributes:[Key:Any]=[:]){self.string=string;runs=[(NSRange(location:0,length:(string as NSString).length),attributes)]}
 var length:Int{(string as NSString).length}
 func attributes(at index:Int,effectiveRange:UnsafeMutablePointer<NSRange>?)->[Key:Any]{runs.first{NSLocationInRange(index,$0.0)}?.1 ?? [:]}
}
class NSMutableAttributedString:NSAttributedString {
 func append(_ value:NSAttributedString){let start=length;string+=value.string;for (range,attributes) in value.runs{runs.append((NSRange(location:start+range.location,length:range.length),attributes))}}
}
struct UIEdgeInsets:Equatable {var top:CGFloat=0,left:CGFloat=0,bottom:CGFloat=0,right:CGFloat=0;static let zero=Self()}
enum NSTextAlignment {case left,right,justified}
enum NSLineBreakMode {case byWordWrapping,byTruncatingTail}
enum UIUserInterfaceStyle {case dark,light}
class UIColor:NSObject {
 static let clear=UIColor(),black=UIColor(),white=UIColor(),gray=UIColor(),blue=UIColor()
 var cgColor:UIColor{self}
}
class UIFont:NSObject {
 enum Weight {case regular,semibold}
 let pointSize:CGFloat;let weight:Weight
 init(size:CGFloat,weight:Weight){pointSize=size;self.weight=weight}
 static func systemFont(ofSize size:CGFloat,weight:Weight = .regular)->UIFont{UIFont(size:size,weight:weight)}
}
class NSMutableParagraphStyle:NSObject {
 var alignment=NSTextAlignment.left;var lineBreakMode=NSLineBreakMode.byWordWrapping
 var paragraphSpacingBefore:CGFloat=0,paragraphSpacing:CGFloat=0,lineSpacing:CGFloat=0
}
extension NSAttributedString.Key {static let font=Self("font"),foregroundColor=Self("color"),paragraphStyle=Self("paragraphStyle")}
class FixturePath {var segments:[(CGPoint,CGPoint)]=[]}
class UIBezierPath {
 let cgPath=FixturePath();var current:CGPoint = .zero
 func move(to point:CGPoint){current=point}
 func addLine(to point:CGPoint){cgPath.segments.append((current,point));current=point}
}
class CALayer {
 weak var superlayer:CALayer?;var sublayers:[CALayer]=[];var frame:CGRect = .zero;var cornerRadius:CGFloat=0;var zPosition:CGFloat=0
 func addSublayer(_ value:CALayer){sublayers.append(value);value.superlayer=self}
}
class CAShapeLayer:CALayer {var fillColor:UIColor?,strokeColor:UIColor?;var lineWidth:CGFloat=0;var path:FixturePath?}
enum CATransaction {static func begin(){};static func commit(){};static func setDisableActions(_ value:Bool){}}
class UIView:NSObject {
 var frame:CGRect {didSet{bounds.size=frame.size}}
 var bounds:CGRect;let layer=CALayer();var clipsToBounds=false;var backgroundColor:UIColor?;var subviews:[UIView]=[]
 var layoutRequested=false
 override convenience init(){self.init(frame:.zero)}
 init(frame:CGRect){self.frame=frame;bounds=CGRect(origin:.zero,size:frame.size);super.init()}
 required init?(coder:NSCoder){frame = .zero;bounds = .zero;super.init()}
 func addSubview(_ value:UIView){subviews.append(value)}
 func setNeedsLayout(){layoutRequested=true}
 func layoutIfNeeded(){if layoutRequested{layoutRequested=false;layoutSubviews()}}
 func layoutSubviews(){}
}
class NSTextContainer {var lineFragmentPadding:CGFloat=5}
class NSLayoutManager {
 var rects:[Int:CGRect]=[:];var ensureCount=0;var glyphRequests:[NSRange]=[]
 func ensureLayout(for container:NSTextContainer){ensureCount+=1}
 func glyphRange(forCharacterRange range:NSRange,actualCharacterRange:UnsafeMutablePointer<NSRange>?)->NSRange{glyphRequests.append(range);return range}
 func boundingRect(forGlyphRange range:NSRange,in container:NSTextContainer)->CGRect{rects[range.location] ?? CGRect(x:0,y:CGFloat(range.location),width:7,height:17)}
}
class UITextView:UIView {
 enum InsetBehavior{case never}
 var isEditable=true,isSelectable=false
 var contentInsetAdjustmentBehavior=InsetBehavior.never
 var textContainerInset=UIEdgeInsets.zero,contentInset=UIEdgeInsets.zero,scrollIndicatorInsets=UIEdgeInsets.zero
 let textContainer=NSTextContainer();let layoutManager=NSLayoutManager()
 var attributedText=NSAttributedString(string:"")
 var contentOffset:CGPoint = .zero {didSet{bounds.origin=contentOffset}}
 var contentSize:CGSize = .zero;var tintColor:UIColor?;var overrideUserInterfaceStyle=UIUserInterfaceStyle.dark
}
#endif

enum Font {
 static func regular(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size)}
 static func semibold(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size,weight:.semibold)}
}
let UIScreenPixel:CGFloat=0.5
struct FixtureStrings {func nagramiXLocalized(_ key:String)->String{key}}
struct FixtureListTheme {
 var itemPrimaryTextColor=UIColor.white,itemBlocksSeparatorColor=UIColor.gray,itemBlocksBackgroundColor=UIColor.gray,itemAccentColor=UIColor.blue,blocksBackgroundColor=UIColor.black
}
struct FixtureBarStyle {var style:Int=1}
struct FixtureRootTheme {var statusBarStyle=FixtureBarStyle()}
struct FixtureTheme {var list=FixtureListTheme();var rootController=FixtureRootTheme();var overallDarkAppearance=true}
struct FixtureFontSize {
 var itemListBaseFontSize:CGFloat=17
 /* ACTUAL HEADER SIZE */
}
final class PresentationData {var strings=FixtureStrings();var listsFontSize=FixtureFontSize();var theme=FixtureTheme()}
struct FixtureAtomic {
 let value:PresentationData
 func with<T>(_ body:(PresentationData)->T)->T{body(value)}
}
struct FixtureSignal {func start(next:@escaping(PresentationData)->Void)->Int{0}}
func deliverOnMainQueue(_ value:FixtureSignal)->FixtureSignal{value}
infix operator |> : AdditionPrecedence
func |> <A,B>(value:A,body:(A)->B)->B{body(value)}
class MetaDisposable {func set(_ value:Int){};func dispose(){}}
class FixtureSharedContext {
 var currentPresentationData=FixtureAtomic(value:PresentationData());var presentationData=FixtureSignal()
}
class AccountContext {let sharedContext=FixtureSharedContext()}
struct NavigationBarPresentationData {init(presentationData:PresentationData){}}
class ASDisplayNode {let view=UIView();var backgroundColor:UIColor?}
struct NavigationLayout {let navigationFrame:CGRect}
struct ContainerViewLayout {var size:CGSize;var safeInsets=UIEdgeInsets.zero;var intrinsicInsets=UIEdgeInsets.zero}
enum ContainedViewLayoutTransition {case immediate}
class FixtureStatusBar {var statusBarStyle=0}
class FixtureNavigationBar {func updatePresentationData(_ value:NavigationBarPresentationData,transition:ContainedViewLayoutTransition){}}
class ViewController:NSObject {
 var displayNode=ASDisplayNode();var navigationBar:FixtureNavigationBar?;var isNodeLoaded=false
 let statusBar=FixtureStatusBar();var title:String?
 init(navigationBarPresentationData:NavigationBarPresentationData){super.init()}
 required init(coder:NSCoder){super.init()}
 func loadDisplayNode(){}
 func displayNodeDidLoad(){isNodeLoaded=true}
 func containerLayoutUpdated(_ layout:ContainerViewLayout,transition:ContainedViewLayoutTransition){}
 func navigationLayout(layout:ContainerViewLayout)->NavigationLayout{NavigationLayout(navigationFrame:CGRect(x:0,y:0,width:layout.size.width,height:88))}
}
