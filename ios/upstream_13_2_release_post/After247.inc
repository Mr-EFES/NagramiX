import Foundation
import UIKit
import AsyncDisplayKit
import Display
import SwiftSignalKit
import TelegramCore
import AccountContext
import PresentationDataUtils
import TelegramPresentationData
import TelegramStringFormatting
import ManagedDiceAnimationNode
import SlotMachineAnimationNode

// A small native progress controller. It does not own the send operation;
// cancellation is explicit and leaves the recipient selection intact.
private final class NagramiXCopyProgressController: ViewController {
    private let panel = ASDisplayNode()
    private let indicator = UIProgressView(progressViewStyle: .default)
    private let percentage = UILabel()
    private let cancel = UIButton(type: .system)
    private let formatter = NumberFormatter()
    private let cancelled: () -> Void
    private let background: UIColor
    private let foreground: UIColor
    private let accent: UIColor
    private let cancelTitle: String
    private var dismissedOnce = false

    init(background: UIColor, foreground: UIColor, accent: UIColor, title: String, language: String, cancelled: @escaping () -> Void) {
        self.background = background
        self.foreground = foreground
        self.accent = accent
        self.cancelTitle = title
        self.cancelled = cancelled
        self.formatter.locale = Locale(identifier: language)
        self.formatter.numberStyle = .percent
        self.formatter.maximumFractionDigits = 0
        super.init(navigationBarPresentationData: nil)
        self.statusBar.statusBarStyle = .Ignore
    }
    required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.displayNode.backgroundColor = self.background.withAlphaComponent(0.4)
        self.panel.backgroundColor = self.background
        self.panel.cornerRadius = 14.0
        self.displayNode.addSubnode(self.panel)
        self.percentage.font = Font.regular(17.0)
        self.percentage.textColor = self.foreground
        self.percentage.textAlignment = .center
        self.indicator.progressTintColor = self.accent
        self.indicator.trackTintColor = self.accent.withAlphaComponent(0.2)
        self.cancel.setTitle(self.cancelTitle, for: .normal)
        self.cancel.titleLabel?.font = Font.regular(17.0)
        self.cancel.tintColor = self.accent
        self.cancel.addTarget(self, action: #selector(self.cancelPressed), for: .touchUpInside)
        self.panel.view.addSubview(self.percentage)
        self.panel.view.addSubview(self.indicator)
        self.panel.view.addSubview(self.cancel)
        self.displayNodeDidLoad()
    }
    override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        let width = min(260.0, layout.size.width - 40.0)
        self.panel.frame = CGRect(x: (layout.size.width - width) / 2.0, y: (layout.size.height - 136.0) / 2.0, width: width, height: 136.0)
        self.percentage.frame = CGRect(x: 12.0, y: 12.0, width: width - 24.0, height: 28.0)
        self.indicator.frame = CGRect(x: 20.0, y: 58.0, width: width - 40.0, height: 4.0)
        self.cancel.frame = CGRect(x: 12.0, y: 84.0, width: width - 24.0, height: 44.0)
    }
    func updateProgress(_ value: Float) {
        let value = min(1.0, max(0.0, value))
        self.indicator.setProgress(value, animated: true)
        self.percentage.text = self.formatter.string(from: NSNumber(value: value))
        self.percentage.accessibilityLabel = self.percentage.text
    }
    @objc private func cancelPressed() { self.cancelled(); self.dismiss() }
    override func dismiss(completion: (() -> Void)? = nil) {
        guard !self.dismissedOnce else { completion?(); return }
        self.dismissedOnce = true
        self.presentingViewController?.dismiss(animated: false, completion: completion)
    }
}

private func nagramiXCopyImageMessage(context: AccountContext, source: EngineRawMessage, image: UIImage) -> EngineRawMessage? {
    guard let data = image.pngData() else { return nil }
    let resource = LocalFileMediaResource(fileId: Int64.random(in: Int64.min ... Int64.max))
    context.engine.resources.storeResourceData(id: EngineMediaResource.Id(resource.id), data: data, synchronous: true)
    let dimensions = PixelDimensions(width: Int32(image.size.width * image.scale), height: Int32(image.size.height * image.scale))
    let media = TelegramMediaImage(imageId: EngineMedia.Id(namespace: Namespaces.Media.LocalImage, id: Int64.random(in: 1 ... Int64.max)), representations: [TelegramMediaImageRepresentation(dimensions: dimensions, resource: resource, progressiveSizes: [], immediateThumbnailData: nil, hasVideo: false, isPersonal: false)], immediateThumbnailData: nil, reference: nil, partialReference: nil, flags: [])
    return source.withUpdatedMedia([media])
}

