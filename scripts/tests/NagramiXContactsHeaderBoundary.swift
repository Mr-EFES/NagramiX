import Foundation

// Hosts for the native navigation component and the existing Contacts actions.
private class UIView {}
private class ASDisplayNode {}
private class NavigationController {
    var pops = 0
    func popViewController(animated: Bool) { pops += 1 }
}
private class ContactsController {
    let isTab: Bool
    let navigationController: NavigationController? = NavigationController()
    var sorts = 0
    var additions = 0

    init(isTab: Bool) { self.isTab = isTab }
    func presentSortMenu(sourceView: UIView, gesture: Int?) { sorts += 1 }
    func addPressed() { additions += 1 }
}
private struct Strings {
    let Contacts_Title = "Contacts"
    let Common_Done = "Done"
    let Contacts_Sort = "Sort"
    let Contacts_VoiceOver_AddContact = "Add Contact"
    func Contacts_SelectedContacts(_ count: Int32) -> String { "Selected \(count)" }
}
private struct PresentationData { let strings = Strings() }
private struct NetworkStatusTitle {
    let text: String
    let activity: Bool
    let hasProxy: Bool
    let connectsViaProxy: Bool
    let isPasscodeSet: Bool
    let isManuallyLocked: Bool
    let peerStatus: Int?
}
private enum NavigationBarComponent {
    struct OverflowInfo {
        let title: String
        let iconName: String?
        let priority: Int?
    }
    struct Button {
        enum Content {
            case text(title: String, isBold: Bool)
            case icon(imageName: String)
        }
        let id: String
        let content: Content
        var overflow: OverflowInfo? = nil
        let action: (UIView) -> Void
    }
}
private enum ChatListHeaderComponent {
    struct Content {
        let title: String
        let titleComponent: Int?
        let chatListTitle: NetworkStatusTitle
        let leftButton: NavigationBarComponent.Button?
        let rightButtons: [NavigationBarComponent.Button]
        let backPressed: (() -> Void)?
    }
}
private struct SelectionState { let selectedPeerIndices: [Int: Int] }
private class ContactListNode {
    var selectionState: SelectionState?
    func updateSelectionState(_ transform: (SelectionState?) -> SelectionState?) {
        selectionState = transform(selectionState)
    }
}
private class ContactsHeader {
    let controller: ContactsController?
    let presentationData = PresentationData()
    let contactListNode = ContactListNode()

    init(isTab: Bool) { controller = ContactsController(isTab: isTab) }

    func makeContent() -> ChatListHeaderComponent.Content {
        // ACTUAL_HEADER_CONTENT
    }
}

@main private struct ContactsHeaderChecks {
    static func main() {
        let tab = ContactsHeader(isTab: true)
        let main = tab.makeContent()
        precondition(main.leftButton?.id == "sort", "Contacts tab puts Sort on the leading side")
        precondition(main.rightButtons.map(\.id) == ["add"], "Contacts tab keeps Add on the trailing side")
        precondition(main.chatListTitle.text == "Contacts" && main.backPressed == nil)
        main.leftButton?.action(UIView())
        main.rightButtons.first?.action(UIView())
        precondition(tab.controller?.sorts == 1 && tab.controller?.additions == 1)

        tab.contactListNode.selectionState = SelectionState(selectedPeerIndices: [42: 0])
        let selection = tab.makeContent()
        precondition(selection.leftButton?.id == "done" && selection.rightButtons.isEmpty)
        precondition(selection.chatListTitle.text == "Selected 1")
        selection.leftButton?.action(UIView())
        precondition(tab.contactListNode.selectionState == nil)
        precondition(tab.makeContent().leftButton?.id == "sort")

        let pushed = ContactsHeader(isTab: false)
        let standalone = pushed.makeContent()
        precondition(standalone.leftButton == nil && standalone.rightButtons.map(\.id) == ["sort", "add"])
        standalone.backPressed?()
        precondition(pushed.controller?.navigationController?.pops == 1)
        print("PASS Contacts tab, selection, pushed header, and button dispatch")
    }
}
