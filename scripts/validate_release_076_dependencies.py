#!/usr/bin/env python3
"""Проверить настройки архива Whisper и отсутствие старой Postbox BUILD-зависимости."""
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
def plan():return json.loads((ROOT/'ios/release_076_dependencies_patches.json').read_text())
def is_applied(source):return all((source/n).is_file() and sha((source/n).read_bytes())==h for n,h in plan()['outputs'].items())
def delegate_if_applied(args):
    from validate_release_076_compile import delegate_if_applied as delegate_compile
    if delegate_compile(args): return True
    if not is_applied(args.source):return False
    subprocess.run([sys.executable,str(Path(__file__).resolve()),'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True);return True

def previous_bytes(p):
    result={n:(ROOT/'ios'/t).read_bytes() for n,t in p['previous'].items()}
    for n,b in result.items():assert sha(b)==p['inputs'][n],n
    return result

def guards(source, p, temp):
    spec = importlib.util.spec_from_file_location('release_076_dependencies', ROOT / 'ios/release_076_dependencies.py')
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
        try: module.apply_release_076_dependencies(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят неверный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if overlay != ROOT / 'ios': shutil.rmtree(overlay)
    def overlay(patch):
        root = temp / 'overlay'; root.mkdir()
        (root / 'release_076_dependencies_patches.json').write_text(json.dumps(patch))
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
    root = seed(); module.apply_release_076_dependencies(root,ROOT/'ios'); reject(root,'repeat application')
    return rejected

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);args=parser.parse_args()
    from validate_release_076_compile import delegate_if_applied as delegate_compile
    if delegate_compile(args): return
    p=plan()
    for n,h in p['outputs'].items():assert sha((args.source/n).read_bytes())==h,n
    for n,h in p['templates'].items():assert sha((ROOT/'ios'/n).read_bytes())==h,n
    module=(args.source/'MODULE.bazel').read_text();assert 'name = "nagramix_whisper",\n    type = "tar.gz",' in module
    assert '7b17da903114ed45d82f48c030e3be6a5a8a279f884b2f733706dbb4e832fb6b' in module
    assert '"//submodules/Postbox:Postbox"' not in (args.source/'submodules/TranslateUI/BUILD').read_text()
    with tempfile.TemporaryDirectory(prefix='nagramix-dependencies-') as folder:
        temp=Path(folder);rejected=guards(args.source,p,temp);root=temp/'prior'
        names={'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift'}
        for stage in ['release_076_sdk','voice_transcription','translation_gpt_oss','message_translation','translation_free_modes','round_video_sheet','round_video_page','round_video_refinement','round_video_bitrate','scheduled_archive_isolation']:
            value=json.loads((ROOT/'ios'/(stage+'_patches.json')).read_text())
            for field in ['inputs','outputs','guards','copies']:names.update(value[field])
        previous=previous_bytes(p)
        for n in names:
            path=root/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(previous[n] if n in previous else (args.source/n).read_bytes())
        subprocess.run([sys.executable,str(ROOT/'scripts/validate_release_076_sdk.py'),'--source',str(root),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    print('PASS: pinned archive format / no Postbox dependency / '+str(len(rejected))+' fail-closed cases')
if __name__=='__main__':main()
