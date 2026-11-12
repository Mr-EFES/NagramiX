import Foundation
import Postbox
import SwiftSignalKit
internal import TelegramApi
import MtProtoKit

public enum EngineAudioTranscriptionResult {
    case success
    case error
}

private enum InternalAudioTranscriptionResult {
    case success(Api.messages.TranscribedAudio)
    case error(AudioTranscriptionMessageAttribute.TranscriptionError)
    case limitExceeded(Int32)
}

private func nagramiXBlocksTelegramTranscription(_ message: Message?) -> Bool {
    guard let message else { return false }
    return nagramiXCanTranscribeTemporaryMedia(message)
        || (nagramiXTemporaryMessagesEnabled() && nagramiXIsTemporaryMessage(message))
}

private func nagramiXTelegramTranscriptionTarget(transaction: Transaction, postbox: Postbox, messageId: MessageId) -> (peer: Api.InputPeer?, message: Message?) {
    let message = transaction.getMessage(messageId)
        ?? NagramiXMessageArchive.forPostbox(postbox)?.transcriptionMessage(id: messageId, liveMessage: nil)
    guard !nagramiXBlocksTelegramTranscription(message) else { return (nil, message) }
    return (transaction.getPeer(messageId.peerId).flatMap(apiInputPeer), message)
}

func _internal_transcribeAudio(postbox: Postbox, network: Network, messageId: MessageId) -> Signal<EngineAudioTranscriptionResult, NoError> {
    return postbox.transaction { transaction -> (peer: Api.InputPeer?, message: Message?) in
        return nagramiXTelegramTranscriptionTarget(transaction: transaction, postbox: postbox, messageId: messageId)
    }
    |> mapToSignal { target -> Signal<EngineAudioTranscriptionResult, NoError> in
        // The server RPC has no non-consuming mode. Recheck the preference at
        // the network boundary as well as inside the serialized preflight.
        guard let inputPeer = target.peer, !nagramiXBlocksTelegramTranscription(target.message) else {
            return .single(.error)
        }
        return network.request(Api.functions.messages.transcribeAudio(peer: inputPeer, msgId: messageId.id))
        |> map { result -> InternalAudioTranscriptionResult in
            return .success(result)
        }
        |> `catch` { error -> Signal<InternalAudioTranscriptionResult, NoError> in
            let mappedError: AudioTranscriptionMessageAttribute.TranscriptionError
            if error.errorDescription.hasPrefix("FLOOD_WAIT_") {
                if let range = error.errorDescription.range(of: "_", options: .backwards) {
                    if let value = Int32(error.errorDescription[range.upperBound...]) {
                        return .single(.limitExceeded(value))
                    }
                }
                mappedError = .generic
            } else if error.errorDescription == "MSG_VOICE_TOO_LONG" {
                mappedError = .tooLong
            } else {
                mappedError = .generic
            }
            return .single(.error(mappedError))
        }
        |> mapToSignal { result -> Signal<EngineAudioTranscriptionResult, NoError> in
            return postbox.transaction { transaction -> EngineAudioTranscriptionResult in
                let updatedAttribute: AudioTranscriptionMessageAttribute
                switch result {
                case let .success(transcribedAudio):
                    switch transcribedAudio {
                    case let .transcribedAudio(transcribedAudioData):
                        let (flags, transcriptionId, text, trialRemainingCount, trialUntilDate) = (transcribedAudioData.flags, transcribedAudioData.transcriptionId, transcribedAudioData.text, transcribedAudioData.trialRemainsNum, transcribedAudioData.trialRemainsUntilDate)
                        let isPending = (flags & (1 << 0)) != 0
                        updatedAttribute = AudioTranscriptionMessageAttribute(id: transcriptionId, text: text, isPending: isPending, didRate: false, error: nil)
                        
                        _internal_updateAudioTranscriptionTrialState(transaction: transaction) { current in
                            var updated = current
                            if let trialRemainingCount = trialRemainingCount, trialRemainingCount > 0 {
                                updated = updated.withUpdatedRemainingCount(trialRemainingCount)
                            } else if let trialUntilDate = trialUntilDate {
                                updated = updated.withUpdatedCooldownUntilTime(trialUntilDate)
                            } else {
                                updated = updated.withUpdatedCooldownUntilTime(nil)
                            }
                            return updated
                        }
                    }
                case let .error(error):
                    updatedAttribute = AudioTranscriptionMessageAttribute(id: 0, text: "", isPending: false, didRate: false, error: error)
                case let .limitExceeded(timeout):
                    let cooldownTime = Int32(CFAbsoluteTimeGetCurrent() + NSTimeIntervalSince1970) + timeout
                    _internal_updateAudioTranscriptionTrialState(transaction: transaction) { current in
                        var updated = current
                        updated = updated.withUpdatedCooldownUntilTime(cooldownTime)
                        return updated
                    }
                    return .error
                }
                    
                transaction.updateMessage(messageId, update: { currentMessage in
                    let storeForwardInfo = currentMessage.forwardInfo.flatMap(StoreMessageForwardInfo.init)
                    var attributes = currentMessage.attributes.filter { !($0 is AudioTranscriptionMessageAttribute) }
                    
                    attributes.append(updatedAttribute)
                    
                    return .update(StoreMessage(id: currentMessage.id, customStableId: nil, globallyUniqueId: currentMessage.globallyUniqueId, groupingKey: currentMessage.groupingKey, threadId: currentMessage.threadId, timestamp: currentMessage.timestamp, flags: StoreMessageFlags(currentMessage.flags), tags: currentMessage.tags, globalTags: currentMessage.globalTags, localTags: currentMessage.localTags, forwardInfo: storeForwardInfo, authorId: currentMessage.author?.id, text: currentMessage.text, attributes: attributes, media: currentMessage.media))
                })
                
                NagramiXMessageArchive.forPostbox(postbox)?.retainTelegramTranscription(id: messageId, attribute: updatedAttribute)
                if updatedAttribute.error == nil {
                    return .success
                } else {
                    return .error
                }
            }
        }
    }
}

