import Foundation
import UIKit
import AsyncDisplayKit
import Display
import ItemListUI
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

private final class NagramiXSettingsSearchTextField: UITextField {
    override func textRect(forBounds bounds: CGRect) -> CGRect {
        return super.textRect(forBounds: bounds).inset(by: UIEdgeInsets(top: 0.0, left: 0.0, bottom: 0.0, right: 12.0))
    }

    override func editingRect(forBounds bounds: CGRect) -> CGRect {
        return super.editingRect(forBounds: bounds).inset(by: UIEdgeInsets(top: 0.0, left: 0.0, bottom: 0.0, right: 12.0))
    }

    override func clearButtonRect(forBounds bounds: CGRect) -> CGRect {
        return super.clearButtonRect(forBounds: bounds).offsetBy(dx: -8.0, dy: 0.0)
    }
}

private final class NagramiXSettingsSearchItemNode: ListViewItemNode, ItemListItemNode, UITextFieldDelegate {
    private var item: NagramiXSettingsSearchItem?
    private var textField: NagramiXSettingsSearchTextField?

    var tag: ItemListItemTag? {
        return nil
    }

    func update(item: NagramiXSettingsSearchItem, params: ListViewItemLayoutParams) -> ListViewItemNodeLayout {
        return ListViewItemNodeLayout(contentSize: CGSize(width: params.width, height: 72.0), insets: UIEdgeInsets())
    }

    func apply(item: NagramiXSettingsSearchItem, params: ListViewItemLayoutParams) {
        self.item = item

        let textField: NagramiXSettingsSearchTextField
        if let current = self.textField {
            textField = current
        } else {
            textField = NagramiXSettingsSearchTextField(frame: .zero)
            textField.borderStyle = .none
            textField.font = Font.regular(17.0)
            textField.layer.cornerRadius = 24.0
            textField.clipsToBounds = true
            textField.clearButtonMode = .whileEditing
            textField.autocorrectionType = .no
            textField.autocapitalizationType = .none
            textField.returnKeyType = .search
            textField.delegate = self
            textField.addTarget(self, action: #selector(self.textUpdated), for: .editingChanged)

            let iconContainer = UIView(frame: CGRect(x: 0.0, y: 0.0, width: 44.0, height: 48.0))
            iconContainer.isUserInteractionEnabled = false
            iconContainer.isAccessibilityElement = false
            let iconLabel = UILabel(frame: CGRect(x: 14.0, y: 0.0, width: 24.0, height: 48.0))
            iconLabel.text = "🔍"
            iconLabel.font = Font.regular(20.0)
            iconLabel.textAlignment = .center
            iconLabel.isAccessibilityElement = false
            iconContainer.addSubview(iconLabel)
            textField.leftView = iconContainer
            textField.leftViewMode = .always
            textField.accessibilityTraits = .searchField
            textField.accessibilityIdentifier = "NagramiX.Settings.Search"

            self.textField = textField
            self.view.addSubview(textField)
        }

        let theme = item.presentationData.theme.rootController.navigationSearchBar
        textField.backgroundColor = theme.inputFillColor
        textField.textColor = theme.inputTextColor
        textField.tintColor = theme.accentColor
        textField.keyboardAppearance = item.presentationData.theme.rootController.keyboardColor == .dark ? .dark : .light
        textField.attributedPlaceholder = NSAttributedString(
            string: item.presentationData.strings.nagramiXSettingsSearch,
            font: Font.regular(17.0),
            textColor: theme.inputPlaceholderTextColor
        )
        textField.accessibilityLabel = item.presentationData.strings.nagramiXSettingsSearch
        if textField.text != item.query {
            textField.text = item.query
        }

        textField.frame = CGRect(
            x: params.leftInset + 16.0,
            y: 12.0,
            width: max(1.0, params.width - params.leftInset - params.rightInset - 32.0),
            height: 48.0
        )
    }

    @objc private func textUpdated() {
        self.item?.queryUpdated(self.textField?.text ?? "")
    }

    func textFieldShouldClear(_ textField: UITextField) -> Bool {
        self.item?.queryUpdated("")
        return true
    }

    func textFieldShouldReturn(_ textField: UITextField) -> Bool {
        textField.resignFirstResponder()
        return true
    }
}
