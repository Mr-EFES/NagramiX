#!/usr/bin/env python3
"""Execute the production copy-reference recovery helpers with native SignalKit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
CORE = 'submodules/TelegramCore/Sources/'
UPLOAD = CORE + 'PendingMessages/PendingMessageUploadedContent.swift'
SK = 'submodules/SSignalKit/SwiftSignalKit/Source/'
FIXTURE = ROOT / 'tests/fixtures/copy_reference_recovery'


def source_model(source):
    """Use the real model fields and constructors; codecs and network are boundaries."""
    image = (source / (CORE + 'SyncCore/SyncCore_TelegramMediaImage.swift')).read_text()
    file = (source / (CORE + 'SyncCore/SyncCore_TelegramMediaFile.swift')).read_text()
    poll = (source / (CORE + 'SyncCore/SyncCore_TelegramMediaPoll.swift')).read_text()
    out = [block(image, 'public struct TelegramMediaImageFlags:')]
    out.append('public final class TelegramMediaImage: Media {\n'
               'public struct VideoRepresentation { let token: Int }\n'
               'public struct EmojiMarkup { let token: Int }\n' +
               image[image.index('    public let imageId:'):image.index('    public init(decoder:', image.index('    public let imageId:'))] +
               block(image, 'public func withUpdatedPartialReference(') + '\n}')
    out.append('public final class TelegramMediaFile: Media {\n'
               'public struct VideoThumbnail { let token: Int }\n' +
               file[file.index('    public let fileId:'):file.index('    public var indexableText:')] +
               block(file, 'public init(\n        fileId:') + '\n' +
               block(file, 'public func withUpdatedResource(') + '\n' +
               block(file, 'public func withUpdatedPartialReference(') + '\n}')
    # Each of these value constructors is part of the exact production mapper's contract.
    option = poll[poll.index('public struct TelegramMediaPollOption:'):poll.index('public struct TelegramMediaPollOptionVoters:')]
    out.append('public final class TelegramMediaPollOption {\n' +
               option[option.index('    public let text:'):option.index('    public init(decoder:')] + '\n}')
    voters = poll[poll.index('public struct TelegramMediaPollOptionVoters:'):poll.index('public struct TelegramMediaPollResults:')]
    out.append('public final class TelegramMediaPollOptionVoters {\n' +
               voters[voters.index('    public let selected:'):voters.index('    public init(decoder:')] + '\n}')
    results = poll[poll.index('public struct TelegramMediaPollResults:'):poll.index('public enum TelegramMediaPollPublicity:')]
    solution = results[results.index('    public struct Solution:'):results.index('    public let voters:')]
    out.append('public final class TelegramMediaPollResults {\npublic struct Solution {\n' +
               solution[solution.index('        public let text:'):solution.index('        public static func ==')] + '\n}\n' +
               results[results.index('    public let voters:'):results.index('    public init(decoder:')] + '\n}')
    fields = poll[poll.index('    public let publicity:'):poll.index('    public init(pollId:')]
    out.append('public final class TelegramMediaPoll: Media {\n'
               'public let pollId: MediaId\npublic var id: MediaId? { pollId }\n' + fields +
               block(poll, 'public init(pollId:') + '\n}')
    return '\n'.join(out)


def runtime_source(source):
    pieces = [(FIXTURE / 'Boundary.swift').read_text()]
    native = ['Atomic.swift', 'Disposable.swift', 'Subscriber.swift']
    for name in native:
        pieces.append((source / (SK + name)).read_text())
    signal = (source / (SK + 'Signal.swift')).read_text()
    pieces.append(signal[:signal.index('@available(iOS 13.0')])
    extra = {
        'Signal_Mapping.swift': ['public func map<T, E, R>(', 'public func castError<T, E>('],
        'Signal_Catch.swift': ['public func `catch`<'],
        'Signal_Take.swift': ['public func take<T, E>(_ count:'],
        'Signal_Meta.swift': ['private final class SignalQueueState', 'public func switchToLatest<',
                              'public func mapToSignal<T, R, E>(', 'public func then<T, E>('],
        'Signal_Timing.swift': ['public func timeout<T, E>('],
    }
    for name, markers in extra.items():
        text = (source / (SK + name)).read_text()
        pieces.extend(block(text, marker) for marker in markers)
    pieces.append(source_model(source))
    policy = (source / (CORE + 'Utils/NagramiXContentCopy.swift')).read_text()
    pieces.append(block(policy, 'public func nagramiXMapPollMedia('))
    pieces.append(block(policy, 'public func nagramiXPollMediaAttachments('))
    upload = (source / UPLOAD).read_text()
    helpers = ['func nagramiXCopyRefreshSignal<Value>(', 'func nagramiXCopyRefreshedMedia(']
    pieces.extend(block(upload, marker) for marker in helpers)
    pieces.append((FIXTURE / 'SenderBoundary.swift').read_text())
    refresh_start = upload.index('    if nagramiXRefreshCopyReferences && !forceReupload')
    refresh_end = upload.index('    if let media = media.first as? TelegramMediaAction', refresh_start)
    pieces.append('''func productionRefreshCopy(accountPeerId: PeerId = 1, network: Network = Network(),
        postbox: Postbox = Postbox(), auxiliaryMethods: AccountAuxiliaryMethods = AccountAuxiliaryMethods(),
        transformOutgoingMessageMedia: TransformOutgoingMessageMedia? = nil,
        messageMediaPreuploadManager: MessageMediaPreuploadManager = MessageMediaPreuploadManager(),
        revalidationContext: MediaReferenceRevalidationContext, forceReupload: Bool = false,
        isGrouped: Bool = false, passFetchProgress: Bool = true, forceNoBigParts: Bool = false,
        peerId: PeerId = 2, messageId: MessageId? = MessageId(peerId: 2, id: 44),
        attributes: [MessageAttribute], text: String = "copied caption", media: [Media],
        mediaReference: AnyMediaReference? = nil, nagramiXRefreshCopyReferences: Bool = true,
        explicitPartialReference: PartialMediaReference? = .message(message: 17),
        forwardInfo: ForwardSourceInfoAttribute? = nil) -> MessageContentToUpload {
''' + upload[refresh_start:refresh_end] + '''
        return .immediate(.bypassed, .media)
    }
''')
    pieces.append('@main struct CopyReferenceRecoveryChecks { static func main() {\n' +
                  (FIXTURE / 'Tests.swift').read_text() + '\n} }')
    native += ['Signal.swift', *extra]
    return '\n'.join(pieces), native


def fixtures(source):
    """Production-extracted Swift fixtures for the stage validator's compiler loop."""
    return {'CopyReferenceRecovery.swift': runtime_source(source)[0]}


