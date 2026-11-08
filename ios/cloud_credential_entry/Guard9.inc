import NagramiXCore
import UIKit
import Display
import TelegramPresentationData
import ItemListUI

// The wheel edits a draft. Dismissal selects the stopped row; the parent
// navigation-bar Save action is the only persistent commit.
final class NagramiXTranslationModelPicker: UIViewController, UIPickerViewDataSource, UIPickerViewDelegate {
    private let models: [String]
    private let selected: String
    private let presentationData: PresentationData
    private let completion: (String) -> Void
    private let backgroundButton = UIButton(type: .custom)
    private let panel = UIView()
    private let handle = UIView()
    private let titleLabel = UILabel()
    private let picker = UIPickerView()
    private var closed = false

    init(models: [String], selected: String, presentationData: PresentationData, completion: @escaping (String) -> Void) {
        self.models = models
        self.selected = selected
        self.presentationData = presentationData
        self.completion = completion
        super.init(nibName: nil, bundle: nil)
        self.modalPresentationStyle = .overFullScreen
        self.modalTransitionStyle = .crossDissolve
        self.overrideUserInterfaceStyle = presentationData.theme.overallDarkAppearance ? .dark : .light
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override func loadView() {
        self.view = UIView()
        self.view.accessibilityViewIsModal = true
        self.backgroundButton.backgroundColor = UIColor.black.withAlphaComponent(0.25)
        self.backgroundButton.accessibilityLabel = self.presentationData.strings.nagramiXUILocalized("Закрыть выбор модели")
        self.backgroundButton.addTarget(self, action: #selector(self.close), for: .touchUpInside)
        self.view.addSubview(self.backgroundButton)
        self.panel.backgroundColor = self.presentationData.theme.list.itemBlocksBackgroundColor
        self.panel.layer.cornerRadius = 24
        self.panel.layer.maskedCorners = [.layerMinXMinYCorner, .layerMaxXMinYCorner]
        self.panel.clipsToBounds = true
        self.view.addSubview(self.panel)
        self.handle.backgroundColor = self.presentationData.theme.list.itemSecondaryTextColor.withAlphaComponent(0.5)
        self.handle.layer.cornerRadius = 3
        self.panel.addSubview(self.handle)
        self.titleLabel.text = self.presentationData.strings.nagramiXUILocalized("Модель")
        self.titleLabel.textAlignment = .center
        self.titleLabel.font = Font.semibold(self.presentationData.listsFontSize.itemListBaseFontSize)
        self.titleLabel.textColor = self.presentationData.theme.list.itemPrimaryTextColor
        self.titleLabel.isUserInteractionEnabled = true
        self.titleLabel.addGestureRecognizer(UIPanGestureRecognizer(target: self, action: #selector(self.pan(_:))))
        self.panel.addSubview(self.titleLabel)
        self.picker.dataSource = self
        self.picker.delegate = self
        self.picker.accessibilityLabel = self.presentationData.strings.nagramiXUILocalized("Модель перевода")
        self.panel.addSubview(self.picker)
        if let row = self.models.firstIndex(of: self.selected) {
            self.picker.selectRow(row, inComponent: 0, animated: false)
        }
    }
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        self.backgroundButton.frame = self.view.bounds
        let bottom = self.view.safeAreaInsets.bottom
        let height = min(self.view.bounds.height - self.view.safeAreaInsets.top, 290 + bottom)
        let width = min(560, self.view.bounds.width)
        self.panel.frame = CGRect(x: (self.view.bounds.width - width) / 2, y: self.view.bounds.height - height, width: width, height: height)
        self.handle.frame = CGRect(x: (width - 36) / 2, y: 8, width: 36, height: 6)
        self.titleLabel.frame = CGRect(x: 20, y: 20, width: width - 40, height: 40)
        self.picker.frame = CGRect(x: 16, y: 60, width: width - 32, height: max(100, height - 60 - bottom))
    }
    func numberOfComponents(in pickerView: UIPickerView) -> Int { 1 }
    func pickerView(_ pickerView: UIPickerView, numberOfRowsInComponent component: Int) -> Int { self.models.count }
    func pickerView(_ pickerView: UIPickerView, rowHeightForComponent component: Int) -> CGFloat {
        let font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        let width = max(100, min(560, self.view.bounds.width) - 64)
        return self.models.reduce(CGFloat(44)) { height, model in
            max(height, ceil((model as NSString).boundingRect(with: CGSize(width: width, height: 1000), options: .usesLineFragmentOrigin, attributes: [.font: font], context: nil).height) + 12)
        }
    }
    func pickerView(_ pickerView: UIPickerView, viewForRow row: Int, forComponent component: Int, reusing view: UIView?) -> UIView {
        let label = (view as? UILabel) ?? UILabel()
        label.font = Font.regular(self.presentationData.listsFontSize.itemListBaseFontSize)
        label.textColor = self.presentationData.theme.list.itemPrimaryTextColor
        label.textAlignment = .center
        label.numberOfLines = 0
        label.text = self.models[row]
        return label
    }
    @objc private func pan(_ gesture: UIPanGestureRecognizer) {
        guard gesture.state == .ended else { return }
        if gesture.translation(in: self.panel).y > 50 || gesture.velocity(in: self.panel).y > 600 { self.close() }
    }
    @objc private func close() {
        guard !self.closed else { return }
        self.closed = true
        let row = self.picker.selectedRow(inComponent: 0)
        if self.models.indices.contains(row) {
            self.picker.selectRow(row, inComponent: 0, animated: false)
            self.completion(self.models[row])
        }
        self.dismiss(animated: true)
    }
    override func accessibilityPerformEscape() -> Bool { self.close(); return true }
}
