"""Полные density node/glass/control против реальных UIKit и Legacy header."""
import subprocess,sys
from pathlib import Path
from validate_quick_format import block
from snow_density_glass_runtime import ROOT,production,SETTINGS

HEADER='submodules/LegacyComponents/PublicHeaders/LegacyComponents/TGPhotoEditorSliderView.h'

def check(source,swiftc,folder):
    if sys.platform!='darwin':
        return {'status':'not_run','reason':'UIKit/UIGlassEffect/Objective-C require macOS+iPhoneOS SDK; local runtime uses explicit adapters.'}
    folder.mkdir(parents=True,exist_ok=True)
    code=(ROOT/'scripts/tests/NagramiXSnowDensityGlassBoundary.swift').read_text()
    code+='\nenum NagramiXSnowSettings {\n'+block((source/SETTINGS).read_text(),'    public static func normalizedDensity(')+'\n}\n'+production(source)
    path=folder/'density-real-uikit.swift';path.write_text(code)
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    result=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-typecheck','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),'-import-objc-header',str(source/HEADER),str(path)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+result.stderr
    return {'status':'passed','scope':'Entire actual density node + geometry + glass view + Legacy subclass; real UIKit/QuartzCore/CoreGraphics/UIGlassEffect/renderer and original ObjC Legacy header at iOS15 target. List/theme/Display boundaries explicit. No physical rendering or touch acceptance.'}
