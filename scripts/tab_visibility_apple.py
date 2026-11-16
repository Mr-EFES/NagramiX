"""UIKit typecheck for the actual new search selectors/model; no SDK app build."""
from pathlib import Path
import subprocess,sys
from validate_quick_format import block
import tab_visibility_runtime as rt

def check(source,swiftc,folder):
    report={'search_gesture_and_model_uikit':'not_run','full_application_sdk':'not_run','physical_iphone':'pending'}
    if sys.platform!='darwin':
        report['reason']='Linux: actual Core/SignalKit and changed bodies run with explicit UIKit/navigation/menu IO hosts.'
        return report
    folder.mkdir(parents=True,exist_ok=True)
    text=(source/rt.COMPONENT).read_text()
    declarations=text.split('    private let contextGesture =',1)[1].split('    private let backgroundView:',1)[0]
    methods='\n'.join(block(text,m) for m in ['    @objc private func onContextGesture(', '    @objc private func onContextAccessibilityAction('])
    registration=text.split('        self.contextGesture.addTarget',1)[1].split('    }',1)[0]
    accessibility=text.split('        self.contextGesture.isEnabled = self.contextAction != nil && !isActive',1)[1].split('        let params = Params(',1)[0]
    code='''import UIKit
final class GestureAPI: UIView {
 struct Params {let isActive:Bool}
 private var params:Params?
 private let contextGesture ='''+declarations+'''
 func configure(isActive:Bool) {
        self.contextGesture.addTarget'''+registration+'\n        self.contextGesture.isEnabled = self.contextAction != nil && !isActive'+accessibility+'\n}\n'+methods+'\n}\nenum TabBarComponent {\n'+block(text,'    public final class Search:')+'\n}\n'
    p=folder/'uikit.swift';p.write_text(code)
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    result=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'cache'),'-sdk',sdk,'-target','arm64-apple-ios15.0','-parse-as-library','-typecheck',str(p)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+result.stderr
    report['search_gesture_and_model_uikit']='passed: actual new gesture selectors/registration and complete Search model; explicit UIView host, not whole application'
    return report
