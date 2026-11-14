"""Реальный UIKit SDK: публичный Core module и все потребители до компиляции приложения."""
import subprocess,sys
from pathlib import Path
import settings_glass_sliders_runtime as runtime
ROOT=Path(__file__).resolve().parents[1]
HEADER='submodules/LegacyComponents/PublicHeaders/LegacyComponents/TGPhotoEditorSliderView.h'

def check(source,swiftc,folder):
 if sys.platform!='darwin':return {'status':'not_run','reason':'Public UIKit module and Objective-C importer require macOS+iPhoneOS SDK. Linux tests use explicit UI boundaries.'}
 folder.mkdir(parents=True,exist_ok=True)
 sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
 common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache')]
 def run(args):
  result=subprocess.run(common+args,capture_output=True,text=True,timeout=180)
  assert result.returncode==0,result.stdout+result.stderr
 run(['-emit-module','-module-name','NagramiXCore','-emit-module-path',str(folder/'NagramiXCore.swiftmodule'),str(source/runtime.C)])
 # Compile outside the defining module: public access and inherited UIKit APIs
 # cannot be satisfied by the Linux fixture's declaration adapters.
 consumer=folder/'slider-consumers.swift'
 consumer.write_text('import NagramiXCore\n'+runtime.boundary(source)+'\n'+runtime.production(source,include_core=False))
 run(['-typecheck','-I',str(folder),'-import-objc-header',str(source/HEADER),str(consumer)])
 return {'status':'passed','target':'arm64-apple-ios15.0','scope':'Actual public Core glass/geometry/UISlider module, complete actual snow and percentage nodes/Legacy wrapper/round bitrate cell, actual ASR temperature branch and translation configure/render/change methods in an external consumer module. Real UIKit, UIGraphicsImageRenderer, UIGlassEffect and native Legacy ObjC header. Explicit List/theme/model hosts; no physical rendering or full app build.'}
