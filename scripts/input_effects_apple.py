"""Проверка новых полных Core helpers настоящим UIKit/QuartzCore SDK на Apple."""
import subprocess,sys
from input_effects_runtime import SETTINGS,ANIMATION


def check(source,swiftc,folder):
    if sys.platform!='darwin':return {'status':'not_run','reason':'Real UIKit/QuartzCore SDK requires macOS'}
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    command=[str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'input-effects-sdk-cache'),str(source/SETTINGS),str(source/ANIMATION)]
    p=subprocess.run(command,capture_output=True,text=True,timeout=120)
    assert p.returncode==0,p.stdout+p.stderr
    return {'status':'passed','target':'arm64-apple-ios15.0','scope':'Entire actual public Core settings and UIKit/QuartzCore animator, real framework constructors, properties, notification names and rendering calls. No device/keyboard execution.'}


def public_api_check(source,swiftc,folder):
    from input_effects_runtime import BOUNDARY
    code=(source/SETTINGS).read_text()+'\n'+(source/ANIMATION).read_text()
    if sys.platform!='darwin':code=BOUNDARY+'\n'+code.replace('import UIKit\n','')
    production=folder/'input-effects-public-module.swift';production.write_text('import Foundation\n'+code)
    client=folder/'input-effects-public-client.swift'
    client.write_text('''import Foundation
#if canImport(UIKit)
import UIKit
#endif
import NagramiXCore
func inputEffectsConsumer(_ target: UIView, _ companion: UIView, _ color: UIColor) {
    let animator = NagramiXTypingAnimation()
    animator.play(target: target, companions: [companion], color: color)
    animator.stop()
    let current: NagramiXTypingConfiguration = NagramiXTypingSettings.current
    _ = NagramiXTypingConfiguration()
    _ = NagramiXTypingPreset.allCases.map { $0.localizationKey }
    _ = NagramiXTypingParameter.allCases.map { current[$0] }
    _ = NagramiXTypingSettings.changedNotification
    NagramiXTypingSettings.update { $0.enabled = true; $0.preset = .custom; $0[.scale] = 45.0 }
}
''')
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'input-effects-public-cache')]
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        common+=['-sdk',sdk,'-target','arm64-apple-ios15.0']
    for command in [common+['-emit-module','-parse-as-library','-module-name','NagramiXCore','-emit-module-path',str(folder/'NagramiXCore.swiftmodule'),str(production)],common+['-typecheck','-I',str(folder),str(client)]]:
        result=subprocess.run(command,capture_output=True,text=True,timeout=120)
        assert result.returncode==0,result.stdout+result.stderr
    return {'status':'passed','scope':'Actual complete Core helpers compiled as a separate public module; external consumer checks constructors, callbacks, enum cases, parameter subscript and play/stop signatures. UIKit adapters on Linux; real UIKit on Apple.'}
