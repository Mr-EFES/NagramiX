"""Real settings-module import; UIKit-backed API probes on Apple, never claimed on Linux."""
from pathlib import Path
import subprocess,sys
from validate_quick_format import block
import feature_photo_policy_runtime as photo
import feature_transcription_master_runtime as transcription
import feature_wide_post_envelope_runtime as wide


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    flags=[]
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        flags=['-sdk',sdk,'-target','arm64-apple-ios15.0']
    base=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'cache'),*flags]
    module=folder/'NagramiXMediaSettings.swiftmodule'
    def run(args):
        r=subprocess.run(base+args,capture_output=True,text=True,timeout=180)
        assert r.returncode==0,r.stdout+r.stderr
    run(['-parse-as-library','-emit-module','-module-name','NagramiXMediaSettings','-emit-module-path',str(module),str(source/photo.MEDIA)])
    caller=folder/'photo-settings-api.swift'
    caller.write_text('import NagramiXMediaSettings\nfunc photoPolicy(_ value:NagramiXMediaSettings)->(Int32,Bool,Double){(value.outgoingPhotoQuality,value.outgoingPhotoHD,value.jpegQuality)}\n')
    run(['-typecheck','-I',str(folder),str(caller)])
    report={'actual_settings_module_and_imported_photo_getters':'passed','uikit_api_probes':'not_run','full_application_sdk':'pending','device':'pending'}
    if sys.platform!='darwin':
        report['reason']='UIKit/iOS SDK unavailable on Linux; no device or framework success inferred.'
        return report
    photo_code=photo.fixture(source)
    photo_code=photo_code.replace(block(photo_code,'public struct NagramiXMediaSettings:'),'',1)
    photo_code=photo_code.replace(block(photo_code,'final class UIImage {'),' ',1)
    photo_code=photo_code.replace(block(photo_code,'func TGScaleImageToPixelSize('),'func TGScaleImageToPixelSize(_ image:UIImage,_ size:CGSize)->UIImage?{image}',1)
    photo_code=photo_code.replace('UIImage(CGSize(width:4000,height:3000))','UIImage()')
    photo_code='import UIKit\nimport NagramiXMediaSettings\n'+photo_code
    wide_code=wide.fixture(source)
    wide_code=wide_code.replace('class ASDisplayNode {\n var frame=CGRect.zero;','class ASDisplayNode:UIView {\n ')
    wide_code=wide_code.replace(' static func main()', ' @MainActor static func main()')
    wide_code='import UIKit\n'+wide_code
    asr_code=transcription.fixture(source)
    asr_code=asr_code.replace(block(asr_code,'enum UIApplication {'),' ',1)
    asr_code='import UIKit\n'+asr_code
    for name,code in [('photo-policy-uikit',photo_code),('wide-envelope-uikit',wide_code),('transcription-master-uikit',asr_code)]:
        path=folder/(name+'.swift');path.write_text(code)
        run(['-typecheck','-parse-as-library','-I',str(folder),str(path)])
    report['uikit_api_probes']='passed: actual new production helpers/callers against real UIKit image/view/notification/geometry types; Telegram, native background, ASDisplayNode and engine edges remain explicit adapters, not full target linkage.'
    return report