// The original outcome is rendered; no inputMediaDice or monetary stake RPC
// is ever constructed by the copy path, including the fallback renderer.
private func nagramiXDiceResultImage(_ dice: TelegramMediaDice) -> UIImage? {
    guard let value = dice.value, value > 0 else { return nil }
    let size = CGSize(width: 384.0, height: 224.0)
    return UIGraphicsImageRenderer(size: size).image { renderer in
        let rect = CGRect(origin: .zero, size: size)
        UIColor.white.setFill(); renderer.fill(rect)
        let text: String
        if dice.emoji == "🎰", value <= 64 {
            let raw = value - 1
            let symbols = ["BAR", "🍇", "🍋", "7"]
            text = [symbols[Int(raw & 3)], symbols[Int((raw >> 2) & 3)], symbols[Int((raw >> 4) & 3)]].joined(separator: "  ")
        } else {
            text = dice.emoji + "  " + String(value)
        }
        let style = NSMutableParagraphStyle(); style.alignment = .center
        (text as NSString).draw(in: CGRect(x: 8.0, y: 68.0, width: size.width - 16.0, height: 100.0), withAttributes: [.font: Font.regular(52.0), .foregroundColor: UIColor.black, .paragraphStyle: style])
    }
}

private func nagramiXCopyDiceImage(context: AccountContext, source: EngineRawMessage, dice: TelegramMediaDice) -> Signal<EngineRawMessage?, NoError> {
    guard let value = dice.value, value > 0 else { return .single(nil) }
    return Signal { subscriber in
        let finished = Atomic<Bool>(value: false)
        let retainedNode: ASDisplayNode
        func finish(_ image: UIImage?) {
            guard !finished.swap(true) else { return }
            subscriber.putNext(image.flatMap { nagramiXCopyImageMessage(context: context, source: source, image: $0) })
            subscriber.putCompletion()
        }
        if dice.emoji == "🎰" {
            let node = SlotMachineAnimationNode(account: context.account)
            retainedNode = node
            node.nagramiXStillImageUpdated = { image in finish(image) }
            node.frame = CGRect(x: 0, y: 0, width: 184, height: 184)
            _ = node.view
            node.setState(.value(value, true))
            node.setNeedsLayout(); node.layoutIfNeeded()
        } else {
            let node = ManagedDiceAnimationNode(context: context, emoji: dice.emoji.strippedEmoji)
            retainedNode = node
            node.imageUpdated = { image in finish(image) }
            node.setState(.value(value, true))
        }
        Queue.mainQueue().after(15.0) {
            if !finished.with({ $0 }) { finish(nagramiXDiceResultImage(dice)) }
        }
        return ActionDisposable {
            _ = retainedNode
            _ = finished.swap(true)
        }
    }
}

private func nagramiXCopyOriginalLink(context: AccountContext, message: EngineRawMessage) -> Signal<String?, NoError> {
    if let story = message.media.first as? TelegramMediaStory {
        return context.engine.messages.exportStoryLink(peerId: story.storyId.peerId, id: story.storyId.id)
        |> timeout(15.0, queue: Queue.mainQueue(), alternate: .single(nil))
    }
    return context.engine.messages.exportMessageLink(peerId: message.id.peerId, messageId: message.id)
    |> timeout(15.0, queue: Queue.mainQueue(), alternate: .single(nil))
}