func _internal_rateAudioTranscription(postbox: Postbox, network: Network, messageId: MessageId, id: Int64, isGood: Bool) -> Signal<Never, NoError> {
    return postbox.transaction { transaction -> (peer: Api.InputPeer?, message: Message?) in
        let target = nagramiXTelegramTranscriptionTarget(transaction: transaction, postbox: postbox, messageId: messageId)
        guard target.peer != nil else { return target }
        transaction.updateMessage(messageId, update: { currentMessage in
            var storeForwardInfo: StoreMessageForwardInfo?
            if let forwardInfo = currentMessage.forwardInfo {
                storeForwardInfo = StoreMessageForwardInfo(authorId: forwardInfo.author?.id, sourceId: forwardInfo.source?.id, sourceMessageId: forwardInfo.sourceMessageId, date: forwardInfo.date, authorSignature: forwardInfo.authorSignature, psaType: forwardInfo.psaType, flags: forwardInfo.flags)
            }
            var attributes = currentMessage.attributes
            for i in 0 ..< attributes.count {
                if let attribute = attributes[i] as? AudioTranscriptionMessageAttribute {
                    attributes[i] = attribute.withDidRate()
                }
            }
            return .update(StoreMessage(
                id: currentMessage.id,
                customStableId: nil,
                globallyUniqueId: currentMessage.globallyUniqueId,
                groupingKey: currentMessage.groupingKey,
                threadId: currentMessage.threadId,
                timestamp: currentMessage.timestamp,
                flags: StoreMessageFlags(currentMessage.flags),
                tags: currentMessage.tags,
                globalTags: currentMessage.globalTags,
                localTags: currentMessage.localTags,
                forwardInfo: storeForwardInfo,
                authorId: currentMessage.author?.id,
                text: currentMessage.text,
                attributes: attributes,
                media: currentMessage.media
            ))
        })
        
        return target
    }
    |> mapToSignal { target -> Signal<Never, NoError> in
        guard let inputPeer = target.peer, !nagramiXBlocksTelegramTranscription(target.message) else {
            return .complete()
        }
        return network.request(Api.functions.messages.rateTranscribedAudio(peer: inputPeer, msgId: messageId.id, transcriptionId: id, good: isGood ? .boolTrue : .boolFalse))
        |> `catch` { _ -> Signal<Api.Bool, NoError> in
            return .single(.boolFalse)
        }
        |> ignoreValues
    }
}

public enum AudioTranscription {
    public struct TrialState: Equatable, Codable {
        public let cooldownUntilTime: Int32?
        public let remainingCount: Int32
        
        func withUpdatedCooldownUntilTime(_ time: Int32?) -> AudioTranscription.TrialState {
            return AudioTranscription.TrialState(cooldownUntilTime: time, remainingCount: time != nil ? 0 : max(1, self.remainingCount))
        }
        
        func withUpdatedRemainingCount(_ remainingCount: Int32) -> AudioTranscription.TrialState {
            return AudioTranscription.TrialState(remainingCount: remainingCount)
        }
        
        public init(cooldownUntilTime: Int32? = nil, remainingCount: Int32) {
            self.cooldownUntilTime = cooldownUntilTime
            self.remainingCount = remainingCount
        }
        
        public static var defaultValue: AudioTranscription.TrialState {
            return AudioTranscription.TrialState(
                cooldownUntilTime: nil,
                remainingCount: 1
            )
        }
    }
}

func _internal_updateAudioTranscriptionTrialState(transaction: Transaction, _ f: (AudioTranscription.TrialState) -> AudioTranscription.TrialState) {
    let current = transaction.getPreferencesEntry(key: PreferencesKeys.audioTranscriptionTrialState)?.get(AudioTranscription.TrialState.self) ?? .defaultValue
    transaction.setPreferencesEntry(key: PreferencesKeys.audioTranscriptionTrialState, value: PreferencesEntry(f(current)))
}

