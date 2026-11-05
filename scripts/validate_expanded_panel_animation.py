#!/usr/bin/env python3
"""Проверить анимацию панелей расширенного редактора и её guarded overlay."""
import argparse,copy,hashlib,importlib.util,json,resource,subprocess,sys,tempfile
from pathlib import Path
from validate_quick_format import block,manifest
ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
PLAN=json.loads((OVERLAY/'expanded_panel_animation_patches.json').read_text())
S='submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextAttachmentScreen.swift'
E='submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextEmojiKeyboardController.swift'
def sha(data):return hashlib.sha256(data).hexdigest()

def verify(source):
    for name,digest in {**PLAN['outputs'],**PLAN['guards']}.items():assert sha((source/name).read_bytes())==digest,name
    for name,digest in PLAN['templates'].items():assert sha((OVERLAY/name).read_bytes())==digest,name
    before=(OVERLAY/PLAN['previous'][E]).read_text();after=(source/E).read_text()
    assert block(before,'struct NagramiXExpandedInputGeometry')==block(after,'struct NagramiXExpandedInputGeometry')
    for method in ['func toggle(', 'func setEmojiMode(', 'func handleInsert(', 'func customEmojiView(']:
        assert block(before,method)==block(after,method),method
    screen=(source/S).read_text();old=(OVERLAY/PLAN['previous'][S]).read_text()
    for method in ['func nagramiXExpandedHasContent(', 'func nagramiXExpandedFormattingAvailable(', 'func nagramiXApplyExpandedFormatting(', 'func nagramiXApplyExpandedExtra(']:
        assert block(old,method)==block(screen,method),method
    assert 'nagramiXPanelSwapPending' not in screen
    assert 'isVisible: !measureOnly || !node.view.isHidden' in after
    assert 'editorAnimation(from: panelTransition)' in screen
    assert 'panelTransition.setFrame(view: actionBarView' in screen