private func nagramiXCopyCard(context: AccountContext, message: EngineRawMessage, presentationData: PresentationData) -> Signal<EngineRawMessage?, NoError> {
    return nagramiXCopyOriginalLink(context: context, message: message)
    |> map { link -> EngineRawMessage? in
        var parts: [String] = []
        if !message.text.isEmpty { parts.append(message.text) }
        if let invoice = message.media.first as? TelegramMediaInvoice {
            parts.append(invoice.title)
            if !invoice.description.isEmpty { parts.append(invoice.description) }
            let formatter = NumberFormatter(); formatter.numberStyle = .currency
            formatter.locale = Locale(identifier: presentationData.strings.baseLanguageCode)
            formatter.currencyCode = invoice.currency
            let digits = invoice.currency == "XTR" ? 0 : formatter.maximumFractionDigits
            let amount = NSDecimalNumber(value: invoice.totalAmount).dividing(by: NSDecimalNumber(mantissa: 1, exponent: Int16(digits), isNegative: false))
            parts.append(formatter.string(from: amount) ?? (invoice.currency + " " + amount.stringValue))
        } else if let game = message.media.first as? TelegramMediaGame {
            parts.append(game.title)
            if !game.description.isEmpty { parts.append(game.description) }
        } else if let poll = message.media.first as? TelegramMediaPoll {
            parts.append(poll.text)
            parts.append(contentsOf: poll.options.map { "• " + $0.text })
            if let solution = poll.results.solution, !solution.text.isEmpty { parts.append(solution.text) }
        } else if let todo = message.media.first as? TelegramMediaTodo {
            parts.append(todo.text)
            let completed = Set(todo.completions.map { $0.id })
            parts.append(contentsOf: todo.items.map { (completed.contains($0.id) ? "☑︎ " : "☐ ") + $0.text })
        } else {
            let description = descriptionStringForMessage(contentSettings: context.currentContentSettings.with { $0 }, message: EngineMessage(message), strings: presentationData.strings, nameDisplayOrder: presentationData.nameDisplayOrder, dateTimeFormat: presentationData.dateTimeFormat, accountPeerId: context.account.peerId).0.string
            if !description.isEmpty && !parts.contains(description) { parts.append(description) }
        }
        if let link, !link.isEmpty { parts.append(link) }
        let text = parts.filter { !$0.isEmpty }.joined(separator: "\n\n")
        guard !text.isEmpty else { return nil }
        let entities = generateTextEntities(text, enabledTypes: .all)
        return message.withUpdatedText(text).withUpdatedMedia([]).withUpdatedAttributes(message.attributes.filter { !($0 is TextEntitiesMessageAttribute) && !($0 is RichTextMessageAttribute) } + [TextEntitiesMessageAttribute(entities: entities)])
    }
}

