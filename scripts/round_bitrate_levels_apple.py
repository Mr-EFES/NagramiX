"""Публичная модель и полный bitrate cell с настоящими UIKit API до app SDK."""
import subprocess,sys
from validate_quick_format import block
import round_bitrate_levels_runtime as runtime
from round_editor_quality_apple import check as model_check

def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    result={'actual_model_and_copy':model_check(source,swiftc,folder/'model'),'complete_control_uikit':{'status':'not_run','reason':'iPhoneOS/UIKit SDK отсутствует на Linux'},'full_application_sdk':'not_run','physical_iphone':'pending'}
    if sys.platform!='darwin':return result
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache')]
    def run(args):
        p=subprocess.run(common+[str(a) for a in args],capture_output=True,text=True,timeout=180);assert p.returncode==0,p.stdout+p.stderr
    run(['-emit-module','-module-name','NagramiXCore','-emit-module-path',folder/'NagramiXCore.swiftmodule',source/runtime.G])
    run(['-emit-module','-module-name','NagramiXMediaSettings','-emit-module-path',folder/'NagramiXMediaSettings.swiftmodule',source/runtime.M])
    code='''import UIKit
import NagramiXCore
import NagramiXMediaSettings
struct FixtureLanguage {let languageCode:String}
struct PresentationStrings {
 var primaryComponent:FixtureLanguage {FixtureLanguage(languageCode:"ru")}
 func nagramiXLocalized(_ key:String)->String {key}
 func nagramiXUILocalized(_ key:String)->String {key}
}
struct ListFontSize {var itemListBaseFontSize:CGFloat{17}}
struct ListTheme {
 var itemSecondaryTextColor:UIColor{.secondaryLabel}
 var itemPrimaryTextColor:UIColor{.label}
 var itemBlocksBackgroundColor:UIColor{.secondarySystemGroupedBackground}
 var itemAccentColor:UIColor{.systemPurple}
}
struct Theme {var list:ListTheme{ListTheme()};var overallDarkAppearance:Bool{true}}
struct PresentationData {var strings:PresentationStrings{PresentationStrings()};var theme:Theme{Theme()};var listsFontSize:ListFontSize{ListFontSize()}}
enum Font {static func regular(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size)}}
func publicLevel(_ value:NagramiXRoundVideoSettings)->NagramiXRoundVideoSettings.BitRateLevel{value.bitRateLevel}
'''
    text=(source/runtime.U).read_text();code+=block(text,'func nagramiXRoundQualitySubtitle(')+'\n'+block(text,'private final class NagramiXRoundBitRateCell:')
    p=folder/'bitrate-real-uikit.swift';p.write_text(code);run(['-typecheck','-I',folder,p])
    result['complete_control_uikit']={'status':'passed','target':'arm64-apple-ios15.0','scope':'Actual Core glass control/public stepping, actual settings model/enum, complete bitrate cell and localized subtitle; real UIKit/AutoLayout/UISlider/VoiceOver APIs. Presentation/strings/theme/Font hosts explicit. No renderer, camera, server or full application claim.'}
    return result
