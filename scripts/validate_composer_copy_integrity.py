#!/usr/bin/env python3
"""Check complete copied entities, leading attachments, ordinary send and preview races."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_quick_format import block,manifest
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import composer_copy_integrity_runtime as runtime
from composer_copy_integrity_apple import check as api_check,foundation_check
ROOT=Path(__file__).resolve().parents[1];STAGE='composer_copy_integrity'


def contract(source,plan):
    assert plan['required_previous_stage']=='local_read_label' and len(plan['inputs'])==7 and not plan['copies']
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(source/n)==h,n
    previous=lambda n:(ROOT/'ios'/plan['previous'][n]).read_text()
    context=(source/runtime.CONTEXT).read_text()
    assert context.count('storeChatMessageTextInPasteboard(')==15
    assert context.replace('storeChatMessageTextInPasteboard(','storeMessageTextInPasteboard(')==previous(runtime.CONTEXT),'Unrelated context action/privacy/selection changed'
    paste=(source/runtime.PASTE).read_text();old=previous(runtime.PASTE)
    new=block(paste,'public func messageTextPasteboardItem(')+'\n\n'+block(paste,'public func storeMessageTextInPasteboard(')
    assert paste.replace(new,block(old,'public func storeMessageTextInPasteboard('),1)==old,'Legacy codecs or unrelated clipboard methods changed'
    item=block(paste,'public func messageTextPasteboardItem(')
    assert 'appSpecificStringWithAppliedEntities(text, entities: entities)' in item and 'if includeRTF' in item
    clip=(source/runtime.CLIP).read_text();old=previous(runtime.CLIP)
    new_helper=block(clip,'public func storeChatMessageTextInPasteboard(')
    start=clip.index('/// One atomic item supplies')
    stop=clip.index('/// Copies a `ComposedRichMessage`',start)
    normalized=clip[:start]+clip[stop:]
    normalized=normalized.replace('import TextFormat\n','',1).replace('storeChatMessageTextInPasteboard(text, entities: entities)','storeMessageTextInPasteboard(text, entities: entities)',1)
    assert normalized==old,'Existing rich/empty clipboard paths changed'
    assert new_helper.count('UIPasteboard.general.items =')==1 and '.general.items' not in new_helper[:new_helper.index('    UIPasteboard.general.items =')]
    assert 'includeRTF: false' in new_helper and 'plain: text' in new_helper
    for build,required in [('submodules/Pasteboard/BUILD',['TextFormat:TextFormat']),('submodules/TelegramUI/Components/Chat/ChatRichTextEditorComposer/BUILD',['//submodules/Pasteboard','//submodules/TextFormat',':RichTextEditorCore',':RichTextEditorUIKit'])]:
        for label in required:assert label in (source/build).read_text(),(build,label)
    menu=(source/runtime.MENU).read_text();old=previous(runtime.MENU)
    for marker in ['func nagramiXComposerFileDraft(','func nagramiXComposerCaptionFiles(','func nagramiXComposerFileMessages(']:
        menu=menu.replace(block(menu,marker),'<OWNED '+marker+'>',1);old=old.replace(block(old,marker),'<OWNED '+marker+'>',1)
    assert menu==old,'Picker IO/edit/cancel/send modes changed'
    node=(source/runtime.NODE).read_text();old=previous(runtime.NODE)
    node=node.replace('if composeContent.allMedia.isEmpty, let urlPreview = self.chatPresentationInterfaceState.urlPreview {','if let urlPreview = self.chatPresentationInterfaceState.urlPreview {',1)
    a='''                    // Attached files are the post's media; an inline URL stays a link.
                    if !composeContent.allMedia.isEmpty {
                        attributes.append(OutgoingContentInfoMessageAttribute(flags: [.disableLinkPreviews]))
                    } else if let urlPreview = self.chatPresentationInterfaceState.urlPreview {'''
    b='''                    // url-preview attribute parity (duplicated, not shared, to keep the text loop byte-identical)
                    if let urlPreview = self.chatPresentationInterfaceState.urlPreview {'''
    assert node.count(a)==1;node=node.replace(a,b,1)
    assert node==old,'Reply/payment/Premium/schedule/clear/forward/send callbacks changed'
    rich=(source/runtime.RICH).read_text();old=previous(runtime.RICH)
    start=rich.index('// Toolbar attachments belong before the post body,')
    end=rich.index('public class RichTextAttachmentScreen:',start)
    normalized=rich[:start]+rich[end:]
    picker='        private func presentImagePicker()'
    assert normalized.replace(block(normalized,picker),block(old,picker),1)==old,'Expanded media registration/preupload/send/close changed'
    assert 'self.editor.replaceRange(from: 0, to: 0, with: nagramiXLeadingAttachmentDocument(items))' in block(rich,picker)
    protocol=(source/(runtime.RTE+'RichTextEngineEditor/RichTextEditorProtocol.swift')).read_text()
    assert 'func replaceRange(from: Int, to: Int, with document: Document)' in protocol
    update=(source/runtime.UPDATE).read_text();old=previous(runtime.UPDATE)
    start=update.index('    // Both editor handoffs use this state path.')
    end=update.index('    if case let .customChatContents',start)
    normalized=update[:start]+'    var canHaveUrlPreview = true\n'+update[end:]
    normalized=normalized.replace('                    guard $0.interfaceState.composeInputState.content.allMedia.isEmpty else { return $0.updatedUrlPreview(nil) }\n','',1)
    assert normalized==old,'Unrelated interface-state/draft/preview logic changed'
    actual=(source/'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift').read_text()
    case=next(x.strip() for x in actual.splitlines() if x.strip().startswith('case message(text: String,'))
    assert case in (ROOT/'scripts/tests/NagramiXComposerFilesBoundary.swift').read_text()
    flags=(source/'submodules/TelegramCore/Sources/SyncCore/SyncCore_OutgoingContentInfoMessageAttribute.swift').read_text()
    assert 'public static let disableLinkPreviews' in flags
    return {'scope':'Only15 existing Copy calls, two clipboard helpers, three draft/send helpers, expanded toolbar attachment insertion and file-preview gates. Every other byte of the seven inputs exact after removing these changes.','copy':'Single atomic plain/RTF/native-fragment/exact Telegram entity item; rich/empty paths unchanged; both native clipboard readers guarded.','attachments':'Leading toolbar attachments in both editors; structural replaceRange command retains native undo. Stable batch/pick order and structural caret; both edge layouts eligible for ordinary file+caption; true inline/long/structured layouts retain rich route.','preview':'Attached media clears/cancels existing query; late result rejected; native and rich payload disable redundant preview; text-only preview unchanged.','unchanged':'Privacy, read, copy permissions, transport retry/upload, edit, Premium limits, thread/reply, scheduled/payment modes, all localization/settings/player/geometry paths.','native_input_origins':plan['native_inputs']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE);c=contract(a.source,plan);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='composer-copy-check-') as d:
        folder=Path(d);refusals=guard_checks(a.source,STAGE,plan,folder/'guards');foundation=foundation_check(a.swiftc,folder);code=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'composer-copy-integrity',code)
        for name,mutated,label in runtime.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
        api=api_check(a.source,a.swiftc,folder,public_api=True);apple=api_check(a.source,a.swiftc,folder)
        for n in plan['inputs']:run([a.swiftc,'-frontend','-parse',a.source/n])
    assert before==manifest(a.source)
    report={'stage':STAGE,'source_contract':c,'loader_refusals':len(refusals),'executions':runs,'public_api':api,'apple_sdk_precheck':apple,'foundation_fixture_precheck':foundation,'source_unchanged_by_checks':True,'full_application_sdk':'not_run','live_rpc':'pending','device':'pending','boundary':'Real native text entities Codable/converters, RTE model/codec/RTF export+import, clipboard helpers, draft/selection/route/enqueue and preview gate code. Explicit pasteboard/peer/media/Postbox and auto-detector boundaries. Not real network RPC delivery or rendered UIKit.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
