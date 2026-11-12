#!/usr/bin/env python3
"""Проверить полную ширину канальных постов и неизменность native OFF до SDK."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import execute,run
import wide_channel_post_consistency_runtime as runtime

ROOT=Path(__file__).resolve().parents[1];STAGE='wide_channel_post_consistency'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert plan['required_previous_stage']=='release_095_composer_strings_compile'
 assert set(plan['inputs'])=={runtime.BUBBLE} and len(plan['guards'])==11 and not plan['copies'] and not plan['deletions']
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
 before=(ROOT/'ios'/plan['previous'][runtime.BUBBLE]).read_text();after=(a.source/runtime.BUBBLE).read_text()
 # Reconstruct every unchanged byte: no changes in eligibility, players,
 # media preparation, captions, context actions, archive or selection policy.
 helper=runtime.block(after,'private func nagramiXWideChannelMosaicLayout(')+'\n\n'
 restored=after.replace(helper,'',1).replace('nagramiXWideChannelMosaicLayout(maxSize: maxSize, itemSizes: contentPropertiesAndLayouts','chatMessageBubbleMosaicLayout(maxSize: maxSize, itemSizes: contentPropertiesAndLayouts',1).replace('}, fillWidth: nagramiXWideChannelPost)', '})',1)
 restored=restored.replace('            // The mosaic cannot narrow the shared text/header/footer budget.\n            maximumNodeWidth = nagramiXWideChannelPost ? maximumContentWidth : size.width\n','            maximumNodeWidth = size.width\n',1).replace('if hasInstantVideo && !nagramiXWideChannelPost {','if hasInstantVideo {')
 assert restored==before,'Unexpected changes outside mosaic width and reaction constraints'
 settings=(a.source/'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift').read_text()
 assert 'defaults.object(forKey: Key.wideChannelPosts) as? Bool ?? true' in settings
 assert 'defaults.set(value.wideChannelPosts, forKey: Key.wideChannelPosts)' in settings
 initial=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='nagramix-wide-post-') as temporary:
  folder=Path(temporary);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
  text=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'wide-post',text)
  runs+=execute(a.swiftc,folder,'published-095-regression',runtime.fixture(a.source,before),'caption keeps the parent width')
  for name,mutated,why in runtime.negatives(text):runs+=execute(a.swiftc,folder,name,mutated,why)
  edge_previous=(ROOT/'ios'/checked_plan('bubble_selection_edge')['previous'][runtime.BUBBLE]).read_text()
  runs+=execute(a.swiftc,folder,'current-wide-selection',runtime.selection_fixture(a.source,edge_previous))
  run([a.swiftc,'-frontend','-parse',a.source/runtime.BUBBLE])
 assert manifest(a.source)==initial
 report={'stage':STAGE,'inputs':len(plan['inputs']),'guards':len(plan['guards']),'loader_refusals':len(refused),'source_files':len(initial),'source_unchanged_by_checks':True,'executions':runs,'boundary':'Actual pinned native MosaicLayout + actual new parent mosaic pass, native UIKit size utility, current parent selection budget/placement. No renderer/player simulation; UIKit pixels, transitions and full SDK remain separate.','apple_sdk':'not_run','device':'pending'}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
