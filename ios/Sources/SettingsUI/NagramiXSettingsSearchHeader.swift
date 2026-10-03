import Foundation
import AsyncDisplayKit
import Display
import ItemListUI
import SearchBarNode
import SwiftSignalKit
import TelegramPresentationData

final class NagramiXSettingsSearchItem: ListViewItem, ItemListItem {
    let presentationData: ItemListPresentationData
    let query: String
    let queryUpdated: (String) -> Void
    let sectionId: ItemListSectionId

    init(presentationData: ItemListPresentationData, query: String, sectionId: ItemListSectionId, queryUpdated: @escaping (String) -> Void) {
        self.presentationData = presentationData
        self.query = query
        self.sectionId = sectionId
        self.queryUpdated = queryUpdated
    }

    var selectable: Bool {
        return false
    }

    func selected(listView: ListView) {
    }

    func nodeConfiguredForParams(async: @escaping (@escaping () -> Void) -> Void, params: ListViewItemLayoutParams, synchronousLoads: Bool, previousItem: ListViewItem?, nextItem: ListViewItem?, completion: @escaping (ListViewItemNode, @escaping () -> (Signal<Void, NoError>?, (ListViewItemApply) -> Void)) -> Void) {
        async {
            let node = NagramiXSettingsSearchItemNode(layerBacked: false)
            let layout = node.update(item: self, params: params)
            node.contentSize = layout.contentSize
            node.insets = layout.insets
            Queue.mainQueue().async {
                completion(node, {
                    return (nil, { _ in
                        node.apply(item: self, params: params)
                    })
                })
            }
        }
    }

    func updateNode(async: @escaping (@escaping () -> Void) -> Void, node: @escaping () -> ListViewItemNode, params: ListViewItemLayoutParams, previousItem: ListViewItem?, nextItem: ListViewItem?, animation: ListViewItemUpdateAnimation, completion: @escaping (ListViewItemNodeLayout, @escaping (ListViewItemApply) -> Void) -> Void) {
        Queue.mainQueue().async {
            guard let node = node() as? NagramiXSettingsSearchItemNode else {
                return
            }
            let layout = node.update(item: self, params: params)
            completion(layout, { _ in
                node.apply(item: self, params: params)
            })
        }
    }
}

private final class NagramiXSettingsSearchItemNode: ListViewItemNode, ItemListItemNode {
    private var item: NagramiXSettingsSearchItem?
    private var searchBarNode: SearchBarNode?

    var tag: ItemListItemTag? {
        return nil
    }

    func update(item: NagramiXSettingsSearchItem, params: ListViewItemLayoutParams) -> ListViewItemNodeLayout {
        return ListViewItemNodeLayout(contentSize: CGSize(width: params.width, height: 64.0), insets: UIEdgeInsets())
    }

    func apply(item: NagramiXSettingsSearchItem, params: ListViewItemLayoutParams) {
        self.item = item

        let searchBarNode: SearchBarNode
        if let current = self.searchBarNode {
            searchBarNode = current
            searchBarNode.updateThemeAndStrings(
                theme: SearchBarNodeTheme(theme: item.presentationData.theme, hasBackground: false, hasSeparator: false, inline: true),
                presentationTheme: item.presentationData.theme,
                preferClearGlass: false,
                strings: item.presentationData.strings
            )
        } else {
            searchBarNode = SearchBarNode(
                theme: SearchBarNodeTheme(theme: item.presentationData.theme, hasBackground: false, hasSeparator: false, inline: true),
                presentationTheme: item.presentationData.theme,
                preferClearGlass: false,
                strings: item.presentationData.strings,
                fieldStyle: .modern,
                forceSeparator: false,
                displayBackground: false
            )
            searchBarNode.hasCancelButton = false
            searchBarNode.textUpdated = { [weak self] text, _ in
                self?.item?.queryUpdated(text)
            }
            self.searchBarNode = searchBarNode
            self.addSubnode(searchBarNode)
        }

        searchBarNode.placeholderString = NSAttributedString(
            string: item.presentationData.strings.nagramiXSettingsSearch,
            font: Font.regular(17.0),
            textColor: item.presentationData.theme.rootController.navigationSearchBar.inputPlaceholderTextColor
        )
        if searchBarNode.text != item.query {
            searchBarNode.text = item.query
        }

        let frame = CGRect(x: 0.0, y: 4.0, width: params.width, height: 56.0)
        searchBarNode.frame = frame
        searchBarNode.updateLayout(
            boundingSize: frame.size,
            leftInset: params.leftInset,
            rightInset: params.rightInset,
            transition: .immediate
        )
    }
}
