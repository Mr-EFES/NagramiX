"""Настоящая Core-модель и Foundation-модуль настроек: начальный и сохранённый выбор."""
import os,sys,subprocess
from validate_quick_format import block
from validate_local_copy_delivery import run
from wide_panel_consistency_runtime import CORE

def check(source,swiftc,folder):
    module=folder/'wide-media';module.mkdir()
    media=sorted((source/'submodules/NagramiXMediaSettings/Sources').glob('*.swift'))
    assert len(media)==13
    suffix='.dylib' if sys.platform=='darwin' else '.so'
    run([swiftc,'-swift-version','5','-module-cache-path',folder/'cache','-warnings-as-errors','-emit-library','-emit-module','-module-name','NagramiXMediaSettings',*media,'-o',module/('libNagramiXMediaSettings'+suffix)])
    core=(source/CORE).read_text().replace('UserDefaults.standard','testDefaults')
    initializer=block(core,'    public static var current: NagramiXTabSettings').replace('public static var current: NagramiXTabSettings','static func usingInitializerDefault() -> NagramiXTabSettings',1)
    assert ',\n            wideTabBar: self.wideTabBarEnabled' in initializer
    initializer=initializer.replace(',\n            wideTabBar: self.wideTabBarEnabled','',1)
    code=core+'\nextension NagramiXTabSettings {\n'+initializer+'\n}\n'+r'''
#if os(Linux)
import Glibc
#else
import Darwin
#endif
let suite="NagramiX.WidePanel."+ProcessInfo.processInfo.globallyUniqueString
let testDefaults=UserDefaults(suiteName:suite)!
defer { testDefaults.removePersistentDomain(forName:suite) }
var count=0
func check(_ value:Bool,_ label:String) { if !value { print("FAIL "+label);exit(91) };count+=1 }
final class Probe:@unchecked Sendable { var count=0 }
let probe=Probe()
let observer=NotificationCenter.default.addObserver(forName:NagramiXTabSettings.changedNotification,object:nil,queue:nil) { _ in probe.count+=1 }
defer { NotificationCenter.default.removeObserver(observer) }
let key="nagramix.tabs.wideBar"
check(testDefaults.object(forKey:key)==nil,"fresh-key-absent")
check(NagramiXTabSettings.current.wideTabBar && NagramiXTabSettings.wideTabBarEnabled,"fresh-on")
testDefaults.set(false,forKey:key)
check(!NagramiXTabSettings.current.wideTabBar && !NagramiXTabSettings.wideTabBarEnabled,"saved-off")
check(NagramiXTabSettings.usingInitializerDefault().wideTabBar,"initializer-default")
let old=NagramiXTabSettings.current
NagramiXTabSettings.update { $0.hideContacts = !old.hideContacts }
check(!NagramiXTabSettings.wideTabBarEnabled && !NagramiXTabSettings.current.wideTabBar,"other-update-keeps-off")
NagramiXTabSettings.update { $0.wideTabBar = true }
check(testDefaults.object(forKey:key) as? Bool == true,"persist-on")
check(NagramiXTabSettings.wideTabBarEnabled && NagramiXTabSettings.current.wideTabBar,"reload-on")
check(NagramiXTabSettings.current.hideContacts != old.hideContacts,"preserve-other-fields")
NagramiXTabSettings.update { $0.wideTabBar = false }
check(testDefaults.object(forKey:key) as? Bool == false,"persist-off")
check(!NagramiXTabSettings.wideTabBarEnabled && !NagramiXTabSettings.current.wideTabBar,"reload-off")
check(probe.count==3,"notifications")
testDefaults.removeObject(forKey:key)
check(NagramiXTabSettings.wideTabBarEnabled,"removed-key-on")
print("PASS wide panel actual Core checks: \(count)")
'''
    variants=[('baseline',code,None)]
    for name,old,new,label in [
        ('wrong-default','object(forKey: Key.wideTabBar) as? Bool ?? true','object(forKey: Key.wideTabBar) as? Bool ?? false','fresh-on'),
        ('wrong-key','static let wideTabBar = "nagramix.tabs.wideBar"','static let wideTabBar = "nagramix.tabs.invalidWideBar"','saved-off'),
        ('missing-write','defaults.set(value.wideTabBar, forKey: Key.wideTabBar)','_ = value.wideTabBar','persist-on'),
        ('wrong-init','wideTabBar: Bool = true','wideTabBar: Bool = false','initializer-default'),
    ]:
        assert old in code,name
        variants.append((name,code.replace(old,new,1),'FAIL '+label))
    env=os.environ.copy();env['DYLD_LIBRARY_PATH' if sys.platform=='darwin' else 'LD_LIBRARY_PATH']=str(module);env['XDG_CONFIG_HOME']=str(folder/'wide-defaults')
    results=[]
    for name,text,diagnostic in variants:
        path=folder/('wide-core-'+name+'.swift');path.write_text(text)
        for mode,flags in [('debug',[]),('optimized',['-O'])]:
            binary=folder/('wide-core-'+name+'-'+mode)
            run([swiftc,'-swift-version','5','-module-cache-path',folder/'cache','-warnings-as-errors',*flags,'-I',module,'-L',module,'-lNagramiXMediaSettings',path,'-o',binary])
            r=subprocess.run([str(binary)],env=env,text=True,capture_output=True,timeout=60)
            assert r.returncode==(91 if diagnostic else 0) and (diagnostic is None or diagnostic in r.stdout),(name,mode,r.stdout,r.stderr)
            results.append({'name':name,'mode':mode,'exit_code':r.returncode,'output':r.stdout.strip()});binary.unlink()
    return results
