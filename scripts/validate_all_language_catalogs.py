#!/usr/bin/env python3
"""Проверить новые 69 ресурсов и отказ overlay до первой записи при неверном входе."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

from validate_app_language_localization import strings
from validate_localization_standard import catalog_contract

ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'

def sha(data):return hashlib.sha256(data).hexdigest()

def verify(source):
    plan=json.loads((OVERLAY/'all_language_catalogs_patches.json').read_text())
    for name,digest in plan['guards'].items():assert sha((source/name).read_bytes())==digest,name
    for name,digest in plan['templates'].items():assert sha((OVERLAY/name).read_bytes())==digest,name
    for name,item in plan['copies'].items():assert (source/name).read_bytes()==(OVERLAY/item['source']).read_bytes(),name
    languages,keys=catalog_contract(source)
    assert languages==71 and keys==612
    terms=json.loads((OVERLAY/'all_language_catalogs/terminology.json').read_text())
    for code,item in terms.items():
        values=strings(source/f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings')
        assert values['NagramiX.Settings.Page.Other']==item['other'],code
        assert values['NagramiX.Settings.Page.Interface']==item['interface'],code
        assert values['NagramiX.Settings.Page.Features']==item['features'],code
    return plan


def rejected_inputs(source,plan):
    spec=importlib.util.spec_from_file_location('all_language_catalogs',OVERLAY/'all_language_catalogs.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='nagramix-all-languages-') as folder:
        root=Path(folder);overlay=root/'overlay';overlay.mkdir()
        for name in set(plan['templates'])|{'app_language_localization/languages.json'}:
            dest=overlay/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((OVERLAY/name).read_bytes())
        manifest=overlay/'all_language_catalogs_patches.json';manifest.write_text(json.dumps(plan))
        files=list(plan['copies']);templates=list(plan['templates']);count=0
        def seed():
            target=root/'source';target.mkdir(exist_ok=True)
            for name in plan['guards']:
                dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((source/name).read_bytes())
            return target
        def snapshot(target):return {str(p.relative_to(target)):p.read_bytes() for p in target.rglob('*') if p.is_file()}
        def reject(change):
            nonlocal count
            target=seed();current=copy.deepcopy(plan);restores=[]
            change(target,current,restores);manifest.write_text(json.dumps(current));before=snapshot(target)
            try:module.apply_all_language_catalogs(target,overlay)
            except (SystemExit,ValueError,KeyError,AssertionError):pass
            else:raise AssertionError('Invalid input accepted')
            assert snapshot(target)==before,'Partial mutation before failed prechecks'
            for path,data in restores:path.write_bytes(data)
            for p in sorted(target.rglob('*'),reverse=True):
                if p.is_file():p.unlink()
                elif p.is_dir():p.rmdir()
            count+=1
        for name in plan['guards']:
            reject(lambda target,_,restores,n=name:(target/n).unlink())
            reject(lambda target,_,restores,n=name:(target/n).write_bytes(b'drift'))
        for name in [templates[0],templates[-1]]:
            def drift(target,current,restores,n=name):
                path=overlay/n;restores.append((path,path.read_bytes()));path.write_bytes(b'drift')
            reject(drift)
        def collision(target,current,restores):
            path=target/files[-1];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'existing')
        reject(collision)
        reject(lambda target,current,restores:current['copies'].pop(files[-1]))
        reject(lambda target,current,restores:current['languages'].pop())
        reject(lambda target,current,restores:current['copies'][files[0]].update(source='../escape'))
        def content(target,current,restores,kind):
            item=current['copies'][files[-1]];path=overlay/item['source'];data=path.read_bytes();restores.append((path,data));values=strings(path)
            if kind=='key':values.pop(next(iter(values)))
            elif kind=='empty':values[next(iter(values))]=''
            elif kind=='format':values[next(iter(values))]='bad %@'
            elif kind=='english':values=strings(source/'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings')
            elif kind=='marker':values[next(iter(values))]='TODO_TRANSLATE'
            payload=''.join(json.dumps(k,ensure_ascii=False)+' = '+json.dumps(v,ensure_ascii=False)+';\n' for k,v in values.items()).encode()
            if kind=='syntax':payload+=b'invalid trailing data'
            if kind=='duplicate':
                key=next(iter(values));payload+=(json.dumps(key)+' = "duplicate";\n').encode()
            path.write_bytes(payload);item['sha256']=sha(payload);current['templates'][item['source']]=sha(payload)
        for kind in ['key','empty','format','english','marker','syntax','duplicate']:reject(lambda target,current,restores,k=kind:content(target,current,restores,k))
        target=seed();manifest.write_text(json.dumps(plan));module.apply_all_language_catalogs(target,overlay)
        for name,item in plan['copies'].items():assert sha((target/name).read_bytes())==item['sha256']
        print(f'PASS: {count} invalid inputs rejected before writes; clean application reproduces all 69 catalogs.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);args=parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    for stage in ('pip_playback_commands', 'round_caption_transport', 'repost_copy_integrity', 'native_pip_baseline', 'copy_delivery', 'rich_draft_upload_retry', 'pip_transition_geometry', 'transfer_consistency', 'editor_attachment_delivery', 'local_model_size', 'archive_deletion_effect', 'pip_visual_handoff', 'local_model_menu', 'archive_deletion_visibility', 'temporary_media_actions', 'message_copy_availability', 'vosk_model_naming', 'local_asr_memory'):
        if delegate_icon_stage_if_applied(args,Path(__file__),stage):
            return
    plan=verify(args.source);rejected_inputs(args.source,plan)
    print('PASS: 71 real language catalogs, 612 keys each; all 69 new resource hashes and terminology verified.')

if __name__=='__main__':main()
