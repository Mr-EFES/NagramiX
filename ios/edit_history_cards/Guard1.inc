import Foundation
import TelegramCore
import SwiftSignalKit
import Display
import AccountContext
import ChatInterfaceState
import TextFormat

extension ChatControllerImpl {
    func nagramiXForwardEditHistoryVersion(_ message: EngineRawMessage) {
        guard !message.text.isEmpty, message.media.isEmpty,
              nagramiXCanCopyMessagesAsNew([message]),
              !self.presentAccountFrozenInfoIfNeeded(delay: true) else {
            return
        }
        self.commitPurposefulAction()
        let _ = self.presentVoiceMessageDiscardAlert(action: { [weak self] in
            guard let self, let navigationController = self.effectiveNavigationController else { return }
            let entities = (message.attributes.first(where: { $0 is TextEntitiesMessageAttribute }) as? TextEntitiesMessageAttribute)?.entities ?? []
            // Не сохраняем исходный server ID в forward draft: его чтение
            // подменило бы выбранную редакцию текущим текстом/вложением.
            let inputState = ChatTextInputState(inputText: chatInputStateStringWithAppliedEntities(message.text, entities: entities))
            let controller = self.context.sharedContext.makePeerSelectionController(PeerSelectionControllerParams(
                context: self.context,
                updatedPresentationData: self.updatedPresentationData,
                filter: [.onlyWriteable, .excludeDisabled, .doNotSearchMessages],
                hasFilters: true,
                multipleSelection: false,
                forwardedMessageIds: [],
                selectForumThreads: true
            ))
            var selecting = false
            controller.peerSelected = { [weak self, weak controller, weak navigationController] peer, threadId in
                guard let self, let controller, let navigationController, !selecting,
                      navigationController.viewControllers.contains(where: { $0 === controller }),
                      !self.presentAccountFrozenInfoIfNeeded(delay: true) else { return }
                selecting = true
                let open: (ChatController?) -> Void = { [weak self, weak controller, weak navigationController] threadController in
                    guard let self, let controller, let navigationController,
                          let index = navigationController.viewControllers.firstIndex(where: { $0 === controller }),
                          navigationController.viewControllers[index...].allSatisfy({ $0 is PeerSelectionController }) else {
                        selecting = false
                        return
                    }
                    let location: NavigateToChatControllerParams.Location
                    if let threadId {
                        guard let threadController, case let .replyThread(message) = threadController.chatLocation,
                              message.peerId == peer.id, message.threadId == threadId else {
                            selecting = false
                            return
                        }
                        location = .replyThread(message)
                    } else {
                        location = .peer(peer)
                    }
                    let stack = Array(navigationController.viewControllers.prefix(index))
                    // Новый обычный чат не переиспользует readonly preview.
                    // Запись/оплата/тихая/отложенная отправка остаются у его composer.
                    self.context.sharedContext.navigateToChatController(NavigateToChatControllerParams(
                        navigationController: navigationController,
                        chatController: threadController,
                        context: self.context,
                        chatLocation: location,
                        updateTextInputState: inputState,
                        activateInput: .text,
                        keepStack: .always,
                        useExisting: false,
                        pushController: { chatController, animated, completion in
                            navigationController.setViewControllers(stack + [chatController], animated: animated)
                            completion()
                        },
                        forceOpenChat: true
                    ))
                }
                if let threadId {
                    self.controllerNavigationDisposable.set((self.context.sharedContext.chatControllerForForumThread(context: self.context, peerId: peer.id, threadId: threadId)
                    |> take(1)
                    |> deliverOnMainQueue).start(next: { chatController in
                        open(chatController)
                    }, completed: {
                        selecting = false
                    }))
                } else {
                    open(nil)
                }
            }
            navigationController.pushViewController(controller)
        })
    }
}
