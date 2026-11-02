#!/usr/bin/env python3
"""Проверить пропущенный импорт TranslateUI и восстановление предыдущих контрактов."""
import argparse,copy,hashlib,importlib.util,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def plan():return json.loads((ROOT/'ios/release_076_import_patches.json').read_text())
def is_applied(source):return all((source/n).is_file() and sha((source/n).read_bytes())==h for n,h in plan()['outputs'].items())
def delegate_if_applied(args):
    from validate_video_ownership_fix import delegate_if_applied as delegate_latest
    if delegate_latest(args): return True
    if not is_applied(args.source):return False
    subprocess.run([sys.executable,str(Path(__file__).resolve()),'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    return True

def guards(source, p, temp):
    spec = importlib.util.spec_from_file_location('release_076_import', ROOT / 'ios/release_076_import.py')
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
        try: module.apply_release_076_import(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят неверный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if overlay != ROOT / 'ios': shutil.rmtree(overlay)
    def overlay(patch):
        root = temp / 'overlay'; root.mkdir()
        (root / 'release_076_import_patches.json').write_text(json.dumps(patch))
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
    root = seed(); module.apply_release_076_import(root,ROOT/'ios'); reject(root,'repeat application')
    return rejected

def previous_bytes(p):
    result={n:(ROOT/'ios'/v).read_bytes() for n,v in p['previous'].items()}
    for n,b in result.items(): assert sha(b)==p['inputs'][n],n
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);args=parser.parse_args()
    from validate_video_ownership_fix import delegate_if_applied as delegate_latest
    if delegate_latest(args): return
    p=plan()
    for n,h in {**p['outputs'],**p['guards']}.items():assert sha((args.source/n).read_bytes())==h,n
    for n,h in p['templates'].items():assert sha((ROOT/'ios'/n).read_bytes())==h,n
    item='submodules/TelegramUI/Sources/ChatControllerNode.swift'
    before=(ROOT/'ios'/p['previous'][item]).read_text();after=(args.source/item).read_text()
    assert after==before.replace('import TelegramCore\n','import TelegramCore\nimport TranslateUI\n',1)
    assert after.count('import TranslateUI\n')==1
    assert '"//submodules/TranslateUI:TranslateUI"' in (args.source/'submodules/TelegramUI/BUILD').read_text()
    runtime=(args.source/'submodules/TranslateUI/Sources/NagramiXTranslationRuntime.swift').read_text()
    assert 'public enum NagramiXTranslationRuntime' in runtime and 'public func nagramiXTranslationChatKey' in runtime
    with tempfile.TemporaryDirectory(prefix='nagramix-import-') as folder:
        temp=Path(folder);rejected=guards(args.source,p,temp);names=set(p['inputs'])|set(p['guards'])
        for file in (ROOT/'ios').glob('*_patches.json'):
            old=json.loads(file.read_text())
            for field in ['inputs','outputs','guards','copies']:names.update(old.get(field,{}))
        names.add('Telegram/Telegram-iOS/en.lproj/Localizable.strings')
        prior=temp/'prior'
        for n in names:
            src=args.source/n
            if not src.is_file():continue
            path=prior/n;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((ROOT/'ios'/p['previous'][n]).read_bytes() if n in p['previous'] else src.read_bytes())
        subprocess.run([sys.executable,str(ROOT/'scripts/validate_release_076_compile.py'),'--source',str(prior),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    print('PASS: импорт TranslateUI / BUILD и публичный API прежние / '+str(len(rejected))+' fail-closed cases')
if __name__=='__main__':main()
