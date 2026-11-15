"""Реальные UIKit и ObjC category API для изменённой кнопки; без имитации UIKit."""
import subprocess,sys
from validate_quick_format import block
from transcription_compatibility_apple import write_module_map

UI='submodules/SettingsUI/Sources/NagramiXFontsController.swift'
HEADER='submodules/UIKitRuntimeUtils/Source/UIKitRuntimeUtils/UIBarButtonItem+Proxy.h'

def item_code(source):
    refresh=block((source/UI).read_text(),'    private func refresh()')
    start=refresh.index('        let applyItem = ')
    end=refresh.index('\n        self.licenseTitle.text =',start)
    return refresh[start:end]

def check(source,swiftc,folder):
    header=(source/HEADER).read_text()
    assert '@property (nonatomic) bool staysInRow;' in header
    code=item_code(source)
    if sys.platform!='darwin':
        return {'status':'not_run','reason':'Настоящий UIKit/iPhoneOS SDK отсутствует на Linux; ObjC header проверен, UI не имитируется.'}
    folder.mkdir(parents=True,exist_ok=True)
    # Only the unrelated Texture type is forward declared. UIKit and the full
    # native UIBarButtonItem category declarations are imported by Swift/Clang.
    header=header.replace('#import <AsyncDisplayKit/ASDisplayNode.h>','@class ASDisplayNode;',1)
    path=folder/'BarItemProxy.h';path.write_text(header)
    module=folder/'module';write_module_map(module,path,'NagramiXBarItemProxy')
    path=folder/'font-apply-real-uikit.swift'
    path.write_text('''import UIKit
import NagramiXBarItemProxy
@MainActor private final class ApplyAPIProbe: NSObject {
    struct Draft { var canApply = false }
    struct Strings { var Theme_Context_Apply = "Применить" }
    let navigationItem = UINavigationItem()
    var draft = Draft()
    let strings = Strings()
    @objc private func applyTapped() {}
    func refresh() {
'''+code+'\n    }\n}\n')
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    result=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-typecheck','-sdk',sdk,'-target','arm64-apple-ios15.0','-I',str(module),'-module-cache-path',str(folder/'cache'),str(path)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    return {'status':'passed','target':'arm64-apple-ios15.0','scope':'Actual modified statements, real UIBarButtonItem/UINavigationItem/selector and native ObjC staysInRow category; draft/strings/controller host only, no pixels or full application compilation.'}