def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('expanded_panel_animation', OVERLAY / 'expanded_panel_animation.py')
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
            module.apply_expanded_panel_animation(target, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Неверный вход принят: ' + label)
        assert manifest(target) == before, 'Частичная запись: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_expanded_panel_animation(valid, OVERLAY)
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
    bad['operations'][S][0][0] += ' broken'
    mutations.append(('anchor', bad))
    bad = copy.deepcopy(PLAN)
    bad['previous'][S] = '../outside.swift'
    mutations.append(('template-traversal', bad))
    bad = copy.deepcopy(PLAN)
    for field in ('inputs', 'outputs', 'previous', 'operations'):
        bad[field]['../outside.swift'] = bad[field].pop(S)
    mutations.append(('source-traversal', bad))
    bad = copy.deepcopy(PLAN)
    bad['operations']['/outside.swift'] = bad['operations'].pop(S)
    mutations.append(('operation-path', bad))
    for label, bad in mutations:
        overlay = temp / ('bad-' + label)
        overlay.mkdir()
        for path in PLAN['templates']:
            destination = overlay / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((OVERLAY / path).read_bytes())
        (overlay / 'expanded_panel_animation_patches.json').write_text(json.dumps(bad))
        reject(seed('root-' + label), label, overlay)
    for label, name in [('input-symlink', S), ('guard-symlink', next(iter(PLAN['guards'])))]:
        target = seed(label)
        path = target / name
        external = temp / (label + '.swift')
        external.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(external)
        reject(target, label)
    return rejected


def runtime_source(source, mode='current'):
    screen=(source/S).read_text();emoji=(source/E).read_text()
    old_screen=(OVERLAY/PLAN['previous'][S]).read_text();old_emoji=(OVERLAY/PLAN['previous'][E]).read_text()
    boundary=(ROOT/'scripts/tests/NagramiXExpandedAnimationBoundary.swift').read_text()
    native=block((source/'submodules/ComponentFlow/Source/Base/Transition.swift').read_text(),'public func setFrame(view:')
    boundary=boundary.replace('// The native setFrame method is inserted here by the validator.',native.replace('public func','func',1))
    geometry=block(emoji,'struct NagramiXExpandedInputGeometry')
    policy=block(emoji,'struct NagramiXExpandedPanelAnimation')
    presentation=block(emoji,'final class NagramiXExpandedPanelPresentation')
    methods=['nagramiXBeginKeyboardHandoff','nagramiXRequestInputPanelLayout','nagramiXSetFormattingMode','nagramiXToggleFormatting','nagramiXToggleEmoji']
    route_source=old_screen if mode in ['old-policy','old-formatting'] else screen
    routes='\n'.join(block(route_source,'func '+name+'(') for name in methods)
    emoji_source=old_emoji if mode=='old-emoji' else emoji
    panel=block(emoji_source,'func updatePanel(')
    # Account/theme construction and native keyboard contents are explicit
    # boundaries. All real visibility/measurement/presentation branches remain.
    a=panel.index('node = ChatEntityKeyboardInputNode(');b=panel.index('\n            node.clipsToBounds',a)
    panel=panel[:a]+'node = ChatEntityKeyboardInputNode(currentData)'+panel[b:]
    a=panel.index('        let presentationData =');b=panel.index('        let deviceMetrics =',a)
    panel=panel[:a]+'        let presentationInterfaceState = 0\n'+panel[b:]
    emoji_routes='\n'.join(block(emoji,'func '+name+'(') for name in ['toggle','setEmojiMode'])
    emoji_host='''
final class EmojiController {
    weak var editor: Editor?
    let requestLayout: () -> Void
    let willRestoreKeyboard: () -> Void
    var currentData: Int? = 1
    var isEmojiMode = false
    var nagramiXMeasuringFormatting = false
    let nagramiXEmptyInputView = EmptyInputView()
    let panelPresentation = NagramiXExpandedPanelPresentation()
    var panelPresented = false
    var inputNode: ChatEntityKeyboardInputNode?
    init(editor: Editor, willRestoreKeyboard: @escaping () -> Void, requestLayout: @escaping () -> Void) {
        self.editor=editor;self.willRestoreKeyboard=willRestoreKeyboard;self.requestLayout=requestLayout
    }
'''+emoji_routes+'\n'+panel+'\n}\n'
    formatter=block(old_screen if mode=='old-formatting' else screen,'private func nagramiXUpdateFormattingPanel(').replace('private func','func',1)
    a=formatter.index('            let strings =')
    b=formatter.index('            if panel.isHidden {',a) if mode=='old-formatting' else formatter.index('            self.nagramiXFormattingPresentation.update(view: panel, frame: CGRect',a)
    # The unchanged formatting actions/labels/content rendering are UIKit
    # bindings; execute the complete real dismissal guard and presentation tail.
    formatter=formatter[:a]+'''            let panel: UIView
            if let current = self.nagramiXFormattingPanel { panel = current }
            else {
                panel = UIView(); panel.isHidden = true
                panel.frame = CGRect(x: 0, y: availableSize.height, width: availableSize.width, height: height)
                self.nagramiXFormattingPanel = panel
            }
'''+formatter[b:]
    coordination_source=old_screen if mode=='old-policy' else screen
    a=coordination_source.index('            let customInputActive =');b=coordination_source.index('            let editorTop =',a)
    coordination=coordination_source[a:b]
    coordination += '\n            self.panelTransition = panelTransition\n            return customInputActive ? max(emojiPanelHeight, environment.safeInsets.bottom) : self.nagramiXInputGeometry.bottomInset\n'
    host='''
final class ExpandedHost: UIView {
    let editor = Editor()
    var componentState: ComponentState? = ComponentState()
    var nagramiXInputGeometry = NagramiXExpandedInputGeometry()
    var nagramiXPanelAnimation = NagramiXExpandedPanelAnimation()
    let nagramiXFormattingPresentation = NagramiXExpandedPanelPresentation()
    var nagramiXFormattingActive = false
    var nagramiXFormattingInputView: UIView?
    var nagramiXFormattingPanel: UIView?
    var nagramiXFormattingGeneration = 0
    var nagramiXPanelSwapPending = false
    var panelTransition = ComponentTransition.immediate
    var emojiKeyboard: EmojiController?
    override init() {
        super.init()
        emojiKeyboard=EmojiController(editor: editor, willRestoreKeyboard: { [weak self] in self?.nagramiXBeginKeyboardHandoff() }, requestLayout: { [weak self] in self?.nagramiXRequestInputPanelLayout() })
    }
'''+routes+'\n'+formatter+'''
    @discardableResult func layout(_ inputHeight: CGFloat, _ transition: ComponentTransition, size availableSize: CGSize = CGSize(width: 393, height: 852)) -> CGFloat {
        let environment=ViewControllerComponentContainer.Environment(inputHeight: inputHeight)
'''+coordination+'\n}\n}\n'
    tests=(ROOT/'scripts/tests/NagramiXExpandedAnimationTests.swift').read_text()
    return '\n'.join([boundary,geometry,policy,presentation,emoji_host,host,tests])


def run_swift(source,swiftc,temp):
    runs=[]
    def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    for mode in ['current','old-policy','old-emoji','old-formatting']:
        suite=temp/(mode+'.swift');suite.write_text(runtime_source(source,mode))
        for optimized in [False,True]:
            name=mode+('-O' if optimized else '-debug');binary=temp/name
            args=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache')]
            if optimized:args.append('-O')
            subprocess.run([*args,str(suite),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,preexec_fn=no_core)
            if mode=='current':
                assert result.returncode==0,result.stdout+result.stderr
                message=result.stdout.strip()
            else:
                assert result.returncode!=0 and 'panel animation regression:' in result.stderr,(mode,result.stdout,result.stderr)
                message='Прежний реальный участок воспроизвёл потерю анимации и отвергнут'
            print(name+': '+message,flush=True);runs.append(name+': '+message)
    return runs


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'message_copy_availability'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'expanded_keyboard_timing'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-expanded-animation-') as folder:
        temp=Path(folder);rejected=guard_checks(args.source,temp)
        runs=run_swift(args.source,args.swiftc,temp) if args.swiftc else []
    if args.swiftc:
        for name in PLAN['outputs']:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/name)],check=True)
    result={'changed_files':2,'guards':len(PLAN['guards']),'fail_closed':rejected,'executions':runs,'sdk':'не запускалась','device':'ожидает проверки на iPhone','boundaries':'UIKit/CA timing, native contents and keyboard delivery; actual native setFrame, presenter, policy, emoji layout branches, formatting guard/tail and routes executed'}
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
