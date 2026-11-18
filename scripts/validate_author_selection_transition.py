#!/usr/bin/env python3
"""Check the real author selection and menu routing on a deterministic UI boundary."""
import argparse
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import ROOT, checked_plan

STAGE = 'author_selection_transition'
UI = 'submodules/TelegramUI/Sources/'
LOAD = UI + 'Chat/ChatControllerLoadDisplayNode.swift'
MENUS = UI + 'ChatInterfaceStateContextMenus.swift'
CONTROLLER = UI + 'ChatController.swift'
INTERFACE = 'submodules/ChatPresentationInterfaceState/Sources/ChatPanelInterfaceInteraction.swift'
DISPOSABLES = 'submodules/SSignalKit/SwiftSignalKit/Source/Disposable.swift'


def fixture(source: Path) -> str:
    load = (source / LOAD).read_text()
    menus = (source / MENUS).read_text()
    routing = (source / INTERFACE).read_text()
    callback_type = next(
        line.split(': ', 1)[1] for line in routing.splitlines() if 'public let selectMessagesByAuthor:' in line
    )
    controller = (source / CONTROLLER).read_text()
    assert 'self.nagramiXCancelAuthorSelection()' in block(controller, '    override public func viewDidDisappear(')
    assert 'self.nagramiXCancelAuthorSelection()' in block(load, '    func reloadChatLocation(')
    ordinary = block(load, 'beginMessageSelection: { [weak self]')
    assert 'nagramiXPostSelectionIds(messageIds)' in ordinary
    assert 'nagramiXCommitMessageSelection(messageIds, completion: completion)' in ordinary

    declarations = (source / DISPOSABLES).read_text()
    disposables = '\n'.join(block(declarations, name) for name in (
        'public protocol Disposable:', 'public final class ActionDisposable', 'public final class MetaDisposable',
        'public final class DisposableSet',
    ))
    start = load.index('private final class NagramiXAuthorSelectionPresentation')
    end = load.index('    func reloadChatLocation(', start)
    wiring = block(load, 'selectMessagesByAuthor: { [weak self]').removeprefix('selectMessagesByAuthor: ')
    occurrences = menus.split('text: chatPresentationInterfaceState.strings.nagramiXSelectFromAuthor')
    assert len(occurrences) == 3
    actions = [block(text, 'action: { action in').removeprefix('action: ') for text in (
        part.split('})))', 1)[0] + '}' for part in occurrences[1:]
    )]
    # The boundary uses the real interface type and both actual action closures.
    presentation = load[start:end] + f'''
    func checkAuthorFlow(_ authorId: EnginePeer.Id, _ action: ContextMenuActionItem.Action, archived: Bool = false) {{
        let callback: {callback_type} = {wiring}
        guard let selectMessagesByAuthor = callback else {{ return }}
        let route: (ContextMenuActionItem.Action) -> Void
        if archived {{ route = {actions[1]} }} else {{ route = {actions[0]} }}
        route(action)
    }}
}}
'''
    test = (ROOT / 'scripts/tests/NagramiXAuthorSelectionTransition.swift').read_text()
    return test.replace('// ACTUAL_AUTHOR_PRESENTATION', disposables + '\n' + presentation, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()

    plan = checked_plan(STAGE)
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name in plan['inputs']:
        run([args.swiftc, '-frontend', '-parse', args.source / name], timeout=60)

    with tempfile.TemporaryDirectory(prefix='author-selection-transition-') as folder:
        work = Path(folder)
        source = work / 'AuthorSelection.swift'
        source.write_text(fixture(args.source))
        for mode, flags in [('debug', []), ('optimized', ['-O'])]:
            binary = work / f'author-selection-{mode}'
            run([args.swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
                 '-module-cache-path', work / 'cache', *flags, source, '-o', binary], timeout=90)
            result = run([binary], timeout=30)
            print(f'{mode}: {result.stdout.strip()}', flush=True)


if __name__ == '__main__':
    main()
