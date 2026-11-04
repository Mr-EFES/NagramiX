#!/usr/bin/env python3
"""Проверить согласование клавиатуры, эмодзи и форматирования расширенного редактора."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'expanded_keyboard_handoff_patches.json').read_text())
S = 'submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextAttachmentScreen.swift'
E = 'submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextEmojiKeyboardController.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_applied(source):
    return all((source / name).is_file() and sha((source / name).read_bytes()) == digest
               for name, digest in PLAN['outputs'].items())


def verify(source):
    assert is_applied(source), 'Expanded keyboard handoff outputs differ'
    for name, digest in PLAN['guards'].items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name


def reverse(source, prior):
    names = set(PLAN['inputs'])
    for path in OVERLAY.glob('*_patches.json'):
        item = json.loads(path.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings',
                  'submodules/TelegramPresentationData/Sources/PresentationData.swift',
                  'submodules/GalleryUI/Sources/ZoomableContentGalleryItemNode.swift'])
    for name in names:
        path = OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name
        if path.is_file():
            target = prior / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())


def delegate_if_applied(args, script):
    from validate_author_check_badge_icon import delegate_variant_five_if_applied
    if delegate_variant_five_if_applied(args, script):
        return True
    if not is_applied(args.source):
        return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='expanded-keyboard-prior-') as folder:
        prior = Path(folder)
        reverse(args.source, prior)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None:
            arguments += ['--upstream', str(args.source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('expanded_keyboard_handoff', OVERLAY / 'expanded_keyboard_handoff.py')
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
            module.apply_expanded_keyboard_handoff(target, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Неверный вход принят: ' + label)
        assert manifest(target) == before, 'Частичная запись: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_expanded_keyboard_handoff(valid, OVERLAY)
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
        (overlay / 'expanded_keyboard_handoff_patches.json').write_text(json.dumps(bad))
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
    current=(source/S).read_text(); emoji=(source/E).read_text()
    before=(OVERLAY/PLAN['previous'][S]).read_text()
    old_emoji=(OVERLAY/PLAN['previous'][E]).read_text()
    geometry=block(emoji, 'struct NagramiXExpandedInputGeometry')
    functions=['nagramiXBeginKeyboardHandoff','nagramiXRequestInputPanelLayout','nagramiXSetFormattingMode','nagramiXToggleFormatting','nagramiXToggleEmoji']
    routes='\n'.join(block(before if mode=='old-owner' and name in functions[2:] else current, 'func '+name+'(') for name in functions)
    emoji_routes='\n'.join(block(old_emoji if mode=='old-owner' else emoji, 'func '+name+'(') for name in ['toggle','setEmojiMode'])
    layout=before if mode=='old-layout' else current
    marker='            let emojiPanelHeight =' if mode=='old-layout' else '            let customInputActive ='
    begin=layout.index(marker)
    end=layout.index('            let editorTop =',begin)
    coordination=layout[begin:end]
    inset=next(line for line in layout.splitlines() if 'var bottomInset =' in line)
    boundary=(ROOT/'scripts/tests/NagramiXExpandedKeyboardBoundary.swift').read_text()
    fallback=next(line.strip().removeprefix('return ') for line in emoji.splitlines() if 'return self.isEmojiMode || measureOnly ?' in line)
    return '\n'.join([boundary,geometry,'''final class EmojiController {
    weak var editor: Editor?
    var isEmojiMode = false
    let nagramiXEmptyInputView = EmptyInputView()
    let requestLayout: () -> Void
    let willRestoreKeyboard: () -> Void
    init(editor: Editor, willRestoreKeyboard: @escaping () -> Void, requestLayout: @escaping () -> Void) {
        self.editor=editor;self.willRestoreKeyboard=willRestoreKeyboard;self.requestLayout=requestLayout
    }
''',emoji_routes,'''func updatePanel(container: UIView, availableSize: CGSize, environment: Environment, transition: ComponentTransition, measureOnly: Bool = false, standardInputHeight: CGFloat? = nil) -> CGFloat {
        // Native node returns expandedHeight == standardInputHeight while collapsed.
        return '''+fallback+'''
    }
}
final class ExpandedHost: UIView {
    let editor = Editor()
    var emojiKeyboard: EmojiController?
    var componentState: ComponentState? = ComponentState()
    var nagramiXFormattingActive = false
    var nagramiXFormattingGeneration = 0
    var nagramiXFormattingInputView: UIView?
    var nagramiXInputGeometry = NagramiXExpandedInputGeometry()
    var nagramiXPanelSwapPending = false
    var lastPanelHeight: CGFloat = 0
    var lastPanelTransition = ComponentTransition.immediate
    override init() {
        super.init()
        emojiKeyboard=EmojiController(editor: editor, willRestoreKeyboard: { [weak self] in self?.nagramiXBeginKeyboardHandoff() }, requestLayout: { [weak self] in self?.nagramiXRequestInputPanelLayout() })
    }
''',routes,'''func nagramiXUpdateFormattingPanel(availableSize: CGSize, height: CGFloat, environment: Environment, transition: ComponentTransition) {
        lastPanelHeight=height;lastPanelTransition=transition
    }
    @discardableResult func layout(_ inputHeight: CGFloat, size: CGSize = CGSize(width: 393, height: 852)) -> CGFloat {
        let availableSize=size
        let environment=Environment(inputHeight: inputHeight)
        let transition=ComponentTransition.spring(duration: 0.4)
''',coordination,inset.replace('var bottomInset','let bottomInset'),'return bottomInset\n}\n}',(ROOT/'scripts/tests/NagramiXExpandedKeyboardTests.swift').read_text()])


def run_swift(source, swiftc, temp):
    runs=[]
    for mode in ['current','old-layout','old-owner']:
        suite=temp/(mode+'.swift');suite.write_text(runtime_source(source,mode))
        for optimized in [False,True]:
            binary=temp/(mode+('-O' if optimized else '-debug'))
            command=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache')]
            if optimized:command+=['-O']
            subprocess.run([*command,str(suite),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if mode=='current':
                assert result.returncode==0,result.stdout+result.stderr
                runs.append(binary.name+': '+result.stdout.strip())
            else:
                assert result.returncode!=0 and 'keyboard regression:' in result.stderr,result.stdout+result.stderr
                runs.append(binary.name+': прежний скачок/повторный reload воспроизведён и отвергнут')
            print(runs[-1],flush=True)
    return runs


def contracts(source):
    screen=(source/S).read_text();emoji=(source/E).read_text();before=(OVERLAY/PLAN['previous'][S]).read_text();old_emoji=(OVERLAY/PLAN['previous'][E]).read_text()
    for name in ['nagramiXExpandedHasContent','nagramiXExpandedFormattingAvailable','nagramiXApplyExpandedFormatting','nagramiXApplyExpandedExtra','nagramiXUpdateFormattingPanel']:
        assert block(screen,'func '+name+'(')==block(before,'func '+name+'('),name
    for name in ['handleInsert','seedEmojiFiles','customEmojiView']:
        assert block(emoji,'func '+name+'(')==block(old_emoji,'func '+name+'('),name
    assert 'standardInputHeight: self.nagramiXInputGeometry.customInputHeight)' in screen
    assert 'standardInputHeight: standardInputHeight,\n            inputHeight: standardInputHeight,' in emoji
    assert 'let standardInputHeight = standardInputHeight ?? deviceMetrics.standardInputHeight(inLandscape: availableSize.width > availableSize.height)' in emoji
    assert 'willRestoreKeyboard: { [weak self] in\n                    self?.nagramiXBeginKeyboardHandoff()' in screen
    assert 'self?.nagramiXFormattingGeneration == generation' in screen
    assert 'UIAccessibility.isReduceMotionEnabled ? .immediate' in screen
    assert 'let sideInset: CGFloat = 20.0' in screen and 'actionBarView.clipsToBounds = true' in screen
    assert '!isEditingText && environment.inputHeight <= 0.0' in screen
    assert 'Sources/**/*.swift' in (source/'submodules/TelegramUI/Components/RichTextAttachmentScreen/BUILD').read_text()
    node=(source/'submodules/TelegramUI/Components/ChatEntityKeyboardInputNode/Sources/ChatEntityKeyboardInputNode.swift').read_text()
    assert 'var expandedHeight = standardInputHeight' in node and 'return (expandedHeight, 0.0)' in node
    for legacy in ['RichTextEditorUIKit/RichTextEditorView.swift','RichTextEngineEditor/RichTextEngineEditorView+Responder.swift']:
        text=(source/'submodules/TelegramUI/Components/RichTextEditor/Sources'/legacy).read_text()
        assert 'reloadInputViews()' in text,'custom input assignment must really reload UIKit'
    pipeline=(OVERLAY/'apply_overlay.py').read_text()
    assert pipeline.index('    apply_inline_temporary_voice(')<pipeline.index('    apply_expanded_keyboard_handoff(')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    from validate_author_check_badge_icon import delegate_variant_five_if_applied
    if delegate_variant_five_if_applied(args, Path(__file__)):
        return
    verify(args.source);contracts(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-expanded-keyboard-') as folder:
        temp=Path(folder)
        rejected=guard_checks(args.source,temp)
        runs=run_swift(args.source,args.swiftc,temp) if args.swiftc else []
    if args.swiftc:
        for name in PLAN['outputs']:
            subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/name)],check=True)
    result={'changed_files':len(PLAN['outputs']),'guards':len(PLAN['guards']),'fail_closed':rejected,'executions':runs,'sdk':'не запускалась','device':'ожидает проверки на iPhone','runtime':'actual geometry, view/controller mode methods and coordination block; Foundation real, UIKit/keyboard/component boundaries'}
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
