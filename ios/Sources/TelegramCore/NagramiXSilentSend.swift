import Foundation
import Postbox
import NagramiXMediaSettings

func nagramiXSilentSendAttributes(_ attributes: [MessageAttribute], enabled: Bool) -> [MessageAttribute] {
    guard enabled else { return attributes }
    var flags: NotificationInfoMessageAttributeFlags = .muted
    for attribute in attributes {
        if let notification = attribute as? NotificationInfoMessageAttribute {
            flags.formUnion(notification.flags)
        }
    }
    // Preserve personal/automatic flags and every unrelated outgoing attribute.
    // One canonical notification attribute also makes repeated application safe.
    var result = attributes.filter { !($0 is NotificationInfoMessageAttribute) }
    result.append(NotificationInfoMessageAttribute(flags: flags))
    return result
}

func nagramiXSilentSendMessage(_ message: EnqueueMessage, enabled: Bool) -> EnqueueMessage {
    guard enabled else { return message }
    return message.withUpdatedAttributes { nagramiXSilentSendAttributes($0, enabled: true) }
}
