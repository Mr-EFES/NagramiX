"""Check native members against Telegram's real generated Objective-C header."""
import hashlib,re,subprocess,sys,types
from pathlib import Path
from localization_literals import _comment_end,_opening,quoted

EN='Telegram/Telegram-iOS/en.lproj/Localizable.strings'
GEN='build-system/GenerateStrings/GenerateStrings.py'
BUILD='Telegram/BUILD'
MENU='submodules/TelegramUI/Sources/ChatControllerOpenAttachmentMenu.swift'
USE=re.compile(r'\b(strings|[a-z]\w*[sS]trings)\s*[!?]?\s*\.\s*([A-Z]\w*)')
TOKENS=re.compile(r'//|/\*|#+"|"')

def code_views(text):
    """Preserve offsets; ignore comments and distinguish lexical type scopes."""
    audit=[];scopes=[];cursor=0
    while True:
        token=TOKENS.search(text,cursor)
        if token is None:break
        start=token.start();audit.append(text[cursor:start]);scopes.append(text[cursor:start])
        end=_comment_end(text,start)
        if end is not None:
            masked=re.sub(r'[^\n]',' ',text[start:end]);audit.append(masked);scopes.append(masked)
        elif _opening(text,start):
            end,_=quoted(text,start)
            # Keep interpolated uses visible to the name audit. Text examples
            # inside literals are conservative candidates, never ignored errors.
            audit.append(text[start:end]);scopes.append(re.sub(r'[^\n]',' ',text[start:end]))
        else:
            end=start+1;audit.append(text[start:end]);scopes.append(text[start:end])
        cursor=end
    audit.append(text[cursor:]);scopes.append(text[cursor:])
    return ''.join(audit),''.join(scopes)

def other_owner_proof(code,position,receiver,member):
    # PresentationData.strings is never confused with a same-named local.
    if code[:position].rstrip().endswith('.'):return False
    pairs={};stack=[]
    for i,c in enumerate(code):
        if c=='{':stack.append(i)
        elif c=='}' and stack:pairs[stack.pop()]=i
    candidates=[]
    for f in re.finditer(r'\b(?:init|func[ \t]+\w+)[ \t]*\([^{}]*\)[^{\n]*\{',code):
        start=f.end()-1;end=pairs.get(start,-1)
        if start<position<end:
            kind=re.search(r'\b'+re.escape(receiver)+r'\s*:\s*(\w+)',f.group())
            if kind:candidates.append((start,kind[1]))
    if not candidates:return False
    _,kind=max(candidates)
    if kind in ('PresentationStrings','_PresentationStrings'):return False
    declaration=re.search(r'\b(?:struct|class)\s+'+re.escape(kind)+r'\b[^{}]*\{',code)
    if not declaration:return False
    start=declaration.end()-1;end=pairs.get(start,-1)
    return member in re.findall(r'\b(?:let|var)\s+([A-Z]\w*)\s*:',code[start:end])

def generate(source,folder):
    build=(source/BUILD).read_text()
    assert 'name = "GeneratedPresentationStrings"' in build
    assert '--source=$(location Telegram-iOS/en.lproj/Localizable.strings)' in build
    # Execute the exact pinned generator without importing it from the source
    # directory: importlib would create __pycache__ inside the reviewed tree.
    module=types.ModuleType('actual_native_generate_strings');module.__file__=str(source/GEN)
    exec(compile((source/GEN).read_bytes(),str(source/GEN),'exec'),module.__dict__)
    entries=module.parse_entries(module.parse_strings(str(source/EN)))
    header=folder/'PresentationStrings.h'
    module.generate(str(header),str(folder/'PresentationStrings.m'),str(folder/'PresentationStrings.data'),entries)
    names=set(re.findall(r'__swift_name__\("(?:getter:)?_PresentationStrings\.(\w+)\(self:',header.read_text()))
    assert names=={module.sanitize_entry_identifer(e.name) for e in entries}
    assert len(names)>12000 and 'Login_UnknownError' in names and 'Common_UnknownError' not in names
    return names,header

def audit(texts,names):
    count=0;used=set();others=0;errors=[]
    for name,text in texts.items():
        if 'strings' not in text and 'Strings' not in text:continue
        try:clean,scope=code_views(text)
        except ValueError as error:raise ValueError(name+': '+str(error)) from error
        for match in USE.finditer(clean):
            receiver,member=match[1],match[2]
            if member not in names:
                if other_owner_proof(scope,match.start(),receiver,member):others+=1;continue
                errors.append(f'{name}:{text.count(chr(10),0,match.start())+1}: undeclared native PresentationStrings.{member}')
            else:count+=1;used.add(member)
    if errors:raise ValueError('\n'.join(errors))
    return {'swift_files':len(texts),'native_generated_members':len(names),'native_string_uses':count,'distinct_native_members':len(used),'proven_other_typed_owner_reads':others},used

def apple_header_check(header,used,swiftc,folder):
    if sys.platform!='darwin' or swiftc is None:return {'status':'not_run','reason':'Real Objective-C/Apple SDK import requires macOS and swiftc'}
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    (folder/'module.modulemap').write_text('module ActualNativeStrings { header "PresentationStrings.h" export * }\n')
    base=[str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-I',str(folder),'-module-cache-path',str(folder/'native-sdk-cache')]
    prefix='import Foundation\nimport ActualNativeStrings\nfunc actualNativeMemberUses(_ strings:_PresentationStrings) {\n'
    path=folder/'actual-native-uses.swift';path.write_text(prefix+''.join(' _ = strings.'+name+'\n' for name in sorted(used))+'}\n')
    result=subprocess.run(base+[str(path)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+result.stderr
    path=folder/'sdk200-rejected.swift';path.write_text(prefix+' _ = strings.Common_UnknownError\n}\n')
    bad=subprocess.run(base+[str(path)],capture_output=True,text=True,timeout=60)
    assert bad.returncode!=0 and "has no member 'Common_UnknownError'" in bad.stderr,bad.stdout+bad.stderr
    return {'status':'passed','generated_objc_header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'actual_native_member_expressions':len(used),'sdk200_missing_member_rejected':True,'target':'arm64-apple-ios15.0'}

def check(source,texts,swiftc,folder):
    names,header=generate(source,folder);report,used=audit(texts,names)
    assert MENU in texts and texts[MENU].count('strings.Login_UnknownError')>=2
    bad=dict(texts);bad[MENU]=bad[MENU].replace('strings.Login_UnknownError','strings.Common_UnknownError',1)
    try:audit(bad,names)
    except ValueError as e:assert 'Common_UnknownError' in str(e)
    else:raise AssertionError('SDK200 regression accepted by native getter audit')
    report['sdk200_mutation_rejected']=True
    report['apple_actual_generated_header']=apple_header_check(header,used,swiftc,folder)
    report['boundary']='Actual native GenerateStrings.py, build rule and final English catalog; generated member existence through strings/namedStrings receivers. Other typed owners need source declaration evidence. Full Swift call arity/type checking and app runtime still require SDK/device.'
    return report
