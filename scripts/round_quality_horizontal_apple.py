"""Вся текущая страница на реальном UIKit; старый gallery API не подменяется."""
import subprocess,sys
from validate_private_temporary_transcription import save_failed_fixture
from round_bitrate_levels_runtime import U,M,G

PAGE_HOST = '''import UIKit
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
enum Font {
 static func regular(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size)}
 static func semibold(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size,weight:.semibold)}
}
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


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    page=folder/'horizontal-page-real-uikit.swift'
    page.write_text(PAGE_HOST+'\n'+'\n'.join(l for l in (source/U).read_text().splitlines() if not l.startswith('import ')))
    parsed=subprocess.run([str(swiftc),'-frontend','-parse',str(page)],capture_output=True,text=True)
    if parsed.returncode:save_failed_fixture(page,'horizontal-page-api','syntax','parse',parsed)
    assert parsed.returncode==0,parsed.stdout+parsed.stderr
    report={'complete_page_probe_parse':'passed','complete_page_uikit':'not_run','full_application_sdk':'not_run','pixels':'not_run','physical_iphone':'pending'}
    if sys.platform!='darwin':
        report['reason']='Linux without UIKit/iPhoneOS SDK. Foundation controls/model run separately; no historical gallery helper fixture is used.'
        return report
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache')]
    def run(args):
        p=subprocess.run(common+[str(a) for a in args],capture_output=True,text=True,timeout=180)
        if p.returncode:save_failed_fixture(page,'horizontal-page-api','iphoneos','typecheck',p)
        assert p.returncode==0,p.stdout+p.stderr
    run(['-emit-module','-module-name','NagramiXCore','-emit-module-path',folder/'NagramiXCore.swiftmodule',source/G])
    run(['-emit-module','-module-name','NagramiXMediaSettings','-emit-module-path',folder/'NagramiXMediaSettings.swiftmodule',source/M])
    run(['-typecheck','-I',folder,page])
    report['complete_page_uikit']='passed: entire actual page, scroll/layout guides, button, table, glass fallback and bitrate. Real public Core/MediaSettings modules and UIKit; Telegram presentation/Texture/controller/account/camera capability are explicit hosts.'
    return report
