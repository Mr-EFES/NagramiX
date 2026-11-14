#!/usr/bin/env python3
"""Named links stay entities through editors, copied sends and broadcasts."""
import argparse
import json
from pathlib import Path
import tempfile
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import named_link_preview_runtime as runtime

STAGE='named_link_preview'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path)
    a=p.parse_args();plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='original_video_media' and len(plan['inputs'])==7 and len(plan['guards'])==30
    assert not plan['copies'] and not plan['deletions']
    assert plan['native_inputs']=={runtime.QUERY:'2b3f3484ea73431dae350a8228d9ed30c0b12e7e'}
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    old=lambda n:(OVERLAY/plan['previous'][n]).read_text()
    copy=(a.source/runtime.COPY).read_text()
    # Policy checks keep native repost/destination routing, resource lifetimes,
    # the complete actual copied body, rich content and media ownership intact.
    for marker in ['public func nagramiXMessagesWithoutAuthor(', 'public func nagramiXMessagesRequiringCopy(', 'public final class NagramiXRecipientCopyBatch {']:
        assert block(old(runtime.COPY),marker)==block(copy,marker)
    menu=(a.source/runtime.MENU).read_text()
    assert 'storeChatMessageTextInPasteboard(' in menu
    state=manifest(a.source)
    ui=runtime.ui_fixture(a.source);copied=runtime.copy_fixture(a.source)
    with tempfile.TemporaryDirectory(prefix='named-link-preview-') as folder:
        temp=Path(folder);refused=guard_checks(a.source,STAGE,plan,temp/'guards')
        runs=execute(a.swiftc,temp,'named-link-editor-send',ui)
        runs+=execute(a.swiftc,temp,'named-link-copy-broadcast',copied)
        ui_variants=[
            ('query-whitelist-missing','if nagramiXHasNamedLink(inputText) {','if false && nagramiXHasNamedLink(inputText) {','named URL never fetches an automatic card'),
            ('reopen-old-card','for media in message.media where !nagramiXSuppressPreview {','for media in message.media where true || !nagramiXSuppressPreview {','reopening old copied/forwarded post cannot seed its old card'),
            ('late-compose-card',', !nagramiXHasNamedLink($0.interfaceState.composeInputState.inputText) else { return $0.updatedUrlPreview(nil) }',' else { return $0.updatedUrlPreview(nil) }','late compose callback cannot resurrect card'),
            ('late-edit-card','guard !nagramiXHasNamedLink($0.interfaceState.editMessage?.inputState.inputText) else { return $0.updatedEditingUrlPreview(nil) }','_ = $0.interfaceState.editMessage?.inputState.inputText','late editing callback cannot resurrect card'),
            ('core-edit-rechecks-missing','disableUrlPreview || nagramiXHasNamedLinkEntities(entities?.entities ?? [])','disableUrlPreview || (false && nagramiXHasNamedLinkEntities(entities?.entities ?? []))','core edit rechecks actual entities'),
        ]
        for name,before,after,why in ui_variants:
            assert ui.count(before)==1,(name,ui.count(before));runs+=execute(a.swiftc,temp,name,ui.replace(before,after,1),why)
        marker='private func nagramiXBuildCopiedMessages('
        current=block(copy,marker);previous=block(old(runtime.COPY),marker)
        # Fixture cleaner removes public imports but retains the actual builder.
        assert copied.count(current)==1
        runs+=execute(a.swiftc,temp,'original78-carries-source-card',copied.replace(current,previous,1),'copy always disables automatic preview')
        fast=' || $0 is TelegramMediaWebpage'
        assert copied.count(fast)==1
        runs+=execute(a.swiftc,temp,'fast-forward-carries-preview',copied.replace(fast,'',1),'source webpage cannot use native fast forward')
        entities='TextEntitiesMessageAttribute(entities: entities.entities)'
        assert copied.count(entities)==1
        runs+=execute(a.swiftc,temp,'flatten-copied-hyperlink',copied.replace(entities,'TextEntitiesMessageAttribute(entities: [])',1),'copied post preserves hyperlink destination and formatting entities')
        run([a.swiftc,'-frontend','-parse',*[a.source/n for n in plan['inputs']]])
    assert state==manifest(a.source)
    report={'stage':STAGE,'runtime_paths':list(plan['inputs']),'guards':30,'loader_refusals':len(refused),'executions':runs,
        'root_cause':'Old preview suppression required attached media. Named text-only links were fetched again while composing/editing; edit initialization seeded old webpage metadata; copy builders preserved the source webpage and the native drop-author fast route carried its card unchanged.',
        'behavior':'Named URL entities keep text/URL/formatting but no automatic card in either editor, initial edit state, late callbacks, rich/plain send or core edit request. Copy/authorless-forward/broadcast remove webpage media and preview-only attributes, always setting disableLinkPreviews. Webpage-bearing selections use existing copy fallback; ordinary no-preview forwards retain native fast transport and albums stay on one transport.',
        'scope':'Actual attachments/captions/entities/rich content/thread/payment/schedule, copy staging/resource ownership, decoder/audio/recording and native incoming rendering remain. Ordinary freshly typed raw URLs retain their native preview behavior; named links and copied posts follow the approved rule.',
        'boundaries':'Production text entities/URL attributes/SignalKit, selected actual UI state/callback/send branches, full copy builder/planner/recipient batch/EnqueueMessage and native edit RPC flag decision execute. UI/rendering, URL detection, server/Postbox/media models are explicit adapters; no real Telegram delivery or iPhone pixels claimed.',
        'source_unchanged_by_checks':True,'full_application_sdk':'pending','physical_iphone':'pending','new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
