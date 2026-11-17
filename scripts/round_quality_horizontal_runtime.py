"""Настоящие button/cell/layout; UIKit measurement/constraints/scroll — явные hosts."""
import json
from pathlib import Path
from validate_quick_format import block
from validate_app_language_localization import strings
from validate_upstream_13_2_release import checked_plan, OVERLAY

ROOT = Path(__file__).resolve().parents[1]
U = 'submodules/SettingsUI/Sources/NagramiXRoundQualityController.swift'


def fixture(source):
    text = (source / U).read_text()
    boundary = (ROOT / 'scripts/tests/NagramiXRoundTitleBoundary.swift').read_text()
    boundary = boundary.replace('let first:Anchor,relation:String,second:Anchor?,constant:CGFloat',
                                'let first:Anchor,relation:String,second:Anchor?\n var constant:CGFloat')
    code = boundary + '\n' + (ROOT / 'scripts/tests/NagramiXRoundHorizontalBoundary.swift').read_text()
    for marker in ['private struct NagramiXRoundSegmentOption', 'private struct NagramiXRoundQualityRowLayout',
                   'private final class NagramiXRoundSegmentButton:', 'private final class NagramiXRoundSegmentCell:']:
        code += '\n' + block(text, marker).replace('@objc ', '').replace('#selector(tapped)', '"tapped"') + '\n'
    plan = checked_plan('tab_visibility_sync')
    catalogs = []
    for lang in json.loads((OVERLAY / 'app_language_localization/languages.json').read_text())['languages']:
        name = 'submodules/NagramiXCore/Resources/' + lang['code'] + '.lproj/Localizable.strings'
        path = source / name
        if not path.exists():
            path = OVERLAY / plan['replacements'][name]
        values = strings(path)
        catalogs.append([values[k] for k in ['NagramiX.UI.c60a0633cc8464f5', 'NagramiX.UI.71abc1e1f08e63a5', 'NagramiX.Settings.Downloads.Maximum']])
    code += '\nlet actualTitles = try! JSONDecoder().decode([[String]].self, from: ' + json.dumps(json.dumps(catalogs, ensure_ascii=False), ensure_ascii=False) + '.data(using: .utf8)!)\n'
    return code + (ROOT / 'scripts/tests/NagramiXRoundHorizontalTests.swift').read_text()
