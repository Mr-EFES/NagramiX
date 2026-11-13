"""Реальная модель настроек и межфайловый вызов; UIKit gate только на Apple."""
from pathlib import Path
import subprocess,sys
from validate_quick_format import block
import round_editor_quality_runtime as runtime


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    flags=[]
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        flags=['-sdk',sdk,'-target','arm64-apple-ios15.0']
    command=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'cache'),*flags]
    def run(args):
        result=subprocess.run(command+args,capture_output=True,text=True,timeout=180)
        assert result.returncode==0,result.stdout+result.stderr
    run(['-emit-module','-parse-as-library','-module-name','NagramiXMediaSettings','-emit-module-path',str(folder/'NagramiXMediaSettings.swiftmodule'),str(source/runtime.MODEL),str(source/'submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift')])
    code=runtime.fixture(source);code=code[:code.index('@main struct RoundQualityTests')]
    model=runtime.clean((source/runtime.MODEL).read_text());assert code.count(model)==1
    code=code.replace(model,'',1)
    helper=runtime.clean(block((source/runtime.VIDEO).read_text(),'func chatMediaEditorRoundVideoValues('));assert code.count(helper)==1
    code=code.replace(helper,'',1)
    shell=folder/'values.swift';shell.write_text(code)
    api=folder/'helper.swift';api.write_text('import NagramiXMediaSettings\n'+helper+'\n')
    caller=folder/'gallery.swift';caller.write_text('func roundItem(_ values:MediaEditorValues)->MediaEditorValues {chatMediaEditorRoundVideoValues(values,settings:.current)}\n')
    run(['-typecheck','-parse-as-library','-I',str(folder),str(shell),str(api),str(caller)])
    result={'actual_settings_module':'passed','contextual_current_cross_file_import':'passed','actual_immutable_constructor_and_copy':'passed with explicit Telegram graph adapters','uikit_badge':'not_run','full_application_sdk':'pending','device':'pending'}
    if sys.platform!='darwin':
        result['reason']='UIKit/iOS SDK недоступны на Linux; аппаратный encoder и UI не объявляются проверенными.'
        return result
    badge=block((source/runtime.COMPONENT).read_text(),'func nagramiXRoundVideoQualityImage(')
    ui=folder/'quality-badge.swift';ui.write_text('''import UIKit
import CoreGraphics
enum Font {static func semibold(_ size:CGFloat)->UIFont{UIFont.systemFont(ofSize:size,weight:.semibold)}}
func generateImage(_ size:CGSize,rotatedContext:(CGSize,CGContext)->Void)->UIImage? {
 let format=UIGraphicsImageRendererFormat();format.scale=1
 return UIGraphicsImageRenderer(size:size,format:format).image{rotatedContext(size,$0.cgContext)}
}
'''+badge)
    run(['-typecheck','-parse-as-library',str(ui)])
    result['uikit_badge']='passed: actual production drawing helper against UIKit/CoreGraphics; Display Font/generateImage and full editor target linkage remain separate boundaries'
    return result
