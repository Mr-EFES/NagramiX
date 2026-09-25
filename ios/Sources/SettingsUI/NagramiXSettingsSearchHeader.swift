import Foundation
import AsyncDisplayKit
import Display
import ItemListUI
import SearchBarNode
import TelegramPresentationData

final class NagramiXSettingsSearchHeaderItem: ItemListControllerHeaderItem {
    let presentationData: PresentationData
    let query: String
    let queryUpdated: (String) -> Void

    init(presentationData: PresentationData, query: String, queryUpdated: @escaping (String) -> Void) {
        self.presentationData = presentationData
        self.query = query
        self.queryUpdated = queryUpdated
    }

    func isEqual(to: ItemListControllerHeaderItem) -> Bool {
        guard let other = to as? NagramiXSettingsSearchHeaderItem else {
            return false
        }
        return self.presentationData.theme === other.presentationData.theme
            && self.presentationData.strings === other.presentationData.strings
            && self.query == other.query
    }

    func node(current: ItemListControllerHeaderItemNode?) -> ItemListControllerHeaderItemNode {
        if let current = current as? NagramiXSettingsSearchHeaderItemNode {
            current.update(item: self)
            return current
        }
        return NagramiXSettingsSearchHeaderItemNode(item: self)
    }
}

private final class NagramiXSettingsSearchHeaderItemNode: ItemListControllerHeaderItemNode {
    private var item: NagramiXSettingsSearchHeaderItem
    private let searchBarNode: SearchBarNode

    init(item: NagramiXSettingsSearchHeaderItem) {
        self.item = item
        self.searchBarNode = SearchBarNode(
            theme: SearchBarNodeTheme(theme: item.presentationData.theme, hasBackground: true, hasSeparator: false, inline: true),
            presentationTheme: item.presentationData.theme,
            preferClearGlass: false,
            strings: item.presentationData.strings,
            fieldStyle: .glass,
            forceSeparator: false,
            displayBackground: true
        )
        self.searchBarNode.hasCancelButton = false
        self.searchBarNode.placeholderString = NSAttributedString(
            string: item.presentationData.strings.nagramiXSettingsSearch,
            font: Font.regular(17.0),
            textColor: item.presentationData.theme.rootController.navigationSearchBar.inputPlaceholderTextColor
        )
        self.searchBarNode.text = item.query

        super.init()

        self.addSubnode(self.searchBarNode)
        self.searchBarNode.textUpdated = { [weak self] text, _ in
            self?.item.queryUpdated(text)
        }
    }

    func update(item: NagramiXSettingsSearchHeaderItem) {
        self.item = item
        self.searchBarNode.updateThemeAndStrings(
            theme: SearchBarNodeTheme(theme: item.presentationData.theme, hasBackground: true, hasSeparator: false, inline: true),
            presentationTheme: item.presentationData.theme,
            preferClearGlass: false,
            strings: item.presentationData.strings
        )
        self.searchBarNode.placeholderString = NSAttributedString(
            string: item.presentationData.strings.nagramiXSettingsSearch,
            font: Font.regular(17.0),
            textColor: item.presentationData.theme.rootController.navigationSearchBar.inputPlaceholderTextColor
        )
        if self.searchBarNode.text != item.query {
            self.searchBarNode.text = item.query
        }
    }

    override func updateLayout(layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) -> CGFloat {
        let height: CGFloat = 56.0
        let leftInset = layout.safeInsets.left + layout.intrinsicInsets.left
        let rightInset = layout.safeInsets.right + layout.intrinsicInsets.right
        transition.updateFrame(node: self.searchBarNode, frame: CGRect(origin: .zero, size: CGSize(width: layout.size.width, height: height)))
        self.searchBarNode.updateLayout(
            boundingSize: CGSize(width: layout.size.width, height: height),
            leftInset: leftInset,
            rightInset: rightInset,
            transition: transition
        )
        return height
    }
}
