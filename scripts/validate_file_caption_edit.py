#!/usr/bin/env python3
"""Проверить native file-caption при редактировании и равные зазоры без расширения пузырька."""
import argparse,json,tempfile,subprocess,sys
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
import file_caption_edit_runtime as rt
STAGE='file_caption_edit'


def contracts(source):
    plan=checked_plan(STAGE)
    assert set(plan['inputs'])=={rt.EDIT,rt.FILE} and len(plan['guards'])==109 and not plan['copies'] and not plan['deletions']
    assert plan['required_previous_stage']=='file_caption_consistency'
    before=lambda n:(OVERLAY/plan['previous'][n]).read_text()
    edit=(source/rt.EDIT).read_text();old=before(rt.EDIT)
    helper=block(edit,'private func nagramiXEditableCaptionFile(')
    restored=edit.replace(helper+'\n\n','',1)
    comments='// Editing one ordinary file with an entity caption must keep the native bubble.\n// Multiple files and structural content cannot be folded into one editMedia request.\n'
    restored=restored.replace(comments,'',1).replace('import ChatHistoryListViewBackend\n\n\n','import ChatHistoryListViewBackend\n\n',1)
    old_decision='                let richText: RichTextMessageAttribute? = content.isEntityExpressible() ? nil : RichTextMessageAttribute(instantPage: instantPage(from: content), fullInstantPage: nil)\n'
    new_decision='''                let nagramiXOriginalRichText = message.attributes.first(where: { $0 is RichTextMessageAttribute }) as? RichTextMessageAttribute
                let nagramiXCaptionFile = nagramiXEditableCaptionFile(content, maxCaptionLength: min(4096, Int(strongSelf.context.userLimits.maxCaptionLength)), originalRichText: nagramiXOriginalRichText)
                let richText: RichTextMessageAttribute? = (nagramiXCaptionFile != nil || content.isEntityExpressible()) ? nil : RichTextMessageAttribute(instantPage: instantPage(from: content), fullInstantPage: nil)
                if nagramiXCaptionFile != nil {
                    disableUrlPreview = true
                    webpage = nil
                    webpagePreviewAttribute = nil
                }
'''
    assert restored.count(new_decision)==1;restored=restored.replace(new_decision,old_decision,1)
    added='''                } else if let nagramiXCaptionFile {
                    media = .update(.standalone(media: nagramiXCaptionFile))
                    updatingMedia = true
'''
    assert restored.count(added)==1;restored=restored.replace(added,'',1)
    assert restored==old,'Unrelated edit lifecycle/producer/pending enqueue changed'
    file=(source/rt.FILE).read_text()
    added='''                            // The caption follows a .text neighbour, so its own top inset is reduced by 2pt.
                            // Together both insets match the file's top padding; width stays unchanged.
                            let captionTopInset = max(0.0, layoutConstants.text.bubbleInsets.top - 2.0)
                            bottomInset = max(bottomInset, fileInsets.top - captionTopInset)
'''
    previous='''                            // Keep a visible file-to-caption gap without changing the bubble width.
                            bottomInset = max(bottomInset, layoutConstants.text.bubbleInsets.top)
'''
    assert file.count(added)==1 and file.replace(added,previous,1)==before(rt.FILE),'Other file layout changed'
    assert 'neighborType: .text, neighborSpacing: neighborSpacing' in (source/'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift').read_text()
    return {'only_two_runtime_files':True,'shared_edit_callback_for_both_editors':True,'single_file_limit_and_complex_fallback_preserved':True,'explicit_replacement_priority_preserved':True,'pending_queue_and_rpc_unchanged':True,'caption_limit_rights_and_lifecycle_unchanged':True,'width_and_file_top_inset_unchanged':True,'existing_rich_top_padding_and_header_preserved':True}


def apple_check(source,swiftc,folder):
    if sys.platform!='darwin':return {'real_uikit_geometry':'not_run','reason':'Linux без UIKit/iPhoneOS SDK','application_sdk':'not_run','pixel_verification':'not_run'}
    folder.mkdir(parents=True,exist_ok=True);code=rt.geometry_fixture(source)
    code=code.replace('import Foundation','import Foundation\nimport UIKit',1).replace('struct UIEdgeInsets {let top:CGFloat,left:CGFloat,bottom:CGFloat,right:CGFloat}\n','',1)
    p=folder/'file-edit-real-uikit.swift';p.write_text(code);sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    v=subprocess.run([str(swiftc),'-typecheck','-parse-as-library','-swift-version','5','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),str(p)],capture_output=True,text=True,timeout=180)
    assert v.returncode==0,v.stdout+v.stderr
    return {'real_uikit_geometry':'passed','application_sdk':'not_run','pixel_verification':'not_run','target':'arm64-apple-ios15.0'}


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True);contract=contracts(source)
    code=rt.fixture(source);geometry=rt.geometry_fixture(source)
    edits=execute(swiftc,folder,'file-caption-edit',code)
    layout=execute(swiftc,folder,'file-edge-geometry',geometry)
    rich=execute(swiftc,folder,'existing-rich-file-top',rt.rich.fixture(source))
    negatives=[]
    for name,text,old,new,why in [
        ('edit-always-rich',code,'(nagramiXCaptionFile != nil || content.isEntityExpressible())','content.isEntityExpressible()','both editors keep native file caption on edit'),
        ('edit-loses-file',code,'media = .update(.standalone(media: nagramiXCaptionFile))','media = .keep; _ = nagramiXCaptionFile','edit attaches the complete file'),
        ('edit-drops-extra-files',code,'files.count == 1, let file = files.first','!files.isEmpty, let file = files.first','multiple files cannot become a partial single-media edit'),
        ('edit-partial-page',code,'originalRichText?.instantPage.isComplete != false','true','partial original rich page cannot become a truncated native edit'),
        ('uneven-file-gap',geometry,'fileInsets.top - captionTopInset','layoutConstants.text.bubbleInsets.top + captionTopInset * 0','top and complete file-to-text gap match'),
    ]:
        assert text.count(old)==1,(name,text.count(old));negatives+=execute(swiftc,folder,name,text.replace(old,new,1),why)
    return {'contracts':contract,'edit_executions':edits,'geometry_executions':layout,'existing_rich_executions':rich,'semantic_negatives':negatives,'apple_api':apple_check(source,swiftc,folder/'apple'),'boundaries':'Real model/Document conversion, caption eligibility and edit decision/media branches execute. Account/media/opaque InstantPage are explicit IO adapters; pending manager and RPC bodies unchanged. Actual native and rich layout formulas execute with explicit UIKit/text-drawing boundaries. Live server rich-to-native conversion and pixels require device validation.','full_application_sdk':'not_run','physical_iphone':'pending','native_telegram_live_delivery':'pending'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    before=manifest(a.source);plan=checked_plan(STAGE)
    with tempfile.TemporaryDirectory(prefix='nagramix-file-edit-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');result=check(a.source,a.swiftc,root/'runtime')
        for n in plan['inputs']:
            v=subprocess.run([str(a.swiftc),'-frontend','-parse',str(a.source/n)],capture_output=True,text=True,timeout=120);assert v.returncode==0,v.stdout+v.stderr
    assert manifest(a.source)==before
    report={'stage':98,'name':STAGE,'runtime_paths':list(plan['inputs']),'guards':109,'loader_refusals':len(refused),'checks':result,'source_unchanged_by_checks':True,'new_localization_keys':0,'full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
