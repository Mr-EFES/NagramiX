#!/usr/bin/env python3
"""Verify the approved Add Account entry without starting an SDK build."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

STAGE = 'account_settings_entry'
ITEMS = 'submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoSettingsItems.swift'
SEARCH = 'submodules/SettingsUI/Sources/Search/SettingsSearchableItems.swift'
PROTOCOL = 'submodules/AccountContext/Sources/ChatController.swift'
SCREEN = 'submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoScreen.swift'
ICONS = 'submodules/TelegramPresentationData/Sources/Resources/PresentationResourcesSettings.swift'
FACTORY = 'submodules/Display/Source/GenerateImage.swift'
ROOT_PROTOCOL = 'submodules/AccountContext/Sources/AccountContext.swift'
LOOP = '        for (peerAccountContext, peer, badgeCount) in settings.accountsAndPeers {'
ADD = '''        items[.accounts]!.append(PeerInfoScreenDisclosureItem(id: 100, text: presentationData.strings.Settings_AddAccount, icon: PresentationResourcesSettings.addAccount, action: {
            interaction.openSettings(.addAccount)
        }))'''


def source_contract(source, baseline):
    plan = checked_plan(STAGE)
    assert set(plan['outputs']) == {ITEMS, SEARCH, PROTOCOL, SCREEN, ICONS}
    assert not plan['copies'] and not plan['deletions']
    for name, value in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == value, name
    for name, value in {**plan['inputs'], **plan['guards']}.items():
        assert digest(baseline / name) == value, name
    before, after = manifest(baseline), manifest(source)
    assert len(before) > 37000, 'Use the full checked pre-account application tree'
    assert before.keys() == after.keys(), 'No application files may be added or deleted'
    changed = {name for name in before if before[name] != after[name]}
    assert changed == set(plan['outputs']), changed
    prefix = LATE_SOURCE_STAGES.index(STAGE)
    assert verified_prefix(baseline) == prefix
    assert verified_prefix(source) == prefix + 1
    return plan, {'baseline_files': len(before), 'final_files': len(after),
                  'changed_files': sorted(changed), 'previous_files_preserved': len(before) - len(changed),
                  'baseline_prefix': prefix, 'final_prefix': prefix + 1}


def ui_contract(source, baseline):
    before = {name: (baseline / name).read_text() for name in (ITEMS, SEARCH, PROTOCOL, SCREEN, ICONS)}
    after = {name: (source / name).read_text() for name in before}
    items = after[ITEMS]
    old_group = block(before[ITEMS], '        if !settings.accountsAndPeers.isEmpty {')
    old_loop = block(old_group, '            for (peerAccountContext, peer, badgeCount) in settings.accountsAndPeers {')
    new_loop = block(items, LOOP)
    dedented = '\n'.join(line[4:] if line.startswith('    ') else line for line in old_loop.split('\n'))
    assert new_loop == dedented, 'Account switch, badge, context menu and original order must survive byte-exact'
    assert items.count(ADD) == 1
    start = items.index('\n\n' + ADD)
    end = items.index(LOOP) + len(new_loop)
    assert items[start:end] == '\n\n' + ADD + '\n\n' + new_loop
    restored = items[:start] + items[end:]
    anchor = '        items[.nagramix]!.append('
    assert restored.count(anchor) == 1
    restored = restored.replace(anchor, old_group + '\n        \n' + anchor, 1)
    reordered = '    case phone\n    case nagramix\n    case myProfile\n    case accounts\n'
    original = '    case phone\n    case accounts\n    case nagramix\n    case myProfile\n'
    assert restored.count(reordered) == 1
    restored = restored.replace(reordered, original, 1)
    assert restored.count('        case info\n        case logout') == 1
    restored = restored.replace('        case info\n        case logout', '        case info\n        case account\n        case logout', 1)
    assert restored.count('    let ItemUsername = 4\n') == 1
    restored = restored.replace('    let ItemUsername = 4\n', '    let ItemUsername = 4\n    let ItemAddAccount = 5\n    let ItemAddAccountHelp = 6\n', 1)
    old_edit_start = before[ITEMS].index('    items[.account]!.append(')
    logout = '    items[.logout]!.append('
    old_edit = before[ITEMS][old_edit_start:before[ITEMS].index(logout)]
    restored = restored.replace(logout, old_edit + logout, 1)
    assert restored == before[ITEMS], 'Unrelated settings/editing behavior changed'
    editing = block(items, 'func settingsEditingItems(')
    assert 'Settings_AddAnotherAccount' not in editing and 'hasPremiumAccounts' not in editing
    assert 'Settings_ChatAutomationInfo' in editing and 'Settings_Logout' in editing
    assert 'if !settings.accountsAndPeers.isEmpty' not in items

    old_search = block(before[SEARCH], '    if canAddAccount {')
    search = block(after[SEARCH], '    if canAddAccount {')
    assert after[SEARCH].replace(search, old_search, 1) == before[SEARCH]
    assert 'id: "edit/add-account"' in search
    assert 'title: strings.Settings_AddAccount' in search
    assert 'alternate: synonyms(strings.SettingsSearch_Synonyms_EditProfile_AddAccount)' in search
    assert 'icon: .myProfile,\n                breadcrumbs: [],' in search
    assert 'beginNewAuth' not in search and 'activateEdit' not in search
    search_closure = block(search, '                present: { context, _, present in')
    expected_closure = '''                present: { context, _, present in
                    if let rootController = context.sharedContext.mainWindow?.viewController as? TelegramRootControllerInterface {
                        rootController.openSettings(edit: false)
                        Queue.mainQueue().justDispatch {
                            if let settingsScreen = rootController.getSettingsController() as? PeerInfoScreen {
                                settingsScreen.openAddAccount()
                            }
                        }
                    }
                }'''
    assert search_closure == expected_closure
    method = block(after[SCREEN], '    public func openAddAccount()')
    assert method == '''    public func openAddAccount() {
        self.controllerNode.openSettings(section: .addAccount)
    }'''
    assert after[SCREEN].replace('\n' + method + '\n', '', 1) == before[SCREEN]
    declaration = '    func openAddAccount()\n'
    assert after[PROTOCOL].count(declaration) == 1
    assert after[PROTOCOL].replace(declaration, '', 1) == before[PROTOCOL]
    assert 'public protocol PeerInfoScreen:' in after[PROTOCOL]
    root = (source / ROOT_PROTOCOL).read_text()
    assert '    func getSettingsController() -> ViewController?' in root
    assert '    func openSettings(edit: Bool)' in root
    assert 'import SwiftSignalKit' in after[SEARCH]
    return after, method, search_closure


def icon_contract(text, before, source):
    marker = '\n\n    public static let addAccount: UIImage? = generateImage('
    assert text.count(marker) == 1
    start = text.index(marker)
    end = text.index('\n    })', start) + len('\n    })')
    icon = text[start + 2:end]
    assert text[:start] + text[end:] == before, 'Existing settings icons changed'
    assert 'generateImage(CGSize(width: 30.0, height: 30.0), contextGenerator:' in icon
    assert 'cornerRadius: 8.0' in icon
    assert 'context.setFillColor(colorBlue.cgColor)' in icon
    assert 'context.setStrokeColor(UIColor.white.cgColor)' in icon
    assert 'context.clip(using: .evenOdd)' in icon
    assert 'context.translateBy(x: 0.0, y: size.height)' in icon
    assert 'context.scaleBy(x: 1.0, y: -1.0)' in icon
    assert 'gradientImage' in icon and 'backdropImage' in icon
    rect_pattern = r'CGRect\(x: ([0-9.]+), y: ([0-9.]+), width: ([0-9.]+), height: ([0-9.]+)\)'
    ring = tuple(map(float, re.search(r'strokeEllipse\(in: ' + rect_pattern, icon).groups()))
    head = tuple(map(float, re.search(r'fillEllipse\(in: ' + rect_pattern, icon).groups()))
    badge = tuple(map(float, re.search(r'let badgeBounds = ' + rect_pattern, icon).groups()))
    assert head[2] == head[3] and ring[2] == ring[3], 'Avatar circles must not tilt or stretch'
    assert abs((head[0] + head[2] / 2) - (ring[0] + ring[2] / 2)) < 0.001
    assert head[1] + head[3] < 16.0, 'Head must remain above the shoulders'
    assert badge[0] > head[0] and badge[1] > head[1]
    assert all(x >= 0 for x in badge) and badge[0] + badge[2] < 30 and badge[1] + badge[3] < 30
    factory = (source / FACTORY).read_text()
    assert 'public func generateImage(_ size: CGSize, contextGenerator: (CGSize, CGContext) -> Void, opaque: Bool = false, scale: CGFloat? = nil) -> UIImage?' in factory
    assert 'DrawingContext(size: size, scale: scale ?? 0.0, opaque: opaque, clear: false)' in factory
    assert 'actualScale = deviceScale' in factory and 'let deviceScale = UIScreen.main.scale' in factory
    return {'tile_points': [30, 30], 'native_pixel_dimensions': [[60, 60], [90, 90]],
            'native_scale_selection': 'unchanged Display factory', 'ring_rect': ring,
            'head_rect': head, 'badge_rect': badge, 'avatar_center_x': head[0] + head[2] / 2,
            'rendering': 'vector source geometry only; UIKit rasterization and device visuals not exercised'}


def fixture(texts, method, search_closure, variant='current'):
    enum = block(texts[ITEMS], 'enum SettingsSection: Int, CaseIterable')
    tap = 'interaction.openSettings(.addAccount)'
    if variant == 'wrong-row-action':
        tap = tap.replace('.addAccount', '.profile')
    if variant == 'wrong-bridge':
        method = method.replace('.addAccount', '.profile')
    if variant == 'edit-search':
        search_closure = search_closure.replace('openSettings(edit: false)', 'openSettings(edit: true)')
    search_body = search_closure.split(' in\n', 1)[1][:-1]
    return '''import Foundation
#if os(Linux)
import Glibc
#else
import Darwin
#endif
var checks = 0
func check(_ value: Bool, _ name: String) { if !value { print("FAIL " + name); exit(91) }; checks += 1 }
''' + enum + '''
enum SettingAction: Equatable { case addAccount; case profile }
final class Node { var actions: [SettingAction] = []; func openSettings(section: SettingAction) { actions.append(section) } }
protocol PeerInfoScreen: AnyObject { func openAddAccount() }
class ViewController {}
final class SettingsScreen: ViewController, PeerInfoScreen {
    let controllerNode = Node()
''' + method + '''
}
protocol TelegramRootControllerInterface: AnyObject {
    func getSettingsController() -> ViewController?
    func openSettings(edit: Bool)
}
final class Root: ViewController, TelegramRootControllerInterface {
    var settings: ViewController?
    var createdOnOpen: ViewController?
    var edits: [Bool] = []
    func getSettingsController() -> ViewController? { return settings }
    func openSettings(edit: Bool) { edits.append(edit); if let createdOnOpen { settings = createdOnOpen } }
}
final class Window { var viewController: ViewController?; init(_ value: ViewController?) { viewController = value } }
final class Shared { var mainWindow: Window? }
final class TestContext { let sharedContext = Shared() }
final class Queue {
    static let queue = Queue()
    var work: [() -> Void] = []
    static func mainQueue() -> Queue { return queue }
    func justDispatch(_ action: @escaping () -> Void) { work.append(action) }
    func drain() { let pending = work; work.removeAll(); pending.forEach { $0() } }
}
final class Interaction {
    var actions: [SettingAction] = []
    func openSettings(_ action: SettingAction) { actions.append(action) }
}
func tapRow(_ interaction: Interaction) {
''' + tap + '''
}
func search(_ context: TestContext) {
''' + search_body + '''
}
let cases = SettingsSection.allCases
check(cases.firstIndex(of: .nagramix)! < cases.firstIndex(of: .myProfile)!, "NagramiX before profile")
check(cases.firstIndex(of: .accounts)! == cases.firstIndex(of: .myProfile)! + 1, "accounts immediately after profile")
check(cases.firstIndex(of: .accounts)! < cases.firstIndex(of: .proxy)!, "accounts before following settings")
let interaction = Interaction(); tapRow(interaction)
check(interaction.actions == [.addAccount], "row uses native add callback")
let context = TestContext()
search(context); check(Queue.queue.work.isEmpty, "missing window is harmless")
context.sharedContext.mainWindow = Window(ViewController())
search(context); check(Queue.queue.work.isEmpty, "unrelated window is harmless")
let root = Root(); let screen = SettingsScreen(); root.createdOnOpen = screen
context.sharedContext.mainWindow = Window(root)
search(context)
check(root.edits == [false], "search opens standard settings")
check(screen.controllerNode.actions.isEmpty, "search waits for settings selection")
check(Queue.queue.work.count == 1, "one queued route")
Queue.queue.drain()
check(screen.controllerNode.actions == [.addAccount], "search invokes public native bridge")
check(Queue.queue.work.isEmpty, "queue drained once")
let wrongScreen = Root(); wrongScreen.createdOnOpen = ViewController()
context.sharedContext.mainWindow = Window(wrongScreen)
search(context); Queue.queue.drain()
check(wrongScreen.edits == [false], "unrelated settings screen is harmless")
let direct = SettingsScreen(); direct.openAddAccount()
check(direct.controllerNode.actions == [.addAccount], "direct public route uses native handler")
print("PASS account settings route checks: \\(checks)")
'''


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_routes(texts, method, search, swiftc, folder):
    positive, negative = [], []
    variants = {'wrong-row-action': 'row uses native add callback',
                'wrong-bridge': 'search invokes public native bridge',
                'edit-search': 'search opens standard settings'}
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        for variant in ('current', *variants):
            path = folder / (mode + '-' + variant + '.swift')
            binary = path.with_suffix('')
            path.write_text(fixture(texts, method, search, variant))
            result = subprocess.run([str(swiftc), '-module-cache-path', str(folder / 'cache'), '-warnings-as-errors', *flags, str(path), '-o', str(binary)], capture_output=True, text=True)
            assert result.returncode == 0, result.stderr[-6000:]
            result = subprocess.run([str(binary)], capture_output=True, text=True, preexec_fn=no_core)
            if variant == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                positive.append({'mode': mode, 'result': result.stdout.strip()})
            else:
                assert result.returncode == 91 and 'FAIL ' + variants[variant] in result.stdout, (variant, result.returncode, result.stdout)
                negative.append({'mode': mode, 'variant': variant, 'diagnostic': result.stdout.strip()})
    return positive, negative


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan, full = source_contract(args.source, args.baseline)
    texts, method, search = ui_contract(args.source, args.baseline)
    geometry = icon_contract(texts[ICONS], (args.baseline / ICONS).read_text(), args.source)
    with tempfile.TemporaryDirectory(prefix='account-settings-entry-') as temporary:
        folder = Path(temporary)
        rejected = guard_checks(args.source, STAGE, plan, folder / 'guards')
        positive, negative = run_routes(texts, method, search, args.swiftc, folder)
        for name in plan['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    _, after = source_contract(args.source, args.baseline)
    assert full == after
    report = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
              'full_source': full, 'production_runs': positive, 'semantic_negatives': negative,
              'fail_closed': rejected, 'swift_parse': len(plan['outputs']), 'icon_geometry': geometry,
              'source_boundary': 'All five files reverse exactly to pre-account bytes except the approved row, section move, editing removal, public bridge, search callback and icon insertion. Existing linked-account loop is byte-exact after dedent.',
              'runtime_boundary': 'Actual section enum, Add Account row action, public bridge and search callback execute with bounded navigation/queue adapters. Native authentication, limits, UIKit, icon rasterization and account network traffic are not executed.',
              'localization': 'Existing Settings_AddAccount and search synonym getters; no new literal UI strings or custom locale keys.',
              'apple_sdk': 'not_run', 'physical_iphone': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
