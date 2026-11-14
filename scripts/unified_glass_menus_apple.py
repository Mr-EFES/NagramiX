"""Actual public Display protocol + complete picker/group APIs on real UIKit."""
import subprocess,sys
from pathlib import Path
from validate_quick_format import block
import unified_glass_menus_runtime as runtime

def modules_check(source,swiftc,folder):
 folder.mkdir(parents=True,exist_ok=True)
 protocol=block((source/runtime.G).read_text(),'public protocol NagramiXGlassActionSheetItem:')
 path=folder/'Display.swift';path.write_text(protocol+'\n')
 common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'cache')]
 def run(args,expected=True):
  p=subprocess.run(common+args,capture_output=True,text=True,timeout=120);assert (p.returncode==0)==expected,p.stdout+p.stderr;return p
 run(['-emit-module','-module-name','Display','-emit-module-path',str(folder/'Display.swiftmodule'),str(path)])
 consumer=folder/'SettingsUI.swift';consumer.write_text('import Display\nfinal class ActualMarkerWitness:NagramiXGlassActionSheetItem {var nagramiXUsesFloatingGlass:Bool{true}}\n')
 run(['-typecheck','-I',str(folder),str(consumer)])
 path.write_text(protocol.replace('public protocol','protocol',1)+'\n');run(['-emit-module','-module-name','Display','-emit-module-path',str(folder/'Display.swiftmodule'),str(path)])
 result=run(['-typecheck','-I',str(folder),str(consumer)],False);assert 'NagramiXGlassActionSheetItem' in result.stderr
 return {'status':'passed','actual_public_display_protocol':'exported and consumed by separate SettingsUI Swift module','internal_protocol_negative':'rejected','scope':'Real Swift access/import compilation; not the full Display/SettingsUI modules or app SDK.'}

def check(source,swiftc,folder):
 if sys.platform!='darwin':return {'status':'not_run','reason':'Real UIKit/UIGlassEffect require macOS+iPhoneOS SDK; Linux executes explicit UI/Texture adapters.'}
 folder.mkdir(parents=True,exist_ok=True)
 sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
 common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache')]
 protocol=block((source/runtime.G).read_text(),'public protocol NagramiXGlassActionSheetItem:')
 p=folder/'Display.swift';p.write_text(protocol+'\n')
 run=lambda args:subprocess.run(common+args,capture_output=True,text=True,timeout=180)
 result=run(['-emit-module','-module-name','Display','-emit-module-path',str(folder/'Display.swiftmodule'),str(p)]);assert result.returncode==0,result.stdout+result.stderr
 boundary=(runtime.ROOT/'scripts/tests/NagramiXUnifiedMenusAppleBoundary.swift').read_text()
 shared=(runtime.ROOT/'scripts/tests/NagramiXUnifiedMenusBoundary.swift').read_text();shared=shared[shared.index('protocol ActionSheetItem '):]
 code=boundary+'\n'+shared+'\n'
 for path,marker in [('submodules/NagramiXCore/Sources/NagramiXTabSettings.swift','public enum NagramiXDnsProvider:'),('submodules/NagramiXCore/Sources/NagramiXTypingSettings.swift','public enum NagramiXTypingPreset:'),('submodules/NagramiXMediaSettings/Sources/NagramiXDownloadSettings.swift','public enum NagramiXDownloadAcceleration:')]:code+=block((source/path).read_text(),marker)+'\n'
 code+=runtime.production(source).replace(protocol,'',1)
 p=folder/'menus-real-uikit.swift';p.write_text(code);result=run(['-typecheck','-I',str(folder),str(p)]);assert result.returncode==0,result.stdout+result.stderr
 return {'status':'passed','target':'arm64-apple-ios15.0','scope':'Complete actual option factory/items/node, full native group/mask/glass code, actual insets getters and all three caller closures. Genuine UIKit, UIImage symbols/palette, UIGlassEffect/blur, CoreAnimation and separate actual public Display protocol. Texture/presentation/settings hosts explicit; no full app or physical pixel claim.'}
