#!/usr/bin/env python3
"""Exercise the reaction dialog against the AlertScreen API from the selected Telegram source."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from validate_message_delivery_recovery import TESTS, reaction_fixture
from validate_private_temporary_transcription import execute
from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest


def alert_boundary(native):
    # Use the actual configuration, actions and callback. Only presentation and animation are simulated.
    marker = 'public convenience init(\n        configuration: Configuration = Configuration(),\n        title:'
    start = native.index(marker)
    signature = native[start:native.index('\n    ) {', start) + len('\n    )')]
    api = '\n'.join(block(native, name) for name in (
        'public enum ActionAligmnent:', 'public struct Configuration:', 'public struct Action:'))
    dismissed, = [line.strip() for line in native.splitlines() if 'public var dismissed:' in line]
    return """
typealias PresentationData = Presentation
extension Chat {
    var updatedPresentationData: (PresentationData, Signal<PresentationData, NoError>) {
        return (presentationData, .single(presentationData))
    }
}
final class AlertScreen {
    let text: String
    let actions: [Action]
    func dismiss() { dismissed?(false) }
""" + api.replace('public ', '') + '\n' + dismissed.removeprefix('public ') + '\n' + signature.replace(
        'public convenience init', 'init') + """ {
        precondition(!configuration.dismissOnOutsideTap && configuration.allowInputInset)
        self.text = text
        self.actions = actions
    }
}
"""


def validate(source, swiftc, directory):
    plan = checked_plan('deferred_reaction_alert')
    files = {}
    for key, table in [('outputs', 'replacements'), ('guards', 'guard_sources')]:
        for name, expected in plan[key].items():
            path = source / name if source else OVERLAY / plan[table][name]
            assert digest(path) == expected, name
            files[Path(name).name] = path.read_text()
    chat = files['ChatController.swift']
    assert '\nimport AlertComponent\n' in chat
    native = files['AlertComponent.swift']
    factory = 'func textAlertController(context: Context,'
    template = (TESTS / 'NagramiXDeferredReactionRecovery.swift').read_text()
    queue = block(files['MessageReactions.swift'], 'func nagramiXEnqueueReactions(')
    guard, = [line.strip() for line in queue.splitlines() if 'guard !messageIds.isEmpty' in line]
    store = files['NagramiXDeferredReactionsStore.swift']
    # Recompile the actual failed call with the return type of the account-context overload.
    signature = block(files['AlertTheme.swift'], 'public func textAlertController(\n    context: AccountContext,').split(' {\n', 1)[0]
    return_type = signature.rsplit(' -> ', 1)[-1]
    assert return_type == 'ViewController', signature
    old_factory = block(template, factory)
    legacy = template.replace(old_factory, old_factory.replace(' -> AlertController {', f' -> {return_type} {{'))
    legacy = legacy.replace('final class AlertController {', 'class ViewController {}\nfinal class AlertController: ViewController {')
    previous, = plan['previous'].values()
    old_file = directory / 'Build233.swift'
    old_file.write_text(reaction_fixture((OVERLAY / previous).read_text(), store, guard, legacy))
    failed = subprocess.run([swiftc, '-swift-version', '5', '-parse-as-library', '-typecheck',
                             '-module-cache-path', directory / 'cache', old_file], text=True, capture_output=True)
    assert failed.returncode and "type 'ViewController' has no member 'dismissed'" in failed.stderr, failed.stderr
    template = template.replace(block(template, factory), '')
    template = template.replace(block(template, 'final class AlertController {'), alert_boundary(native))
    template = template.replace('[AlertController]', '[AlertScreen]').replace('(_ alert: AlertController,', '(_ alert: AlertScreen,')
    template = template.replace('// EXTERNAL DISMISSAL', '''
        let firstPrompt = chat.alerts[0]
        firstPrompt.dismiss()
        precondition(db.listeners.isEmpty && store.records.count == 1 && account.sent.count == 1)
        chat.nagramiXFlushDeferredReactionsIfActive()
        let nextPrompt = chat.alerts.last!
        precondition(nextPrompt !== firstPrompt)
        firstPrompt.actions[1].action()
        firstPrompt.dismiss()
        precondition(!db.listeners.isEmpty && store.records.count == 1 && account.sent.count == 1)
    ''')
    code = reaction_fixture(chat, store, guard, template)
    for result in execute(swiftc, directory, 'DeferredReactionAlert', code):
        print(result['mode'], result['output'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-reaction-alert-') as tmp:
        validate(args.source, args.swiftc, Path(tmp))
