#!/usr/bin/env python3
"""Type-check the timeout menu caller against the real localization extension."""
import argparse
from pathlib import Path
import tempfile

from validate_custom_member_references import RESOLVER, STRINGS
from validate_local_copy_delivery import run
from validate_quick_format import block

CONTROLLER = 'submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift'
SHEET = 'submodules/SettingsUI/Sources/NagramiXOptionSheet.swift'


def check(source, swiftc):
    for name in (CONTROLLER, SHEET, STRINGS):
        run([swiftc, '-frontend', '-parse', source / name], timeout=60)

    controller = (source / CONTROLLER).read_text()
    sheet = (source / SHEET).read_text()
    option = block(sheet, 'struct NagramiXOptionSheetOption {')
    declaration = block(sheet, 'func nagramiXOptionSheet(').split('{', 1)[0]
    caller = block(controller, '    selectTimeoutImpl = {')
    title = block(controller, 'private func nagramiXTimeoutTitle(')
    with tempfile.TemporaryDirectory(prefix='nagramix-proxy-timeout-') as folder:
        temp = Path(folder)
        flags = [swiftc, '-swift-version', '5', '-warnings-as-errors', '-module-cache-path', temp / 'cache']
        # UIKit presentation and account settings are host boundaries. Compile the
        # real string getter and resolver separately so a missing public getter fails.
        host = temp / 'Presentation.swift'
        host.write_text('''
public struct PresentationStringsComponent {
    public let languageCode: String
    public let dict: [String: String]
}
public final class PresentationStrings {
    public let primaryComponent: PresentationStringsComponent
    public let secondaryComponent: PresentationStringsComponent?
    public init(primary: PresentationStringsComponent, secondary: PresentationStringsComponent?) {
        self.primaryComponent = primary
        self.secondaryComponent = secondary
    }
}
''')
        run([*flags, '-emit-module', '-module-name', 'TelegramPresentationData', host,
             '-emit-module-path', temp / 'TelegramPresentationData.swiftmodule'], timeout=60)
        run([*flags, '-emit-module', '-module-name', 'NagramiXCore', '-I', temp, source / STRINGS,
             source / RESOLVER, '-emit-module-path', temp / 'NagramiXCore.swiftmodule'], timeout=60)
        consumer = temp / 'SettingsUI.swift'
        consumer.write_text('''
import TelegramPresentationData
import NagramiXCore

struct PresentationData { let strings: PresentationStrings }
struct CurrentPresentationData {
    let value: PresentationData
    func with<T>(_ transform: (PresentationData) -> T) -> T { transform(value) }
}
struct SharedContext { let currentPresentationData: CurrentPresentationData }
struct NagramiXTabSettings {
    static let current = NagramiXTabSettings()
    var proxyAutoSwitchTimeout = 30
}
struct ActionSheetController {}
func updateNagramiXSettings(_ update: (inout NagramiXTabSettings) -> Void) {
    var settings = NagramiXTabSettings.current
    update(&settings)
}
''' + option + '\n' + declaration + '{ ActionSheetController() }\n' + title + '''

func configureTimeout(sharedContext: SharedContext, presentControllerImpl: ((ActionSheetController) -> Void)?) {
    let selectTimeoutImpl: () -> Void
''' + caller + '''
    selectTimeoutImpl()
}
''')
        run([*flags, '-typecheck', '-I', temp, consumer], timeout=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    check(args.source, args.swiftc)
    print('PASS: проверены Swift-исходники панели и вызов нового заголовка из SettingsUI.')


if __name__ == '__main__':
    main()
