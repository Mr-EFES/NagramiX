#!/usr/bin/env python3
"""Проверить память локальной расшифровки и ограниченные PCM-буферы."""
import argparse,copy,hashlib,importlib.util,json,resource,shutil,subprocess,tempfile
from pathlib import Path
from validate_quick_format import block,manifest
ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
PLAN=json.loads((OVERLAY/'local_asr_memory_patches.json').read_text())
P='submodules/NagramiXTranscription/'
A=P+'Sources/Whisper.swift'
V=P+'Sources/VoskRecognizer.swift'
M=P+'Sources/MediaPreparation.swift'
C=P+'Whisper/Bridge.cpp'
F=P+'Sources/LocalInferenceMemory.swift'
def sha(data):return hashlib.sha256(data).hexdigest()

def verify(source):
    for name,digest in {**PLAN['outputs'],**PLAN['guards']}.items():assert sha((source/name).read_bytes())==digest,name
    for name,item in PLAN['copies'].items():assert sha((source/name).read_bytes())==item['sha256'],name
    for name,digest in PLAN['templates'].items():assert sha((OVERLAY/name).read_bytes())==digest,name
    for name in [A,V]:
        text=(source/name).read_text()
        assert 'os_proc_available_memory() >=' not in text and 'media.pcm(' not in text
        assert text.count('NagramiXLocalInferenceMemory.require(required)')==2
        assert 'NagramiXLocalInferenceMemory.queue.async' in text and 'autoreleasepool' in text
    assert 'cp.flash_attn = true' in (source/C).read_text()
    assert 'params.greedy.best_of = 1' in (source/C).read_text()
    assert 'std::bad_alloc' in (source/C).read_text()
    old_model=block((OVERLAY/PLAN['previous'][V]).read_text(),'    static func model(')
    old_default='return matching.first { NagramiXVoskModels.shared.installed($0) } ?? matching.first { $0.type == "small" } ?? matching.first'
    new_default='let mobile = matching.filter { $0.type == "small" }\n        return mobile.first { NagramiXVoskModels.shared.installed($0) } ?? mobile.first'
    assert block((source/V).read_text(),'    static func model(')==old_model.replace(old_default,new_default)
    preferences=(source/(P+'Sources/Preferences.swift')).read_text()
    before_preferences=(OVERLAY/PLAN['previous'][P+'Sources/Preferences.swift']).read_text()
    expected_title=block(before_preferences,'    private func whisperModelTitle(')
    expected_title=expected_title.replace('switch model {\n','switch model {\n        case .base: return self.presentationData.strings.nagramiXUILocalized("Базовая") + " · " + model.title\n        case .large_v3_turbo_q8_0: return self.presentationData.strings.nagramiXUILocalized("Максимальная") + " · " + model.title\n',1)
    expected_title=expected_title.replace('case .small_full: return (self.presentationData.strings.nagramiXUILocalized("Базовая"))','case .small_full: return self.presentationData.strings.nagramiXUILocalized("Средняя") + " · " + model.title')
    assert block(preferences,'    private func whisperModelTitle(')==expected_title,'Only requested tier labels change; all use existing localized keys'
    assert preferences.count('NagramiXLocalInferenceMemory.whisperModels.map')==1
    assert preferences.count('NagramiXLocalInferenceMemory.voskModels(language: code)')==1
    assert 'let codes = NagramiXLocalInferenceMemory.voskLanguages.sorted' in preferences
    before_settings=(OVERLAY/PLAN['previous'][P+'Sources/Settings.swift']).read_text()
    assert (source/(P+'Sources/Settings.swift')).read_text()==before_settings.replace('public var whisper: NagramiXWhisperModel = .small_full','public var whisper: NagramiXWhisperModel = .base')
    models_path=P+'Sources/VoskModels.swift'
    previous_models=(OVERLAY/PLAN['previous'][models_path]).read_text()
    current_models=(source/models_path).read_text()
    import re
    pattern=r'private static let catalog = #"(.*?)"#'
    old_rows=json.loads(re.search(pattern,previous_models)[1])
    rows=json.loads(re.search(pattern,current_models)[1])
    assert rows[:-1]==old_rows and len(old_rows)==52
    assert rows[-1]['name']=='vosk-model-ru-0.10-lgraph' and rows[-1]['obsolete']=='true'
    assert rows[-1]['size']==175747869 and rows[-1]['md5']=='dc070919ee619c3c928e8cd939dc5f5b'
    # Installer, digest/ZIP/path/lease rules remain byte-identical.
    assert block(previous_models,'final class NagramiXVoskModels:')==block(current_models,'final class NagramiXVoskModels:')
    media=(source/M).read_text();before=(OVERLAY/PLAN['previous'][M]).read_text()
    assert block(media,'private final class NagramiXAudioPreparation')==block(before,'private final class NagramiXAudioPreparation')