extension ChatControllerImpl {
    func nagramiXResolveCopyObjects(messages: [EngineRawMessage], completion: @escaping ([EngineRawMessage]?) -> Void) {
        let data = self.presentationData
        let context = self.context
        let signals: [Signal<EngineRawMessage?, NoError>] = messages.map { message in
            guard let media = message.media.first else { return .single(message) }
            if let dice = media as? TelegramMediaDice {
                if dice.value == nil || dice.value == 0 { return nagramiXCopyCard(context: context, message: message, presentationData: data) }
                return nagramiXCopyDiceImage(context: context, source: message, dice: dice)
            }
            if let story = media as? TelegramMediaStory {
                return context.engine.messages.getStory(peerId: story.storyId.peerId, id: story.storyId.id)
                |> timeout(20.0, queue: Queue.mainQueue(), alternate: .single(nil))
                |> mapToSignal { item -> Signal<EngineRawMessage?, NoError> in
                    guard case let .item(story)? = item, let media = story.media, story.music == nil, story.mediaAreas.isEmpty else {
                        return nagramiXCopyCard(context: context, message: message, presentationData: data)
                    }
                    let prefix = message.text.isEmpty ? "" : message.text + "\n\n"
                    let offset = prefix.utf16.count
                    let oldEntities = message.attributes.compactMap { $0 as? TextEntitiesMessageAttribute }.first?.entities ?? []
                    let entities = oldEntities + story.entities.map { MessageTextEntity(range: ($0.range.lowerBound + offset) ..< ($0.range.upperBound + offset), type: $0.type) }
                    var result = message.withUpdatedMedia([media]).withUpdatedText(prefix + story.text).withUpdatedAttributes(message.attributes.filter { !($0 is TextEntitiesMessageAttribute) } + [TextEntitiesMessageAttribute(entities: entities)])
                    if story.isForwardingDisabled { result = result.withUpdatedFlags(result.flags.union(.CopyProtected)) }
                    return .single(result)
                }
            }
            if let paid = media as? TelegramMediaPaidContent {
                guard !paid.extendedMedia.isEmpty, paid.extendedMedia.allSatisfy({ if case .full = $0 { return true }; return false }) else {
                    return nagramiXCopyCard(context: context, message: message, presentationData: data)
                }
                return .single(message)
            }
            if let todo = media as? TelegramMediaTodo {
                guard todo.completions.isEmpty else { return nagramiXCopyCard(context: context, message: message, presentationData: data) }
                return context.engine.data.get(TelegramEngine.EngineData.Item.Peer.Peer(id: context.account.peerId))
                |> mapToSignal { peer -> Signal<EngineRawMessage?, NoError> in
                    guard peer?.isPremium == true else { return nagramiXCopyCard(context: context, message: message, presentationData: data) }
                    return nagramiXCopyCard(context: context, message: message, presentationData: data)
                    |> map { card in
                        guard let card else { return nil }
                        return message.withUpdatedAttributes(message.attributes + [OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy], nagramiXCopyFallbackText: card.text)])
                    }
                }
            }
            if media is TelegramMediaGame {
                return nagramiXCopyCard(context: context, message: message, presentationData: data)
                |> map { card in
                    guard let card else { return nil }
                    return message.withUpdatedAttributes(message.attributes + [OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy], nagramiXCopyFallbackText: card.text)])
                }
            }
            if let poll = media as? TelegramMediaPoll, case .quiz = poll.kind,
               poll.correctAnswers?.isEmpty != false && poll.results.voters?.contains(where: { $0.isCorrect }) != true {
                return nagramiXCopyCard(context: context, message: message, presentationData: data)
            }
            if media is TelegramMediaImage || media is TelegramMediaFile || media is TelegramMediaContact || media is TelegramMediaMap || media is TelegramMediaWebpage || media is TelegramMediaPoll {
                return .single(message)
            }
            return nagramiXCopyCard(context: context, message: message, presentationData: data)
        }
        let completed = Atomic<Bool>(value: false)
        self.nagramiXContentCopyDisposable.set((combineLatest(signals)
        |> take(1)
        |> deliverOnMainQueue).startStrict(next: { result in
            guard !completed.swap(true) else { return }
            let messages = result.compactMap { $0 }
            completion(messages.count == result.count ? messages : nil)
        }, completed: {
            if !completed.swap(true) { completion(nil) }
        }))
    }

    func nagramiXPrepareCopyUpload(messages: [EngineRawMessage], present: @escaping (ViewController) -> Void, completion: @escaping (NagramiXCopyMediaLease?, Bool) -> Void) {
        let finished = Atomic<Bool>(value: false)
        let data = self.presentationData
        let progress = NagramiXCopyProgressController(background: data.theme.actionSheet.opaqueItemBackgroundColor, foreground: data.theme.actionSheet.primaryTextColor, accent: data.theme.actionSheet.controlAccentColor, title: data.strings.Common_Cancel, language: data.strings.baseLanguageCode, cancelled: { [weak self] in
            if !finished.swap(true) { self?.nagramiXContentCopyDisposable.set(nil); completion(nil, true) }
        })
        Queue.mainQueue().after(0.15) {
            guard !finished.with({ $0 }) else { return }
            present(progress)
        }
        self.nagramiXContentCopyDisposable.set((nagramiXPrepareCopyMedia(account: self.context.account, messages: messages)
        |> deliverOnMainQueue
        |> afterDisposed {
            let wasFinished = finished.swap(true)
            Queue.mainQueue().async { progress.dismiss(); if !wasFinished { completion(nil, true) } }
        }).startStrict(next: { event in
            switch event {
            case let .progress(value): progress.updateProgress(value)
            case let .ready(lease):
                guard !finished.swap(true) else { lease.dispose(); return }
                progress.dismiss(); completion(lease, false)
            case .failed:
                guard !finished.swap(true) else { return }
                progress.dismiss(); completion(nil, false)
            }
        }, completed: {
            if !finished.swap(true) { progress.dismiss(); completion(nil, false) }
        }))
    }
}

struct NagramiXCopyDeliveryRecipient {
    let peer: EnginePeer
    let messageIds: [EngineMessage.Id]
    let correlationIds: [Int64]
}

