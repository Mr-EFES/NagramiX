#!/usr/bin/env python3
"""Validate complete counter values and the optional native abbreviations."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
HELPER='submodules/NagramiXMediaSettings/Sources/NagramiXNumberSettings.swift'
UI='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'
PRESENTATION='submodules/TelegramPresentationData/Sources/PresentationData.swift'
FORMATTERS=[('submodules/TelegramPresentationData/Sources/NumericFormat.swift','public func compactNumericCountString(', 'stockCompactNumericCountString'),('submodules/TelegramPresentationData/Sources/DefaultPresentationStrings.swift','public func countString(', 'stockCountString')]
def manifest(p):
    return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
def block(text,marker):
    assert text.count(marker)==1,marker
    start=text.index(marker);brace=text.index('{',start);depth=1
    for i in range(brace+1,len(text)):
        if text[i]=='{':depth+=1
        elif text[i]=='}':depth-=1
        if depth==0:return text[start:i+1]
    raise AssertionError(marker)
def validate(before,after,swiftc):
    plan=json.loads((ROOT/'ios/number_rounding_patches.json').read_text());a,b=manifest(before),manifest(after)
    changed={n for n in a if a[n]!=b.get(n)}
    expected={p[0] for p in plan['patches']}|{'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift',*[f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings' for lang in ['ru','en']]}
    assert changed==expected,changed^expected
    assert b.keys()-a.keys()=={HELPER} and not a.keys()-b.keys()
    texts={n:(before/n).read_text() for n in plan['hashes']};assert all(a[n]==sha for n,sha in plan['hashes'].items())
    for n,old,new,count in plan['patches']:
        assert texts[n].count(old)==count;texts[n]=texts[n].replace(old,new,count)
    assert all((after/n).read_bytes()==v.encode() for n,v in texts.items())
    for src,n in plan['provided'].items():assert (after/n).read_bytes()==(ROOT/'ios'/src).read_bytes()
    spec=importlib.util.spec_from_file_location('number_rounding',ROOT/'ios/number_rounding.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[]
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        def seed(p):
            for n in plan['hashes']:
                q=p/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(before/n,q)
            for src,n in plan['provided'].items():
                q=p/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'ios'/src,q)
        def reject(p,label,overlay=ROOT/'ios'):
            old=manifest(p)
            try:module.apply_number_rounding(p,overlay)
            except (SystemExit,FileNotFoundError):pass
            else:raise AssertionError(label)
            assert manifest(p)==old,'partial write: '+label
            rejected.append(label)
        p=folder/'valid';seed(p);module.apply_number_rounding(p,ROOT/'ios');assert all((p/n).read_bytes()==(after/n).read_bytes() for n in plan['hashes']);reject(p,'reapply')
        for i,n in enumerate(plan['hashes']):
            for kind in ['missing','drift']:
                p=folder/(kind+str(i));seed(p)
                if kind=='missing':(p/n).unlink()
                else:(p/n).write_bytes((p/n).read_bytes()+b'\n// drift\n')
                reject(p,kind+' '+n)
        for src,n in plan['provided'].items():
            for kind in ['missing','drift']:
                p=folder/(kind+'-helper');seed(p)
                if kind=='missing':(p/n).unlink()
                else:(p/n).write_text('// stale helper')
                reject(p,kind+' helper')
            p=folder/'template';seed(p);overlay=folder/'overlay';overlay.mkdir();shutil.copy2(ROOT/'ios/number_rounding_patches.json',overlay);reject(p,'missing canonical helper',overlay)
    generated=['import Foundation']
    guard='    if !NagramiXNumberSettings.roundingEnabled {\n        return NagramiXNumberSettings.fullCountString(count)\n    }\n'
    for n,marker,alias in FORMATTERS:
        original=block((before/n).read_text(),marker);current=block((after/n).read_text(),marker)
        assert current.count(guard)==1 and current.replace(guard,'',1)==original,'native ON changed'
        generated += [original.replace(marker, 'func '+alias+'(',1), current]
    generated += [block((after/PRESENTATION).read_text(),'private func nagramiXNumberRoundingSignal()').replace('private func','func',1)]
    execution=[]
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp);source=folder/'NativeFormatters.swift';source.write_text('\n'.join(generated)+'\n')
        for mode in ['debug','optimized']:
            binary=folder/('numbers-'+mode)
            cmd=[str(swiftc),'-warnings-as-errors','-module-cache-path',str(folder/'module-cache'),str(after/HELPER),str(source),str(ROOT/'scripts/tests/NagramiXNumberRoundingTests.swift'),'-o',str(binary)]
            if mode=='optimized':cmd.insert(1,'-O')
            subprocess.run(cmd,check=True)
            env=dict(os.environ,XDG_CONFIG_HOME=str(folder/('preferences-'+mode)))
            execution.append(mode+': '+subprocess.check_output([str(binary)],text=True,env=env,timeout=30).strip())
            for command,value in [('fresh','false'),('set','true'),('read','true'),('set','false'),('read','false'),('read','false')]:subprocess.run([str(binary),command,value],env=env,check=True,stdout=subprocess.PIPE,timeout=15)
            execution.append(mode+': PASS 6 separate cold processes')
        subprocess.run([str(swiftc),'-frontend','-parse',*[str(after/n) for n in sorted(changed|{HELPER}) if n.endswith('.swift')]],check=True)
    ui=(after/UI).read_text();data=(after/PRESENTATION).read_text()
    args=block(ui,'private struct NagramiXSettingsControllerArguments')
    calls=ui[ui.index('    let arguments = NagramiXSettingsControllerArguments('):ui.index('    let mediaInputSettings = context.sharedContext.accountManager.sharedData(')]
    assert re.findall(r'^    let (\w+):',args,re.M)==re.findall(r'^        (\w+):',calls,re.M)
    assert ui.count('case .numberRounding: return 156')==1 and ui.count('case .numberRounding: return 1011')==1
    assert '.numberRounding(NagramiXNumberSettings.roundingEnabled)' in ui
    assert ui.count('.compactChatList, .numberRounding, .compactChatListInfo')==2
    assert 'maximumNumberOfLines: 0' in ui[ui.index('case let .numberRounding(value):'):][:400]
    assert 'return strings.nagramiXNumberRoundingSearchTerms' in ui
    assert 'systemUserInterfaceStyle, nagramiXNumberRoundingSignal())' in data
    assert 'secondaryComponent: nil, groupingSeparator: "")' in data
    build=(after/'submodules/TelegramPresentationData/BUILD').read_text()
    assert '"//submodules/NagramiXMediaSettings:NagramiXMediaSettings"' in build
    assert '"//submodules/NagramiXCore' not in build,'dependency cycle'
    assert 'deps = ' not in (after/'submodules/NagramiXMediaSettings/BUILD').read_text(),'Foundation helper acquired dependencies'
    for lang,title in [('ru','Округление чисел'),('en','Round Numbers')]:
        s=(after/f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        assert s.count('"NagramiX.Numbers.Rounding.Title" = "'+title+'";')==1 and s.count('"NagramiX.Numbers.Rounding.SearchTerms" = ')==1
    for n in ['ios/apply_features.py','ios/number_rounding.py','scripts/validate_number_rounding.py']:ast.parse((ROOT/n).read_text())
    return {'outputs':len(b),'changed':sorted(changed),'added':sorted(b.keys()-a.keys()),'unchanged':len(a)-len(changed),'sha_guards':len(plan['hashes']),'exact_operations':len(plan['patches']),'fail_closed':rejected,'execution':execution,'apple_sdk':'not run: no build authorization','physical_iphone':'pending'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']:p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args();result=validate(args.before,args.after,args.swiftc);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
