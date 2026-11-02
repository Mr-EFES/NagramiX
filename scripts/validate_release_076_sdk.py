#!/usr/bin/env python3
"""Проверить перенос локальных результатов через TelegramEngine после отказа SDK135."""
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

ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def plan():return json.loads((ROOT/'ios/release_076_sdk_patches.json').read_text())
def is_applied(source):return all((source/n).is_file() and sha((source/n).read_bytes())==h for n,h in plan()['outputs'].items())
def delegate_if_applied(args):
    from validate_release_076_dependencies import delegate_if_applied as delegate_dependencies
    if delegate_dependencies(args): return True
    if not is_applied(args.source):return False
    subprocess.run([sys.executable,str(Path(__file__).resolve()),'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True);return True

def previous_bytes(p):
    result={n:(ROOT/'ios'/t).read_bytes() for n,t in p['previous'].items()}
    for n,b in result.items():assert sha(b)==p['inputs'][n],n
    return result

def guards(source, p, temp):
    spec = importlib.util.spec_from_file_location('release_076_sdk', ROOT / 'ios/release_076_sdk.py')
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
        try: module.apply_release_076_sdk(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят неверный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if overlay != ROOT / 'ios': shutil.rmtree(overlay)
    def overlay(patch):
        root = temp / 'overlay'; root.mkdir()
        (root / 'release_076_sdk_patches.json').write_text(json.dumps(patch))
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
    root = seed(); module.apply_release_076_sdk(root,ROOT/'ios'); reject(root,'repeat application')
    return rejected

def prior(source,p,temp):
    names={'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift'}
    for stage in ['voice_transcription','translation_gpt_oss','message_translation','translation_free_modes','round_video_sheet','round_video_page','round_video_refinement','round_video_bitrate','scheduled_archive_isolation']:
        data=json.loads((ROOT/'ios'/(stage+'_patches.json')).read_text())
        for field in ['inputs','outputs','guards','copies']:names.update(data[field])
    previous=previous_bytes(p);root=temp/'prior'
    for n in names:
        dest=root/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(previous[n] if n in previous else (source/n).read_bytes())
    subprocess.run([sys.executable,str(ROOT/'scripts/validate_voice_transcription.py'),'--source',str(root)],check=True)
    shutil.rmtree(root)

def swift_checks(source,swiftc,temp):
    from validate_message_translation import run_swift
    tests=ROOT/'scripts/tests';engine=source/'submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXLocalMessageData.swift'
    def stripped(path):return 'import Foundation\n#if canImport(FoundationNetworking)\nimport FoundationNetworking\n#endif\n'+'\n'.join(l for l in path.read_text().splitlines() if not l.startswith('import ')).replace('public ','')
    helper=temp/'Engine.swift';helper.write_text(stripped(engine))
    common='\nenum TelegramEngine { final class Messages { let account:Account; init(_ account:Account){self.account=account} } }\n'
    asr=temp/'ASRBoundary.swift';text=(tests/'NagramiXTranscriptionRuntimeBoundary.swift').read_text()
    a='final class Engine{let resources=Resources()}';assert text.count(a)==1
    text=text.replace(a,'final class Engine{let resources=Resources();let messages:TelegramEngine.Messages;init(account:Account){self.messages=TelegramEngine.Messages(account)}}')
    a='final class AccountContext{let account=Account();let engine=Engine()}';assert text.count(a)==1
    text=text.replace(a,'final class AccountContext{let account=Account();lazy var engine=Engine(account:self.account)}')
    asr.write_text(text+common+'\ntypealias EngineCodableEntry=CodableEntry\n')
    prefix=source/'submodules/NagramiXTranscription/Sources';runtime=temp/'ASRRuntime.swift';runtime.write_text(stripped(prefix/'Runtime.swift'))
    tr=temp/'TranslationBoundary.swift';text=(tests/'NagramiXTranslationRuntimeBoundary.swift').read_text();a='final class AccountContext { let account: Account;';assert text.count(a)==1
    text=text.replace(a,'final class AccountContext { lazy var engine=LocalEngine(account); let account: Account;')
    tr.write_text(text+common+'\ntypealias EngineRawMessage=Message\nfinal class LocalEngine{let messages:TelegramEngine.Messages;init(_ account:Account){messages=TelegramEngine.Messages(account)}}\n')
    translation=source/'submodules/TranslateUI/Sources';translated=temp/'TranslationRuntime.swift';translated.write_text(stripped(translation/'NagramiXTranslationRuntime.swift'))
    runs=[]
    for optimized in [False,True]:
        suffix='-O' if optimized else '-debug'
        runs.append(run_swift(swiftc,temp,'sdk-asr'+suffix,[prefix/'Settings.swift',prefix/'Coordinator.swift',asr,helper,runtime,tests/'NagramiXTranscriptionRuntimeTests.swift'],optimized))
        runs.append(run_swift(swiftc,temp,'sdk-translation'+suffix,[translation/('NagramiXTranslation'+n+'.swift') for n in ['Settings','Cloud','Web','TextPlan']]+[tr,helper,translated,tests/'NagramiXTranslationRuntimeTests.swift'],optimized))
    subprocess.run([str(swiftc),'-frontend','-parse',str(engine),str(source/'submodules/NagramiXTranscription/Sources/Runtime.swift'),str(translation/'NagramiXTranslationRuntime.swift')],check=True)
    return runs

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    from validate_release_076_dependencies import delegate_if_applied as delegate_dependencies
    if delegate_dependencies(args): return
    p=plan()
    for n,h in {**p['outputs'],**p['guards'],**{n:i['sha256'] for n,i in p['copies'].items()}}.items():assert sha((args.source/n).read_bytes())==h,n
    for n,h in p['templates'].items():assert sha((ROOT/'ios'/n).read_bytes())==h,n
    for n in p['outputs']:
        if n.endswith('.swift'):
            text=(args.source/n).read_text();assert 'import Postbox' not in text and '.postbox' not in text,n
    with tempfile.TemporaryDirectory(prefix='nagramix-sdk-') as folder:
        temp=Path(folder);rejected=guards(args.source,p,temp);prior(args.source,p,temp)
        runs=swift_checks(args.source,args.swiftc,temp) if args.swiftc else []
    report=dict(fail_closed=rejected,runs=runs,SDK='ожидается',iPhone='ожидается')
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PASS: TelegramEngine local data boundary / previous chain / '+str(len(rejected))+' fail-closed checks')
if __name__=='__main__':main()
