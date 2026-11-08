#!/usr/bin/env python3
"""Проверить настройку широкой панели, хранение выбора и все 71 перевода."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from validate_wide_bottom_bar import (ROOT,OVERLAY,NODE,COMP,CORE,UI,STR,KEY,block,plan,verify,guard_checks,run_geometry,source_contract,no_core)
from validate_localization_standard import catalog_contract
from validate_app_language_localization import strings

def ui_contract(source):
    text=(source/UI).read_text();presentation=(source/STR).read_text()
    assert 'var nagramiXWideTabBar: String { self.nagramiXLocalized("'+KEY+'") }' in presentation
    assert 'let updateWideTabBar: (Bool) -> Void' in text
    assert 'case wideTabBar(Bool)' in text
    assert 'case .wideTabBar: return 165' in text
    ids=re.findall(r'case \.([A-Za-z0-9_]+): return 165\b',block(text,'    var stableId:'))
    assert ids==['wideTabBar'],ids
    assert 'case .wideTabBar: return 5' in block(text,'    static func <')
    assert '.tabsHeader, .wideTabBar(settings.wideTabBar), .hideContacts(settings.hideContacts)' in text
    assert 'updateWideTabBar: { value in update { $0.wideTabBar = value } }' in text
    assert 'case .tabsHeader, .wideTabBar, .hideContacts' in text
    assert 'case .wideTabBar: return strings.nagramiXWideTabBar' in text
    item=block(text,'    func item(')
    start=item.index('        case let .wideTabBar(value):')
    row=item[start:item.index('        case let .hideContacts(value):',start)]
    assert 'title: presentationData.strings.nagramiXWideTabBar' in row
    assert 'value: value' in row and 'updated: arguments.updateWideTabBar' in row and 'maximumNumberOfLines: 0' in row
    root=(source/'submodules/TelegramUI/Sources/TelegramRootController.swift').read_text()
    assert 'addObserver(forName: NagramiXTabSettings.changedNotification' in root
    assert 'rootTabController.updateLayout(transition: .immediate)' in root
    core=(source/CORE).read_text()
    assert 'NotificationCenter.default.post(name: self.changedNotification, object: nil)' in core
    p=plan('wide_tab_bar_setting');codes={x['code'] for x in json.loads((OVERLAY/'app_language_localization/languages.json').read_text())['languages']}
    count=catalog_contract(source)
    assert count==(71,630),count
    for code in codes:
        name=f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings'
        old=strings(OVERLAY/p['previous'][name]);new=strings(source/name)
        assert len(old)==629 and new.keys()-old.keys()=={KEY},code
        assert all(new[k]==v for k,v in old.items()),code
        assert new[KEY].strip() and '%' not in new[KEY],code
    return count

def core_source(source):
    # Only the UserDefaults storage boundary is redirected into an isolated suite.
    # All real struct/init/current/update bodies and actual module implementations execute.
    core=(source/CORE).read_text().replace('UserDefaults.standard','testDefaults')
    current=block(core,'    public static var current: NagramiXTabSettings')
    assert ',\n            wideTabBar: defaults.object(forKey: Key.wideTabBar) as? Bool ?? true' in current
    default_initializer=current.replace('public static var current: NagramiXTabSettings','static func makeUsingInitializerDefault() -> NagramiXTabSettings',1)
    default_initializer=default_initializer.replace(',\n            wideTabBar: defaults.object(forKey: Key.wideTabBar) as? Bool ?? true','',1)
    extension='\nextension NagramiXTabSettings {\n'+default_initializer+'\n}\n'
    tests='''
#if os(Linux)
import Glibc
#else
import Darwin
#endif
let suite = "NagramiX.WidePanel.Tests." + ProcessInfo.processInfo.globallyUniqueString
let testDefaults = UserDefaults(suiteName: suite)!
defer { testDefaults.removePersistentDomain(forName: suite) }
var checks = 0
func check(_ value: Bool, _ label: String) { if !value { print("FAIL " + label); exit(91) }; checks += 1 }
final class NotificationProbe: @unchecked Sendable { var count = 0 }
let probe = NotificationProbe()
let observer = NotificationCenter.default.addObserver(forName:NagramiXTabSettings.changedNotification, object:nil, queue:nil) { _ in probe.count += 1 }
defer { NotificationCenter.default.removeObserver(observer) }
let key = "nagramix.tabs.wideBar"
check(testDefaults.object(forKey:key)==nil,"fresh-absent")
check(NagramiXTabSettings.current.wideTabBar,"fresh-enabled")
testDefaults.set(false,forKey:key)
check(!NagramiXTabSettings.current.wideTabBar,"saved-off")
check(NagramiXTabSettings.makeUsingInitializerDefault().wideTabBar,"initializer-default")
let old = NagramiXTabSettings.current
var changed = old
changed.wideTabBar = true
check(old != changed,"setting-equatable")
NagramiXTabSettings.update { $0.hideContacts = !old.hideContacts }
check(!NagramiXTabSettings.current.wideTabBar,"unrelated-preserves-off")
check(NagramiXTabSettings.current.hideContacts != old.hideContacts,"unrelated-update-applied")
NagramiXTabSettings.update { $0.wideTabBar = true }
check(testDefaults.object(forKey:key) as? Bool == true,"persist-on")
check(NagramiXTabSettings.current.wideTabBar,"reload-on")
check(NagramiXTabSettings.current.hideContacts != old.hideContacts,"preserve-other-fields")
NagramiXTabSettings.update { $0.wideTabBar = false }
check(testDefaults.object(forKey:key) as? Bool == false,"persist-off")
check(!NagramiXTabSettings.current.wideTabBar,"reload-off")
check(probe.count==3,"live-notification")
testDefaults.removeObject(forKey:key)
check(NagramiXTabSettings.current.wideTabBar,"removed-key-default")
print("PASS wide settings checks: \\(checks)")
'''
    return core+extension+tests

def run_core(source,swiftc,temp):
    module=temp/'media-module';module.mkdir()
    media=sorted((ROOT/'ios/Sources/NagramiXMediaSettings/Sources').glob('*.swift'))
    assert len(media)==11
    suffix='.dylib' if sys.platform=='darwin' else '.so'
    subprocess.run([swiftc,'-module-cache-path',str(temp/'module-cache'),'-warnings-as-errors','-emit-library','-emit-module','-module-name','NagramiXMediaSettings',*[str(p) for p in media],'-o',str(module/('libNagramiXMediaSettings'+suffix))],check=True,capture_output=True,text=True)
    code=core_source(source)
    variants=[('saved-choice','as? Bool ?? true\n        )','as? Bool ?? false\n        )','fresh-enabled'),
              ('initializer','wideTabBar: Bool = true','wideTabBar: Bool = false','initializer-default'),
              ('no-write','defaults.set(value.wideTabBar, forKey: Key.wideTabBar)','_ = value.wideTabBar','persist-on'),
              ('wrong-key','static let wideTabBar = "nagramix.tabs.wideBar"','static let wideTabBar = "nagramix.tabs.wrongWideBar"','saved-off')]
    results=[];negative=0
    env=os.environ.copy();library_path='DYLD_LIBRARY_PATH' if sys.platform=='darwin' else 'LD_LIBRARY_PATH'
    env[library_path]=str(module)+(':'+env[library_path] if env.get(library_path) else '');env['XDG_CONFIG_HOME']=str(temp/'user-defaults')
    link=['-I',str(module),'-L',str(module),'-lNagramiXMediaSettings']
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        path=temp/('core-'+mode+'.swift');path.write_text(code);binary=temp/('core-'+mode)
        subprocess.run([swiftc,'-module-cache-path',str(temp/'module-cache'),'-warnings-as-errors',*flags,*link,str(path),'-o',str(binary)],check=True,capture_output=True,text=True)
        result=subprocess.run([str(binary)],check=True,capture_output=True,text=True,env=env,preexec_fn=no_core);results.append(result.stdout.strip())
        for name,old,new,label in variants:
            assert old in code,name
            variant=temp/('core-'+mode+'-'+name+'.swift');variant.write_text(code.replace(old,new,1));bad=temp/('core-'+mode+'-'+name)
            subprocess.run([swiftc,'-module-cache-path',str(temp/'module-cache'),'-warnings-as-errors',*flags,*link,str(variant),'-o',str(bad)],check=True,capture_output=True,text=True)
            result=subprocess.run([str(bad)],capture_output=True,text=True,env=env,preexec_fn=no_core)
            assert result.returncode==91 and 'FAIL '+label in result.stdout,(name,result.returncode,result.stdout)
            negative+=1
    return results,negative

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc');parser.add_argument('--report',type=Path)
    args=parser.parse_args();stage='wide_tab_bar_setting';verify(args.source,stage);source_contract(args.source,setting=True);catalog=ui_contract(args.source)
    with tempfile.TemporaryDirectory(prefix='wide-tab-setting-') as folder:
        temp=Path(folder);guard=guard_checks(stage,temp/'guards')
        geometry,gnegative=run_geometry(args.source,args.swiftc,temp,setting=True) if args.swiftc else ([],0)
        core,cnegative=run_core(args.source,args.swiftc,temp) if args.swiftc else ([],0)
        if args.swiftc:
            for n in plan(stage)['outputs']:
                if n.endswith('.swift'):subprocess.run([args.swiftc,'-frontend','-parse',str(args.source/n)],check=True)
    result={'stage':stage,'geometry_runs':geometry,'core_runs':core,'semantic_negative_runs':gnegative+cnegative,'fail_closed':guard,'catalogs':catalog,'outputs':plan(stage)['outputs'],'boundaries':'Real Core/init/current/update and actual media module; isolated UserDefaults suite. Native layout bodies execute with UIKit screen-pixel adapter. UI scene/device pending.','apple_sdk':'not run','physical_device':'pending'}
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
