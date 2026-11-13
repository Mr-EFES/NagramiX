"""Ранний typecheck новых production шрифтов/экрана против реального UIKit SDK."""
from pathlib import Path
import subprocess,sys,re
from app_font_selection_runtime import MODEL,FONT,MANAGER,UI

ACCESS_IMPORTS = 'import Foundation\n#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n'
NAVIGATION = 'submodules/Display/Source/NavigationBar.swift'
TRANSITION = 'submodules/Display/Source/ContainedViewLayoutTransition.swift'

def navigation_signature(source):
    lines=[line.strip() for line in (source/NAVIGATION).read_text().splitlines() if line.strip().startswith('func updatePresentationData(')]
    assert len(lines)==1,lines
    assert lines[0]=='func updatePresentationData(_ presentationData: NavigationBarPresentationData, transition: ContainedViewLayoutTransition)',lines
    assert 'public enum ContainedViewLayoutTransition {\n    case immediate\n' in (source/TRANSITION).read_text()
    return lines[0]

def navigation_check(source,swiftc,folder):
    """Compile the actual caller against the actual native protocol signature."""
    signature=navigation_signature(source)
    calls=[line.strip() for line in (source/UI).read_text().splitlines() if 'self.navigationBar?.updatePresentationData(' in line]
    expected = 2 if 'private func refreshLicense()' in (source/UI).read_text() else 1
    assert len(calls)==expected,calls
    assert all(', transition: .immediate)' in value for value in calls),calls
    call=calls[0]
    assert ', transition: .immediate)' in call,call
    prefix='''struct NavigationBarPresentationData {init(presentationData:Int){}}
enum ContainedViewLayoutTransition {case immediate}
final class NavigationBar {'''+signature+''' {}}
final class ActualFontScreenCall {
 var navigationBar:NavigationBar?=NavigationBar()
 func update(_ value:Int){
'''
    reports=[]
    cases=[('current',call,True),('sdk199-missing-transition',call.replace(', transition: .immediate','',1),False),('wrong-transition-label',call.replace('transition: .immediate','animation: .immediate',1),False)]
    for name,body,expected in cases:
        path=folder/(name+'.swift');path.write_text(prefix+body+'\n}}\n')
        result=subprocess.run([str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-module-cache-path',str(folder/'navigation-cache'),str(path)],capture_output=True,text=True,timeout=60)
        assert (result.returncode==0)==expected,result.stdout+result.stderr
        if not expected: assert 'transition' in result.stderr,result.stderr
        reports.append({'name':name,'expected_result':'passed' if expected else 'rejected','verified':True})
    return {'native_signature':signature,'actual_caller':call,'checks':reports}

def access_check(source,swiftc,folder):
    """Actual public override signature must use public adapter types too."""
    ui=(source/UI).read_text()
    signature=next(line.strip() for line in ui.splitlines() if 'public override func containerLayoutUpdated(' in line)
    signature=signature[:signature.index('{')+1]+'}\n'
    declarations='\n'.join(next(line for line in UI_BOUNDARY.splitlines() if line.startswith('public '+kind+' '+name+' ')) for kind,name in [('struct','ContainerViewLayout'),('enum','ContainedViewLayoutTransition')])
    code=ACCESS_IMPORTS+'struct UIEdgeInsets {static let zero=Self()}\n'+declarations+'''
public class NativeViewControllerBoundary {
 func containerLayoutUpdated(_ layout:ContainerViewLayout,transition:ContainedViewLayoutTransition){}
}
public final class ActualFontOverrideBoundary:NativeViewControllerBoundary {
'''+signature+'}\n'
    checks=[]
    for name,body,expected in [('public-types',code,True),('internal-layout',code.replace('public struct ContainerViewLayout','struct ContainerViewLayout',1),False),('internal-transition',code.replace('public enum ContainedViewLayoutTransition','enum ContainedViewLayoutTransition',1),False)]:
        path=folder/(name+'.swift');path.write_text(body)
        result=subprocess.run([str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-module-cache-path',str(folder/'access-cache'),str(path)],capture_output=True,text=True,timeout=60)
        assert (result.returncode==0)==expected,result.stdout+result.stderr
        if not expected: assert 'parameter uses an internal type' in result.stderr,result.stderr
        checks.append({'name':name,'expected_result':'passed' if expected else 'rejected','verified':True})
    return checks

def check(source,swiftc,folder,expect_ui_transition_error=False):
    if sys.platform!='darwin':return {'status':'not_run','reason':'Apple UIKit SDK unavailable on Linux'}
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    clean=lambda text:'\n'.join(line for line in text.splitlines() if not line.startswith('import '))
    boundary=UI_BOUNDARY
    ui=(source/UI).read_text();ui_contract=None
    if 'private final class NagramiXFontApplyNode: ASDisplayNode' in ui:
        from font_preview_apply_native import final_ui
        ui,ui_contract=final_ui(source)
    if 'self.statusBar.statusBarStyle =' in (source/UI).read_text():
        from font_theme_contrast_apple import theme_boundary
        boundary=theme_boundary(source,boundary)
    if 'NagramiXFontApplyNode' in (source/UI).read_text():
        boundary=preview_boundary(source,boundary)
    code='import Foundation\nimport UIKit\nimport CoreText\nimport ObjectiveC\n'+SIGNAL_BOUNDARY+'\n'+boundary
    code+='\nfinal class NavigationBar {'+navigation_signature(source)+' {}}\n'
    code+='\n'+'\n'.join(clean(ui if n==UI else (source/n).read_text()) for n in [MODEL,FONT,MANAGER,UI])
    path=folder/'fonts-real-uikit.swift';path.write_text(code)
    command=[str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'sdk-cache'),str(path)]
    p=subprocess.run(command,capture_output=True,text=True,timeout=120)
    if expect_ui_transition_error:
        # Stage41 is immutable historical input. It must reproduce SDK199's
        # exact native API failure; the final corrected stage44 is checked
        # positively here before overlay and again before the native build.
        errors=re.findall(r'^.*:\d+:\d+: error: (.*)$',p.stderr,re.M)
        assert p.returncode!=0 and errors==["missing argument for parameter 'transition' in call"],p.stdout+p.stderr
        return {'status':'expected_historical_failure_verified','diagnostic':errors[0],'final_corrected_screen':'mandatory positive check in release_095_fonts_compile'}
    assert p.returncode==0,p.stdout+p.stderr
    return {'status':'passed','target':'arm64-apple-ios15.0','font_ui_contract':ui_contract,'scope':'Complete actual model, Font.swift, resolver, Objective-C hooks and font-screen bodies; real UIKit/CoreText/Foundation/ObjectiveC APIs. Display/AccountContext/theme and SignalKit ownership interfaces are explicit adapters, whole native modules still require SDK build.'}

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
class ASDisplayNode {var view=UIView();var backgroundColor:UIColor?{get{view.backgroundColor}set{view.backgroundColor=newValue}}}
public struct ContainerViewLayout {var size=CGSize.zero;var intrinsicInsets=UIEdgeInsets.zero}
public enum ContainedViewLayoutTransition {case immediate}
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


def preview_boundary(source, boundary):
    """Adapt only app-owned interfaces; UIKit itself remains the real SDK."""
    from validate_upstream_13_2_release import checked_plan,OVERLAY
    import hashlib
    plan=checked_plan('font_preview_apply')
    names=['submodules/UIKitRuntimeUtils/Source/UIKitRuntimeUtils/UIBarButtonItem+Proxy.h',
           'submodules/AsyncDisplayKit/Source/PublicHeaders/AsyncDisplayKit/ASDisplayNode.h',
           'submodules/AsyncDisplayKit/Source/PublicHeaders/AsyncDisplayKit/ASDisplayNode+Subclasses.h',
           'submodules/Display/Source/ContainerViewLayout.swift',
           'submodules/TelegramPresentationData/Sources/PresentationTheme.swift']
    texts={}
    for name in names:
        path=source/name
        data=path.read_bytes() if path.exists() else (OVERLAY/plan['guard_sources'][name]).read_bytes()
        assert hashlib.sha256(data).hexdigest()==plan['guards'][name],name
        texts[name]=data.decode()
    assert '- (instancetype)initWithCustomDisplayNode:(ASDisplayNode *)customDisplayNode;' in texts[names[0]]
    assert '- (instancetype)initWithViewBlock:(ASDisplayNodeViewBlock)viewBlock;' in texts[names[1]]
    assert '- (CGSize)calculateSizeThatFits:(CGSize)constrainedSize;' in texts[names[2]]
    assert '- (void)invalidateCalculatedLayout;' in texts[names[2]]
    assert 'public var safeInsets: UIEdgeInsets' in texts[names[3]]
    assert 'public let itemCheckColors: PresentationThemeFillStrokeForeground' in texts[names[4]]
    boundary=boundary.replace('struct PresentationStrings {','struct PresentationStrings {\n var Theme_Context_Apply:String {"Apply"}',1)
    boundary=boundary.replace('struct ListTheme {','struct FontCheckColors {var foregroundColor=UIColor.white}\nstruct ListTheme {\n var itemCheckColors=FontCheckColors()',1)
    boundary=boundary.replace('var intrinsicInsets=UIEdgeInsets.zero}', 'var intrinsicInsets=UIEdgeInsets.zero;var safeInsets=UIEdgeInsets.zero}',1)
    boundary=boundary.replace('class ASDisplayNode {var view=UIView();', 'class ASDisplayNode {var view=UIView();init(){};init(viewBlock:()->UIView,didLoad:((ASDisplayNode)->Void)?){view=viewBlock()};convenience init(viewBlock:()->UIView){self.init(viewBlock:viewBlock,didLoad:nil)};var frame:CGRect{get{view.frame}set{view.frame=newValue}};func calculateSizeThatFits(_ constrainedSize:CGSize)->CGSize{.zero};func invalidateCalculatedLayout(){};',1)
    boundary+='\nextension UIBarButtonItem {convenience init?(customDisplayNode:ASDisplayNode){self.init()};var staysInRow:Bool{get{false}set{}}}\n'
    return boundary
