"""Общее правило регистра для заголовков категорий настроек NagramiX."""
import re
from swift_member_code import code_view

SETTINGS='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'

def check(text):
    # Ignore comments/literals while preserving real source positions and nesting.
    code=code_view(text)
    headers=0
    for match in re.finditer(r'\bItemListSectionHeaderItem\s*\(',code):
        start=match.end();end=start;depth=1
        while depth and end<len(code):
            if code[end]=='(':depth+=1
            elif code[end]==')':depth-=1
            end+=1
        if depth:raise ValueError('Незавершённый ItemListSectionHeaderItem')
        call=code[start:end-1]
        argument=re.search(r'\btext\s*:',call)
        if argument is None:raise ValueError('У заголовка категории нет text')
        a=argument.end();b=a;level=0
        while b<len(call):
            if call[b] in '([{':level+=1
            elif call[b] in ')]}':level-=1
            elif call[b]==',' and level==0:break
            b+=1
        expression=call[a:b].strip()
        if not re.search(r'\.\s*uppercased\s*\(\s*\)\s*$',expression):
            line=text.count('\n',0,match.start())+1
            raise ValueError(f'{SETTINGS}:{line}: заголовок категории должен использовать .uppercased() после локализации')
        headers+=1
    if not headers:raise ValueError('Не найдены заголовки категорий настроек')
    return {'section_headers':headers,'explicit_uppercase_after_localization':headers,'scope':SETTINGS}
