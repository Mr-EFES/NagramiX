#!/usr/bin/env python3
"""Проверить доступную с iOS 18 проверку состояния пары и прежнюю цепочку."""
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLAN=json.loads((ROOT/'ios/translation_sdk_fix_patches.json').read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def is_applied(source): return all((source/name).is_file() and digest(source/name)==value for name,value in PLAN['outputs'].items())
def delegate_if_applied(args):
    from validate_pip_removal_work import delegate_if_applied as delegate_latest
    if delegate_latest(args): return True
    if not is_applied(args.source): return False
    subprocess.run([sys.executable,__file__,'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    return True
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--standalone',action='store_true');args=parser.parse_args()
    from validate_pip_removal_work import delegate_if_applied as delegate_latest
    if delegate_latest(args): return
    assert is_applied(args.source)
    name=next(iter(PLAN['inputs']))
    code=(args.source/name).read_text()
    assert 'if await session.isReady' not in code
    assert 'availability.status(from: Locale.Language(identifier: self.source), to: Locale.Language(identifier: self.target))' in code
    assert 'if status == .installed { self.finished = true }' in code
    spec=importlib.util.spec_from_file_location('translation_sdk_fix',ROOT/'ios/translation_sdk_fix.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='nagramix-translation-sdk-') as folder:
        temp=Path(folder);base=temp/'base';path=base/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/PLAN['previous'][name],path)
        module.apply_translation_sdk_fix(base,ROOT/'ios');assert is_applied(base)
        if args.swiftc:subprocess.run([str(args.swiftc),'-frontend','-parse',str(path)],check=True)
        shutil.copyfile(ROOT/'ios'/PLAN['previous'][name],path);path.write_bytes(path.read_bytes()+b'// drift');old=path.read_bytes()
        try:module.apply_translation_sdk_fix(base,ROOT/'ios')
        except SystemExit:pass
        else:raise AssertionError('Дрейф входа принят')
        assert path.read_bytes()==old
        if not args.standalone:
            prior=temp/'prior';names=set(PLAN['inputs'])
            for manifest in (ROOT/'ios').glob('*_patches.json'):
                plan=json.loads(manifest.read_text())
                for field in ('inputs','outputs','guards','copies'):names.update(plan.get(field,{}))
            names.add('Telegram/Telegram-iOS/en.lproj/Localizable.strings')
            for n in names:
                src=args.source/n
                if not src.is_file():continue
                dest=prior/n;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/'ios'/PLAN['previous'][n] if n in PLAN['previous'] else src,dest)
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_translation_completion.py'),'--source',str(prior),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    print('PASS: iOS 18 language status, fail-closed'+('' if args.standalone else ', previous chain'))
if __name__=='__main__':main()
