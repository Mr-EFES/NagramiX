"""Проверка публичной модели и полного нового sheet с настоящим UIKit на Apple."""
from pathlib import Path
import subprocess,sys
from validate_quick_format import block
import round_quality_summary_runtime as runtime
from round_editor_quality_apple import check as settings_check
ROOT=Path(__file__).resolve().parents[1]

def check(source,swiftc,folder):
 folder.mkdir(parents=True,exist_ok=True)
 model=settings_check(source,swiftc,folder/'model')
 result={'actual_model_and_copy':model,'complete_sheet_uikit':{'status':'not_run','reason':'macOS/iPhoneOS SDK required'},'full_application_sdk':'not_run','physical_iphone':'pending'}
 if sys.platform!='darwin':return result
 sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
 common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache')]
 protocol=block((source/runtime.menus.G).read_text(),'public protocol NagramiXGlassActionSheetItem:')
 producer=folder/'Display.swift';producer.write_text(protocol+'\n')
 def run(args):
  p=subprocess.run(common+[str(a) for a in args],capture_output=True,text=True,timeout=180);assert p.returncode==0,p.stdout+p.stderr
 run(['-emit-module','-module-name','Display','-emit-module-path',folder/'Display.swiftmodule',producer])
 boundary=(ROOT/'scripts/tests/NagramiXUnifiedMenusAppleBoundary.swift').read_text()
 shared=(ROOT/'scripts/tests/NagramiXUnifiedMenusBoundary.swift').read_text();shared=shared[shared.index('protocol ActionSheetItem '):]
 code=boundary+'\n'+shared+'''\nclass ActionSheetItemGroupNode {}
struct FixtureComponent {let languageCode:String}
extension PresentationStrings {
 var UserInfo_NotificationsDefault:String {"Default"}
 var primaryComponent:FixtureComponent {FixtureComponent(languageCode:"en")}
 func nagramiXUILocalized(_ value:String)->String {value}
}
struct MediaEditorValues {var nagramiXRoundTuning:[Int]?}
'''+runtime.menus.body((source/runtime.N).read_text())
 for path,marker in [('submodules/NagramiXCore/Sources/NagramiXTabSettings.swift','public enum NagramiXDnsProvider:'),('submodules/NagramiXCore/Sources/NagramiXTypingSettings.swift','public enum NagramiXTypingPreset:'),('submodules/NagramiXMediaSettings/Sources/NagramiXDownloadSettings.swift','public enum NagramiXDownloadAcceleration:')]:code+=block((source/path).read_text(),marker)+'\n'
 p=folder/'round-quality-real-uikit.swift';p.write_text(code);run(['-typecheck','-I',folder,p])
 result['complete_sheet_uikit']={'status':'passed','target':'arm64-apple-ios15.0','scope':'Complete actual rows/factory/item/node, real UIKit/Foundation/UIFont/SF Symbols/geometry/selector/accessibility; actual Display marker exported across a real Swift module. Texture/controller/presentation/strings/value hosts explicit; not full app or pixels.'}
 return result
