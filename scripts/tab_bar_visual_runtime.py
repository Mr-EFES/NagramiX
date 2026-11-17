"""Production-переходы панели; UIKit/layout/ready delivery — явные IO-границы."""
from pathlib import Path
from validate_quick_format import block
from tab_visibility_runtime import BAR, NODE, COMPONENT, CONTACTS

ROOT = Path(__file__).resolve().parents[1]


def ready_region(text):
    return text.split('        let signals = combineLatest', 1)[1].split('        self._ready.set(allReady)', 1)[0]


def pieces(source):
    bar = (source / BAR).read_text()
    node = (source / NODE).read_text()
    component = (source / COMPONENT).read_text()
    set_controllers = block(bar, '    public func setControllers(')
    start = set_controllers.index('        let signals = combineLatest')
    end = set_controllers.index('        self._ready.set(allReady)') + len('        self._ready.set(allReady)')
    # This untouched asynchronous image/readiness pipeline is an explicit IO
    # boundary. Check it is byte-identical to the preimage in the validator.
    set_controllers = set_controllers[:start] + '        self.readyBoundary += 1' + set_controllers[end:]
    prefix = block(component, '        func update(component: TabBarComponent, availableSize:').split('            let previousComponent = self.component', 1)[1].split('            // Search is laid out', 1)[0]
    on_layout = node.split('        (self.view as? View)?.onLayout = { [weak self] in', 1)[1].split('        self.backgroundColor = theme.list.plainBackgroundColor', 1)[0].rsplit('        }', 1)[0]
    return {
        'CONTACT': block((source / CONTACTS).read_text(), '    private func nagramiXUpdateTabItem('),
        'PARAMS': block(node, '    private struct Params:') + '\n' + block(node, '    private struct LayoutResult'),
        'ITEMS': block(node, '    func updateTabBarItems('),
        'SELECT': block(node, '    func updateSelectedIndex('),
        'LAYOUT': block(node, '    func containerLayoutUpdated('),
        'REQUEST': block(node, '    private func requestUpdate('),
        'FLUSH': '    func flush() { let action: () -> Void = { [weak self] in' + on_layout + '\n        }; action()\n    }',
        'CONTROLLERS': set_controllers,
        'SELECTED_PROPERTY': block(bar, '    public var selectedIndex:'),
        'COMPLETE': block(bar, '    private func nagramiXCompleteTabSelection('),
        'RECONCILE': block(component, '        private func nagramiXReconcileTabStructure('),
        'APPLY': '    func apply(_ component: TabBarComponent, _ requested: ComponentTransition) -> ComponentTransition {\n        let previousComponent = self.component\n        var transition = requested\n' + prefix.replace('            var transition = transition\n', '') + '\n        self.component = component\n        return transition\n    }',
    }


def fixture(source):
    host = (ROOT / 'scripts/tests/NagramiXTabBarVisualBoundary.swift').read_text()
    for key, value in pieces(source).items():
        assert host.count('// ' + key + '\n') == 1, key
        host = host.replace('// ' + key + '\n', value + '\n', 1)
    return host + '\n' + (ROOT / 'scripts/tests/NagramiXTabBarVisualTests.swift').read_text()
