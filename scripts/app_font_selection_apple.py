"""Ранний typecheck новых production шрифтов/экрана против реального UIKit SDK."""
from pathlib import Path
import subprocess,sys
from app_font_selection_runtime import MODEL,FONT,MANAGER,UI

def access_check(source,swiftc,folder):
    """Actual public override signature must use public adapter types too."""
    ui=(source/UI).read_text()
    signature=next(line.strip() for line in ui.splitlines() if 'public override func containerLayoutUpdated(' in line)
    signature=signature[:signature.index('{')+1]+'}\n'
    declarations='\n'.join(next(line for line in UI_BOUNDARY.splitlines() if line.startswith('public struct '+name+' ')) for name in ['ContainerViewLayout','ContainedViewLayoutTransition'])
    code='import Foundation\nstruct UIEdgeInsets {static let zero=Self()}\n'+declarations+'''
public class NativeViewControllerBoundary {
 func containerLayoutUpdated(_ layout:ContainerViewLayout,transition:ContainedViewLayoutTransition){}
}
public final class ActualFontOverrideBoundary:NativeViewControllerBoundary {
'''+signature+'}\n'
    checks=[]
    for name,body,expected in [('public-types',code,True),('internal-layout',code.replace('public struct ContainerViewLayout','struct ContainerViewLayout',1),False),('internal-transition',code.replace('public struct ContainedViewLayoutTransition','struct ContainedViewLayoutTransition',1),False)]:
        path=folder/(name+'.swift');path.write_text(body)
        result=subprocess.run([str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-module-cache-path',str(folder/'access-cache'),str(path)],capture_output=True,text=True,timeout=60)
        assert (result.returncode==0)==expected,result.stdout+result.stderr
        if not expected: assert 'parameter uses an internal type' in result.stderr,result.stderr
        checks.append({'name':name,'expected_result':'passed' if expected else 'rejected','verified':True})
    return checks

def check(source,swiftc,folder):
    if sys.platform!='darwin':return {'status':'not_run','reason':'Apple UIKit SDK unavailable on Linux'}
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    clean=lambda text:'\n'.join(line for line in text.splitlines() if not line.startswith('import '))
    code='import Foundation\nimport UIKit\nimport CoreText\nimport ObjectiveC\n'+SIGNAL_BOUNDARY+'\n'+UI_BOUNDARY
    code+='\n'+'\n'.join(clean((source/n).read_text()) for n in [MODEL,FONT,MANAGER,UI])
    path=folder/'fonts-real-uikit.swift';path.write_text(code)
    command=[str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'sdk-cache'),str(path)]
    p=subprocess.run(command,capture_output=True,text=True,timeout=120)
    assert p.returncode==0,p.stdout+p.stderr
    return {'status':'passed','target':'arm64-apple-ios15.0','scope':'Complete actual model, Font.swift, resolver, Objective-C hooks and font-screen bodies; real UIKit/CoreText/Foundation/ObjectiveC APIs. Display/AccountContext/theme and SignalKit ownership interfaces are explicit adapters, whole native modules still require SDK build.'}

SIGNAL_BOUNDARY=r'''
public enum NoError{}
protocol Disposable {func dispose()}
final class ActionDisposable:Disposable {init(_ action:@escaping()->Void){};func dispose(){}}
final class MetaDisposable:Disposable {func set(_ value:Disposable?){};func dispose(){}}
final class Subscriber<V,E>{func putNext(_ value:V){}}
public final class Signal<V,E>{init(_ generator:@escaping(Subscriber<V,E>)->Disposable){};func start(next:@escaping(V)->Void)->Disposable{ActionDisposable{}}}
infix operator |> : AdditionPrecedence
func |> <A,B>(value:A,f:(A)->B)->B {f(value)}
func distinctUntilChanged<V:Equatable,E>(_ value:Signal<V,E>)->Signal<V,E>{value}
func deliverOnMainQueue<V,E>(_ value:Signal<V,E>)->Signal<V,E>{value}
'''
UI_BOUNDARY=r'''
struct PresentationStrings {
 func nagramiXLocalized(_ key:String)->String{key}
}
struct ListTheme {
 var blocksBackgroundColor=UIColor.black;var itemBlocksBackgroundColor=UIColor.gray
 var itemBlocksSeparatorColor=UIColor.gray;var itemPrimaryTextColor=UIColor.white
 var itemSecondaryTextColor=UIColor.gray;var itemAccentColor=UIColor.blue
}
struct PresentationTheme {var list=ListTheme();var overallDarkAppearance=true}
struct ListFontSize {var itemListBaseFontSize:CGFloat=17}
final class PresentationData {var strings=PresentationStrings();var theme=PresentationTheme();var listsFontSize=ListFontSize()}
struct PresentationAtomic {func with<T>(_ f:(PresentationData)->T)->T{f(PresentationData())}}
struct FontSharedContext {var currentPresentationData=PresentationAtomic();var presentationData=Signal<PresentationData,NoError>{_ in ActionDisposable{}}}
public final class AccountContext {var sharedContext=FontSharedContext()}
struct NavigationBarPresentationData {init(presentationData:PresentationData){}}
final class NavigationBar {func updatePresentationData(_ data:NavigationBarPresentationData){}}
class ASDisplayNode {var view=UIView();var backgroundColor:UIColor?{get{view.backgroundColor}set{view.backgroundColor=newValue}}}
public struct ContainerViewLayout {var size=CGSize.zero;var intrinsicInsets=UIEdgeInsets.zero}
public struct ContainedViewLayoutTransition {}
struct NavigationLayout {var navigationFrame=CGRect.zero}
public class ViewController:UIViewController {
 var displayNode=ASDisplayNode();var navigationBar:NavigationBar?;var isNodeLoaded:Bool{false}
 init(navigationBarPresentationData:NavigationBarPresentationData){super.init(nibName:nil,bundle:nil)}
 public required init(coder:NSCoder){fatalError()}
 func loadDisplayNode(){}
 func displayNodeDidLoad(){}
 func containerLayoutUpdated(_ layout:ContainerViewLayout,transition:ContainedViewLayoutTransition){}
 func navigationLayout(layout:ContainerViewLayout)->NavigationLayout{NavigationLayout()}
 func push(_ controller:ViewController){}
}
'''
