#!/usr/bin/env python3
"""Проверить три SDK137-исправления без ослабления предыдущих SHA-контрактов."""
import argparse
import copy
import shutil
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
STAGE='release_076_compile'
def sha(data): return hashlib.sha256(data).hexdigest()
def plan(): return json.loads((ROOT/'ios'/(STAGE+'_patches.json')).read_text())
def is_applied(source): return all((source/n).is_file() and sha((source/n).read_bytes())==h for n,h in plan()['outputs'].items())
def delegate_if_applied(args):
    from validate_release_076_import import delegate_if_applied as delegate_import
    if delegate_import(args): return True
    if not is_applied(args.source): return False
    subprocess.run([sys.executable,str(Path(__file__).resolve()),'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    return True

def guards(source, p, temp):
    spec = importlib.util.spec_from_file_location('release_076_compile', ROOT / 'ios/release_076_compile.py')
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
        try: module.apply_release_076_compile(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят неверный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if overlay != ROOT / 'ios': shutil.rmtree(overlay)
    def overlay(patch):
        root = temp / 'overlay'; root.mkdir()
        (root / 'release_076_compile_patches.json').write_text(json.dumps(patch))
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
        if not p[field]: continue
        bad = copy.deepcopy(p); bad[field][next(iter(bad[field]))] = '0'*64
        reject(seed(),field + ' SHA',overlay(bad))
    for field in ['replacements','previous']:
        bad = copy.deepcopy(p); bad[field][next(iter(bad[field]))] = '../outside'
        reject(seed(),field+' traversal',overlay(bad))
    if p['copies']:
        bad = copy.deepcopy(p); entry = bad['copies'].pop(next(iter(bad['copies']))); bad['copies']['../outside'] = entry
        reject(seed(),'copy traversal',overlay(bad))
    root = seed(); module.apply_release_076_compile(root,ROOT/'ios'); reject(root,'repeat application')
    return rejected

def previous_bytes(p):
    result={n:(ROOT/'ios'/v).read_bytes() for n,v in p['previous'].items()}
    for n,b in result.items(): assert sha(b)==p['inputs'][n],n
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);args=parser.parse_args()
    from validate_release_076_import import delegate_if_applied as delegate_import
    if delegate_import(args): return
    p=plan()
    for n,h in p['outputs'].items(): assert sha((args.source/n).read_bytes())==h,n
    for n,h in p['templates'].items(): assert sha((ROOT/'ios'/n).read_bytes())==h,n
    prefix='submodules/NagramiXTranscription/Sources/'
    coord=(args.source/(prefix+'Coordinator.swift')).read_text()
    assert 'self.queue.async { [self] in\n            guard !consumer.cancelled' in coord
    assert 'consumer.add { [weak self, weak job] in' in coord
    media=(args.source/(prefix+'MediaPreparation.swift')).read_text()
    assert 'stopRequestingMediaData' not in media
    assert 'input.requestMediaDataWhenReady(on: self.queue) { [weak self] in self?.feed() }' in media
    assert 'guard !self.finished else { return }; self.finished = true' in media
    assert 'self.input?.markAsFinished()' in media and 'self.writer?.cancelWriting()' in media
    gallery=(args.source/'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift').read_text()
    assert 'strings.Common_Copy' not in gallery
    assert 'strings.Conversation_ContextMenuCopy, action:' in gallery
    strings=(args.source/'Telegram/Telegram-iOS/en.lproj/Localizable.strings').read_text()
    assert '"Conversation.ContextMenuCopy" = "Copy";' in strings
    with tempfile.TemporaryDirectory(prefix='nagramix-compile-') as folder:
        temp=Path(folder)
        rejected=guards(args.source,p,temp)
        if args.swiftc:
            from validate_message_translation import run_swift
            from validate_release_076_sdk import swift_checks
            swift_checks(args.source,args.swiftc,temp)
            for optimized in [False,True]:
                run_swift(args.swiftc,temp,'compile-core-'+str(optimized),[args.source/(prefix+n+'.swift') for n in ['Settings','Cloud','Coordinator']]+[ROOT/'scripts/tests/NagramiXTranscriptionCoreTests.swift'],optimized)
            subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.source/n) for n in p['outputs']]],check=True)
        # Restore precise old bytes in an isolated subset for every earlier check.
        names=set(p['inputs'])
        for file in (ROOT/'ios').glob('*_patches.json'):
            old=json.loads(file.read_text())
            for field in ['inputs','outputs','guards','copies']: names.update(old.get(field,{}))
        prior=temp/'prior'
        for n in names:
            src=args.source/n
            if not src.is_file(): continue
            path=prior/n;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((ROOT/'ios'/p['previous'][n]).read_bytes() if n in p['previous'] else src.read_bytes())
        for script in ['validate_release_076_dependencies.py','validate_pip_native_entry.py']:
            subprocess.run([sys.executable,str(ROOT/'scripts'/script),'--source',str(prior)],check=True)
    print('PASS: три SDK137-исправления / предыдущие SHA-контракты / '+str(len(rejected))+' fail-closed cases')
if __name__=='__main__': main()
