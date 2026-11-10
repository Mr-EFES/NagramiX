#!/usr/bin/env python3
"""Проверить единый стандарт строк настроек/debug и полноту всех языков."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from localization_literals import canonical,literals
from validate_app_language_localization import strings, runtime_checks

ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
UI_CATALOG=json.loads((OVERLAY/'app_language_localization/ui_catalog.json').read_text())
REVIEWED=json.loads((OVERLAY/'localization_standard/reviewed_raw_sinks.json').read_text())['files']
INTENTIONAL={
    'submodules/TranslateUI/Sources/NagramiXTranslationChatLanguage.swift': 'Локальный словарь распознавания языка, не UI',
    'submodules/TranslateUI/Sources/NagramiXServiceIcon.swift': 'Буква/имя бренда в значке',
    'submodules/NagramiXTranscription/Sources/NagramiXServiceIcon.swift': 'Буква/имя бренда в значке',
    'submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/NagramiXFormattingKeyboard.swift': 'Многоязычный образец приветствия',
}
# One centralized resolver owns its exact source/template dictionary.
RESOLVER='submodules/NagramiXCore/Sources/NagramiXAppLocalization.swift'
SINK=re.compile(r'\b(?:title|text|label|placeholder|subtitle|message|accessibilityLabel|accessibilityValue)\s*[:=]\s*$|\b(?:setTitle|setPlaceholder|setAccessibilityLabel|Text)\(\s*$|\.(?:plain|markdown)\(\s*$')


def catalog_contract(source,codes=None):
    resources=source/'submodules/NagramiXCore/Resources'
    english=strings(resources/'en.lproj/Localizable.strings')
    if not english or any(re.search('[А-Яа-яЁё]',value) for value in english.values()):
        raise ValueError('Пустой английский каталог или русский текст внутри него')
    if codes is None:
        codes={item['code'] for item in json.loads((OVERLAY/'app_language_localization/languages.json').read_text())['languages']}
    available={p.parent.name.removesuffix('.lproj'):strings(p) for p in resources.glob('*.lproj/Localizable.strings')}
    missing=sorted(set(codes)-available.keys())
    if missing:raise ValueError(f'Локализация не завершена: отсутствуют {len(missing)} каталогов: '+', '.join(missing))
    formats=lambda value:sorted(re.findall(r'%(?:[1-9][0-9]*\$)?[@dfius]|%%',value))
    for code,values in available.items():
        if values.keys()!=english.keys():raise ValueError('Неполный набор ключей: '+code)
        for key,value in values.items():
            if not value.strip() or value.strip().startswith(('__NAGRAMIX_MISSING__','TODO_TRANSLATE','TRANSLATE_ME')):
                raise ValueError('Пустой перевод/заглушка: '+code+' '+key)
            if formats(value)!=formats(english[key]):raise ValueError('Аргументы перевода изменились: '+code+' '+key)
        changed=sum(values[key]!=english[key] for key in english)
        if code!='en' and changed<min(20,max(1,len(english)//10)):
            raise ValueError('Английская копия вместо перевода: '+code)
    return len(available),len(english)


def source_files(source):
    paths={p for p in (source/'submodules').rglob('*.swift') if 'Sources' in p.parts and (
        p.name.startswith('NagramiX') or any(part.startswith('NagramiX') for part in p.relative_to(source).parts))}
    plan=json.loads((OVERLAY/'app_language_localization_patches.json').read_text())
    paths.update(source/name for name in plan['outputs'] if name.endswith('.swift'))
    paths.update((source/'submodules/DebugSettingsUI/Sources').glob('*.swift'))
    return sorted(paths)


def source_contract(source):
    english=strings(source/'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings')
    errors=[];calls=0;paths=source_files(source)
    for path in paths:
        name=path.relative_to(source).as_posix()
        if name==RESOLVER:continue
        text=path.read_text();raw=Counter()
        for start,end,parts in literals(text):
            value=canonical(parts);prefix=text[max(0,start-100):start]
            location=f'{name}:{text.count(chr(10),0,start)+1}'
            if prefix.endswith('.nagramiXUILocalized('):
                if value not in UI_CATALOG:errors.append(location+': нет UI-ключа '+value)
                elif UI_CATALOG[value]['key'] not in english:errors.append(location+': отсутствует ключ '+UI_CATALOG[value]['key'])
                calls+=1;continue
            if prefix.endswith('.nagramiXLocalized(') and text[end:].lstrip().startswith(')'):
                if value not in english:errors.append(location+': отсутствует ключ '+value)
                calls+=1;continue
            if prefix.endswith('.nagramiXDebugLocalized('):
                if any(re.search('[A-Za-z]',v) for kind,v in parts if kind=='text') and 'NagramiX.Debug.'+value not in english:
                    errors.append(location+': отсутствует debug-ключ '+value)
                calls+=1;continue
            if re.search('[А-Яа-яЁё]',value) and name not in INTENTIONAL and value not in UI_CATALOG:
                errors.append(location+': неизвестный русский текст вне каталога '+value)
            if re.search('[A-Za-zА-Яа-яЁё]',value) and SINK.search(prefix):raw[value]+=1
        allowed=Counter(REVIEWED.get(name,{}))
        for value,count in (raw-allowed).items():errors.append(name+': жёстко заданный UI-текст '+repr(value)+f' ({count})')
    if errors:raise ValueError('\n'.join(errors))
    return len(paths),calls


def final_upstream_catalog_contract(source):
    """Verify the exact late 13.2 catalogs, without unwrapping historical stages."""
    from validate_upstream_13_2_release import checked_plan, checked_sdk_plans
    plan=checked_plan('upstream_13_2_release_post')
    _,final_outputs=checked_sdk_plans(plan)
    wide=checked_plan('wide_tab_bar_setting')
    wide_key='NagramiX.Settings.Tabs.WideBar'
    round_video=checked_plan('round_video_editor')
    round_keys=['NagramiX.RoundVideo.Title','NagramiX.RoundVideo.CropHint']
    round_name='round_video_editor/localization.json'
    round_data=(OVERLAY/round_name).read_bytes()
    if hashlib.sha256(round_data).hexdigest()!=round_video['templates'][round_name]:
        raise ValueError('Изменён реестр переводов круглого видео')
    round_translations=json.loads(round_data)
    premium=checked_plan('hide_premium_offers')
    premium_keys=['NagramiX.Settings.HidePremiumOffers','NagramiX.Settings.HidePremiumOffersInfo']
    premium_name='hide_premium_offers/localization.json'
    premium_data=(OVERLAY/premium_name).read_bytes()
    if hashlib.sha256(premium_data).hexdigest()!=premium['templates'][premium_name]:
        raise ValueError('Изменён реестр переводов скрытия Premium')
    premium_translations=json.loads(premium_data)
    consent=checked_plan('content_interaction_consent')
    consent_key='NagramiX.Temporary.MarkOpened'
    consent_name='content_interaction_consent/localization.json'
    consent_data=(OVERLAY/consent_name).read_bytes()
    if hashlib.sha256(consent_data).hexdigest()!=consent['templates'][consent_name]:
        raise ValueError('Изменён реестр переводов явного открытия')
    consent_translations=json.loads(consent_data)
    premium_label=checked_plan('premium_label_cleanup')
    label_name='premium_label_cleanup/localization.json'
    label_data=(OVERLAY/label_name).read_bytes()
    if hashlib.sha256(label_data).hexdigest()!=premium_label['templates'][label_name]:
        raise ValueError('Изменён реестр названия Premium-переключателя')
    label_translations=json.loads(label_data)
    label_spelling=checked_plan('premium_label_spelling')
    spelling_name='premium_label_spelling/localization.json'
    spelling_data=(OVERLAY/spelling_name).read_bytes()
    if hashlib.sha256(spelling_data).hexdigest()!=label_spelling['templates'][spelling_name]:
        raise ValueError('Изменён реестр уточнённого названия Premium')
    spelling_translations=json.loads(spelling_data)
    label_resources={'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings'}
    if set(label_translations)!={'ru'} or {p for p in premium_label['outputs'] if p.endswith('.lproj/Localizable.strings')}!=label_resources:
        raise ValueError('Неверный набор ресурсов переименования Premium')
    if set(spelling_translations)!={'ru'} or set(label_spelling['outputs'])!=label_resources:
        raise ValueError('Неверный набор ресурсов уточнения названия Premium')
    name='upstream_13_2_release/localization.json'
    data=(OVERLAY/name).read_bytes()
    if hashlib.sha256(data).hexdigest()!=plan['templates'][name]:
        raise ValueError('Изменён реестр новых переводов Telegram13.2')
    localization=json.loads(data)
    codes={item['code'] for item in json.loads((OVERLAY/'app_language_localization/languages.json').read_text())['languages']}
    if set(localization['translations'])!=codes or len(localization['keys'])!=16:
        raise ValueError('Неполный реестр новых переводов Telegram13.2')
    if set(round_translations)!=codes:
        raise ValueError('Неполные переводы круглого видео')
    if set(consent_translations)!=codes:
        raise ValueError('Неполные переводы явного открытия')
    if set(premium_translations)!=codes:
        raise ValueError('Неполные переводы скрытия Premium')
    for code in sorted(codes):
        path='submodules/NagramiXCore/Resources/'+code+'.lproj/Localizable.strings'
        if hashlib.sha256((source/path).read_bytes()).hexdigest()!=final_outputs[path]:
            raise ValueError('Изменён итоговый каталог: '+code)
        final_values=strings(source/path)
        label_values=strings(OVERLAY/label_spelling['previous'][path]) if path in label_resources else final_values
        # Validate historical translations against the exact pinned preimage;
        # the new stage changes one existing Russian title, adding no keys.
        values=strings(OVERLAY/premium_label['previous'][path]) if path in label_resources else final_values
        original=strings(OVERLAY/plan['replacements'][path])
        if values.keys()!=original.keys()|{wide_key}|set(round_keys)|set(premium_keys)|{consent_key} or any(values.get(key)!=value for key,value in original.items()):
            raise ValueError('Изменены прежние переводы или набор новых ключей: '+code)
        if path not in wide['outputs'] or round_video['inputs'].get(path)!=wide['outputs'][path] or premium['inputs'].get(path)!=round_video['outputs'].get(path) or consent['inputs'].get(path)!=premium['outputs'].get(path) or final_outputs[path]!=label_spelling['outputs'].get(path,premium_label['outputs'].get(path,consent['outputs'].get(path))):
            raise ValueError('Нет точного позднего контракта перевода широкой панели: '+code)
        if path in label_resources and (premium_label['inputs'][path]!=consent['outputs'].get(path) or label_values!={**values,premium_keys[0]:label_translations[code]}):
            raise ValueError('Изменены другие переводы при переименовании Premium: '+code)
        if path in label_resources and (label_spelling['inputs'][path]!=premium_label['outputs'].get(path) or final_values!={**label_values,premium_keys[0]:spelling_translations[code]}):
            raise ValueError('Изменены другие переводы при уточнении названия Premium: '+code)
        prior=strings(OVERLAY/round_video['previous'][path])
        if any(values.get(key)!=value for key,value in prior.items()):
            raise ValueError('Изменены прежние переводы перед круглым видео: '+code)
        if len(round_translations[code])!=2 or any(values.get(key)!=value for key,value in zip(round_keys,round_translations[code])):
            raise ValueError('Неверный перевод круглого видео: '+code)
        prior=strings(OVERLAY/premium['previous'][path])
        if any(values.get(key)!=value for key,value in prior.items()):
            raise ValueError('Изменены прежние переводы перед скрытием Premium: '+code)
        if len(premium_translations[code])!=2 or any(values.get(key)!=value for key,value in zip(premium_keys,premium_translations[code])):
            raise ValueError('Неверный перевод скрытия Premium: '+code)
        prior=strings(OVERLAY/consent['previous'][path])
        if any(values.get(key)!=value for key,value in prior.items()) or consent_translations[code]!=[values.get(consent_key)]:
            raise ValueError('Изменён каталог явного открытия: '+code)
        translations=localization['translations'][code]
        if len(translations)!=len(localization['keys']):
            raise ValueError('Неполные новые переводы: '+code)
        for key,value in zip(localization['keys'],translations):
            if values.get('NagramiX.Debug.'+key)!=value:
                raise ValueError('Неверный новый перевод: '+code+' '+key)
    languages,keys=catalog_contract(source,codes)
    if languages!=71 or keys!=635 or keys!=localization['key_count']+6:
        raise ValueError('Неполный итоговый набор языков/ключей Telegram13.2')
    return languages,keys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path)
    parser.add_argument('--source-contract-only',action='store_true',help='Только локальная проверка исходников; не готовность локализации к выпуску')
    parser.add_argument('--final-upstream-13-2',action='store_true',help='Проверить итоговые 71×635 каталоги после переноса на Telegram13.2 и поздних исходных стадий')
    args=parser.parse_args()
    if args.final_upstream_13_2 and (args.source_contract_only or not args.swiftc):
        parser.error('--final-upstream-13-2 требует --swiftc и полную проверку')
    paths,calls=source_contract(args.source)
    print(f'PASS: {paths} файлов настроек/debug/NagramiX; {calls} обращений к локализации; новых raw UI-строк нет.',flush=True)
    if args.source_contract_only:
        print('Полнота языков не проверялась. Это не проверка готовности выпуска.')
        return
    # Inspect the final tree before historical validators unwrap late stages.
    # A future feature cannot hide a missing new key by restoring old resources.
    languages,keys=final_upstream_catalog_contract(args.source) if args.final_upstream_13_2 else catalog_contract(args.source)
    print(f'PASS: текущая композиция — {languages} языков по {keys} ключей.',flush=True)
    if args.final_upstream_13_2:
        runtime_checks(args.source,args.swiftc)
        return
    command=[sys.executable,str(ROOT/'scripts/validate_app_language_localization.py'),'--source',str(args.source)]
    if args.swiftc:command+=['--swiftc',str(args.swiftc)]
    subprocess.run(command,check=True)

if __name__=='__main__':
    try:main()
    except ValueError as error:raise SystemExit(str(error)) from None