def guard_checks(source,temp):
    spec=importlib.util.spec_from_file_location('local_asr_memory',OVERLAY/'local_asr_memory.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[]
    def seed(label):
        target=temp/label
        for name in {**PLAN['inputs'],**PLAN['guards']}:
            data=(OVERLAY/PLAN['previous'][name]).read_bytes() if name in PLAN['previous'] else (source/name).read_bytes()
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        return target
    def reject(target,label,overlay=OVERLAY):
        before=manifest(target)
        try:module.apply_local_asr_memory(target,overlay)
        except (SystemExit,OSError):pass
        else:raise AssertionError('Invalid input accepted: '+label)
        assert manifest(target)==before,'Partial write: '+label
        rejected.append(label)
    valid=seed('valid');module.apply_local_asr_memory(valid,OVERLAY)
    assert all((valid/name).read_bytes()==(source/name).read_bytes() for name in PLAN['outputs'])
    for name,item in PLAN['copies'].items():assert (valid/name).read_bytes()==(source/name).read_bytes()
    reject(valid,'repeat')
    for name in {**PLAN['inputs'],**PLAN['guards']}:
        for kind in ['missing','drift']:
            target=seed(str(len(rejected)));path=target/name
            if kind=='missing':path.unlink()
            else:path.write_bytes(path.read_bytes()+b'\n// drift\n')
            reject(target,kind+' '+name)
    mutations=[]
    for field in ['inputs','outputs','guards','templates']:
        bad=copy.deepcopy(PLAN);bad[field][next(iter(bad[field]))]='0'*64;mutations.append((field+'-SHA',bad))
    for field in ['previous','replacements']:
        bad=copy.deepcopy(PLAN);bad[field][A]='../outside.swift';mutations.append((field+'-traversal',bad))
    bad=copy.deepcopy(PLAN)
    for field in ['inputs','outputs','previous','replacements']:bad[field]['../outside.swift']=bad[field].pop(A)
    mutations.append(('source-traversal',bad))
    bad=copy.deepcopy(PLAN);bad['outputs'].pop(A);mutations.append(('inconsistent-keys',bad))
    for label,bad in mutations:
        overlay=temp/('overlay-'+label)
        for name in PLAN['templates']:
            path=overlay/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((OVERLAY/name).read_bytes())
        (overlay/'local_asr_memory_patches.json').write_text(json.dumps(bad))
        reject(seed('source-'+label),label,overlay)
    for label,name in [('input-symlink',A),('guard-symlink',next(iter(PLAN['guards'])))]:
        target=seed(label);path=target/name;external=temp/(label+'.swift');external.write_bytes(path.read_bytes());path.unlink();path.symlink_to(external)
        reject(target,label)
    # A bad final template must be rejected before writing even the first file.
    overlay=temp/'overlay-last-template'
    for name in PLAN['templates']:
        path=overlay/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((OVERLAY/name).read_bytes())
    (overlay/'local_asr_memory_patches.json').write_text(json.dumps(PLAN))
    (overlay/next(reversed(PLAN['replacements'].values()))).write_bytes(b'bad final template')
    reject(seed('last-template'),'last-output-template',overlay)
    helper=next(iter(PLAN['copies']))
    for label,kind in [('copy-collision','existing'),('copy-broken-symlink','link')]:
        target=seed(label);path=target/helper;path.parent.mkdir(parents=True,exist_ok=True)
        if kind=='existing':path.write_bytes(b'existing')
        else:path.symlink_to(temp/'missing-helper')
        reject(target,label)
    return rejected

def runtime_source(source, mode='current'):
    root=ROOT
    native=source/'submodules/NagramiXTranscription'
    boundary=(root/'scripts/tests/NagramiXLocalASRMemoryBoundary.swift').read_text()
    media=block((native/'Sources/MediaPreparation.swift').read_text(),'    func withPCM<T>(').replace('.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication','.posixPermissions: 0o600')
    if mode=='old-pcm':
        media=block((OVERLAY/PLAN['previous'][M]).read_text(),'    func pcm(cancellation:')+'''
        func withPCM<T>(cancellation:NagramiXTranscriptionCancellation,_ body:(UnsafeBufferPointer<Float>)throws->T)throws->T {
            let samples=try self.pcm(cancellation:cancellation)
            return try samples.withUnsafeBufferPointer(body)
        }
    '''
    boundary=boundary.replace('    // ACTUAL_WITH_PCM',media)
    text=boundary+'\n'+(native/'Sources/Settings.swift').read_text()+'\n'
    text+=block((native/'Sources/VoskModels.swift').read_text(),'struct NagramiXVoskModel:')+'\n'
    for file in ['LocalInferenceMemory.swift','Whisper.swift','VoskRecognizer.swift']:
     code=(native/'Sources'/file).read_text();text+='\n'+'\n'.join(l for l in code.splitlines() if not l.startswith('import '))+'\n'
    if mode=='old-budget':
        current=block(text,'    static func whisper(')
        text=text.replace(current,'''    static func whisper(_ model:NagramiXWhisperModel)throws->UInt64 {UInt64(model.size)*2+512*mib}''')
    text+=(root/'scripts/tests/NagramiXLocalASRMemoryTests.swift').read_text()
    return text

def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def preferences_actions_checks(source, swiftc, temp):
    name=P+'Sources/Preferences.swift'
    boundary=(ROOT/'scripts/tests/NagramiXModelDeletionActions.swift').read_text()
    results=[]
    for previous in [False, True]:
        code=(OVERLAY/PLAN['previous'][name] if previous else source/name).read_text()
        method=block(code,'    public func tableView(_ tableView: UITableView, trailingSwipeActionsConfigurationForRowAt')
        method=method.replace('public func tableView(', 'func tableView(', 1)
        path=temp/('previous-model-actions.swift' if previous else 'model-actions.swift')
        path.write_text(boundary.replace('    // ACTUAL_SWIPE_ACTIONS',method))
        command=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache')]
        if previous:
            result=subprocess.run([*command,'-typecheck',str(path)],capture_output=True,text=True)
            errors=[line for line in result.stderr.splitlines() if 'previous-model-actions.swift:' in line and ': error:' in line]
            assert result.returncode!=0 and len(errors)==2 and all("must be unwrapped to refer to member 'presentationData'" in line for line in errors),result.stderr
            message='Previous weak-self localization SDK error reproduced and rejected'
            print(message,flush=True);results.append(message)
        else:
            for optimized in [False,True]:
                binary=temp/('model-actions-O' if optimized else 'model-actions-debug')
                subprocess.run([*command,*(['-O'] if optimized else []),str(path),'-o',str(binary)],check=True)
                result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=10,preexec_fn=no_core)
                assert result.returncode==0,result.stdout+result.stderr
                print(result.stdout.strip(),flush=True);results.append(result.stdout.strip())
    return results

