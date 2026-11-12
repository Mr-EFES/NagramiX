"""Проверить реальные theme/status типы и новый bitmap helper против UIKit."""
import hashlib,json,subprocess,sys
from pathlib import Path
from validate_quick_format import block

ROOT=Path(__file__).resolve().parents[1]
STATUS='submodules/Display/Source/StatusBarProxyNode.swift'
THEME='submodules/TelegramPresentationData/Sources/PresentationTheme.swift'
SETTINGS='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'


def native_types(source):
    plan=json.loads((ROOT/'ios/font_theme_contrast_patches.json').read_text())
    for name in [STATUS,THEME,'submodules/Display/Source/StatusBar.swift','submodules/Display/Source/ViewController.swift']:
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==plan['guards'][name],name
    status=block((source/STATUS).read_text(),'public enum StatusBarStyle {')
    # Native enum cases form the nominal Display boundary. Its unrelated
    # deprecated UIKit conversion initializer is compiled by the full SDK build.
    cases='\n'.join(x for x in status.splitlines() if x.strip().startswith('case ') and ':' not in x)
    native=block((source/THEME).read_text(),'public enum PresentationThemeStatusBarStyle: Int32 {')
    assert 'public var statusBarStyle: StatusBarStyle {' in (source/'submodules/Display/Source/StatusBar.swift').read_text()
    assert 'public let statusBar: StatusBar' in (source/'submodules/Display/Source/ViewController.swift').read_text()
    assert 'public let statusBarStyle: PresentationThemeStatusBarStyle' in (source/THEME).read_text()
    assert 'rootController: PresentationThemeRootController' in (source/THEME).read_text()
    return 'public enum StatusBarStyle {\n'+cases+'\n}\n'+native+'\n'


def theme_boundary(source, boundary):
    assert boundary.count('struct PresentationTheme {var list=ListTheme();var overallDarkAppearance=true}')==1
    assert boundary.count('public class ViewController:UIViewController {')==1
    boundary=boundary.replace('struct PresentationTheme {var list=ListTheme();var overallDarkAppearance=true}', 'struct FontRootTheme {var statusBarStyle=PresentationThemeStatusBarStyle.white}\nstruct PresentationTheme {var list=ListTheme();var rootController=FontRootTheme();var overallDarkAppearance=true}')
    boundary=boundary.replace('public class ViewController:UIViewController {','final class FontStatusBar {var statusBarStyle=StatusBarStyle.Black}\npublic class ViewController:UIViewController {\n var statusBar=FontStatusBar()')
    return native_types(source)+boundary


def icon_check(source,swiftc,folder):
    if sys.platform!='darwin':return {'status':'not_run','reason':'Real UIKit renderer typecheck requires Apple SDK'}
    helper=block((source/SETTINGS).read_text(),'private func nagramiXFontSettingsIcon(')
    code='import Foundation\nimport UIKit\n'+helper+'\n'
    path=folder/'font-icon-real-uikit.swift';path.write_text(code)
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    p=subprocess.run([str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'icon-sdk-cache'),str(path)],capture_output=True,text=True,timeout=60)
    assert p.returncode==0,p.stdout+p.stderr
    return {'status':'passed','target':'arm64-apple-ios15.0','scope':'Complete actual font icon helper with real UIImage/UIGraphicsImageRenderer APIs; no pixel/device execution'}


def member_check(source,swiftc,folder):
    from app_font_selection_apple import UI_BOUNDARY
    from validate_local_copy_delivery import run
    boundary=theme_boundary(source,UI_BOUNDARY)
    ui=(source/'submodules/SettingsUI/Sources/NagramiXFontsController.swift').read_text()
    line=next(x.strip() for x in ui.splitlines() if 'self.statusBar.statusBarStyle = self.presentation.' in x)
    code='import Foundation\n'+native_types(source)+'struct ListTheme {}\n'
    for marker in ['struct FontRootTheme {','struct PresentationTheme {','final class FontStatusBar {']:
        code+=block(boundary,marker)+'\n'
    code+='struct Data {var theme=PresentationTheme()}\nfinal class NativeMemberProbe {var statusBar=FontStatusBar();var presentation=Data();func refresh(){'+line+'}}'
    path=folder/'actual-font-theme-members.swift';path.write_text(code)
    run([swiftc,'-typecheck','-warnings-as-errors','-module-cache-path',folder/'member-cache',path])
    return {'status':'passed','scope':'Actual final font UIKit adapter root/status declarations with native enum cases/getter and actual caller; pixels not exercised'}
