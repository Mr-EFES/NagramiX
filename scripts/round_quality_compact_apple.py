"""Вся страница/стекло с реальными UIKit и публичными Core/MediaSettings."""
import subprocess,sys
from round_bitrate_levels_apple import check as bitrate_check
from round_bitrate_levels_runtime import U,M,G

def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    previous=bitrate_check(source,swiftc,folder/'bitrate')
    report={'unchanged_bitrate_and_model':previous,'complete_page_uikit':{'status':'not_run','reason':'Linux без UIKit/iPhoneOS SDK'},'full_application_sdk':'not_run','physical_iphone':'pending'}
    if sys.platform!='darwin':return report
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache')]
    code='''import UIKit
import NagramiXCore
import NagramiXMediaSettings
struct FixtureLanguage {let languageCode:String}
struct PresentationStrings {
 var primaryComponent:FixtureLanguage{FixtureLanguage(languageCode:"ru")}
 func nagramiXUILocalized(_ key:String)->String{key}
 func nagramiXLocalized(_ key:String)->String{key}
}
struct ListTheme {
 var itemSecondaryTextColor:UIColor{.secondaryLabel};var itemPrimaryTextColor:UIColor{.label}
 var itemBlocksBackgroundColor:UIColor{.secondarySystemGroupedBackground};var blocksBackgroundColor:UIColor{.systemGroupedBackground}
 var itemAccentColor:UIColor{.systemPurple};var itemBlocksSeparatorColor:UIColor{.separator};var sectionHeaderTextColor:UIColor{.secondaryLabel}
}
struct FixtureStyle {let style=0}
struct RootTheme {let statusBarStyle=FixtureStyle()}
struct Theme {let list=ListTheme(),rootController=RootTheme();let overallDarkAppearance=true}
struct ListFontSize {let itemListBaseFontSize:CGFloat=17,itemListBaseHeaderFontSize:CGFloat=13}
struct PresentationData {let strings=PresentationStrings(),theme=Theme(),listsFontSize=ListFontSize()}
enum Font {static func regular(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size)}}
struct NavigationBarPresentationData {init(presentationData:PresentationData){}}
struct FixtureData {func with(_ f:(PresentationData)->PresentationData)->PresentationData{f(PresentationData())}}
struct SharedContext {let currentPresentationData=FixtureData()}
struct AccountContext {let sharedContext=SharedContext()}
final class ASDisplayNode {let view=UIView();var backgroundColor:UIColor?{get{view.backgroundColor}set{view.backgroundColor=newValue}}}
struct ContainerViewLayout {let size:CGSize;let intrinsicInsets:UIEdgeInsets}
enum ContainedViewLayoutTransition {case immediate}
struct NavigationLayout {let navigationFrame:CGRect}
class ViewController:UIViewController {
 final class StatusBar {var statusBarStyle=0}
 let statusBar=StatusBar();var displayNode:ASDisplayNode!
 init(navigationBarPresentationData:NavigationBarPresentationData){super.init(nibName:nil,bundle:nil)}
 required init?(coder:NSCoder){fatalError()}
 func loadDisplayNode(){}
 func displayNodeDidLoad(){}
 func containerLayoutUpdated(_ layout:ContainerViewLayout,transition:ContainedViewLayoutTransition){}
 func navigationLayout(layout:ContainerViewLayout)->NavigationLayout{NavigationLayout(navigationFrame:.zero)}
}
enum NagramiXCinematicCapture {static func supports(_ value:NagramiXRoundVideoSettings)->Bool{false}}
'''
    code+='\n'.join(line for line in (source/U).read_text().splitlines() if not line.startswith('import '))
    path=folder/'compact-real-uikit.swift';path.write_text(code)
    result=subprocess.run(common+['-typecheck','-I',str(folder/'bitrate'),str(path)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+result.stderr
    report['complete_page_uikit']={'status':'passed','target':'arm64-apple-ios15.0','scope':'Entire actual page, button, glass/blur fallback, constraints, table delegate/init and bitrate cell. Real UIKit and public Core/MediaSettings modules. Presentation/Texture/Display/controller/account/camera capability are explicit hosts; native app/pixels/device not verified.'}
    return report
