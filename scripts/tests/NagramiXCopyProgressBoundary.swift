import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

// UIKit/ASDisplayNode presentation is a boundary. UIViewController's mutable
// optional title is deliberately retained to catch a conflicting stored field.
struct UIColor {func withAlphaComponent(_ value:CGFloat)->Self {self}}
enum Font {static func regular(_ size:CGFloat)->Int {Int(size)}}
enum Alignment {case center}
enum ControlState {case normal}
enum ControlEvent {case touchUpInside}
class UIView {
    var subviews:[UIView]=[];var frame=CGRect.zero
    func addSubview(_ view:UIView){subviews.append(view)}
}
class UILabel:UIView {var font:Int?;var textColor:UIColor?;var textAlignment=Alignment.center;var text:String?;var accessibilityLabel:String?}
class UIButton:UIView {
    enum ButtonType {case system};let titleLabel:UILabel?=UILabel();var tintColor:UIColor?;var action:(()->Void)?;var text:String?
    init(type:ButtonType) {}
    func setTitle(_ value:String,for state:ControlState){text=value}
    func addTarget(_ target:AnyObject,action:@escaping()->Void,for event:ControlEvent){self.action=action}
}
class UIProgressView:UIView {
    enum ProgressViewStyle {case `default`};var progressTintColor:UIColor?;var trackTintColor:UIColor?;var progress:Float=0
    init(progressViewStyle:ProgressViewStyle) {}
    func setProgress(_ value:Float,animated:Bool){progress=value}
}
class ASDisplayNode {let view=UIView();var backgroundColor:UIColor?;var cornerRadius:CGFloat=0;var frame=CGRect.zero;var children:[ASDisplayNode]=[];func addSubnode(_ node:ASDisplayNode){children.append(node)}}
struct ContainerViewLayout {var size:CGSize}
enum ContainedViewLayoutTransition {case immediate}
final class StatusBar {enum Style {case Ignore};var statusBarStyle=Style.Ignore}
class ViewController {
    var title:String?;var displayNode=ASDisplayNode();let statusBar=StatusBar();var presentingViewController:ViewController?;var dismissCount=0
    init(navigationBarPresentationData:Any?) {}
    required init(coder:NSCoder) {}
    func loadDisplayNode() {}
    func displayNodeDidLoad() {}
    func containerLayoutUpdated(_ layout:ContainerViewLayout,transition:ContainedViewLayoutTransition) {}
    func dismiss(completion:(()->Void)?=nil){completion?()}
    func dismiss(animated:Bool,completion:(()->Void)?=nil){dismissCount+=1;completion?()}
}
// PRODUCTION_PROGRESS
@main struct ProgressTests {
    static func main() {
        var checks=0
        func check(_ value:@autoclosure()->Bool,_ label:String){if !value(){fatalError("Copy progress regression: "+label)};checks+=1}
        var cancellations=0
        let progress=NagramiXCopyProgressController(background:UIColor(),foreground:UIColor(),accent:UIColor(),title:"Abbrechen",language:"de",cancelled:{cancellations+=1})
        progress.updateProgress(0.35);progress.loadDisplayNode()
        progress.containerLayoutUpdated(.init(size:CGSize(width:390,height:844)),transition:.immediate)
        let panel=progress.displayNode.children[0]
        let label=panel.view.subviews.compactMap{$0 as? UILabel}[0]
        let indicator=panel.view.subviews.compactMap{$0 as? UIProgressView}[0]
        let button=panel.view.subviews.compactMap{$0 as? UIButton}[0]
        check(indicator.progress==0.35,"progress received before presentation survives node creation")
        let formatter=NumberFormatter();formatter.locale=Locale(identifier:"de");formatter.numberStyle = .percent;formatter.maximumFractionDigits=0
        check(label.text==formatter.string(from:0.35),"percentage uses selected language")
        check(button.text=="Abbrechen" && panel.frame.width==260,"localized cancel and compact native geometry")
        progress.updateProgress(2);check(indicator.progress==1,"progress clamped")
        let presenter=ViewController(navigationBarPresentationData:nil);progress.presentingViewController=presenter
        button.action?();progress.dismiss()
        check(cancellations==1 && presenter.dismissCount==1,"cancel callback and dismissal occur once")
        print("Copy progress UI boundary checks: \(checks)")
    }
}
