#!/usr/bin/env python3
"""Проверить одинаковый native caption обоих редакторов и отступ без расширения пузырька."""
import argparse,json,tempfile,subprocess,sys
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
import file_caption_consistency_runtime as rt

STAGE='file_caption_consistency'


def contracts(source):
    plan=checked_plan(STAGE)
    assert set(plan['inputs'])=={rt.MENU,rt.FILE} and len(plan['guards'])==83 and not plan['copies'] and not plan['deletions']
    assert plan['required_previous_stage']=='round_quality_preset_badge'
    before=lambda n:(OVERLAY/plan['previous'][n]).read_text()
    menu=(source/rt.MENU).read_text();old=before(rt.MENU)
    for name in ['nagramiXComposerFileDraft','nagramiXComposerCaptionFiles','nagramiXComposerSendContent','nagramiXComposerFileMessages']:
        assert block(menu,'func '+name+'(')==block(old,'func '+name+'('),name
    for marker in ['                        let performRichTextSend:', '                            syncContent:']:
        assert block(menu,marker)==block(old,marker),'Existing lifecycle/paid send changed'
    def rich_case(t):
        a=t.index('                    case .richText:');b=t.index('                    default:',a);return t[a:b]
    restored=menu.replace(rich_case(menu),rich_case(old),1)
    for marker in ['private func nagramiXDocumentUsesNativeFileCaption(', 'func nagramiXComposerCaptionMessages(']:
        restored=restored.replace(block(restored,marker)+'\n\n','',1)
    for comment in ['// A native caption must not lose unresolved media or article-only formatting in the bridge.\n','// Both editors use the same native file/caption payload when the whole post is representable.\n']:
        restored=restored.replace(comment,'',1)
    assert restored==old,'Unrelated attachment menu changed'
    case=rich_case(menu)
    assert case.count('guard let messages = buildRichTextMessages(')==3
    assert case.count('transformEnqueueMessages(messages,')==2
    assert 'performRichTextSend(strongSelf, messages)' in case and '[message]' not in case
    old_rich=block(old,'                                switch composeRichMessage(')
    assert old_rich==block(menu,'                                switch composeRichMessage('),'Fallback rich serializer changed'
    file=(source/rt.FILE).read_text()
    added='''                            // Keep a visible file-to-caption gap without changing the bubble width.
                            bottomInset = max(bottomInset, layoutConstants.text.bubbleInsets.top)
'''
    assert file.count(added)==1 and file.replace(added,'',1)==before(rt.FILE),'Other file layout changed'
    return {'only_two_runtime_files':True,'native_caption_limits_entities_enqueue_unchanged':True,'all_three_standalone_callbacks_use_complete_message_array':True,'rich_fallback_and_paid_send_lifecycle_unchanged':True,'other_attachment_menu_actions_verbatim':True,'file_layout_changes_only_vertical_condensed_caption_gap':True,'bubble_width_measurement_and_fonts_unchanged':True}


def apple_check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    report={'real_uikit_geometry':'not_run','reason':'Linux без UIKit/iPhoneOS SDK','application_sdk':'not_run','pixel_verification':'not_run'}
    if sys.platform!='darwin':return report
    code=rt.geometry_fixture(source)
    code=code.replace('import Foundation','import Foundation\nimport UIKit',1)
    code=code.replace('struct UIEdgeInsets {let top:CGFloat,left:CGFloat,bottom:CGFloat,right:CGFloat}\n','',1)
    path=folder/'file-caption-real-uikit.swift';path.write_text(code)
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    v=subprocess.run([str(swiftc),'-typecheck','-parse-as-library','-swift-version','5','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),str(path)],capture_output=True,text=True,timeout=180)
    assert v.returncode==0,v.stdout+v.stderr
    return {'real_uikit_geometry':'passed','target':'arm64-apple-ios15.0','scope':'Actual native inset constants and bottom-height expression use real UIKit UIEdgeInsets/CGFloat/CGSize. Controller/transport and full file node linkage require app SDK.','application_sdk':'not_run','pixel_verification':'not_run'}


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True);contract=contracts(source)
    code=rt.fixture(source);geometry=rt.geometry_fixture(source)
    native=execute(swiftc,folder,'file-caption-send',code)
    layout=execute(swiftc,folder,'file-caption-geometry',geometry)
    negatives=[]
    for name,text,old,new,why in [
        ('expanded-always-rich',code,'if nagramiXDocumentUsesNativeFileCaption(document, media: media, sendWithoutFormatting: sendWithoutFormatting) {','if false && nagramiXDocumentUsesNativeFileCaption(document, media: media, sendWithoutFormatting: sendWithoutFormatting) {','normal and expanded send identical complete text'),
        ('native-loses-entities',code,'nagramiXComposerFileMessages(files: files, caption: caption, inlineStickers: inlineStickers','nagramiXComposerFileMessages(files: files, caption: NSAttributedString(string: caption.string), inlineStickers: inlineStickers','normal and expanded send identical formatting entities'),
        ('partial-native-payload',code,'!value.items.isEmpty && value.items.allSatisfy { media[$0.mediaID] != nil }','!value.items.isEmpty','missing media cannot downgrade a partial post to native caption'),
        ('collapsed-caption-gap',geometry,'                            bottomInset = max(bottomInset, layoutConstants.text.bubbleInsets.top)\n','','visible gap below file is retained'),
    ]:
        assert text.count(old)==1,(name,text.count(old))
        negatives+=execute(swiftc,folder,name,text.replace(old,new,1),why)
    return {'contracts':contract,'executions':native,'geometry_executions':layout,'semantic_negatives':negatives,'apple_api':apple_check(source,swiftc,folder/'apple'),'boundary':'Actual Document/clipboard/format conversion, both native enqueue helpers and standalone builder closure execute. Account, Postbox/media IO, rich serializer and platform edges are explicit adapters. Source contracts keep all three callbacks, paid send and opaque rich fallback intact. Geometry executes actual inset/height formulas; no UIKit pixels or foreign client rendering is asserted.','full_application_sdk':'not_run','physical_iphone':'pending','native_telegram_live_delivery':'pending'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    before=manifest(a.source);plan=checked_plan(STAGE)
    with tempfile.TemporaryDirectory(prefix='nagramix-file-caption-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');result=check(a.source,a.swiftc,root/'runtime')
        for n in plan['inputs']:
            v=subprocess.run([str(a.swiftc),'-frontend','-parse',str(a.source/n)],capture_output=True,text=True,timeout=120)
            assert v.returncode==0,v.stdout+v.stderr
    assert manifest(a.source)==before
    report={'stage':97,'name':STAGE,'runtime_paths':list(plan['inputs']),'guards':83,'loader_refusals':len(refused),'checks':result,'source_unchanged_by_checks':True,'new_localization_keys':0,'full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
