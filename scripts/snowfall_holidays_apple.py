"""Full, unmodified holiday Core and Snow view; real UIKit required on Apple."""
import subprocess,sys
from snowfall_runtime import SETTINGS,VIEW,BOUNDARY
from snowfall_holidays_runtime import POLICY,SCHEDULE


def check(source,swiftc,folder,public_api=False):
    if sys.platform!='darwin' and not public_api:return {'status':'not_run','reason':'Real UIKit/QuartzCore SDK requires macOS'}
    code='\n'.join((source/n).read_text() for n in [SETTINGS,POLICY,SCHEDULE,VIEW])
    if sys.platform!='darwin':
        boundary=BOUNDARY.replace('static let willResignActiveNotification=', 'static let significantTimeChangeNotification=Notification.Name("significant");static let willResignActiveNotification=')
        code='import Foundation\n'+boundary+'\n'+code.replace('import UIKit\n','')
    production=folder/'snow-holidays-public-module.swift';production.write_text(code)
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'snow-holidays-sdk-cache')]
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip();common+=['-sdk',sdk,'-target','arm64-apple-ios15.0']
    result=subprocess.run(common+['-emit-module','-parse-as-library','-module-name','NagramiXCore','-emit-module-path',str(folder/'NagramiXCore.swiftmodule'),str(production)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    client=folder/'snow-holidays-public-client.swift';client.write_text('''import Foundation
#if canImport(UIKit)
import UIKit
#endif
import NagramiXCore
@MainActor func holidayConsumer(_ parent:UIView) {
 let header=NagramiXSnowView(scope:.header)
 header.bind(to:parent);header.setVisible(true)
 let date=Date(),zone=TimeZone.autoupdatingCurrent
 _ = NagramiXSnowSettings.current
 _ = NagramiXSnowSettings.configuration(at:date,timeZone:zone)
 NagramiXSnowSettings.refreshSchedule(at:date,timeZone:zone)
 _ = NagramiXSnowHolidays.dayInterval(at:date,timeZone:zone)
 _ = NagramiXSnowHolidays.window(at:date,timeZone:zone)
 _ = NagramiXSnowHolidays.configuration(NagramiXSnowConfiguration(),during:nil)
 NagramiXSnowSettings.update {$0.enabled=false;$0.density=50}
}
''')
    result=subprocess.run(common+['-typecheck','-I',str(folder),str(client)],capture_output=True,text=True,timeout=120);assert result.returncode==0,result.stdout+result.stderr
    return {'status':'passed','scope':'Entire unmodified production holiday policy/settings/schedule/Snow view as public Core plus external UI consumer. Real Foundation and explicit UIKit/CA adapters on Linux; real UIKit/QuartzCore on Apple. Full application SDK/device still separate.'}
