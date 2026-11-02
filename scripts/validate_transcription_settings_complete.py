#!/usr/bin/env python3
"""Проверить настройки и движки транскрибации и строгую цепочку."""
import argparse,copy,hashlib,importlib.util,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def plan():return json.loads((ROOT/'ios/transcription_settings_complete_patches.json').read_text())
def is_applied(source):return all((source/n).is_file() and sha((source/n).read_bytes())==h for n,h in plan()['outputs'].items())
def delegate_if_applied(args):
    from validate_translation_settings_revision import delegate_if_applied as delegate_latest
    if delegate_latest(args): return True
    if not is_applied(args.source):return False
    subprocess.run([sys.executable,str(Path(__file__).resolve()),'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    return True

def guards(source, p, temp):
    spec = importlib.util.spec_from_file_location('transcription_settings_complete', ROOT / 'ios/transcription_settings_complete.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    original = {n: (source / n).read_bytes() for n in p['guards']}; original.update(previous_bytes(p))
    rejected = []
    from validate_quick_format import manifest
    def seed():
        root = temp / 'source'
        for n, data in original.items():
            dest = root / n; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
        return root
    def reject(root, label, overlay=ROOT / 'ios'):
        before = manifest(root)
        try: module.apply_transcription_settings_complete(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят неверный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if overlay != ROOT / 'ios': shutil.rmtree(overlay)
    def overlay(patch):
        root = temp / 'overlay'; root.mkdir()
        (root / 'transcription_settings_complete_patches.json').write_text(json.dumps(patch))
        for n in p['templates']:
            dest = root / n; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes((ROOT / 'ios' / n).read_bytes())
        return root
    for n in original:
        for mode in ['missing','drift']:
            root = seed(); path = root / n
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes()+b'\n// drift')
            reject(root, mode + ' ' + n)
    for n in p['copies']:
        root = seed(); path = root / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('collision')
        reject(root, 'helper collision ' + n)
    for n in p['templates']:
        for mode in ['missing','drift']:
            root = seed(); bad = overlay(p); path = bad / n
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes()+b'\n// drift')
            reject(root, mode + ' template ' + n, bad)
    for field in ['inputs','outputs','guards','templates']:
        if not p[field]: continue
        bad = copy.deepcopy(p); bad[field][next(iter(bad[field]))] = '0'*64
        reject(seed(),field + ' SHA',overlay(bad))
    for field in ['replacements','previous']:
        bad = copy.deepcopy(p); bad[field][next(iter(bad[field]))] = '../outside'
        reject(seed(),field+' traversal',overlay(bad))
    if p['copies']:
        bad = copy.deepcopy(p); entry = bad['copies'].pop(next(iter(bad['copies']))); bad['copies']['../outside'] = entry
        reject(seed(),'copy traversal',overlay(bad))
    root = seed(); module.apply_transcription_settings_complete(root,ROOT/'ios'); reject(root,'repeat application')
    return rejected

def previous_bytes(p):
    result={n:(ROOT/'ios'/v).read_bytes() for n,v in p['previous'].items()}
    for n,b in result.items(): assert sha(b)==p['inputs'][n],n
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);args=parser.parse_args()
    from validate_translation_settings_revision import delegate_if_applied as delegate_latest
    if delegate_latest(args): return
    p=plan()
    for n,h in {**p['outputs'],**p['guards']}.items():assert sha((args.source/n).read_bytes())==h,n
    ui=(args.source/'submodules/NagramiXTranscription/Sources/Preferences.swift').read_text();cloud=(args.source/'submodules/NagramiXTranscription/Sources/Cloud.swift').read_text()
    for s in ['Настройки ','TELEGRAM','НА УСТРОЙСТВЕ','ЧЕРЕЗ ИНТЕРНЕТ','trailingSwipeActionsConfigurationForRowAt','UIPickerView','Разрешить передачу аудио','Загрузка через мобильную сеть','appleLanguages','whisperLanguages','Сохранить']:assert s in ui,s
    assert 'https://api.x.ai/v1/stt' in cloud and 'provider == .grok' in cloud
    with tempfile.TemporaryDirectory(prefix='nagramix-transcription-complete-') as folder:
        temp=Path(folder);rejected=guards(args.source,p,temp);names=set(p['inputs'])|set(p['guards'])
        if args.swiftc:
            from validate_message_translation import run_swift
            prefix=args.source/'submodules/NagramiXTranscription/Sources'
            from validate_quick_format import block
            source_ui=(prefix/'Preferences.swift').read_text()
            layout_template=(ROOT/'scripts/tests/NagramiXTranscriptionSettingsLayoutTests.swift').read_text()
            actual_types='\n'.join(block(source_ui, x).replace('private ', '') for x in ['private enum Page {','private struct Row {','private enum Action {'])
            actual_sections=block(source_ui,'private func makeSections() ->').replace('private func makeSections()', 'func makeSections()')
            layout_test=temp/'Layout.swift';layout_test.write_text(layout_template.replace('// ACTUAL_TYPES',actual_types).replace('// ACTUAL_SECTIONS',actual_sections))
            analyzer=temp/'Analyzer.swift'; analyzer.write_text('import Foundation\n'+'\n'.join(line for line in (prefix/'AppleAnalyzer.swift').read_text().splitlines() if not line.startswith('import ')).replace('#if compiler(>=6.2)', '#if true'))
            models=temp/'Models.swift'; models.write_text((prefix/'Models.swift').read_text().replace('import CryptoKit','import FoundationNetworking'))
            model_boundary=temp/'ModelBoundary.swift';model_boundary.write_text('import Foundation\nimport FoundationNetworking\nstruct SHA256 { mutating func update(data:Data){}; func finalize()->[UInt8]{[]} }\n')
            subprocess.run([str(args.swiftc),'-typecheck','-warnings-as-errors','-module-cache-path',str(temp/'cache'),str(prefix/'Settings.swift'),str(models),str(model_boundary)],check=True)
            for optimized in [False,True]:
                run_swift(args.swiftc,temp,'layout'+str(optimized),[prefix/'Settings.swift',layout_test],optimized)
                run_swift(args.swiftc,temp,'activation'+str(optimized),[prefix/'Settings.swift',models,model_boundary,ROOT/'scripts/tests/NagramiXWhisperActivationTests.swift'],optimized)
                run_swift(args.swiftc,temp,'analyzer'+str(optimized),[prefix/'Settings.swift',ROOT/'scripts/tests/NagramiXTranscriptionAnalyzerBoundary.swift',analyzer,ROOT/'scripts/tests/NagramiXTranscriptionRevisedAnalyzerTests.swift'],optimized)
                for test,files in [('grok',[prefix/'Settings.swift',prefix/'Cloud.swift',ROOT/'scripts/tests/NagramiXGrokTranscriptionTests.swift']),('core',[prefix/'Settings.swift',prefix/'Cloud.swift',prefix/'Coordinator.swift',ROOT/'scripts/tests/NagramiXTranscriptionRevisedCoreTests.swift']),('http',[prefix/'Settings.swift',prefix/'Cloud.swift',ROOT/'scripts/tests/NagramiXTranscriptionRevisedHTTPTests.swift'])]:
                    run_swift(args.swiftc,temp,test+str(optimized),files,optimized)
            subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.source/n) for n in p['outputs']]],check=True)
        for file in (ROOT/'ios').glob('*_patches.json'):
            old=json.loads(file.read_text())
            for field in ['inputs','outputs','guards','copies']:names.update(old.get(field,{}))
        names.add('Telegram/Telegram-iOS/en.lproj/Localizable.strings');prior=temp/'prior';previous=previous_bytes(p)
        for n in names:
            src=args.source/n
            if not src.is_file():continue
            path=prior/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(previous[n] if n in previous else src.read_bytes())
        subprocess.run([sys.executable,str(ROOT/'scripts/validate_transcription_settings_refinement.py'),'--source',str(prior)],check=True)
    print('PASS: настройки транскрибации / предыдущая цепочка / fail-closed:',len(rejected))
if __name__=='__main__':main()
