"""Добавить полные локальные каталоги всех поддерживаемых языков после прежних стадий."""
import hashlib
import json
from pathlib import Path
import re


def apply_all_language_catalogs(source: Path, overlay: Path) -> None:
    plan=json.loads((overlay/'all_language_catalogs_patches.json').read_text())
    supported=json.loads((overlay/'app_language_localization/languages.json').read_text())
    languages={item['code'] for item in supported['languages']}-{'en','ru'}
    expected={f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings' for code in languages}
    if set(plan['copies'])!=expected or set(plan['languages'])!=languages:
        raise SystemExit('Language catalogs: incomplete language destinations')
    if plan['inputs'] or plan['outputs'] or plan['previous']:
        raise SystemExit('Language catalogs: this stage only adds resources')

    def safe(root,name):
        relative=Path(name);path=root/relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('Language catalogs: unsafe path '+name)
        return path
    def checked(root,name,digest):
        path=safe(root,name)
        if not path.is_file():raise SystemExit('Language catalogs: missing '+name)
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise SystemExit('Language catalogs: hash drift '+name)
        return data
    def catalog(data):
        text=data.decode('utf-8')
        entry=r'"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)";'
        if re.sub(entry,'',text).strip():raise SystemExit('Language catalogs: malformed strings')
        pairs=re.findall(entry,text)
        values=[(json.loads('"'+key+'"'),json.loads('"'+value+'"')) for key,value in pairs]
        if not values or len(values)!=len(dict(values)):raise SystemExit('Language catalogs: invalid/duplicate strings')
        return dict(values)

    for name,digest in plan['templates'].items():checked(overlay,name,digest)
    for name,digest in plan['guards'].items():checked(source,name,digest)
    english=catalog((source/'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings').read_bytes())
    formats=lambda value:sorted(re.findall(r'%(?:[1-9][0-9]*\$)?[@dfius]|%%',value))
    prepared={}
    for name,item in plan['copies'].items():
        target=safe(source,name)
        if target.exists():raise SystemExit('Language catalogs: destination already exists '+name)
        data=checked(overlay,item['source'],item['sha256']);values=catalog(data)
        if values.keys()!=english.keys():raise SystemExit('Language catalogs: incomplete keys '+name)
        for key,value in values.items():
            if not value.strip() or formats(value)!=formats(english[key]) or any(marker in value for marker in ('ZXQ','QXZ','TODO_TRANSLATE','TRANSLATE_ME','__NAGRAMIX_MISSING__')):
                raise SystemExit('Language catalogs: empty value/format drift '+name+' '+key)
        if sum(value!=english[key] for key,value in values.items())<20:
            raise SystemExit('Language catalogs: English copy '+name)
        prepared[name]=data
    # No directory or file is created until every input, template, destination,
    # key set and format argument has passed the checks above.
    for name,data in prepared.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
