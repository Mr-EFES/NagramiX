#!/usr/bin/env python3
"""Verify the DoH failure alert with its real configuration and localized message."""
import argparse
from pathlib import Path
import re
import tempfile

from late_source_stages import ROOT
from validate_app_language_localization import strings
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest

ALERT = 'submodules/TelegramUI/Components/AlertComponent/Sources/AlertComponent.swift'
EDITOR = 'submodules/SettingsUI/Sources/NagramiXCustomDohController.swift'
KEY = 'NagramiX.Network.DNS.CustomUnavailable'


def validate(source, swiftc):
    plan = checked_plan('doh_alert_message')
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
        if name.endswith('Localizable.strings'):
            lines = strings(source / name)[KEY].split('\n')
            previous = strings(ROOT / 'ios' / plan['previous'][name])[KEY]
            assert len(lines) == 2 and all(lines) and ' '.join(lines) == previous, name

    alert = (source / ALERT).read_text()
    editor = (source / EDITOR).read_text()
    content = (source / Path(ALERT).with_name('AlertContent.swift')).read_text()
    assert 'let contentSideInset = component.configuration.contentSideInset' in alert
    assert 'width: alertWidth - contentSideInset * 2.0' in alert
    assert 'width: availableSize.width - inset * 2.0' in content
    assert 'maximumNumberOfLines: 0' in content
    failure = block(editor, '            if !didResolve && submission.failed()')
    assert 'text: strings.nagramiXCustomDohUnavailable' in failure
    assert 'title: strings.Common_OK, type: .default' in failure
    assert 'controller?.present(alert, in: .window(.root))' in failure

    def number(pattern, text):
        return re.search(pattern, text)[1]

    # Exercise the configuration used by the error and the actual Core Text font on macOS.
    config = block(alert, '    public struct Configuration: Equatable')
    alignment = block(alert, '    public enum ActionAligmnent: Equatable')
    call = number(r'configuration: (\.init\([^)]*\))', failure)
    width = number(r'let alertWidth: CGFloat = ([\d.]+)', alert)
    inset = number(r'let inset: CGFloat = ([-\d.]+)', block(content, 'public final class AlertTextComponent:'))
    font_size = number(r'let defaultTextFont = Font.regular\(([\d.]+)\)', content)
    ru = source / 'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings'
    with tempfile.TemporaryDirectory(prefix='doh-alert-layout-') as tmp:
        folder = Path(tmp)
        fixture = (ROOT / 'scripts/tests/NagramiXDohAlertMessage.swift').read_text()
        fixture = fixture.replace('// CONFIGURATION', alignment + '\n' + config)
        fixture = fixture.replace('ALERT_CONFIG', call).replace('ALERT_WIDTH', width)
        fixture = fixture.replace('TEXT_INSET', inset).replace('FONT_SIZE', font_size)
        test = folder / 'Layout.swift'
        test.write_text(fixture)
        run([swiftc, '-frontend', '-parse', source / EDITOR, source / ALERT])
        run([swiftc, '-warnings-as-errors', '-module-cache-path', folder / 'cache', test, '-o', folder / 'layout'])
        print(run([folder / 'layout', ru]).stdout.strip(), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    validate(args.source, args.swiftc)
