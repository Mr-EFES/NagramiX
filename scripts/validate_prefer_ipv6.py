#!/usr/bin/env python3
"""Check IPv6 preference integration without an Apple SDK/IPA build."""
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
UI='submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift'
PREFS='submodules/NagramiXMediaSettings/Sources/NagramiXProxyPreferences.swift'
CONTEXT='submodules/MtProtoKit/Sources/MTContext.m'
TCP='submodules/MtProtoKit/Sources/MTTcpConnection.m'
DNS='submodules/MtProtoKit/Sources/MTDNS.m'
RESOLVER='submodules/MtProtoKit/Sources/NagramiXDNSResolver.m'
def manifest(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def block(text,marker):
    assert text.count(marker)==1,marker
    start=text.index(marker);brace=text.index('{',start);depth=1
    for i in range(brace+1,len(text)):
        if text[i]=='{':depth+=1
        elif text[i]=='}':depth-=1
        if depth==0:return text[start:i+1]
    raise AssertionError(marker)
def validate(before,after,swiftc,clang):
    plan=json.loads((ROOT/'ios/prefer_ipv6_patches.json').read_text());a,b=manifest(before),manifest(after)
    changed={n for n in a if a[n]!=b.get(n)}
    expected={p[0] for p in plan['patches']}|{PREFS,'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift',*[f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings' for lang in ['ru','en']]}
    assert changed==expected,changed^expected
    assert b.keys()-a.keys()==set(plan['copies'].values()) and not a.keys()-b.keys()
    texts={n:(before/n).read_text() for n in plan['hashes']};assert all(a[n]==sha for n,sha in plan['hashes'].items())
    for n,old,new,count in plan['patches']:
        assert texts[n].count(old)==count;texts[n]=texts[n].replace(old,new,count)
    assert all((after/n).read_bytes()==v.encode() for n,v in texts.items())
    for src,n in (plan['provided']|plan['copies']).items():assert (after/n).read_bytes()==(ROOT/'ios'/src).read_bytes()
    spec=importlib.util.spec_from_file_location('prefer_ipv6',ROOT/'ios/prefer_ipv6.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
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
            try:module.apply_prefer_ipv6(p,overlay)
            except (SystemExit,FileNotFoundError):pass
            else:raise AssertionError(label)
            assert manifest(p)==old,'partial write: '+label
            rejected.append(label)
        def overlay_copy(p):
            p.mkdir();shutil.copy2(ROOT/'ios/prefer_ipv6_patches.json',p)
            for src in plan['provided']|plan['copies']:
                q=p/src;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'ios'/src,q)
        p=folder/'valid';seed(p);module.apply_prefer_ipv6(p,ROOT/'ios');assert all((p/n).read_bytes()==(after/n).read_bytes() for n in plan['hashes']);reject(p,'reapply')
        for i,n in enumerate(plan['hashes']):
            for kind in ['missing','drift']:
                p=folder/(kind+str(i));seed(p)
                if kind=='missing':(p/n).unlink()
                else:(p/n).write_bytes((p/n).read_bytes()+b'\n// drift\n')
                reject(p,kind+' '+n)
        for i,(src,n) in enumerate(plan['provided'].items()):
            for kind in ['missing','drift']:
                p=folder/(kind+'-provided'+str(i));seed(p)
                if kind=='missing':(p/n).unlink()
                else:(p/n).write_text('// stale preference bridge')
                reject(p,kind+' provided '+n)
            p=folder/('provided-template'+str(i));seed(p);overlay=folder/('overlay-provided'+str(i));overlay_copy(overlay);(overlay/src).unlink();reject(p,'missing canonical '+src,overlay)
        for i,(src,n) in enumerate(plan['copies'].items()):
            p=folder/('collision'+str(i));seed(p);(p/n).write_text('// collision');reject(p,'collision '+n)
            p=folder/('copy-template'+str(i));seed(p);overlay=folder/('overlay-copy'+str(i));overlay_copy(overlay);(overlay/src).unlink();reject(p,'missing template '+src,overlay)
        p=folder/'parent';seed(p);overlay=folder/'overlay-parent';overlay_copy(overlay);bad=json.loads((overlay/'prefer_ipv6_patches.json').read_text());bad['copies'][next(iter(bad['copies']))]='absent-parent/helper.h';(overlay/'prefer_ipv6_patches.json').write_text(json.dumps(bad));reject(p,'missing destination parent',overlay)
    execution=[]
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        for mode,opt in [('debug','-O0'),('optimized','-O2')]:
            binary=folder/('policy-'+mode)
            subprocess.run([str(clang),'-std=c11',opt,'-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(after/'submodules/MtProtoKit/Sources'),str(ROOT/'scripts/tests/NagramiXIPv6PolicyTests.c'),'-lm','-o',str(binary)],check=True)
            execution.append(mode+': '+subprocess.check_output([str(binary)],text=True,timeout=15).strip())
            binary=folder/('preferences-'+mode)
            cmd=[str(swiftc),'-warnings-as-errors','-module-cache-path',str(folder/'module-cache'),str(after/PREFS),str(ROOT/'scripts/tests/NagramiXIPv6PreferencesTests.swift'),'-o',str(binary)]
            if mode=='optimized':cmd.insert(1,'-O')
            subprocess.run(cmd,check=True)
            env=dict(os.environ,XDG_CONFIG_HOME=str(folder/('preferences-'+mode+'-data')))
            execution.append(mode+': '+subprocess.check_output([str(binary)],text=True,env=env,timeout=30).strip())
            for command,value in [('fresh','false'),('set','true'),('read','true'),('set','false'),('read','false'),('read','false')]:subprocess.run([str(binary),command,value],env=env,check=True,stdout=subprocess.PIPE,timeout=15)
            execution.append(mode+': PASS 6 separate cold processes')
        subprocess.run([str(swiftc),'-frontend','-parse',*[str(after/n) for n in sorted(changed) if n.endswith('.swift')]],check=True)
    ui=(after/UI).read_text();context=(after/CONTEXT).read_text();tcp=(after/TCP).read_text();dns=(after/DNS).read_text();resolver=(after/RESOLVER).read_text()
    # Stable identities, exact requested order, and native row/search-free layout.
    assert ui.count('case .preferIPv6: return .index(17)')==1
    assert 'case .dns: return 1\n        case .preferIPv6: return 2\n        case .customDoh: return 3' in ui
    dnsrow=ui.index('    entries.append(.dns(');ipv6row=ui.index('    entries.append(.preferIPv6(');custom=ui.index('    if nagramiXSettings.dnsProvider == .customDoh {')
    assert dnsrow<ipv6row<custom
    row=ui.split('        case let .preferIPv6(_, title, value):',1)[1].split('        case let .customDoh',1)[0]
    assert 'maximumNumberOfLines: 0' in row and 'arguments.togglePreferIPv6' in row
    assert 'togglePreferIPv6: @escaping (Bool) -> Void' in ui and 'NagramiXProxyPreferences.setPreferIPv6(value)' in ui
    assert 'bool preferIpv6 = [NagramiXIPv6Preference enabled] && _apiEnvironment.socksProxySettings == nil;' in context
    assert '__block bool scanIpv6 = preferIpv6;' in context and ': earliestFailure > current.lastFailureTimestamp' in context
    assert block(tcp,'- (void)requestSocksConnection {')==block((before/TCP).read_text(),'- (void)requestSocksConnection {')
    # The WEB carrier's no-DNS branch must not become a direct hostname lookup.
    for marker in ['            if (_isWebProxy) {\n                if (!injectedIsWebProxyCarrier)', '            if (_isWebProxy) {\n                // Resolve NOTHING']:
        assert block(tcp,marker)==block((before/TCP).read_text(),marker)
    assert 'NagramiXIPv6ShouldRecordFailure([NagramiXIPv6Preference enabled], error, _nagramiXTcpConnected, _nagramiXIPv6Endpoint, _nagramiXProxyHostname.length != 0)' in tcp
    assert '_nagramiXTcpConnected = true;' in tcp and 'recordSuccessForHost:_nagramiXProxyHostname' in tcp
    assert 'NagramiXIPv6DNSFamily([NagramiXIPv6Preference preferForHost:host port:port]' in dns
    assert 'resolveHostname:hostname preferIPv6:[NagramiXIPv6Preference preferForHost:hostname port:port]' in dns
    assert resolver.count('NagramiXIPv6DNSQueryType(preferIPv6,')==4
    assert (after/'submodules/MtProtoKit/Sources/NagramiXDNSResolver.h').read_bytes()==(after/'submodules/MtProtoKit/PublicHeaders/MtProtoKit/NagramiXDNSResolver.h').read_bytes()
    prefs=(after/PREFS).read_text();native=(after/'submodules/MtProtoKit/Sources/NagramiXIPv6Preference.m').read_text()
    assert 'nagramix.network.preferIPv6' in prefs and '@"nagramix.network.preferIPv6"' in native
    assert '@synchronized (self)' in native and 'values.count >= 256 && values[key] == nil' in native and 'systemUptime' in native
    account=(after/'submodules/TelegramCore/Sources/Account/Account.swift').read_text();network=(after/'submodules/TelegramCore/Sources/Network/Network.swift').read_text()
    assert 'NagramiXDnsSettingsChanged' in account and 'network.reconnectForNagramiXDnsChange()' in account
    assert 'self.mainSession.setPaused(!keepConnection)' in network
    for lang,title in [('ru','Предпочитать IPv6'),('en','Prefer IPv6')]:
        text=(after/f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text();assert text.count('"NagramiX.Proxy.PreferIPv6" = "'+title+'";')==1
    for n in ['ios/apply_features.py','ios/prefer_ipv6.py','scripts/validate_prefer_ipv6.py']:ast.parse((ROOT/n).read_text())
    return {'outputs':len(b),'changed':sorted(changed),'added':sorted(b.keys()-a.keys()),'unchanged':len(a)-len(changed),'sha_guards':len(plan['hashes']),'exact_operations':len(plan['patches']),'fail_closed':rejected,'execution':execution,'apple_sdk':'not run: no build authorization','physical_network':'pending: dual stack, IPv4-only, IPv6-only, unreachable IPv6, SOCKS/MTProto, DoH, VPN'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','clang','report']:p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args();result=validate(args.before,args.after,args.swiftc,args.clang);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
