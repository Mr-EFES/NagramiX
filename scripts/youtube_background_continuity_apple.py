"""Early real iPhoneOS framework check; Linux never reports SDK compilation."""
import subprocess,sys
from youtube_background_continuity_runtime import fixture


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    if sys.platform!='darwin':return {'status':'not_run','reason':'Real UIKit/WebKit iPhoneOS SDK requires macOS'}
    code=fixture(source,apple=True)
    path=folder/'youtube-background-real-sdk.swift';path.write_text(code)
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    result=subprocess.run([str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),str(path)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    return {'status':'passed','target':'arm64-apple-ios15.0','scope':'Entire production WebKit helper and actual media status definitions/reconciliation; actual changed content lifecycle and managed ownership statements. Real UIKit notifications, Foundation/Dispatch and all WK initializers/frame/script APIs. Presentation hosts, SignalKit and managed audio queue are explicit adapters; no application linking or live stream execution.'}
