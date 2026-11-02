#!/usr/bin/env python3
"""Verify full-name menu source and measured row geometry without Apple SDK."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
R = 'submodules/Components/ReactionListContextMenuContent/Sources/ReactionListContextMenuContent.swift'
P = 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift'


def production(before, after):
    source = (after/R).read_text()
    geometry = block(source, 'private struct NagramiXReactionRowLayout ')
    key = block(source, 'private struct NagramiXReactionNameMeasureKey:')
    funcs = '\n'.join(block(source,'private func '+name+'(') for name in ['nagramiXReactionCredibilityInset','nagramiXReactionNameWidth'])
    measure = block(source,'private func nagramiXMeasureRows(')
    def pin(root):
        text = (root/P).read_text()
        start = text.index('                                contextItems.append(.action(ContextMenuActionItem(text: strongSelf.presentationData.strings.Conversation_PinMessagesFor(')
        end = text.index('\n                                \n                                contextItems.append(',start)
        return text[start:end]
    return geometry+'\n'+key+'\n'+funcs+'''
final class MeasureHost {
    let context = Context()
    var state = ItemsState()
    var displayReadTimestamps = true
    fileprivate var nagramiXRowLayout = NagramiXReactionRowLayout()
    let nagramiXNameMeasureNode = ImmediateTextNode()
    fileprivate var nagramiXNameMeasures: [NagramiXReactionNameMeasureKey:CGFloat] = [:]
''' + measure.replace('private func','func',1) + '''
}
final class PinHost {
    var presentationData = PresentationData()
    var calls: [(Bool,Bool)] = []
    func build(_ peer: EnginePeer, legacy: Bool = false) -> ContextMenuActionItem {
        let strongSelf = self
        let pinAction: (Bool,Bool) -> Void = { self.calls.append(($0,$1)) }
        var contextItems: [ContextMenuItem] = []
        if legacy {
''' + pin(before) + '''
        } else {
''' + pin(after) + '''
        }
        guard case let .action(item) = contextItems[0] else { fatalError() }
        return item
    }
}
'''


def validate(args):
    plan = json.loads((ROOT/'ios/menu_full_names_patches.json').read_text())
    a,b = manifest(args.before),manifest(args.after)
    assert a.keys() == b.keys()
    changed = {n for n in a if a[n] != b[n]}
    assert changed == set(plan['hashes']),changed
    assert all(a[n] == value for n,value in plan['hashes'].items())
    source = (args.after/R).read_text()
    assert 'self.titleLabelNode.maximumNumberOfLines = 0' in source
    assert 'let baseContentHeight = self.nagramiXRowLayout.contentHeight' in source
    assert 'self.nagramiXRowLayout.frame(at: index, width: size.width)' in source
    assert 'let visibleRange = self.nagramiXRowLayout.visibleRange(in: visibleBounds)' in source
    assert 'self.state.canLoadMore && maxVisibleIndex >= self.state.listState.items.count - 16' in source
    # The two title measurement paths must share width/font and unrestricted height.
    assert source.count('nagramiXReactionNameWidth(width:') == 3
    assert 'let titleFontSize = presentationData.listsFontSize.baseDisplaySize * 17.0 / 17.0' in source
    assert source.count('height: .greatestFiniteMagnitude') >= 3
    spec = importlib.util.spec_from_file_location('menu_names',ROOT/'ios/menu_full_names.py')
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    failures,runs=[],[]
    with tempfile.TemporaryDirectory(prefix='nagramix-names-') as folder:
        folder=Path(folder)
        def seed(target):
            for n in plan['hashes']:
                (target/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.before/n,target/n)
        def reject(target,label,overlay=ROOT/'ios'):
            old=manifest(target)
            try:module.apply_menu_full_names(target,overlay)
            except SystemExit:pass
            else:raise AssertionError(label)
            assert manifest(target)==old,label
            failures.append(label)
        target=folder/'valid';seed(target);module.apply_menu_full_names(target,ROOT/'ios')
        assert all((target/n).read_bytes()==(args.after/n).read_bytes() for n in changed)
        reject(target,'already applied')
        for n in plan['hashes']:
            for kind in ['missing','drift']:
                target=folder/(kind+str(len(failures)));seed(target)
                if kind=='missing':(target/n).unlink()
                else:(target/n).write_text((target/n).read_text()+'\n// drift')
                reject(target,kind+' '+n)
        for index in range(len(plan['patches'])):
            custom=json.loads(json.dumps(plan));custom['patches'][index][1]+=' missing anchor'
            overlay=folder/('bad'+str(index));overlay.mkdir()
            for n in plan['templates'].values():
                (overlay/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/n,overlay/n)
            (overlay/'menu_full_names_patches.json').write_text(json.dumps(custom))
            target=folder/('anchor'+str(index));seed(target);reject(target,'anchor '+str(index),overlay)
        for index,n in enumerate(plan['templates'].values()):
            for kind in ['missing','empty']:
                overlay=folder/('template'+str(index)+kind);overlay.mkdir()
                for name in plan['templates'].values():
                    (overlay/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/name,overlay/name)
                if kind=='missing':(overlay/n).unlink()
                else:(overlay/n).write_text(' ')
                (overlay/'menu_full_names_patches.json').write_text(json.dumps(plan))
                target=folder/('source'+str(index)+kind);seed(target);reject(target,kind+' template '+n,overlay)
        code = (ROOT/'scripts/tests/NagramiXMenuFullNamesBoundary.swift').read_text()+'\n'+production(args.before,args.after)+'\n'+(ROOT/'scripts/tests/NagramiXMenuFullNamesTests.swift').read_text()
        swift=folder/'Tests.swift';swift.write_text(code)
        for mode in ['debug','optimized']:
            binary=folder/mode
            command=[str(args.swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(folder/'cache'),str(swift),'-o',str(binary)]
            if mode=='optimized':command.insert(1,'-O')
            subprocess.run(command,check=True)
            runs.append(mode+': '+subprocess.check_output([str(binary)],text=True,timeout=30).strip())
        subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.after/n) for n in sorted(changed)]],check=True)
    for n in ['ios/menu_full_names.py','ios/apply_features.py','scripts/validate_menu_full_names.py']:ast.parse((ROOT/n).read_text())
    return dict(native_outputs=len(b),changed=sorted(changed),unchanged=len(b)-len(changed),sha_guards=len(plan['hashes']),operations=len(plan['patches']),templates=len(plan['templates']),fail_closed=failures,runs=runs,SDK='not run',UIKit_CoreText='measurement boundary, not actual rendering',physical_iPhone='pending')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']:parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args();result=validate(args)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
