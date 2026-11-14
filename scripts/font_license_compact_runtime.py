"""Полный actual license controller/formatter/TextKit view, с явными host границами."""
from pathlib import Path
from validate_quick_format import block
ROOT=Path(__file__).resolve().parents[1]
UI='submodules/SettingsUI/Sources/NagramiXFontsController.swift'
MODEL='submodules/NagramiXMediaSettings/Sources/NagramiXFontSettings.swift'
ITEM='submodules/ItemListUI/Sources/ItemListItem.swift'
RESOURCE='submodules/Display/Resources/NagramiXFonts/'
DOCUMENTS=[('PT Astra Sans','PTAstraSans-LICENSE.txt'),('PT Astra Serif','PTAstraSerif-LICENSE.txt'),('Roboto · NOTICE','Roboto-NOTICE.txt'),('Roboto · Apache License 2.0','Roboto-LICENSE.txt')]
MARKERS=['private final class NagramiXFontLicensesController:','private struct NagramiXFontLicenseSeparator {','private struct NagramiXFontLicenseDocument {','private final class NagramiXFontLicenseTextView:']
def production(source):
 text=(source/UI).read_text()
 return '\n'.join(block(text,marker) for marker in MARKERS)
def boundary(source):
 text=(ROOT/'scripts/tests/NagramiXFontLicenseCompactBoundary.swift').read_text()
 native=block((source/ITEM).read_text(),'    var itemListBaseHeaderFontSize: CGFloat {')
 text=text.replace('/* ACTUAL HEADER SIZE */',native)
 text+='\n'+block((source/MODEL).read_text(),'public enum NagramiXFontLicenseLayout {')+'\n'
 from validate_upstream_13_2_release import checked_plan,OVERLAY
 import hashlib
 plan=checked_plan('font_license_compact')
 docs=[]
 for name,file in DOCUMENTS:
  relative=RESOURCE+file;path=source/relative
  # Early canonical projections contain Swift only. Read the exact guarded
  # resource template there; full-source contracts separately require files.
  data=path.read_bytes() if path.is_file() else (OVERLAY/plan['guard_sources'][relative]).read_bytes()
  assert hashlib.sha256(data).hexdigest()==plan['guards'][relative],relative
  docs.append((name,data.decode('utf8')))
 import json
 text+='\nenum NagramiXFontManager {static var licenseDocuments:[(name:String,text:String)]=['+','.join('('+json.dumps(a,ensure_ascii=False)+','+json.dumps(b,ensure_ascii=False)+')' for a,b in docs)+']}\n'
 return text

def fixture(source):
 return boundary(source)+'\n'+production(source).replace('private ','fileprivate ')+'\n'+(ROOT/'scripts/tests/NagramiXFontLicenseCompactTests.swift').read_text()