def execute(source,swiftc,cxx,temp):
    runs=[]
    if swiftc:
        runs.extend(preferences_actions_checks(source,swiftc,temp))
        for mode in ['current','old-budget','old-pcm']:
            path=temp/(mode+'.swift');path.write_text(runtime_source(source,mode))
            for optimized in [False,True]:
                label=mode+('-O' if optimized else '-debug');binary=temp/label
                command=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache')]
                if optimized:command.append('-O')
                subprocess.run([*command,str(path),'-o',str(binary)],check=True)
                r=subprocess.run([str(binary)],capture_output=True,text=True,preexec_fn=no_core,timeout=30)
                if mode=='current':assert r.returncode==0,r.stdout+r.stderr;message=r.stdout.strip()
                else:
                    expected='two copies of its weights' if mode=='old-budget' else 'bounded at 64KB'
                    assert r.returncode!=0 and 'local ASR memory regression:' in r.stderr and expected in r.stderr,(r.stdout,r.stderr)
                    message='Previous implementation rejected by regression suite'
                print(label+': '+message,flush=True);runs.append(label+': '+message)
        for name in [*PLAN['outputs'],*PLAN['copies']]:
            if name.endswith('.swift'):subprocess.run([str(swiftc),'-frontend','-parse',str(source/name)],check=True)
    if cxx:
        include=temp/'include';include.mkdir();(include/'whisper.h').write_bytes((ROOT/'scripts/tests/NagramiXWhisperMemoryAPI.h').read_bytes())
        for old in [False,True]:
            path=temp/('old-bridge.cpp' if old else 'bridge.cpp')
            path.write_bytes((OVERLAY/PLAN['previous'][C]).read_bytes() if old else (source/C).read_bytes())
            binary=temp/('old-native' if old else 'native')
            subprocess.run([str(cxx),'-std=c++17','-O2','-Wall','-Wextra','-Werror',str(path),str(ROOT/'scripts/tests/NagramiXWhisperMemoryBoundary.cpp'),'-I',str(source/(P+'Whisper')),'-I',str(include),'-o',str(binary)],check=True)
            r=subprocess.run([str(binary)],capture_output=True,text=True,preexec_fn=no_core,timeout=10)
            if old:assert r.returncode!=0 and 'flash' in r.stderr;message='Previous full-attention bridge rejected'
            else:assert r.returncode==0,r.stdout+r.stderr;message=r.stdout.strip()
            print(message,flush=True);runs.append(message)
    return runs


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--cxx',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_visual_handoff'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_menu'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_visibility'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'temporary_media_actions'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'message_copy_availability'):
        return
    if delegate_icon_stage_if_applied(args,Path(__file__),'vosk_model_naming'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='local-asr-memory-') as folder:
        temp=Path(folder);rejected=guard_checks(args.source,temp);runs=execute(args.source,args.swiftc,args.cxx or shutil.which('c++'),temp)
    result={'replacements':len(PLAN['outputs']),'copies':len(PLAN['copies']),'guards':len(PLAN['guards']),'fail_closed':rejected,'executions':runs,'sdk':'not run','device':'pending; physical RAM and process budget remain real limits','boundaries':'Swift actual budgets, FST parsing, filesystem scanning, PCM IO/mapping and recognizer orchestration. AVFoundation, os headroom, pools and native inference are explicit test boundaries; portable C++ suite stubs whisper C API.'}
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
