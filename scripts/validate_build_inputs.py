#!/usr/bin/env python3
"""Проверить сборочные входы; native-mode проверяет реальную среду macOS/iPhoneOS."""
import argparse,ast,hashlib,json,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def require(value,message):
    if not value:raise SystemExit(message)


def workflow_contract(text):
    on=re.search(r'^on:\n(.*?)(?=^\S)',text,re.M|re.S)
    require(on is not None and re.findall(r'^  ([\w-]+):',on.group(1),re.M)==['workflow_dispatch'], 'Разрешён только ручной workflow_dispatch')
    require(not re.search(r'^\s*cancel-in-progress:\s*true\s*$',text,re.M),'Сборка не должна отменять уже запущенный run')
    for fragment in ('runs-on: xcode-27','--configuration=release_arm64','python3 ios/generate_fake_profiles.py','bash scripts/package_unsigned_ipa.sh','--team NAGRAMIX0','--bundle com.mr-efes.nagramix'):
        require(fragment in text,'Изменён контракт сборки/подписи: '+fragment)
    paths=set(re.findall(r'\b(?:python3|bash)\s+((?:scripts|ios)/[\w./-]+\.(?:py|sh))\b',text))
    require(paths,'Не найдены вызываемые скрипты')
    return paths


def exact_path(root,name):
    current=root
    for part in Path(name).parts:
        require(part not in ('..','/'), 'Небезопасный путь: '+name)
        require(current.is_dir() and part in {p.name for p in current.iterdir()},'Файл отсутствует или регистр имени неверен: '+name)
        current=current/part
    require(current.is_file(),'Ожидался файл: '+name)
    return current


def check_repo():
    workflow=(ROOT/'.github/workflows/build-unsigned-ipa.yml').read_text()
    paths=workflow_contract(workflow)
    for name in paths:exact_path(ROOT,name)
    version=json.loads((ROOT/'product/features/registry.json').read_text())['release']
    require(re.search(r'^  NAGRAMIX_VERSION: '+re.escape(version)+r'$',workflow,re.M),'Версия workflow/реестра различается')
    from validate_upstream_13_2_release import checked_plan,checked_sdk_plans,SDK_STAGES
    from late_source_stages import LATE_SOURCE_STAGES
    plans,_=checked_sdk_plans(checked_plan('upstream_13_2_release_post'))
    from fetch_upstream_submodules import load_plan
    deps=load_plan()
    config=json.loads((ROOT/'ios/configuration.template.json').read_text())
    require(config['bundle_id']=='com.mr-efes.nagramix' and config['team_id']=='NAGRAMIX0','Изменён bundle/team существующей сборки')
    require(config['api_id']=='__TELEGRAM_API_ID__' and config['api_hash']=='__TELEGRAM_API_HASH__','Ожидались placeholders, а не credentials')
    overlay=(ROOT/'ios/apply_overlay.py').read_text()
    for expression in ('make_file = source / "build-system" / "Make" / "Make.py"','build_file = source / "Telegram" / "BUILD"'):
        require(expression in overlay,'Потеряна предусмотренная настройка native target: '+expression)
    count=0
    for path in (ROOT/'scripts').rglob('*.py'):
        ast.parse(path.read_text(),filename=str(path));count+=1
    for path in (ROOT/'ios').glob('*.py'):
        ast.parse(path.read_text(),filename=str(path));count+=1
    for path in (ROOT/'scripts').glob('*.sh'):
        subprocess.run(['bash','-n',str(path)],check=True)
    tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT,text=True).split('\0'))
    used={'.github/workflows/build-unsigned-ipa.yml','ios/apply_overlay.py','ios/configuration.template.json','ios/upstream.env'}|paths
    for stage in SDK_STAGES:
        exact_path(ROOT,'ios/'+stage+'.py');used.add('ios/'+stage+'.py');used.add('ios/'+stage+'_patches.json')
    # New preparation files may be unstaged during local work; CI must use only
    # the immutable checked-out commit, including all source/resource templates.
    if os.environ.get('GITHUB_ACTIONS')=='true':
        require(used<=tracked,'В commit отсутствуют сборочные входы: '+str(sorted(used-tracked)))
        for plan in plans:
            for name in plan['templates']:require('ios/'+name in tracked,'Снимок не включён в commit: '+name)
    return {'version':version,'workflow_scripts':len(paths),'python_syntax_files':count,'late_stages':len(LATE_SOURCE_STAGES),'sdk_plans':len(plans),'submodules':len(deps['submodules']),'manual_only':True,'existing_unsigned_signing_contract':'preserved','native_environment':'not_run'}


