"""Проверить точные лицензированные ресурсы шрифтов в будущей IPA0.9.5+."""
import hashlib,json,plistlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def validate_font_resources(archive,prefix):
    plan=json.loads((ROOT/'ios/app_font_selection_patches.json').read_text())
    path=ROOT/'ios/app_font_selection/fonts.json';data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==plan['templates']['app_font_selection/fonts.json'],'Изменён реестр шрифтов'
    fonts=json.loads(data);names=archive.namelist();suffix='/NagramiXFontsResources.bundle/Info.plist'
    roots=[n[:-len('Info.plist')] for n in names if n.startswith(prefix) and n.endswith(suffix) and not n.startswith(prefix+'PlugIns/')]
    assert len(roots)==1,'Нет единственного основного bundle шрифтов'
    root=roots[0];info=plistlib.loads(archive.read(root+'Info.plist'))
    assert info['CFBundleIdentifier']=='com.mr-efes.nagramix.fonts'
    expected={f['file']:f['sha256'] for f in fonts['fonts']};expected.update(fonts['licenses'])
    assert len(expected)==24
    for file,sha in expected.items():
        packed=root+file
        assert names.count(packed)==1,'Отсутствующий или дублированный ресурс шрифта: '+file
        assert hashlib.sha256(archive.read(packed)).hexdigest()==sha,'Изменён ресурс шрифта: '+file
    actual={n[len(root):] for n in names if n.startswith(root) and n.lower().endswith(('.ttf','.otf','.txt'))}
    assert actual==set(expected),'Неожиданные ресурсы в bundle шрифтов'
    return {'bundle':root,'faces':len(fonts['fonts']),'license_documents':len(fonts['licenses'])}
