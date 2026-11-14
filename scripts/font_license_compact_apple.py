"""Полный actual reader с настоящими UIKit/TextKit/NSAttributedString на iOS15."""
import subprocess,sys
from pathlib import Path
import font_license_compact_runtime as runtime

def check(source,swiftc,folder):
 if sys.platform!='darwin':return {'status':'not_run','reason':'Real UIKit/TextKit layout and CoreAnimation require macOS+iPhoneOS SDK; Linux has explicit UI, attributed-run, glyph-metric and host boundaries.'}
 folder.mkdir(parents=True,exist_ok=True)
 boundary=runtime.boundary(source)
 # Keep UIViewController's actual actor/initializer/title contract on Apple.
 # The Linux lifecycle host is NSObject because UIKit is unavailable there.
 for old,new in [
  ('class ViewController:NSObject {','class ViewController:UIViewController {'),
  ('let statusBar=FixtureStatusBar();var title:String?','let statusBar=FixtureStatusBar()'),
  ('init(navigationBarPresentationData:NavigationBarPresentationData){super.init()}','init(navigationBarPresentationData:NavigationBarPresentationData){super.init(nibName:nil,bundle:nil)}'),
  ('required init(coder:NSCoder){super.init()}','required init(coder:NSCoder){fatalError()}'),
 ]:
  assert boundary.count(old)==1,old
  boundary=boundary.replace(old,new,1)
 path=folder/'font-license-real-uikit.swift';path.write_text(boundary+'\n'+runtime.production(source))
 sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
 result=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-typecheck','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),str(path)],capture_output=True,text=True,timeout=180)
 assert result.returncode==0,result.stdout+result.stderr
 return {'status':'passed','target':'arm64-apple-ios15.0','scope':'Complete actual license controller, document formatter and UITextView subclass with real NSAttributedString, UIFont, NSMutableParagraphStyle, NSLayoutManager, NSTextContainer and CAShapeLayer. App-owned context/theme/navigation/Display/Signal interfaces remain explicit adapters. No simulator pixels, full app build or physical iPhone claim.'}
