#!/usr/bin/env python3
"""Проверить явное открытие временного медиа, его сохранение и capture privacy."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import execute,run
import content_interaction_consent_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]
STAGE='content_interaction_consent'


def contract(source):
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='hide_premium_offers'
    assert len(plan['inputs'])==81 and len(plan['guards'])==22 and len(plan['native_inputs'])==1
    assert not plan['copies'] and not plan['deletions']
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,sha in {**plan['outputs'],**plan['guards']}.items():assert digest(source/name)==sha,name
    previous=lambda name:(ROOT/'ios'/plan['previous'][name]).read_text()
    for name,sha in plan['native_inputs'].items():
        data=previous(name).encode();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==sha
    mark=(source/runtime.MARK).read_text()
    assert block(mark,'func _internal_markMessageContentAsConsumedInteractively(')==block(previous(runtime.MARK),'func _internal_markMessageContentAsConsumedInteractively('),'automatic native producer changed'
    assert block(mark,'func markMessageContentAsConsumedRemotely(')==block(previous(runtime.MARK),'func markMessageContentAsConsumedRemotely('),'server truth changed'
    explicit=block(mark,'func _internal_markTemporaryMediaOpened(')
    for forbidden in ['countdownBeginTime:', 'UserDefaults', 'applyMaxRead', 'updateReadState', 'AutoremoveTimeoutMessageAttribute(', 'AutoclearTimeoutMessageAttribute(']:assert forbidden not in explicit,forbidden
    engine=(source/runtime.ENGINE).read_text();new=block(engine,'        public func markTemporaryMediaOpened(')
    start=engine.index('        /// User consent is persisted');end=engine.index('        public func installInteractiveReadMessagesAction(',start)
    assert engine[:start]+engine[end:]==previous(runtime.ENGINE),'unrelated engine API changed'
    assert new.index('nagramiXFetchContentCopyMedia')<new.index('canExplicitlyOpenTemporaryMedia')<new.index('authorizeTemporaryMediaOpen')<new.index('_internal_markTemporaryMediaOpened')
    assert new.count('timeout(')==2 and 'take(1)' in new
    menu=(source/runtime.MENU).read_text();start=menu.index('        if nagramiXCanMarkTemporaryMediaOpened(message) {');end=menu.index('        if (UserDefaults.standard.object(forKey: "nagramix.context.transcribe")',start)
    assert menu[:start]+menu[end:]==previous(runtime.MENU),'unrelated menu action changed'
    action=menu[start:end]
    assert 'disposable.dispose()' in action and 'afterDisposed' in action and 'progress.dismiss()' in action
    assert 'nagramiXMarkTemporaryOpened' in action and '.start(next:' in action
    archive=(source/runtime.ARCHIVE).read_text();readonly=block(archive,'    public func temporaryInteractionMessage(')
    for bad in ['persist(', 'captureTemporary', 'snapshotForExpiredMessage(', '.queue.', '.network.']:assert bad not in readonly,bad
    assert 'var explicitlyOpened: Bool? = nil' in archive
    consent=block(archive,'    public func authorizeTemporaryMediaOpen(')
    assert 'retryNow: true' in consent and 'subscriber.putNext(saved)' in consent
    assert 'hasCompleteRetainedMedia' not in consent # readiness is centralized in the real renderer
    ready=block(archive,'    public func canExplicitlyOpenTemporaryMedia(')
    assert 'requireCompleteMedia: true' in ready and 'record.deletedAt == nil' in ready
    secret=(source/runtime.SECRET).read_text();old=previous(runtime.SECRET)
    for marker in ['private func boxedDecryptedSecretMessageAction(', 'private func markOutgoingOperationAsCompleted(', 'private func sendServiceActionMessage(']:
        assert block(secret,marker)==block(old,marker),marker
    capture='submodules/TelegramCore/Sources/SecretChats/SetSecretChatMessageAutoremoveTimeoutInteractively.swift'
    text=(source/capture).read_text();guard='        guard nagramiXShouldNotifyScreenCapture() else { return }\n'
    assert text.replace(guard,'')==previous(capture) and text.count(guard)==1
    # Copy semantics remain the agreed independent copies; no consent metadata
    # is ever part of an outgoing MessageAttribute or public content payload.
    assert runtime.receipts.CORE+'Utils/NagramiXContentCopy.swift' in plan['guards']
    return plan


def negatives(archive,consumption,engine):
    def change(name,text,old,new,reason):
        assert old in text,name
        return name,text.replace(old,new,1),reason
    no_cancel=archive.replace('guard !cancelled.with({ $0 }), self.canExplicitlyOpenTemporaryMedia(id: id) else', 'guard self.canExplicitlyOpenTemporaryMedia(id: id) else',1)
    authorize=block(archive,'    func authorizeTemporaryMediaOpen(')
    failed_write=archive.replace(authorize,authorize.replace('subscriber.putNext(saved); subscriber.putCompletion()', 'subscriber.putNext(true); subscriber.putCompletion()'),1)
    return [
        change('automatic-leak',consumption,'if nagramiXShouldSuppressTemporaryReceipt(transaction: transaction, postbox: postbox, messageId: messageId) { return }','if false { return }','automatic playback sends no content receipt'),
        change('missing-consent',consumption,'NagramiXMessageArchive.forPostbox(postbox)?.hasExplicitTemporaryMediaOpen(id: messageId) == true else { return false }','true else { return false }','producer requires durable consent'),
        change('ghost-drops-explicit',consumption,'!NagramiXGhostSettings.current.hidesMessageReads || explicitMediaOpen','!NagramiXGhostSettings.current.hidesMessageReads && explicitMediaOpen','exactly one selected native receipt'),
        change('queued-neighbour-leaks',consumption,'&& !nagramiXShouldSuppressTemporaryReceipt(transaction: transaction, postbox: postbox, messageId: id, allowExplicitOpen: true)','&& true','mixed queued IDs'),
        change('capture-queue-leaks',consumption,'if case let .screenshotMessages(layer, actionGloballyUniqueId, _, _) = action, !nagramiXShouldNotifyScreenCapture() {','if case let .screenshotMessages(layer, actionGloballyUniqueId, _, _) = action, false {','capture bypass replaces queued screenshot'),
        change('expired-hidden',archive,'guard (deleted && settings.showDeletedMessages) || (settings.saveTemporaryMessages && record.wasTemporary) else','guard deleted ? settings.showDeletedMessages : (settings.saveTemporaryMessages && record.wasTemporary) else','temporary snapshot remains'),
        change('fake-deleted-style',archive,'deletedAt: settings.showDeletedMessages ? (record.deletedAt ?? 0) : 0','deletedAt: record.deletedAt ?? 0','deleted styling belongs only'),
        change('premature-consent',archive,'requireCompleteMedia: true),\n              !retained.media.isEmpty','requireCompleteMedia: false),\n              !retained.media.isEmpty','incomplete retained file denies consent'),
        ('cancelled-consent-commits',no_cancel,'cancelled queued consent never commits'),
        ('failed-write-authorized',failed_write,'failed JSON write cannot authorize receipt'),
        change('fetch-failure-ignored',engine,'guard fetched, nagramiXTemporaryMessagesEnabled() else','guard nagramiXTemporaryMessagesEnabled() else','engine preparation result: fetch-fails'),
    ]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=contract(a.source);before=manifest(a.source)
    texts=[runtime.archive(a.source),runtime.consumption(a.source),runtime.orchestration(a.source)]
    with tempfile.TemporaryDirectory(prefix='nagramix-content-consent-') as tmp:
        root=Path(tmp);refusals=guard_checks(a.source,STAGE,plan,root/'guards');runs=[]
        for name,text in zip(['archive','consumption','engine'],texts):runs+=execute(a.swiftc,root,name,text)
        for name,text,reason in negatives(*texts):runs+=execute(a.swiftc,root,name,text,reason)
        paths=[name for name in plan['outputs'] if name.endswith('.swift')]
        for name in paths:run([a.swiftc,'-frontend','-parse',a.source/name])
    run(['python3',a.source/'build-system/Make/PostboxImportCheck.py',a.source])
    assert manifest(a.source)==before
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),'native_inputs':plan['native_inputs'],'loader_refusals':len(refusals),'runs':runs,'swift_parse':len(paths),'source_unchanged':True,'source_files':len(before),
      'boundary':'Production eligibility, Codable record, archive persistence/rendering, consume producer, secret action filter and native serializers execute with explicit Postbox/media/queue/network adapters. Engine method executes with immediate deadline adapter; real SignalKit timeout timing and UIKit progress/menu are not proven. Apple SDK, actual file retention and Telegram/iPhone network acceptance require device verification.',
      'apple_sdk':'not_run','ipa':'not_built','physical_iphone':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['outputs','runs']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