// This transport deliberately accepts no peer or message ID. It uploads only
// the prepared audio and cannot call transcribe/read/consume on the original.
public enum EngineAudioFileTranscriptionError: Error, Equatable {
    case cancelled, premiumRequired, quota, tooLarge, noSpeech, unavailable, invalidResponse, network
}

public extension TelegramEngine.Messages {
    func nagramiXTranscribeAudioFile(path: String, isAllowed: @escaping () -> Bool) -> Signal<Result<String, EngineAudioFileTranscriptionError>, NoError> {
        return Signal { subscriber in
            guard isAllowed() else { subscriber.putNext(.failure(.cancelled)); subscriber.putCompletion(); return EmptyDisposable }
            let data: Data
            do {
                let attributes = try FileManager.default.attributesOfItem(atPath: path)
                guard let size = attributes[.size] as? NSNumber, size.int64Value > 0, size.int64Value <= 25 * 1024 * 1024 else {
                    subscriber.putNext(.failure(.tooLarge)); subscriber.putCompletion(); return EmptyDisposable
                }
                data = try Data(contentsOf: URL(fileURLWithPath: path), options: .mappedIfSafe)
                guard !data.isEmpty, data.count <= 25 * 1024 * 1024 else { subscriber.putNext(.failure(.tooLarge)); subscriber.putCompletion(); return EmptyDisposable }
            } catch {
                subscriber.putNext(.failure(.unavailable)); subscriber.putCompletion(); return EmptyDisposable
            }
            guard isAllowed() else { subscriber.putNext(.failure(.cancelled)); subscriber.putCompletion(); return EmptyDisposable }
            let upload = multipartUpload(network: self.account.network, postbox: self.account.postbox, source: .data(data), encrypt: false, tag: nil, hintFileSize: Int64(data.count), hintFileIsLarge: false, forceNoBigParts: true)
            |> filter { value in
                if case .progress = value { return false }
                return true
            }
            |> take(1)
            |> mapToSignal { value -> Signal<Result<String, EngineAudioFileTranscriptionError>, MultipartUploadError> in
                guard isAllowed() else { return .single(.failure(.cancelled)) }
                switch value {
                case .progress: return .complete()
                case let .inputFile(file):
                    let namedFile: Api.InputFile
                    switch file {
                    case let .inputFile(value): namedFile = .inputFile(.init(id: value.id, parts: value.parts, name: "voice.m4a", md5Checksum: value.md5Checksum))
                    case let .inputFileBig(value): namedFile = .inputFileBig(.init(id: value.id, parts: value.parts, name: "voice.m4a"))
                    case .inputFileStoryDocument: return .single(.failure(.unavailable))
                    }
                    guard isAllowed() else { return .single(.failure(.cancelled)) }
                    return self.account.network.request(Api.functions.messages.transcribeAudioFile(file: namedFile), automaticFloodWait: false)
                    |> map { value -> Result<String, EngineAudioFileTranscriptionError> in
                        guard isAllowed() else { return .failure(.cancelled) }
                        switch value {
                        case let .transcribedAudio(value):
                            guard (value.flags & 1) == 0, value.text.utf16.count <= 100_000 else { return .failure(.invalidResponse) }
                            let text = value.text.trimmingCharacters(in: .whitespacesAndNewlines)
                            return text.isEmpty ? .failure(.noSpeech) : .success(text)
                        }
                    }
                    |> `catch` { error -> Signal<Result<String, EngineAudioFileTranscriptionError>, MultipartUploadError> in
                        guard isAllowed() else { return .single(.failure(.cancelled)) }
                        let description = error.errorDescription
                        if description == "PREMIUM_ACCOUNT_REQUIRED" { return .single(.failure(.premiumRequired)) }
                        if description.hasPrefix("FLOOD_WAIT") || description.hasPrefix("FLOOD_PREMIUM_WAIT") { return .single(.failure(.quota)) }
                        if description == "MSG_VOICE_TOO_LONG" || description == "FILE_TOO_BIG" { return .single(.failure(.tooLarge)) }
                        if description == "METHOD_INVALID" || description == "INPUT_METHOD_INVALID" || description == "METHOD_NOT_AVAILABLE" { return .single(.failure(.unavailable)) }
                        return .single(.failure(.network))
                    }
                case .inputSecretFile: return .single(.failure(.unavailable))
                }
            }
            |> `catch` { _ -> Signal<Result<String, EngineAudioFileTranscriptionError>, NoError> in
                return .single(.failure(isAllowed() ? .network : .cancelled))
            }
            return upload.start(next: subscriber.putNext, completed: subscriber.putCompletion)
        }
    }
}
