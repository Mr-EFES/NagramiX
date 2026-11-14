"""Actual font enum + ItemListUI public extension exported/imported as Swift modules."""
import subprocess
from pathlib import Path
from validate_quick_format import block
import font_license_compact_runtime as runtime
NATIVE='submodules/TelegramUIPreferences/Sources/PresentationThemeSettings.swift'

def check(source,swiftc,folder):
 folder.mkdir(parents=True,exist_ok=True)
 common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'cache'),'-I',str(folder)]
 def run(arguments,expected=True):
  result=subprocess.run(common+arguments,capture_output=True,text=True,timeout=120)
  assert (result.returncode==0)==expected,result.stdout+result.stderr
  return result
 enum=block((source/NATIVE).read_text(),'public enum PresentationFontSize: Int32, CaseIterable {')
 extension=block((source/runtime.ITEM).read_text(),'public extension PresentationFontSize {')
 font=folder/'PresentationFontSize.swift';font.write_text('import Foundation\n'+enum+'\n')
 run(['-emit-module','-module-name','TelegramUIPreferences','-emit-module-path',str(folder/'TelegramUIPreferences.swiftmodule'),str(font)])
 item=folder/'ItemListFontSize.swift';item.write_text('import Foundation\n#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\nimport TelegramUIPreferences\n'+extension+'\n')
 run(['-emit-module','-module-name','ItemListUI','-emit-module-path',str(folder/'ItemListUI.swiftmodule'),str(item)])
 code='import Foundation\nimport TelegramUIPreferences\nimport ItemListUI\nstruct ActualPresentationBoundary {let listsFontSize:PresentationFontSize}\nfunc actualReaderSize(presentation:ActualPresentationBoundary) {\n'
 license=block((source/runtime.UI).read_text(),'private final class NagramiXFontLicensesController:')
 call=next(line.strip() for line in license.splitlines() if 'let base = presentation.listsFontSize.' in line)
 code+=call+'\n_ = base\n}\n';consumer=folder/'FontLicenseSizeConsumer.swift';consumer.write_text(code)
 run(['-typecheck',str(consumer)])
 consumer.write_text(code.replace('import ItemListUI\n','',1));result=run(['-typecheck',str(consumer)],False)
 assert 'itemListBaseHeaderFontSize' in result.stderr and 'no member' in result.stderr,result.stderr
 return {'status':'passed','actual_native_type':NATIVE,'actual_extension':runtime.ITEM,'actual_caller':call,'exported_modules':['TelegramUIPreferences','ItemListUI'],'positive_import':'passed','missing_itemlist_import':'rejected','scope':'Real Swift module export/import and actual source getter/enum/call; Foundation/CGFloat boundary, not full SettingsUI or UIKit application compilation.'}
