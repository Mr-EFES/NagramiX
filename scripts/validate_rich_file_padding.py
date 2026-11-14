#!/usr/bin/env python3
"""Проверить утверждённый отступ file/audio внутри расширенного пузырька."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import rich_file_padding_runtime as runtime

STAGE='rich_file_padding'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
 plan=checked_plan(STAGE);assert plan['required_previous_stage']=='named_link_preview'
 assert set(plan['inputs'])=={runtime.LAYOUT,runtime.HOST,runtime.PREVIEW} and len(plan['guards'])==19
 assert set(plan['native_inputs'])==set(plan['inputs']) and not plan['copies'] and not plan['deletions']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 before=lambda n:(OVERLAY/plan['previous'][n]).read_text()
 layout=(a.source/runtime.LAYOUT).read_text();host=(a.source/runtime.HOST).read_text();preview=(a.source/runtime.PREVIEW).read_text()
 assert '    leadingFileInset: CGFloat = 0.0,' in layout
 assert '        leadingFileInset: leadingFileInset,' in layout and '    let leadingFileInset: CGFloat' in layout
 assert 'leadingFileInset: isBubblelessPage ? 0.0 : layoutConstants.file.bubbleInsets.top,' in host
 assert 'leadingFileInset: ChatMessageItemLayoutConstants.default.file.bubbleInsets.top,' in preview and 'import ChatMessageItemCommon' in preview
 assert '"//submodules/TelegramUI/Components/Chat/ChatMessageItemCommon"' in (a.source/'submodules/TelegramUI/BUILD').read_text()
 # Caption/control/media layout itself, ending rhythm, caches, clipping and
 # reveal/status/hit-testing stay byte-identical; only the leading driver changes.
 for marker in ['private func layoutBlock(', 'private func layoutCaptionAndCredit(']:assert block(layout,marker)==block(before(runtime.LAYOUT),marker)
 driver=block(layout,'private func layoutBlockSequence(');oldDriver=block(before(runtime.LAYOUT),'private func layoutBlockSequence(')
 insertion='''            // Unlike an image, a file row must not touch a chat bubble's rounded top edge.
            // Apply before the host's edge trim so the page inset is counted exactly once.
            switch block {
            case .audio, .document:
                spacing = max(spacing, context.leadingFileInset)
            default:
                break
            }
'''
 assert driver.count(insertion)==1 and driver.replace(insertion,'',1)==oldDriver
 state=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='rich-file-padding-') as folder:
  temp=Path(folder);refused=guard_checks(a.source,STAGE,plan,temp/'guards');text=runtime.fixture(a.source)
  runs=execute(a.swiftc,temp,'rich-file-padding',text)
  variants=[
   ('old-flush-driver',driver,oldDriver,'top file matches ordinary file padding'),
   ('nested-padding',driver,driver.replace('previousBlock == nil && kind == .topLevel','previousBlock == nil',1),'nested layout preserves native spacing'),
   ('audio-only','case .audio, .document:\n                spacing = max(spacing, context.leadingFileInset)','case .audio:\n                spacing = max(spacing, context.leadingFileInset)','top file matches ordinary file padding'),
   ('double-edge-inset','spacing = max(spacing, context.leadingFileInset)','spacing = max(spacing, context.leadingFileInset + context.edgeSpacingReduction)','top file matches ordinary file padding'),
   ('duplicate-header','if fileTopInset > 0.0, let first','if false && fileTopInset > 0.0, let first','file header does not double count new padding'),
  ]
  for name,old,new,why in variants:
   assert text.count(old)==1,(name,text.count(old));runs+=execute(a.swiftc,temp,name,text.replace(old,new,1),why)
  run([a.swiftc,'-frontend','-parse',*[a.source/n for n in plan['inputs']]])
 assert manifest(a.source)==state
 report={'stage':STAGE,'inputs':3,'guards':19,'loader_refusals':len(refused),'executions':runs,'source_unchanged_by_checks':True,
  'root_cause':'Native rich V2 audio/document are flushAbove, beginning at y=0; chat host supplies only 2pt page rim. Ordinary file bubble uses 15pt top inset.',
  'change':'Top-level first rendered audio/document consumes native file inset before edge trim. Chat host and send preview opt in; header does not double count. Anchors/missing media retain driver semantics.',
  'boundaries':'Actual V2 sequence driver, spacing rules, metrics, audio/document row branches and header helper compile and execute in debug/O. Model/storage/text drawing/other block renderers are explicit boundaries. Width/index/whole-caption translation and nested/default/native geometry are checked. Apple SDK app compilation, UIKit pixels and physical iPhone pending.',
  'native_app_compilation':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
