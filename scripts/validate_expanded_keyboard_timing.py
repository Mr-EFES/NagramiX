#!/usr/bin/env python3
"""Проверить ненулевую длительность переключений редактора после видео владельца."""
import argparse,copy,hashlib,importlib.util,json,resource,subprocess,sys,tempfile
from pathlib import Path
from validate_quick_format import block,manifest
from validate_expanded_panel_animation import runtime_source as panel_runtime
ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
PLAN=json.loads((OVERLAY/'expanded_keyboard_timing_patches.json').read_text())
E='submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextEmojiKeyboardController.swift'
ADAPTER='submodules/Components/ComponentDisplayAdapters/Sources/ComponentDisplayAdapters.swift'
WINDOW='submodules/Display/Source/WindowContent.swift'
def sha(data):return hashlib.sha256(data).hexdigest()

def verify(source):
    for name,digest in {**PLAN['outputs'],**PLAN['guards']}.items():assert sha((source/name).read_bytes())==digest,name
    for name,digest in PLAN['templates'].items():assert sha((OVERLAY/name).read_bytes())==digest,name
    text=(source/E).read_text()
    for old,new,count in reversed(PLAN['operations'][E]):
        assert text.count(new)==count;text=text.replace(new,old)
    assert text==(OVERLAY/PLAN['previous'][E]).read_text()
    window=(source/WINDOW).read_text()
    assert 'UIResponder.keyboardAnimationDurationUserInfoKey' in window
    assert 'var transition: ContainedViewLayoutTransition = .animated(duration: duration, curve: transitionCurve)' in window

def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('expanded_keyboard_timing', OVERLAY / 'expanded_keyboard_timing.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def seed(label):
        target = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            data = (OVERLAY / PLAN['previous'][name]).read_bytes() if name in PLAN['previous'] else (source / name).read_bytes()
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return target
    rejected = []
    def reject(target, label, overlay=OVERLAY):
        before = manifest(target)
        try:
            module.apply_expanded_keyboard_timing(target, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Неверный вход принят: ' + label)
        assert manifest(target) == before, 'Частичная запись: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_expanded_keyboard_timing(valid, OVERLAY)
    assert all((valid / name).read_bytes() == (source / name).read_bytes() for name in PLAN['outputs'])
    reject(valid, 'повторное применение')
    for name in {**PLAN['inputs'], **PLAN['guards']}:
        for kind in ('missing', 'drift'):
            target = seed(str(len(rejected)))
            path = target / name
            if kind == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes() + b'\n// drift\n')
            reject(target, kind + ' ' + name)
    mutations = []
    for field in ('inputs', 'outputs', 'guards', 'templates'):
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        mutations.append((field + '-SHA', bad))
    bad = copy.deepcopy(PLAN)
    bad['operations'][E][0][0] += ' broken'
    mutations.append(('anchor', bad))
    bad = copy.deepcopy(PLAN)
    bad['previous'][E] = '../outside.swift'
    mutations.append(('template-traversal', bad))
    bad = copy.deepcopy(PLAN)
    for field in ('inputs', 'outputs', 'previous', 'operations'):
        bad[field]['../outside.swift'] = bad[field].pop(E)
    mutations.append(('source-traversal', bad))
    bad = copy.deepcopy(PLAN)
    bad['operations']['/outside.swift'] = bad['operations'].pop(E)
    mutations.append(('operation-path', bad))
    for label, bad in mutations:
        overlay = temp / ('bad-' + label)
        overlay.mkdir()
        for path in PLAN['templates']:
            destination = overlay / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((OVERLAY / path).read_bytes())
        (overlay / 'expanded_keyboard_timing_patches.json').write_text(json.dumps(bad))
        reject(seed('root-' + label), label, overlay)
    for label, name in [('input-symlink', E), ('guard-symlink', next(iter(PLAN['guards'])))]:
        target = seed(label)
        path = target / name
        external = temp / (label + '.swift')
        external.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(external)
        reject(target, label)
    return rejected


def runtime_source(source, old=False):
    text=panel_runtime(source).replace('@main enum Tests','enum Tests')
    if old:
        current=block((source/E).read_text(),'struct NagramiXExpandedPanelAnimation')
        before=block((OVERLAY/PLAN['previous'][E]).read_text(),'struct NagramiXExpandedPanelAnimation')
        assert text.count(current)==1;text=text.replace(current,before)
    text=text.replace('enum Curve: Equatable { case spring, keyboard, linear }','enum Curve: Equatable { case spring, keyboard, linear, easeInOut, easeIn, custom(Float, Float, Float, Float) }')
    adapter=(source/ADAPTER).read_text()
    curve=block(adapter,'init(_ curve: ContainedViewLayoutTransitionCurve)')
    conversion=block(adapter,'init(_ transition: ContainedViewLayoutTransition)')
    text+='''
enum ContainedViewLayoutTransitionCurve {
    case linear, easeInOut, easeIn, spring, customSpring
    case custom(Float, Float, Float, Float)
}
enum ContainedViewLayoutTransition {
    case immediate
    case animated(duration: Double, curve: ContainedViewLayoutTransitionCurve)
}
'''
    text+='\nextension ComponentTransition.Animation.Curve {\n'+curve+'\n}\n'
    text+='\nextension ComponentTransition {\n'+conversion+'\n}\n'
    return text+'\n'+(ROOT/'scripts/tests/NagramiXExpandedTimingTests.swift').read_text()


def run_swift(source,swiftc,temp):
    runs=[]
    def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    for old in [False,True]:
        suite=temp/('old.swift' if old else 'current.swift');suite.write_text(runtime_source(source,old))
        for optimized in [False,True]:
            name=('old-zero-duration' if old else 'current')+('-O' if optimized else '-debug');binary=temp/name
            args=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache')]
            if optimized:args.append('-O')
            subprocess.run([*args,str(suite),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,preexec_fn=no_core)
            if old:
                assert result.returncode!=0 and 'keyboard timing regression:' in result.stderr,(result.stdout,result.stderr)
                message='Прежняя policy пропустила нулевую длительность и отвергнута'
            else:
                assert result.returncode==0,result.stdout+result.stderr;message=result.stdout.strip()
            print(name+': '+message,flush=True);runs.append(name+': '+message)
    return runs


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
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
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-expanded-timing-') as folder:
        temp=Path(folder);rejected=guard_checks(args.source,temp);runs=run_swift(args.source,args.swiftc,temp) if args.swiftc else []
    if args.swiftc:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/E)],check=True)
    result={'changed_files':1,'guards':len(PLAN['guards']),'fail_closed':rejected,'executions':runs,'sdk':'не запускалась','device':'ожидает проверки на iPhone','boundaries':'Native conversion/policy plus existing actual panel/route suite; UIKit/CA and keyboard delivery remain boundaries'}
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
