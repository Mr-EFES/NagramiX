#!/usr/bin/env python3
"""Проверить ручной битрейт кружков и фактические параметры обоих энкодеров."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import textwrap
from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'submodules/NagramiXMediaSettings/Sources/NagramiXRoundVideoSettings.swift'
UI = 'submodules/SettingsUI/Sources/NagramiXRoundQualityController.swift'
CAPTURE = 'submodules/Camera/CameraNeo/Sources/VideoRecorder.swift'
SCREEN = 'submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift'
VALUES = 'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift'
WRITER = 'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorVideoAVAssetWriter.swift'
PRIOR = ['round_video_sheet', 'round_video_page', 'round_video_refinement']


def sha(data): return hashlib.sha256(data).hexdigest()
def plan(): return json.loads((ROOT/'ios/round_video_bitrate_patches.json').read_text())


def is_applied(source):
    return all((source/name).is_file() and sha((source/name).read_bytes()) == digest for name,digest in plan()['outputs'].items())


def delegate_if_applied(args):
    # Later slider stages replace the UI file used to identify the bitrate
    # stage. Reconstruct those guarded states before testing the older contract.
    from validate_round_slider_touch import delegate_if_applied as delegate_slider
    if delegate_slider(args, Path(sys.argv[0]).resolve()): return True
    if not is_applied(args.source): return False
    subprocess.run([sys.executable, str(Path(__file__).resolve()), '--source', str(args.source),
                    *(['--swiftc', str(args.swiftc)] if args.swiftc else [])], check=True)
    return True


def reverse(source, current):
    previous = {name:(source/name).read_bytes() for name in current['inputs']}
    for name,old,new,count in reversed(current['patches']):
        text=previous[name].decode(); assert text.count(new)==count,name
        previous[name]=text.replace(new,old,count).encode()
    for name,data in previous.items(): assert sha(data)==current['inputs'][name],name
    return previous


def guard_checks(source, current, previous, temp):
    spec=importlib.util.spec_from_file_location('round_video_bitrate',ROOT/'ios/round_video_bitrate.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    original={**{name:(source/name).read_bytes() for name in current['guards']},**previous}
    rejected=[]
    def seed(label):
        target=temp/label
        for name,data in original.items():
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return target
    def overlay_for(label, altered):
        overlay=temp/('overlay-'+label);overlay.mkdir()
        (overlay/'round_video_bitrate_patches.json').write_text(json.dumps(altered))
        for name in current['templates']:
            path=overlay/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/'ios'/name).read_bytes())
        return overlay
    def reject(target,label,overlay=ROOT/'ios'):
        before=manifest(target)
        try:mod.apply_round_video_bitrate(target,overlay)
        except SystemExit:pass
        else:raise AssertionError('Принят некорректный вход: '+label)
        assert manifest(target)==before,'Частичная запись: '+label
        rejected.append(label)
        shutil.rmtree(target)
        if overlay != ROOT/'ios': shutil.rmtree(overlay)
    target=seed('valid');mod.apply_round_video_bitrate(target,ROOT/'ios')
    assert all((target/name).read_bytes()==(source/name).read_bytes() for name in original)
    reject(target,'reapply')
    for name in original:
        for mode in ['missing','drift']:
            target=seed('source-'+str(len(rejected)));path=target/name
            if mode=='missing':path.unlink()
            else:path.write_bytes(path.read_bytes()+b'\n// drift\n')
            reject(target,mode+' '+name)
    for name in current['templates']:
        for mode in ['missing','drift']:
            label='template-'+str(len(rejected));overlay=overlay_for(label,current);path=overlay/name
            if mode=='missing':path.unlink()
            else:path.write_bytes(path.read_bytes()+b'\n// drift\n')
            reject(seed('root-'+label),mode+' '+name,overlay)
    mutations=[]
    for index in range(len(current['patches'])):
        altered=copy.deepcopy(current);altered['patches'][index][1]+=' broken';mutations.append(('anchor-'+str(index),altered))
    for section in ['inputs','outputs','guards']:
        altered=copy.deepcopy(current);altered[section][next(iter(altered[section]))]='0'*64;mutations.append((section+'-sha',altered))
    altered=copy.deepcopy(current);altered['inputs']['../outside']='0'*64;altered['outputs']['../outside']='0'*64;mutations.append(('traversal',altered))
    altered=copy.deepcopy(current);altered['patches'][0][0]='/outside';mutations.append(('operation-path',altered))
    for label,altered in mutations:reject(seed('root-'+label),label,overlay_for(label,altered))
    return rejected


def previous_source(source, current, previous, temp, swiftc):
    names=set(current['guards'])|set(current['inputs'])
    for stage in PRIOR:
        p=json.loads((ROOT/'ios'/(stage+'_patches.json')).read_text())
        for field in ['outputs','guards','copies']:names.update(p[field])
    native=temp/'prior'
    for name in names:
        path=native/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(previous[name] if name in previous else (source/name).read_bytes())
    for stage in PRIOR:
        subprocess.run([sys.executable,str(ROOT/'scripts'/('validate_'+stage+'.py')),'--source',str(native),
                        *(['--swiftc',str(swiftc)] if swiftc and stage=='round_video_refinement' else [])],check=True)
    return native


def export_branch(text):
    return text.split('    // Snapshot from this recording, including deferred resource conversion.\n',1)[1].split('    let compressionProperties: [String: Any]',1)[0]


def test_prefix(source):
    ui=(source/UI).read_text();recorder=(source/CAPTURE).read_text();values=(source/VALUES).read_text()
    font_enum=block((source/'submodules/TelegramUIPreferences/Sources/PresentationThemeSettings.swift').read_text(),'public enum PresentationFontSize:')
    font_extension=block((source/'submodules/ItemListUI/Sources/ItemListItem.swift').read_text(),'public extension PresentationFontSize {')
    prefix='import Foundation\n'+font_enum+'\n'+font_extension+'\n'
    prefix+=block(ui,'private func nagramiXRoundBitRateText(')+'\n'+block(ui,'func nagramiXRoundQualityTitle(')+'\n'
    boundary=(ROOT/'scripts/tests/NagramiXRoundBitRateBoundary.swift').read_text()
    cell='\n'.join(block(ui,marker).replace('@objc ','').replace('private func','func') for marker in ['func update(_ value: NagramiXRoundVideoSettings)', '@objc private func valueChanged()'])
    page='\n'.join(block(ui,marker).replace('private func','func') for marker in [
        'private func supports(', 'private func shouldShowCinematic(', 'private func enabled(', 'func numberOfSections(',
        'func tableView(_ tableView: UITableView, numberOfRowsInSection', 'func tableView(_ tableView: UITableView, titleForHeaderInSection',
        'private func configure(', 'private func refreshVisibleRows(', 'private func commit(', 'private func updateBitRate(',
        'func tableView(_ tableView: UITableView, didSelectRowAt'])
    capture_start=recorder.index('        var compressionProperties: [String: Any] = [')
    capture_end=recorder.index('        assetWriter.add(videoInput)',capture_start)+len('        assetWriter.add(videoInput)')
    capture=recorder[capture_start:capture_end]
    camera=(source/SCREEN).read_text()
    snapshot=next(line.split('nagramiXRoundTuning: ',1)[1].strip() for line in camera.splitlines() if 'nagramiXRoundTuning: self.node.nagramiXQuality.map' in line)
    writer=(source/WRITER).read_text();start=writer.index('        var dimensions = configuration.dimensions')
    end=writer.index('        let videoInput = AVAssetWriterInput',start)
    decode=next(line.strip() for line in values.splitlines() if 'self.nagramiXRoundTuning = try container.decodeIfPresent' in line)
    encode=next(line.strip() for line in values.splitlines() if 'try container.encodeIfPresent(self.nagramiXRoundTuning' in line)
    for marker,replacement in [('// CELL_METHODS',cell),('// PAGE_METHODS',page),('// CAPTURE_SETTINGS',capture),
                                ('SNAPSHOT_EXPRESSION',snapshot),('// EXPORT_BRANCH',export_branch(values)),
                                ('// EXPORT_WRITER_SETTINGS',writer[start:end]),('// DECODE_TUNING',decode),('// ENCODE_TUNING',encode)]:
        assert boundary.count(marker)==1,marker;boundary=boundary.replace(marker,replacement)
    return prefix+boundary


def run_tests(source, previous, swiftc, temp):
    prefix=test_prefix(source);model=source/MODEL
    settings_test=(ROOT/'scripts/tests/NagramiXRoundBitRateTests.swift').read_text()
    page_test=(ROOT/'scripts/tests/NagramiXRoundBitRatePageTests.swift').read_text()
    variants=[('settings',prefix+settings_test,None),('page',prefix+page_test,None),
              ('old-capture',prefix.replace('self.processor.quality?.bitRate ?? 1_200_000','self.processor.quality?.quality.bitRate ?? 1_200_000')+settings_test,'capture must use chosen independent bitrate'),
              ('old-snapshot',prefix.replace(', $0.bitRate]',' ]')+settings_test,'recording snapshots the chosen bitrate'),
              ('old-export',prefix.replace(export_branch((source/VALUES).read_text()),export_branch(previous[VALUES].decode()))+settings_test,'deferred/trim export accepts four-field recording snapshot')]
    runs=[]
    for optimized in [False,True]:
        for name,code,failure in variants:
            label=name+('-O' if optimized else '-debug');path=temp/(label+'.swift');path.write_text(code);binary=temp/label
            subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),
                            *(['-O'] if optimized else []),str(model),str(path),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],env=dict(os.environ,XDG_CONFIG_HOME=str(temp/(label+'-prefs'))),capture_output=True,text=True,timeout=45,
                                  preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if failure:
                assert result.returncode!=0 and failure in result.stderr,result.stdout+result.stderr
                runs.append(label+': прежний путь записи/снимка/экспорта воспроизведён и отвергнут')
            else:
                assert result.returncode==0,result.stdout+result.stderr;runs.append(label+': '+result.stdout.strip())
            print(runs[-1],flush=True)
    subprocess.run([str(swiftc),'-frontend','-parse',*[str(source/name) for name in plan()['outputs']]],check=True)
    return runs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    from validate_message_translation import delegate_if_applied
    if delegate_if_applied(args): return
    current=plan()
    for name,digest in {**current['guards'],**current['outputs']}.items():assert sha((args.source/name).read_bytes())==digest,name
    for name,digest in current['templates'].items():assert sha((ROOT/'ios'/name).read_bytes())==digest,name
    assert (args.source/MODEL).read_bytes()==(args.source/'submodules/Camera/Sources/NagramiXRoundVideoSettings.swift').read_bytes()
    ui=(args.source/UI).read_text()
    assert all(marker not in ui for marker in ['reloadData(', 'reloadRows(', 'setItemGroups(', 'UIFont.preferredFont'])
    assert 'Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)' in ui
    assert 'self.presentationData.theme.rootController.statusBarStyle.style' in ui
    assert 'self.slider.minimumValue = 0' in ui and 'self.slider.maximumValue = 10' in ui and 'self.slider.accessibilityValue' in ui
    assert '["КАЧЕСТВО", "БИТРЕЙТ", "ЧАСТОТА КАДРОВ", "КОДЕК", "КИНОЭФФЕКТ"]' in ui
    screen=(args.source/SCREEN).read_text()
    assert 'requested.enabled ? requested : nil' in screen
    assert 'videoCodec: self.node.nagramiXQuality?.codec.telegramIdentifier' in screen and 'flags: [.instantRoundVideo]' in screen
    calls=[node.func.id for node in ast.walk(ast.parse((ROOT/'ios/apply_overlay.py').read_text())) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)]
    assert calls.index('apply_scheduled_archive_isolation')<calls.index('apply_round_video_bitrate')
    with tempfile.TemporaryDirectory(prefix='nagramix-round-bitrate-') as folder:
        temp=Path(folder);previous=reverse(args.source,current)
        rejected=guard_checks(args.source,current,previous,temp)
        previous_source(args.source,current,previous,temp,args.swiftc)
        runs=run_tests(args.source,previous,args.swiftc,temp) if args.swiftc else []
    result=dict(files=len(current['outputs']),operations=len(current['patches']),guards=len(current['guards']),fail_closed=rejected,runs=runs,
                prior_contracts='точное обратное восстановление предыдущих SHA; прежние sheet/page/refinement guards и проверки сохранены',
                runtime='production model/slider/page/capture/snapshot/JSON/export/writer bodies; UIKit/AVFoundation boundaries',
                SDK='не запускалась',physical_iPhone='ожидается',encoded_file_inspection='фактический файл iPhone не получен')
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
