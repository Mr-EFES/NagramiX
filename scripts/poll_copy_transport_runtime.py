"""Полная production-ветка сборки poll и media resolver с настоящим SignalKit."""
from pathlib import Path
from validate_quick_format import block
from validate_copy_delivery import clean
from copy_reference_recovery_runtime import source_model, CORE, UPLOAD, SK, FIXTURE

ROOT=Path(__file__).resolve().parents[1]
TESTS=ROOT/'tests/fixtures/poll_copy_transport'
COPY=CORE+'Utils/NagramiXOutgoingCopy.swift'


def fixture(source):
    boundary=(FIXTURE/'Boundary.swift').read_text()
    pieces=[boundary]
    for name in ['Atomic.swift','Disposable.swift','Subscriber.swift']:
        pieces.append((source/(SK+name)).read_text())
    signal=(source/(SK+'Signal.swift')).read_text()
    pieces.append(signal[:signal.index('@available(iOS 13.0')])
    operators={
        'Signal_Single.swift':['public func single<'],
        'Signal_Mapping.swift':['public func map<T, E, R>(', 'public func castError<T, E>(', 'public func mapError<T, E, R>('],
        'Signal_Catch.swift':['public func `catch`<'],
        'Signal_Take.swift':['public func take<T, E>(_ count:'],
        'Signal_Meta.swift':['private final class SignalQueueState','public func switchToLatest<','public func mapToSignal<T, R, E>(', 'public func then<T, E>('],
        'Signal_Timing.swift':['public func timeout<T, E>('],
        'Signal_Combine.swift':['private struct SignalCombineState {','private func combineLatestAny<','private func signalOfAny<','public func combineLatest<T, E>(queue:'],
    }
    for name,markers in operators.items():
        text=(source/(SK+name)).read_text()
        for marker in markers:pieces.append(block(text,marker))
    pieces.append('public func deliverOn<T,E>(_ queue:Queue)->(Signal<T,E>)->Signal<T,E>{{ $0 }}')
    pieces.append(clean(source_model(source)))
    policy=(source/(CORE+'Utils/NagramiXContentCopy.swift')).read_text()
    for marker in ['func nagramiXMapPollMedia(', 'func nagramiXPollMediaAttachments(']:pieces.append(clean(block(policy,marker)))
    pieces.append((TESTS/'Boundary.swift').read_text())
    upload=(source/UPLOAD).read_text()
    for marker in ['func nagramiXCopyRefreshSignal<Value>(', 'func nagramiXCopyRefreshedMedia(', 'private func nagramiXPollCopyReferenceCanRetry(', 'private func nagramiXPollCopyMediaContent(']:
        pieces.append(block(upload,marker).replace('private func','func',1))
    pieces.append(block((source/COPY).read_text(),'private func nagramiXCopyPollAsNew(').replace('private func','func',1))
    branch=block(upload,'    } else if let poll = media as? TelegramMediaPoll {')
    branch=branch[branch.index('{')+1:-1]
    pieces.append('''func productionPoll(_ poll:TelegramMediaPoll,network:Network,postbox:Postbox,revalidationContext:MediaReferenceRevalidationContext,peerId:PeerId=2,attributes:[MessageAttribute]=[OutgoingContentInfoMessageAttribute()],forceReupload:Bool=false)->Signal<PendingMessageUploadedContentResult,PendingMessageUploadError> {
        let accountPeerId:PeerId=1,auxiliaryMethods=AccountAuxiliaryMethods(),messageMediaPreuploadManager=MessageMediaPreuploadManager()
        let transformOutgoingMessageMedia:TransformOutgoingMessageMedia?=nil
        let forceNoBigParts=false,messageId:MessageId?=MessageId(peerId:peerId,id:44),text="caption with https://example.org"
        let explicitPartialReference:PartialMediaReference? = .message(message:17)
        let mediaReference:AnyMediaReference?=nil
'''+branch+'\n}\n')
    factory=(FIXTURE/'Tests.swift').read_text();start=factory.index('func doc(');end=factory.index('func refresh(',start)
    pieces.append(factory[start:end])
    pieces.append((TESTS/'Tests.swift').read_text())
    return '\n'.join(pieces)


def negatives(text):
    changes=[
        ('received-answer-form','} else if isCopiedPoll {','} else if isCopiedPoll && false {','new poll uses input answers'),
        ('source-subscriber-rule','restrictToSubscribers: false, countries: poll.countries','restrictToSubscribers: poll.restrictToSubscribers, countries: poll.countries','source channel rule is not inherited'),
        ('source-option-identities','opaqueIdentifier: Data(String(index).utf8)','opaqueIdentifier: option.opaqueIdentifier','fresh native option IDs'),
        ('skip-reference-registration','(!isCopiedPoll && !forceReupload && attachments.allSatisfy','(!forceReupload && attachments.allSatisfy','cloud video is registered without byte upload'),
        ('retry-permission-failure','guard nagramiXPollCopyReferenceCanRetry(error.errorDescription) else','guard nagramiXPollCopyReferenceCanRetry(error.errorDescription) || error.errorDescription.contains("FORBIDDEN") else','permission failure remains a real failure'),
        ('drop-empty-refresh-fallback','return uploadBytes(media)\n            }\n            return registerReference(updated)','return .complete()\n            }\n            return registerReference(updated)','empty refresh falls back to bytes'),
    ]
    out=[]
    for name,old,new,reason in changes:
        assert old in text,name
        out.append((name,text.replace(old,new,1),reason))
    return out
