"""Typecheck the entire production recognizer and history hooks against real UIKit."""
import subprocess
import sys
from single_touch_message_selection_runtime import ROOT, production, HISTORY_FIELDS


def check(source, swiftc, folder):
    if sys.platform != 'darwin':
        return {'status': 'not_run', 'reason': 'Real UIKit requires the Apple SDK on macOS'}
    helper, methods = production(source)
    # Keep all real UIKit types/methods. Only Telegram list/model/timer boundaries
    # remain explicit stand-ins; complete TelegramUI compilation is a later gate.
    boundary = (ROOT/'scripts/tests/NagramiXMessageDragSelectionBoundary.swift').read_text()
    boundary = boundary[boundary.index('typealias MessageId ='):]
    code = 'import Foundation\nimport UIKit\n'+helper+'\n'+boundary+'\nfinal class HistoryHarness: NSObject {\n'+HISTORY_FIELDS+methods+'\n}\n'
    path = folder/'message-drag-selection-uikit.swift'
    path.write_text(code)
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
    command = [str(swiftc), '-swift-version', '5', '-warnings-as-errors', '-typecheck', '-parse-as-library',
               '-sdk', sdk, '-target', 'arm64-apple-ios15.0', '-module-cache-path', str(folder/'selection-uikit-cache'), str(path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout+result.stderr
    return {'status': 'passed', 'scope': 'Whole unmodified helper, selector binding, coordinate conversion, range/history hooks and native scroll methods with real UIKit; explicit Telegram model/list/timer I/O. Full application SDK and physical gesture arbitration remain separate.'}
