#!/usr/bin/env python3
"""Проверка промежуточной стадии настроек переводчика и цепочки."""
import argparse, hashlib, json, subprocess, sys, tempfile, shutil, importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PLAN = json.loads((ROOT / 'ios/translation_completion_patches.json').read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def is_applied(source): return all((source / n).is_file() and digest(source / n) == h for n, h in PLAN['outputs'].items())
def delegate_if_applied(args):
    from validate_translation_sdk_fix import delegate_if_applied as delegate_latest
    if delegate_latest(args): return True
    if not is_applied(args.source): return False
    subprocess.run([sys.executable, __file__, '--source', str(args.source), *(['--swiftc', str(args.swiftc)] if args.swiftc else [])], check=True)
    return True
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--source', type=Path, required=True); parser.add_argument('--swiftc',type=Path); parser.add_argument('--standalone',action='store_true'); args=parser.parse_args()
    from validate_translation_sdk_fix import delegate_if_applied as delegate_latest
    if delegate_latest(args): return
    assert is_applied(args.source)
    ui=(args.source/'submodules/TranslateUI/Sources/NagramiXTranslationPreferences.swift').read_text()
    settings=(args.source/'submodules/TranslateUI/Sources/NagramiXTranslationSettings.swift').read_text()
    runtime=(args.source/'submodules/TranslateUI/Sources/NagramiXTranslationRuntime.swift').read_text()
    apple=(args.source/'submodules/TranslateUI/Sources/NagramiXTranslationApple.swift').read_text()
    assert 'appleSource: String?' in settings and 'self.appleSource' not in settings
    assert 'nagramiXShowAppleLanguages' in ui and '$0.appleSource = code' in ui
    assert 'availability.supportedLanguages' in apple and 'availability.status(from: language, to: targetLanguage)' in apple
    assert 'try await session.prepareTranslation()' in apple and 'if await session.isReady' in apple
    assert 'NagramiXTranslationLanguage.isExcluded(source, ignored: configuration.ignored)' in runtime
    assert 'NagramiXTranslationLanguage.isExcluded($0, ignored: configuration.ignored)' in runtime
    assert 'NagramiXTranslationLanguage.isExcluded(providerSource, ignored: configuration.ignored)' in runtime
    moved=ui.split('@objc private func temperatureMoved',1)[1].split('@objc private func temperatureSaved',1)[0]
    saved=ui.split('@objc private func saveCredentials()',1)[1].split('private func configureTemperature',1)[0]
    assert 'self.draftTemperature = Double(sender.value)' in moved
    assert 'value.temperatures = temperatures' in saved
    assert 'guard case .gptoss = self.page else { return }' in ui
    for name, expected in PLAN['templates'].items(): assert digest(ROOT/'ios'/name)==expected, name
    spec=importlib.util.spec_from_file_location('translation_completion',ROOT/'ios/translation_completion.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='nagramix-translation-settings-') as folder:
        temp=Path(folder); base=temp/'base'
        for name, item in PLAN['previous'].items():
            path=base/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/item,path)
        module.apply_translation_completion(base, ROOT/'ios')
        assert is_applied(base)
        for bad in PLAN['inputs']:
            copy=temp/'bad';shutil.copytree(base,copy)
            for name,item in PLAN['previous'].items(): shutil.copyfile(ROOT/'ios'/item,copy/name)
            path=copy/bad;path.write_bytes(path.read_bytes()+b'// drift')
            snapshot={n:(copy/n).read_bytes() for n in PLAN['inputs']}
            try: module.apply_translation_completion(copy,ROOT/'ios')
            except SystemExit: pass
            else: raise AssertionError('Дрейф входа принят: '+bad)
            assert snapshot=={n:(copy/n).read_bytes() for n in PLAN['inputs']}
            shutil.rmtree(copy)
        for bad in PLAN['templates']:
            overlay=temp/'bad-overlay';overlay.mkdir()
            (overlay/'translation_completion_patches.json').write_text(json.dumps(PLAN))
            for name in PLAN['templates']:
                target=overlay/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/name,target)
            path=overlay/bad;path.write_bytes(path.read_bytes()+b'// drift')
            copy=temp/'bad-template-source';copy.mkdir()
            for name,item in PLAN['previous'].items():
                target=copy/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/item,target)
            snapshot={n:(copy/n).read_bytes() for n in PLAN['inputs']}
            try: module.apply_translation_completion(copy,overlay)
            except SystemExit: pass
            else: raise AssertionError('Дрейф шаблона принят: '+bad)
            assert snapshot=={n:(copy/n).read_bytes() for n in PLAN['inputs']}
            shutil.rmtree(copy);shutil.rmtree(overlay)
        if args.swiftc:
            from validate_message_translation import run_swift
            for optimized in [False, True]:
                run_swift(args.swiftc, temp, 'translation-completion-' + str(optimized), [base / 'submodules/TranslateUI/Sources/NagramiXTranslationSettings.swift', ROOT / 'scripts/tests/NagramiXTranslationCompletionTests.swift'], optimized)
            subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(base/n) for n in PLAN['outputs']]],check=True)
        # Restore the exact inputs for the previous strict validator.
        if not args.standalone:
            prior=temp/'prior'
            names=set(PLAN['inputs']) | set(PLAN['guards'])
            for manifest in (ROOT/'ios').glob('*_patches.json'):
                earlier=json.loads(manifest.read_text())
                for field in ('inputs', 'outputs', 'guards', 'copies'): names.update(earlier.get(field, {}))
            names.add('Telegram/Telegram-iOS/en.lproj/Localizable.strings')
            for name in names:
                source=args.source/name
                if not source.is_file(): continue
                target=prior/name;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/'ios'/PLAN['previous'][name] if name in PLAN['previous'] else source,target)
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_translation_settings_revision.py'),'--source',str(prior),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    print('PASS: translation completion, fail-closed' + ('' if args.standalone else ', previous chain'))
if __name__=='__main__':main()
