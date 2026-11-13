"""Полные фактические history hooks и recognizer с реальными UIKit declarations."""
import subprocess
import sys
from single_touch_message_selection_runtime import production,ROOT
from selection_column_coordinates_runtime import FIELDS


def check(source,swiftc,folder):
    if sys.platform!='darwin':
        return {'status':'not_run','reason':'UIKit requires macOS and the iOS SDK; affine runtime fixture is not UIKit.'}
    helper,methods=production(source)
    boundary=(ROOT/'scripts/tests/NagramiXMessageDragSelectionBoundary.swift').read_text()
    boundary=boundary[boundary.index('typealias MessageId ='):]
    code='import Foundation\nimport UIKit\n'+helper+'\n'+boundary+'\nfinal class HistoryHarness:NSObject {\n'+FIELDS+methods+'\n}\n'
    path=folder/'selection-column-real-uikit.swift';path.write_text(code)
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    result=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-typecheck','-parse-as-library','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'selection-column-sdk-cache'),str(path)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    return {'status':'passed','scope':'Whole actual recognizer/helper/history hooks, real UIView.bounds.maxX/convert, CGPoint and Objective-C selectors. Telegram model/list/timer are explicit adapters; runtime UIKit gesture competition and iPhone remain pending.'}