def validate(source, swiftc):
    combined, native = runtime_source(source)
    executions = []
    with tempfile.TemporaryDirectory(prefix='copy-reference-runtime-') as temp:
        folder = Path(temp)
        main = folder / 'main.swift'
        main.write_text(combined)
        for mode in ['debug', 'optimized']:
            binary = folder / mode
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'),
                       str(main), '-o', str(binary)]
            if mode == 'optimized':
                command.insert(1, '-O')
            subprocess.run(command, check=True)
            output = subprocess.check_output([str(binary)], text=True, timeout=30).strip()
            executions.append({'mode': mode, 'output': output})
    return {
        'executions': executions,
        'production_helpers': ['nagramiXCopyRefreshSignal', 'nagramiXCopyRefreshedMedia',
                               'nagramiXMapPollMedia', 'nagramiXPollMediaAttachments',
                               'messageContentToUpload refresh branch'],
        'native_signal_files': {name: hashlib.sha256((source / (SK + name)).read_bytes()).hexdigest()
                                for name in native},
        'boundary': 'Real production helpers, model fields/constructors and native SignalKit operators; '
                    'deterministic Queue/Timer and Telegram resource/message values are adapters. '
                    'No Apple SDK, Telegram RPC or physical device claim.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = validate(args.source, args.swiftc)
    report = json.dumps(result, indent=2) + '\n'
    if args.report:
        args.report.write_text(report)
    print(report, end='')
