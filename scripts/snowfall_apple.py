"""Typecheck complete production Snow helpers and public consumer; real UIKit on Apple."""
import subprocess,sys
from snowfall_runtime import SETTINGS,VIEW,BOUNDARY


def check(source,swiftc,folder,public_api=False):
    if sys.platform!='darwin' and not public_api:return {'status':'not_run','reason':'Real UIKit/QuartzCore SDK requires macOS'}
    code=(source/SETTINGS).read_text()+'\n'+(source/VIEW).read_text()
    if sys.platform!='darwin':code='import Foundation\n'+BOUNDARY+'\n'+code.replace('import UIKit\n','')
    production=folder/'snow-public-module.swift';production.write_text(code)
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'snow-sdk-cache')]
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip();common+=['-sdk',sdk,'-target','arm64-apple-ios15.0']
    command=common+['-emit-module','-parse-as-library','-module-name','NagramiXCore','-emit-module-path',str(folder/'NagramiXCore.swiftmodule'),str(production)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=120);assert result.returncode==0,result.stdout+result.stderr
    client=folder/'snow-public-client.swift';client.write_text('''import Foundation
#if canImport(UIKit)
import UIKit
#endif
import NagramiXCore
@MainActor func snowConsumer(_ parent:UIView,_ background:UIView) {
 let header=NagramiXSnowView(scope:.header),messages=NagramiXSnowView(scope:.messages)
 header.bind(to:parent,above:background);messages.bind(to:parent)
 header.setVisible(true);messages.setVisible(false)
 _ = NagramiXSnowConfiguration()
 _ = NagramiXSnowSettings.current
 _ = NagramiXSnowSettings.changedNotification
 _ = NagramiXSnowSettings.normalizedDensity(50)
 NagramiXSnowSettings.update {$0.enabled=true;$0.inChats=false;$0.density=50}
}
''')
    result=subprocess.run(common+['-typecheck','-I',str(folder),str(client)],capture_output=True,text=True,timeout=120);assert result.returncode==0,result.stdout+result.stderr
    return {'status':'passed','scope':'Entire production settings/view emitted as a public module plus external consumer. Real Foundation; explicit UIKit/CA adapters on Linux, real UIKit/QuartzCore on Apple. No physical rendering.'}