private final class NagramiXCopyDeliveryObservation {
    private weak var controller: ChatControllerImpl?
    private let context: AccountContext
    private let recipients: [NagramiXCopyDeliveryRecipient]
    private let success: () -> Void
    private let disposable = MetaDisposable()
    private var reportedFailures = Set<EngineMessage.Id>()
    private var completed = false

    init(controller: ChatControllerImpl, recipients: [NagramiXCopyDeliveryRecipient], success: @escaping () -> Void) {
        self.controller = controller; self.context = controller.context
        self.recipients = recipients; self.success = success
    }
    func dispose() { self.disposable.dispose() }
    private func errorText(_ reason: PendingMessageFailureReason?, strings: PresentationStrings) -> String {
        switch reason {
        case .flood?: return strings.Conversation_SendMessageErrorFlood
        case .publicBan?: return strings.Conversation_SendMessageErrorGroupRestricted
        case .tooMuchScheduled?: return strings.Conversation_SendMessageErrorTooMuchScheduled
        case .slowmodeActive?, .sendingTooFast?: return strings.Conversation_SendMessageErrorTooFast
        default: return strings.Forward_ErrorDisabledForChat
        }
    }
    func start() {
        let ids = self.recipients.flatMap { $0.messageIds }
        guard !ids.isEmpty else { return }
        let statuses = combineLatest(ids.map { self.context.account.pendingMessageManager.pendingMessageStatus($0) })
        self.disposable.set((combineLatest(self.context.engine.data.subscribe(EngineDataMap(ids.map(TelegramEngine.EngineData.Item.Messages.Message.init))), statuses)
        |> deliverOnMainQueue).start(next: { [weak self] messages, statuses in
            guard let self, !self.completed else { return }
            var sentCount = 0
            var failures: [EngineMessage.Id] = []
            var failureLines: [String] = []
            var offset = 0
            let data = self.context.sharedContext.currentPresentationData.with { $0 }
            for recipient in self.recipients {
                var recipientFailed: PendingMessageFailureReason?
                var hasFailure = false
                for i in recipient.messageIds.indices {
                    let id = recipient.messageIds[i]
                    let message = (messages[id] ?? nil)?._asMessage()
                    let reason = statuses.indices.contains(offset + i) ? statuses[offset + i].1 : nil
                    let acknowledged = recipient.correlationIds.indices.contains(i) && self.context.engine.messages.synchronouslyLookupCorrelationId(correlationId: recipient.correlationIds[i]) != nil
                    switch nagramiXCopiedMessageDeliveryState(message, acknowledged: acknowledged) {
                    case .failed: failures.append(id); recipientFailed = reason; hasFailure = true
                    case .accepted: sentCount += 1
                    case .queued: break
                    }
                }
                offset += recipient.messageIds.count
                if hasFailure {
                    let name = recipient.peer.displayTitle(strings: data.strings, displayOrder: data.nameDisplayOrder)
                    failureLines.append(name + ":\n" + self.errorText(recipientFailed, strings: data.strings))
                }
            }
            if sentCount == ids.count {
                self.completed = true; self.success(); self.disposable.set(nil)
                return
            }
            let newFailures = Set(failures).subtracting(self.reportedFailures)
            if !newFailures.isEmpty, let controller = self.controller {
                self.reportedFailures.formUnion(failures)
                controller.present(textAlertController(context: self.context, title: nil, text: failureLines.joined(separator: "\n\n"), actions: [
                    TextAlertAction(type: .genericAction, title: data.strings.Common_Cancel, action: {}),
                    TextAlertAction(type: .defaultAction, title: data.strings.nagramiXArchiveStorageRetry, action: { [weak self] in
                        guard let self else { return }
                        self.reportedFailures.subtract(failures)
                        let _ = nagramiXRetryCopiedMessages(account: self.context.account, messageIds: failures).startStandalone()
                    })
                ]), in: .window(.root))
            }
        }))
    }
}

extension ChatControllerImpl {
    func nagramiXObserveCopyDelivery(_ recipients: [NagramiXCopyDeliveryRecipient], success: @escaping () -> Void) {
        let observation = NagramiXCopyDeliveryObservation(controller: self, recipients: recipients, success: success)
        if self.shareStatusDisposable == nil { self.shareStatusDisposable = MetaDisposable() }
        self.shareStatusDisposable?.set(ActionDisposable { observation.dispose() })
        observation.start()
    }
}