def command(*args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=120)
    require(result.returncode==0,'Ошибка инструмента '+args[0]+': '+(result.stdout+result.stderr)[-2500:])
    return result.stdout.strip()


def check_native(source):
    require(sys.platform=='darwin','Native-проверка требует настоящую macOS')
    source=source.resolve(strict=True)
    for name in ('versions.json','Telegram/BUILD','build-system/Make/Make.py','build-system/Make/ImportCertificates.py','build-system/fake-codesigning/certs/SelfSigned.p12'):
        exact_path(source,name)
    require(any((source/'build-system/fake-codesigning/profiles').glob('*.mobileprovision')),'Отсутствуют native build-only profiles')
    versions=json.loads((source/'versions.json').read_text())
    selected=command('xcode-select','-p')
    require(Path(selected).resolve()==Path(f"/Applications/Xcode_{versions['xcode']}.app/Contents/Developer").resolve(),'Выбран иной Xcode')
    xcode=command('xcodebuild','-version')
    require(xcode.splitlines()[0]=='Xcode '+versions['xcode'],'Фактическая версия Xcode не совпала с pin')
    sdk=command('xcrun','--sdk','iphoneos','--show-sdk-path')
    sdk_version=command('xcrun','--sdk','iphoneos','--show-sdk-version')
    require('iPhoneOS.platform' in sdk and Path(sdk).is_dir(),'Ожидался SDK физического iPhone')
    require('minimum_os_version = "15.0"' in (source/'Telegram/BUILD').read_text(),'Потерян согласованный target iOS15')
    for name in ('git','openssl','security','codesign','zip','unzip','node','xcrun'):
        require(shutil.which(name),'Отсутствует инструмент '+name)
    require(Path('/usr/libexec/PlistBuddy').is_file(),'Не найден PlistBuddy упаковщика')
    require(int(command('node','--version').lstrip('v').split('.')[0])>=22,'Нужен Node22+')
    # Never print credential contents; initial job checks their shape before
    # overlay generation, keychain work or native application compilation.
    require(os.environ.get('TELEGRAM_API_ID','').isdigit(),'TELEGRAM_API_ID отсутствует или имеет неверный формат')
    require(re.fullmatch('[0-9a-fA-F]{32}',os.environ.get('TELEGRAM_API_HASH','')),'TELEGRAM_API_HASH отсутствует или имеет неверный формат')
    from fetch_upstream_submodules import load_plan,validate_source,git
    deps=load_plan();validate_source(source,deps)
    for item in deps['submodules']:
        target=source/item['path']
        require(git(target,'rev-parse','HEAD',capture=True)==item['checkout_ref'],'Не получена закреплённая зависимость: '+item['path'])
        for name,expected in item.get('required_files',{}).items():
            require(hashlib.sha256(exact_path(target,name).read_bytes()).hexdigest()==expected,'Изменён обязательный файл зависимости: '+name)
    with tempfile.TemporaryDirectory(prefix='nagramix-device-sdk-preflight-') as temp:
        folder=Path(temp);probe=folder/'DeviceSDK.swift'
        probe.write_text('''import UIKit
import AVFoundation
import AVKit
import WebKit
import MetalKit
@MainActor func nagramixDeviceSDKProbe() {
 let config=WKWebViewConfiguration();config.allowsInlineMediaPlayback=true
 let codec:AVVideoCodecType = .hevc
 let route=AVAudioSession.sharedInstance().currentRoute
 let pipSupported=AVPictureInPictureController.isPictureInPictureSupported()
 _ = (config,codec,route,pipSupported,UIFont.systemFont(ofSize:17),MTLCreateSystemDefaultDevice())
}
''')
        command('xcrun','swiftc','-swift-version','5','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-parse-as-library','-typecheck',str(probe))
    return {'xcode':xcode,'selected_developer':selected,'iphoneos_sdk':sdk_version,'device_target':'arm64-apple-ios15.0','device_framework_imports':'typechecked','submodules_checked':len(deps['submodules']),'API_credentials':'shape_checked_without_output','free_workspace_bytes':shutil.disk_usage(ROOT).free,'free_temp_bytes':shutil.disk_usage(tempfile.gettempdir()).free,'full_application_compilation':'not_run_by_this_probe'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--native',action='store_true');parser.add_argument('--upstream',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    result=check_repo()
    if args.native:
        require(args.upstream is not None,'Нужен --upstream для native-проверки');result['native_environment']=check_native(args.upstream)
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
