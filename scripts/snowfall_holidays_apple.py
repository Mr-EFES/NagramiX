"""Full, unmodified holiday Core and Snow view; real UIKit required on Apple."""
import hashlib,subprocess,sys
from snowfall_runtime import SETTINGS,VIEW,BOUNDARY
from snowfall_holidays_runtime import POLICY,SCHEDULE
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan,OVERLAY


def sdk_policy(source):
    # Stage57 remains an exact historical source/runtime checkpoint. Its known
    # iOS17-only enum case is not a final build target; always compile the exact
    # late61 replacement for the native iOS15 gate, without mutating that tree.
    plan=checked_plan('release_096_calendar_compatibility')
    data=(source/POLICY).read_bytes();original=hashlib.sha256(data).hexdigest()
    assert original in (plan['inputs'][POLICY],plan['outputs'][POLICY]),'Unknown calendar policy checkpoint'
    if original==plan['inputs'][POLICY]:data=(OVERLAY/plan['replacements'][POLICY]).read_bytes()
    assert hashlib.sha256(data).hexdigest()==plan['outputs'][POLICY]
    return data.decode(),{'source_policy_sha256':original,'sdk_policy_sha256':plan['outputs'][POLICY],'late_stage':61}


def check(source,swiftc,folder,public_api=False):
    if sys.platform!='darwin' and not public_api:return {'status':'not_run','reason':'Real UIKit/QuartzCore SDK requires macOS'}
    policy,policy_contract=sdk_policy(source)
    code='\n'.join(policy if n==POLICY else (source/n).read_text() for n in [SETTINGS,POLICY,SCHEDULE,VIEW])
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
    regression='not_run; native iOS15 SDK requires Apple'
    if sys.platform=='darwin':
        plan=checked_plan('release_096_calendar_compatibility')
        old=(OVERLAY/plan['previous'][POLICY]).read_text()
        config=block((source/SETTINGS).read_text(),'public struct NagramiXSnowConfiguration:')
        bad=folder/'calendar-original-ios17-api.swift';bad.write_text('import Foundation\n'+config+'\n'+old)
        result=subprocess.run(common+['-typecheck','-parse-as-library',str(bad)],capture_output=True,text=True,timeout=60)
        assert result.returncode!=0 and 'isLeapMonth' in result.stderr and 'only available in iOS 17' in result.stderr,result.stdout+result.stderr
        regression='original204 error reproduced and rejected at arm64-apple-ios15.0'
    return {'status':'passed','policy_contract':policy_contract,'original_ios15_regression':regression,'scope':'Exact final61 calendar policy plus complete production settings/schedule/Snow view as public Core and external consumer. Historical57 runtime bytes remain separately checked. Real Foundation and explicit UIKit/CA adapters on Linux; actual UIKit/QuartzCore and iOS15 deployment target on Apple. Full application SDK/device still separate.'}
