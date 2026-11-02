#!/usr/bin/env python3
"""Проверить inline-перевод, сохранность оригиналов и явный Telegram Premium."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'translation_inline_telegram_patches.json').read_text())


def sha(data): return hashlib.sha256(data).hexdigest()


def is_applied(source):
    expected = {**PLAN['outputs'], **{n: item['sha256'] for n, item in PLAN['copies'].items()}}
    return all((source / n).is_file() and sha((source / n).read_bytes()) == h for n, h in expected.items()) and not any((source / n).exists() for n in PLAN['deletions'])


def reverse(source, target):
    names = set(PLAN['inputs']) | set(PLAN['deletions'])
    for manifest in OVERLAY.glob('*_patches.json'):
        item = json.loads(manifest.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift'])
    for name in names - set(PLAN['copies']):
        original = PLAN['previous'].get(name) or PLAN['deletions'].get(name, {}).get('source')
        path = OVERLAY / original if original else source / name
        if not path.is_file(): continue
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())


def delegate_if_applied(args, script):
    from validate_translation_premium_visibility import delegate_if_applied as delegate_latest
    if delegate_latest(args, script): return True
    if not is_applied(args.source): return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='before-inline-translation-') as folder:
        prior = Path(folder)
        reverse(args.source, prior)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None:
            arguments += ['--upstream', str(args.source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def verify(source):
    assert is_applied(source)
    for n, h in PLAN['guards'].items(): assert sha((source / n).read_bytes()) == h, n
    for n, h in PLAN['templates'].items(): assert sha((OVERLAY / n).read_bytes()) == h, n
    files = {Path(n).name: (source / n).read_text() for n in PLAN['outputs']}
    model = files['NagramiXTranslationSettings.swift']
    assert 'case telegram, apple, google, yandex, gemini, chatgpt, deepseek' in model
    assert 'case .telegram: return "Telegram Premium"' in model
    ui = files['NagramiXTranslationPreferences.swift']
    assert '["ПЕРЕВОД", "TELEGRAM", "СЛОВАРИ", "ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ"]' in ui
    assert 'case .settings: return 4' in ui and 'if section == 1 { return 1 }' in ui
    assert 'section == 1 ? [.telegram]' in ui
    assert 'item.0 == .telegram, self.isPremium != true' in ui
    assert 'data.subscribe(TelegramEngine.EngineData.Item.Peer.Peer(id: context.account.peerId))' in ui
    assert 'self.premiumDisposable.dispose()' in ui
    assert block(ui, 'public func tableView(_ tableView: UITableView, titleForFooterInSection').count('return nil') == 1
    assert 'Удалить ключ' not in ui and 'Готово' not in ui
    runtime = files['NagramiXTranslationRuntime.swift']
    telegram = runtime.split('if configuration.provider == .telegram {', 1)[1].split('if configuration.provider == .apple {', 1)[0]
    assert 'peer?.isPremium == true' in telegram
    assert 'context.engine.messages.translate(texts:' in telegram
    assert 'current.revision == configuration.revision' in telegram
    assert 'NagramiXTranslationKeys' not in telegram and 'CloudClient' not in telegram
    assert 'nagramiXInlineTranslationTarget(current) == nil' in runtime
    assert 'nagramiXInlineTranslationTarget($0) == nil' in runtime
    menu = files['ChatInterfaceStateContextMenus.swift']
    # The only changed whole-message .translate action uses the inline runtime.
    start = menu.index('NagramiXInlineTranslationRuntime.showOriginal')
    end = menu.index('f(.default)', start)
    assert 'NagramiXInlineTranslationRuntime.translate' in menu[start:end]
    assert '} else {\n                            controllerInteraction.performTextSelectionAction' in menu[start:end]
    assert 'Показать оригинал' in menu
    assert 'NagramiXMessageTranslationController' not in menu
    assert menu.count('String? = nagramiXInlineTranslationTarget(message)') == 5
    bubble = files['ChatMessageTextBubbleContentNode.swift']
    assert 'inlineTarget ?? item.associatedData.translateToLanguage' in bubble
    assert '(incoming || inlineTarget != nil)' in bubble
    assert 'rawText = attribute.text' in bubble and 'messageEntities = attribute.entities' in bubble
    assert files['ChatHistoryListNode.swift'].count('if nagramiXInlineTranslationTarget(message) != nil { continue }') == 2
    attribute = files['SyncCore_TranslationMessageAttribute.swift']
    assert 'nagramiXInlineRevision: String? = nil' in attribute
    assert 'nagramiXInlineHidden: Bool = false' in attribute
    for key in ['nxr', 'nxs', 'nxh']: assert attribute.count('"' + key + '"') >= 2
    assert 'translation.nagramiXInlineSource == nagramiXInlineTranslationFingerprint(message)' in attribute
    assert 'NagramiXInlineTranslationConfiguration.revision() == revision' in attribute
    assert 'settings["enabled"] as? Bool == true' in attribute
    inline = (source / next(iter(PLAN['copies']))).read_text()
    assert 'let account: Int64' in inline and 'let message: EngineMessage.Id' in inline
    assert 'previous?.revision != configuration.revision' in inline and 'self.current(key, token)' in inline
    assert 'current.revision == configuration.revision' in inline
    assert 'nagramiXInlineTranslationFingerprint(currentMessage) == fingerprint' in inline
    assert 'current.resolvedTarget(interface: interface, targetOverride: choice.target) == target' in inline
    assert 'nagramiXInlineHidden: true' in inline
    assert 'updateChat(' not in inline and 'display(' not in inline and 'TranslateScreen' not in inline
    assert '"account": context.account.peerId.toInt64()' in inline
    assert 'error != .cancelled' in inline
    assert 'TranslationMessageAttribute(text: translatedText, entities: translatedEntities' in inline
    assert 'self.account.postbox.transaction' in (source / 'submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXLocalMessageData.swift').read_text()
    # Earlier non-message selection / native-OFF presentation is deliberately untouched.
    for path in PLAN['outputs']:
        text = (source / path).read_text().lower()
        assert 'pollinations' not in text and 'gptoss' not in text


def guard_tests(source):
    spec = importlib.util.spec_from_file_location('translation_inline_telegram', OVERLAY / 'translation_inline_telegram.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    originals = {n: (OVERLAY / f).read_bytes() for n, f in PLAN['previous'].items()}
    for n, item in PLAN['deletions'].items(): originals[n] = (OVERLAY / item['source']).read_bytes()
    originals.update({n: (source / n).read_bytes() for n in PLAN['guards'] if n not in PLAN['deletions']})
    with tempfile.TemporaryDirectory(prefix='inline-translation-guards-') as folder:
        temp = Path(folder)
        def seed():
            base = temp / 'input'
            for n, data in originals.items():
                path = base / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            return base
        def snapshot(base): return {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}
        def reject(base, overlay=OVERLAY):
            old = snapshot(base)
            try: module.apply_translation_inline_telegram(base, overlay)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError('Принят дрейф')
            assert snapshot(base) == old, 'Частичная запись/удаление'
            shutil.rmtree(base)
        base = seed(); module.apply_translation_inline_telegram(base, OVERLAY); verify(base); reject(base)
        rejected = 1
        for n in originals:
            for missing in (False, True):
                base = seed()
                if missing: (base / n).unlink()
                else: (base / n).write_bytes(b'// drift')
                reject(base); rejected += 1
        for n in PLAN['templates']:
            base = seed(); overlay = temp / 'overlay'; overlay.mkdir()
            for name in PLAN['templates']:
                path = overlay / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((OVERLAY / name).read_bytes())
            (overlay / n).write_bytes(b'// drift')
            (overlay / 'translation_inline_telegram_patches.json').write_text(json.dumps(PLAN))
            reject(base, overlay); shutil.rmtree(overlay); rejected += 1
        base = seed(); collision = base / next(iter(PLAN['copies'])); collision.parent.mkdir(parents=True, exist_ok=True); collision.write_bytes(b'// existing'); reject(base); rejected += 1
    print(f'PASS: {rejected} fail-closed cases, no partial writes/deletion')


def execute_swift(source, compiler):
    with tempfile.TemporaryDirectory(prefix='inline-translation-swift-') as folder:
        temp = Path(folder)
        core = (source / 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TranslationMessageAttribute.swift').read_text()
        attribute = temp / 'Attribute.swift'
        attribute.write_text(core.replace('import Postbox\n', ''))
        settings = source / 'submodules/TranslateUI/Sources/NagramiXTranslationSettings.swift'
        for flags in ([], ['-O']):
            binary = temp / 'tests'
            subprocess.run([str(compiler), '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), *flags,
                str(settings), str(attribute), str(ROOT / 'scripts/tests/NagramiXInlineTranslationBoundary.swift'),
                str(ROOT / 'scripts/tests/NagramiXInlineTranslationTests.swift'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=30)
        subprocess.run([str(compiler), '-frontend', '-parse', *[str(source / n) for n in [*PLAN['outputs'], *PLAN['copies']]]], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--standalone', action='store_true')
    parser.add_argument('--swiftc', type=Path)
    args = parser.parse_args()
    from validate_translation_premium_visibility import delegate_if_applied as delegate_latest
    if delegate_latest(args, Path(__file__)): return
    verify(args.source); guard_tests(args.source)
    if args.swiftc: execute_swift(args.source, args.swiftc)
    if not args.standalone:
        with tempfile.TemporaryDirectory(prefix='inline-translation-prior-') as folder:
            prior = Path(folder); reverse(args.source, prior)
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_translation_simplification.py'), '--source', str(prior)], check=True)
    print('PASS: inline message translation / explicit Telegram Premium / exact prior chain; SDK and iPhone pending')


if __name__ == '__main__': main()
