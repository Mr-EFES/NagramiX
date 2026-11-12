#!/usr/bin/env python3
"""Компилировать настоящее объявление аргументов настроек и порядок всего вызова."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

from validate_quick_format import block
from validate_custom_member_references import canonical_texts
from validate_local_copy_delivery import execute,run

ROOT=Path(__file__).resolve().parents[1]
SETTINGS='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'
NAME='NagramiXSettingsControllerArguments'


def parts(text):
    declaration=block(text,'private struct '+NAME+' {')
    start=text.index('    let arguments = '+NAME+'(')
    end=text.index('\n    )\n',start)+len('\n    )')
    call=text[start:end]
    fields=re.findall(r'^    let (\w+):\s*(.*?)\s*$',declaration,re.M)
    labels=re.findall(r'^        (\w+):',call,re.M)
    assert len(fields)==len(labels) and {n for n,_ in fields}==set(labels)
    return declaration,call,fields,labels


def fixture(text):
    declaration,call,fields,labels=parts(text);types=dict(fields)
    typing_parameter = ''
    if any('NagramiXTypingParameter' in signature for _, signature in fields):
        typing_parameter = block(canonical_texts()['submodules/NagramiXCore/Sources/NagramiXTypingSettings.swift'], 'public enum NagramiXTypingParameter:') + '\n'
    values=[]
    for label in labels:
        signature=types[label];assert signature.endswith(' -> Void')
        inner=signature[1:signature.index(')')];count=0 if not inner else len(inner.split(','))
        value='{ '+', '.join('_' for _ in range(count))+' in }' if count else '{}'
        if label in ['updateRoundVideo','updateBackgroundVideoPlayback']:
            value=re.search(r'^        '+label+r': (.*),$',call,re.M).group(1)
        values.append('        '+label+': '+value)
    return 'import Foundation\n'+typing_parameter+'''
// Legacy privacy parameter types are adapted; the typing parameter enum above
// is its complete guarded production declaration when the caller needs it.
// The compiler binds the real argument struct and every real label.
enum NagramiXReadMode {case standard}
struct NagramiXPrivacySettings {enum Option {case screenshotBypass}}
struct MediaState {var roundVideo=false}
struct SettingsState {var media=MediaState();var backgroundVideoPlayback=false}
private var stored=SettingsState()
private func update(_ f:(inout SettingsState)->Void){f(&stored)}
'''+declaration+'''\nprivate func makeArguments()->'''+NAME+''' {
    return '''+NAME+'(\n'+',\n'.join(values)+'''\n    )
}
@main struct SettingsBindings {
 static func main(){
  let arguments=makeArguments()
  arguments.updateRoundVideo(true)
  precondition(stored.media.roundVideo && !stored.backgroundVideoPlayback)
  arguments.updateBackgroundVideoPlayback(true)
  precondition(stored.media.roundVideo && stored.backgroundVideoPlayback)
  arguments.updateRoundVideo(false)
  precondition(!stored.media.roundVideo && stored.backgroundVideoPlayback)
  print("PASS full settings constructor and independent callbacks")
 }
}
'''


def validate(text,swiftc,folder):
    decl,call,fields,labels=parts(text)
    production=fixture(text);runs=execute(swiftc,folder,'settings-bindings',production)
    assert labels==[name for name,_ in fields],'Memberwise argument declaration/call order differs'
    old=production.replace('        updateBackgroundVideoPlayback: { value in update { $0.backgroundVideoPlayback = value } },\n        updateRoundVideo: { value in update { $0.media.roundVideo = value } },',
        '        updateRoundVideo: { value in update { $0.media.roundVideo = value } },\n        updateBackgroundVideoPlayback: { value in update { $0.backgroundVideoPlayback = value } },',1)
    assert old!=production
    negative=folder/'old-order.swift';negative.write_text(old);failures=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        result=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-module-cache-path',str(folder/'cache'),*flags,'-typecheck',str(negative)],capture_output=True,text=True)
        assert result.returncode!=0 and "argument 'updateBackgroundVideoPlayback' must precede argument 'updateRoundVideo'" in result.stderr,result.stderr
        failures.append({'mode':mode,'original_sdk_error_reproduced':True})
    return {'callback_fields':len(fields),'whole_call_labels_checked':len(labels),'executions':runs,'negative_original_order':failures,'fixture_sha256':hashlib.sha256(production.encode()).hexdigest(),
      'boundary':'Actual complete stored-property declaration and all labels from the production caller. Unrelated callback bodies are neutral; the real round/background callback bodies execute with a typed storage adapter. UIKit and the whole ItemListController graph require SDK compilation.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--source',type=Path);g.add_argument('--canonical',action='store_true');p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    text=(a.source/SETTINGS).read_text() if a.source else canonical_texts()[SETTINGS]
    with tempfile.TemporaryDirectory(prefix='nagramix-settings-bindings-') as d:result=validate(text,a.swiftc,Path(d))
    if a.report:a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
