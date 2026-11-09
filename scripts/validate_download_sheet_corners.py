#!/usr/bin/env python3
"""Проверить ориентацию, прозрачность и совместимость маски верхних углов."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import execute, run
from validate_download_sheet_edge import layout_fixture, selection_fixture
import download_sheet_corners_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]
STAGE='download_sheet_corners'


def contract(source):
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='proxy_doh_editor'
    assert set(plan['inputs'])=={runtime.GROUP} and len(plan['guards'])==15
    assert not plan['copies'] and not plan['deletions'] and not plan['native_inputs']
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,sha in {**plan['outputs'],**plan['guards']}.items():assert digest(source/name)==sha,name
    before=(ROOT/'ios'/plan['previous'][runtime.GROUP]).read_text()
    after=(source/runtime.GROUP).read_text()
    old='return generateImage(CGSize(width: 33.0, height: 33.0), rotatedContext: { size, context in\n        let bounds = CGRect(origin: .zero, size: size)'
    new='return generateImage(CGSize(width: 33.0, height: 33.0), contextGenerator: { size, context in\n        let bounds = CGRect(origin: .zero, size: size)\n        context.clear(bounds)'
    assert before.count(old)==1 and after==before.replace(old,new)
    # The complete group class, layer clipping, inset/scroll layout, native
    # dismiss animations and selection factory are exact unchanged bytes.
    marker='final class ActionSheetItemGroupNode:'
    assert after[after.index(marker):]==before[before.index(marker):]
    image=(source/runtime.IMAGE).read_text()
    assert 'context.withFlippedContext' in block(image,'public func generateImage(_ size: CGSize, contextGenerator:')
    assert 'context.withContext' in block(image,'public func generateImage(_ size: CGSize, opaque:')
    assert 'context.scaleBy(x: 1.0, y: -1.0)' in block(image,'    public func withContext(')
    assert 'f(self.context)' in block(image,'    public func withFlippedContext(')
    assert 'clear: false' in block(image,'public func generateImage(_ size: CGSize, contextGenerator:')
    allocator=(source/'submodules/AsyncDisplayKit/Source/ASCGImageBuffer.mm').read_text()
    assert '_mutableBytes = malloc(length);' in allocator
    assert 'self.clippingNode.cornerRadius = 16.0' in after
    assert 'cornerRadii: CGSize(width: 16.0, height: 16.0)' in after
    assert '?.stretchableImage(withLeftCapWidth: 16, topCapHeight: 16)' in after
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();plan=contract(args.source);before=manifest(args.source)
    mask=runtime.fixture(args.source)
    helper=block(mask,'private func nagramiXActionSheetTopCornerDimImage(')
    old=(ROOT/'ios'/plan['previous'][runtime.GROUP]).read_text()
    old=block(old,'private func nagramiXActionSheetTopCornerDimImage(')
    negatives=[
        ('upside-down-corners',mask.replace(helper,helper.replace('contextGenerator:', 'rotatedContext:',1)), 'dim belongs at the top corners, not at the bottom'),
        ('dirty-alpha-buffer',mask.replace(helper,helper.replace('        context.clear(bounds)\n','',1)), 'reused malloc bytes never alter the mask or add dark pixels'),
        ('original-mask-defect',mask.replace(helper,old), 'reused malloc bytes never alter the mask or add dark pixels'),
    ]
    with tempfile.TemporaryDirectory(prefix='download-sheet-corners-') as temporary:
        root=Path(temporary)
        rejected=guard_checks(args.source,STAGE,plan,root/'guards')
        runs=execute(args.swiftc,root,'mask',mask)
        runs+=execute(args.swiftc,root,'layout',layout_fixture(args.source))
        runs+=execute(args.swiftc,root,'selection',selection_fixture(args.source))
        for name,text,diagnostic in negatives:runs+=execute(args.swiftc,root,name,text,diagnostic)
        run([args.swiftc,'-frontend','-parse',args.source/runtime.GROUP])
    assert before==manifest(args.source)
    run(['python3',args.source/'build-system/Make/PostboxImportCheck.py',args.source])
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),
            'fail_closed':len(rejected),'executions':runs,'swift_parse':1,'source_files':len(before),
            'source_unchanged_by_checks':True,'native_postbox_imports':'passed',
            'boundary':'The production mask helper, both native generateImage overloads and real DrawingContext '
                       'coordinate-transform methods execute in an explicit premultiplied bitmap/rounded-path '
                       'adapter, including dirty allocator memory, scale 1/2/3, symmetry and nine-slice caps. '
                       'Actual native sheet layout and factory callbacks execute in existing adapters. '
                       'This does not prove UIKit/CoreGraphics pixels, blur compositing, recorded animation '
                       'frames or physical iPhone rendering.',
            'apple_sdk':'not_run','ipa':'not_built','physical_iphone':'pending'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('outputs','executions')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
