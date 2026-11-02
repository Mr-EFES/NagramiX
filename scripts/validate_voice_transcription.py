#!/usr/bin/env python3
"""Проверить новую расшифровку, guards и сохранение предыдущей нативной цепочки."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/NagramiXTranscription/Sources/'
def sha(data): return hashlib.sha256(data).hexdigest()
def plan(): return json.loads((ROOT / 'ios/voice_transcription_patches.json').read_text())
def is_applied(source): return all((source / n).is_file() and sha((source / n).read_bytes()) == h for n, h in plan()['outputs'].items())
def delegate_if_applied(args):
    from validate_release_076_sdk import delegate_if_applied as delegate_sdk
    if delegate_sdk(args): return True
    if not is_applied(args.source): return False
    subprocess.run([sys.executable, str(Path(__file__).resolve()), '--source', str(args.source), *(['--swiftc', str(args.swiftc)] if args.swiftc else [])], check=True)
    return True

def previous_bytes(p):
    result = {}
    for n, template in p['previous'].items():
        data = (ROOT / 'ios' / template).read_bytes(); assert sha(data) == p['inputs'][n], n; result[n] = data
    return result

def guards(source, p, temp):
    spec = importlib.util.spec_from_file_location('voice_transcription', ROOT / 'ios/voice_transcription.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    original = {n: (source / n).read_bytes() for n in p['guards']}; original.update(previous_bytes(p))
    rejected = []
    from validate_quick_format import manifest
    def seed():
        root = temp / 'source'
        for n, data in original.items():
            dest = root / n; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
        return root
    def reject(root, label, overlay=ROOT / 'ios'):
        before = manifest(root)
        try: module.apply_voice_transcription(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят неверный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if overlay != ROOT / 'ios': shutil.rmtree(overlay)
    def overlay(patch):
        root = temp / 'overlay'; root.mkdir()
        (root / 'voice_transcription_patches.json').write_text(json.dumps(patch))
        for n in p['templates']:
            dest = root / n; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes((ROOT / 'ios' / n).read_bytes())
        return root
    for n in original:
        for mode in ['missing','drift']:
            root = seed(); path = root / n
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes()+b'\n// drift')
            reject(root, mode + ' ' + n)
    for n in p['copies']:
        root = seed(); path = root / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('collision')
        reject(root, 'helper collision ' + n)
    for n in p['templates']:
        for mode in ['missing','drift']:
            root = seed(); bad = overlay(p); path = bad / n
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes()+b'\n// drift')
            reject(root, mode + ' template ' + n, bad)
    for field in ['inputs','outputs','guards','templates']:
        bad = copy.deepcopy(p); bad[field][next(iter(bad[field]))] = '0'*64
        reject(seed(),field + ' SHA',overlay(bad))
    for field in ['replacements','previous']:
        bad = copy.deepcopy(p); bad[field][next(iter(bad[field]))] = '../outside'
        reject(seed(),field+' traversal',overlay(bad))
    bad = copy.deepcopy(p); entry = bad['copies'].pop(next(iter(bad['copies']))); bad['copies']['../outside'] = entry
    reject(seed(),'copy traversal',overlay(bad))
    root = seed(); module.apply_voice_transcription(root,ROOT/'ios'); reject(root,'repeat application')
    return rejected

def prior(source, p, temp):
    previous = previous_bytes(p)
    names = {'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift'}
    for stage in ['translation_gpt_oss','message_translation','translation_free_modes','round_video_sheet','round_video_page','round_video_refinement','round_video_bitrate','scheduled_archive_isolation']:
        value=json.loads((ROOT/'ios'/(stage+'_patches.json')).read_text())
        for field in ['inputs','outputs','guards','copies']: names.update(value[field])
    root = temp/'previous'
    for n in names:
        path=root/n; path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(previous[n] if n in previous else (source/n).read_bytes())
    subprocess.run([sys.executable,str(ROOT/'scripts/validate_translation_gpt_oss.py'),'--source',str(root)],check=True)
    shutil.rmtree(root)

def swift_checks(source, swiftc, temp):
    from validate_message_translation import run_swift
    tests = ROOT/'scripts/tests'
    paths = {n: source/(PREFIX+n+'.swift') for n in ['Settings','Cloud','Coordinator','Runtime','Credentials']}
    for name in ['Runtime','Credentials']:
        text=paths[name].read_text();text='import Foundation\n'+'\n'.join(l for l in text.splitlines() if not l.startswith('import ')).replace('public ','')
        (temp/(name+'.swift')).write_text(text)
    analyzer = temp/'Analyzer.swift'
    analyzer.write_text('import Foundation\n'+'\n'.join(l for l in (source/(PREFIX+'AppleAnalyzer.swift')).read_text().splitlines() if not l.startswith('import ')).replace('#if compiler(>=6.2)', '#if true'))
    legacy = temp/'Apple.swift'; legacy.write_text((source/(PREFIX+'Apple.swift')).read_text().replace('import Speech\n','').replace('#if compiler(>=6.2)', '#if false'))
    models = temp/'Models.swift'; models.write_text((source/(PREFIX+'Models.swift')).read_text().replace('import CryptoKit','import FoundationNetworking'))
    model_boundary = temp/'ModelBoundary.swift'; model_boundary.write_text('import Foundation\nimport FoundationNetworking\nstruct SHA256 { mutating func update(data:Data){}; func finalize()->[UInt8]{[]} }\nextension URLRequest { var allowsExpensiveNetworkAccess:Bool {get{true}set{}};var allowsConstrainedNetworkAccess:Bool {get{true}set{}} }\n')
    subprocess.run([str(swiftc),'-typecheck','-warnings-as-errors','-module-cache-path',str(temp/'cache'),str(paths['Settings']),str(models),str(model_boundary)],check=True)
    runs=[]
    for optimized in [False,True]:
        suffix='-O' if optimized else '-debug'
        runs.append(run_swift(swiftc,temp,'asr-analyzer'+suffix,[paths['Settings'],tests/'NagramiXTranscriptionAnalyzerBoundary.swift',analyzer,tests/'NagramiXTranscriptionAnalyzerTests.swift'],optimized))
        runs.append(run_swift(swiftc,temp,'asr-apple'+suffix,[paths['Settings'],tests/'NagramiXTranscriptionAppleBoundary.swift',legacy,tests/'NagramiXTranscriptionAppleTests.swift'],optimized))
        runs.append(run_swift(swiftc,temp,'asr-core'+suffix,[paths[n] for n in ['Settings','Cloud','Coordinator']]+[tests/'NagramiXTranscriptionCoreTests.swift'],optimized))
        runs.append(run_swift(swiftc,temp,'asr-http'+suffix,[paths[n] for n in ['Settings','Cloud']]+[tests/'NagramiXTranscriptionHTTPTests.swift'],optimized))
        runs.append(run_swift(swiftc,temp,'asr-keychain'+suffix,[paths['Settings'],tests/'NagramiXTranslationKeychainBoundary.swift',temp/'Credentials.swift',tests/'NagramiXTranscriptionKeychainTests.swift'],optimized))
        runs.append(run_swift(swiftc,temp,'asr-runtime'+suffix,[paths['Settings'],paths['Coordinator'],tests/'NagramiXTranscriptionRuntimeBoundary.swift',temp/'Runtime.swift',tests/'NagramiXTranscriptionRuntimeTests.swift'],optimized))
    files=[str(source/n) for n in set(plan()['outputs'])|set(plan()['copies']) if n.endswith('.swift')]
    subprocess.run([str(swiftc),'-frontend','-parse',*files],check=True)
    return runs

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    from validate_release_076_sdk import delegate_if_applied as delegate_sdk
    if delegate_sdk(args): return
    p=plan()
    expected={**p['guards'],**p['outputs'],**{n:i['sha256'] for n,i in p['copies'].items()}}
    for n,h in expected.items():assert sha((args.source/n).read_bytes())==h,n
    for n,h in p['templates'].items():assert sha((ROOT/'ios'/n).read_bytes())==h,n
    with tempfile.TemporaryDirectory(prefix='nagramix-asr-') as folder:
        temp=Path(folder);rejected=guards(args.source,p,temp);prior(args.source,p,temp)
        runs=swift_checks(args.source,args.swiftc,temp) if args.swiftc else []
    report=dict(replacements=len(p['inputs']),helpers=len(p['copies']),fail_closed=rejected,runs=runs,source_hashes=expected,SDK='ожидается',iPhone='ожидается',IPA='не собиралась')
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PASS: расшифровка / предыдущие stages / '+str(len(rejected))+' fail-closed checks')
if __name__=='__main__':main()
