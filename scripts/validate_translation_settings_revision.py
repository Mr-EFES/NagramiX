#!/usr/bin/env python3
"""Проверка промежуточной стадии настроек переводчика и цепочки."""
import argparse, hashlib, json, subprocess, sys, tempfile, shutil, importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PLAN = json.loads((ROOT / 'ios/translation_settings_revision_patches.json').read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def is_applied(source): return all((source / n).is_file() and digest(source / n) == h for n, h in PLAN['outputs'].items())
def delegate_if_applied(args):
    from validate_translation_completion import delegate_if_applied as delegate_latest
    if delegate_latest(args): return True
    if not is_applied(args.source): return False
    subprocess.run([sys.executable, __file__, '--source', str(args.source), *(['--swiftc', str(args.swiftc)] if args.swiftc else [])], check=True)
    return True
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--source', type=Path, required=True); parser.add_argument('--swiftc',type=Path); args=parser.parse_args()
    from validate_translation_completion import delegate_if_applied as delegate_latest
    if delegate_latest(args): return
    assert is_applied(args.source)
    for name, expected in PLAN['templates'].items(): assert digest(ROOT/'ios'/name)==expected, name
    spec=importlib.util.spec_from_file_location('translation_settings_revision',ROOT/'ios/translation_settings_revision.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='nagramix-translation-settings-') as folder:
        temp=Path(folder); base=temp/'base'
        for name, item in PLAN['previous'].items():
            path=base/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/item,path)
        module.apply_translation_settings_revision(base, ROOT/'ios')
        assert is_applied(base)
        for bad in PLAN['inputs']:
            copy=temp/'bad';shutil.copytree(base,copy)
            for name,item in PLAN['previous'].items(): shutil.copyfile(ROOT/'ios'/item,copy/name)
            path=copy/bad;path.write_bytes(path.read_bytes()+b'// drift')
            snapshot={n:(copy/n).read_bytes() for n in PLAN['inputs']}
            try: module.apply_translation_settings_revision(copy,ROOT/'ios')
            except SystemExit: pass
            else: raise AssertionError('Дрейф входа принят: '+bad)
            assert snapshot=={n:(copy/n).read_bytes() for n in PLAN['inputs']}
            shutil.rmtree(copy)
        if args.swiftc:
            subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(base/n) for n in PLAN['outputs']]],check=True)
        # Restore the exact inputs for all older strict validators.
        prior=temp/'prior'
        names=set(PLAN['inputs']) | set(PLAN['guards'])
        for manifest in (ROOT/'ios').glob('*_patches.json'):
            earlier=json.loads(manifest.read_text())
            for field in ('inputs', 'outputs', 'guards', 'copies'): names.update(earlier.get(field, {}))
        names.add('Telegram/Telegram-iOS/en.lproj/Localizable.strings')
        for name in names:
            source=args.source/name
            if not source.is_file(): continue
            target=prior/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/'ios'/PLAN['previous'][name] if name in PLAN['previous'] else source,target)
        subprocess.run([sys.executable,str(ROOT/'scripts/validate_transcription_settings_complete.py'),'--source',str(prior),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    print('PASS: translation settings revision, fail-closed, previous chain')
if __name__=='__main__':main()
