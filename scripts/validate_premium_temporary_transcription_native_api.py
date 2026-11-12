#!/usr/bin/env python3
"""До SDK пересобрать native SwiftTL и проверить настоящий файловый RPC и его типы."""
import argparse,hashlib,json,sys,tempfile
from pathlib import Path
from validate_local_copy_delivery import run
from validate_quick_format import block

ROOT=Path(__file__).resolve().parents[1];STAGE='premium_temporary_transcription';OVERLAY=ROOT/'ios'

def check(source,swiftc,folder):
    plan=json.loads((OVERLAY/(STAGE+'_patches.json')).read_text());meta_name=STAGE+'/native-api.json';rpc_name=STAGE+'/NativeRPC.inc'
    for n in [meta_name,rpc_name]:assert hashlib.sha256((OVERLAY/n).read_bytes()).hexdigest()==plan['templates'][n],n
    meta=json.loads((OVERLAY/meta_name).read_text())
    assert meta['pin']=='24638bc69bd083981b178dd1e7f921eebbf7fc46'
    schema=source/'submodules/TelegramApi/swift_scheme.tl';data=schema.read_bytes()
    assert hashlib.sha256(data).hexdigest()==meta['schema_sha256']
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==meta['schema_git_blob']=='896c1c6a910edeaaa39811db5a53e3cb8d184581'
    files=sorted((source/'build-system/SwiftTL/Sources/SwiftTL').rglob('*.swift'))
    assert {p.relative_to(source).as_posix() for p in files}==meta['generator_sources'].keys()
    for p in files:assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['generator_sources'][p.relative_to(source).as_posix()],str(p)
    folder.mkdir(parents=True,exist_ok=True);extra=[]
    if sys.platform!='darwin':
        z=folder/'zlib';z.mkdir();(z/'module.modulemap').write_text('module zlib [system] { header "/usr/include/zlib.h" link "z" export * }\n');extra=['-I',z]
    # Match the native host-generator BUILD flags; production ASR fixtures are
    # independently compiled with warnings-as-errors in debug and optimized modes.
    run([swiftc,'-module-cache-path',folder/'cache',*extra,*files,'-lz','-o',folder/'SwiftTL'])
    generated=folder/'Generated';generated.mkdir()
    run([folder/'SwiftTL',schema,generated,'--swift-file-count=44','--objc-output='+str(generated)])
    texts=[p.read_text() for p in generated.glob('*.swift')];rpc=next(block(s,'    static func transcribeAudioFile(') for s in texts if '    static func transcribeAudioFile(' in s)
    assert rpc.encode()==(OVERLAY/rpc_name).read_bytes(),'Actual native RPC differs from the early fixture'
    all_text='\n'.join(texts)
    input_type=block(all_text,'    enum InputFile:')
    for name in meta['native_input_file_cases']:assert 'case '+name+'(' in input_type,name
    for name,signature in [('Cons_inputFile','init(id: Int64, parts: Int32, name: String, md5Checksum: String)'),('Cons_inputFileBig','init(id: Int64, parts: Int32, name: String)')]:
        assert signature in block(all_text,'public extension Api.InputFile.'+name+' {'),name
    response=block(all_text,'public extension Api.messages.TranscribedAudio.Cons_transcribedAudio {')
    assert 'var flags: Int32' in response and 'var text: String' in response
    network=(source/'submodules/TelegramCore/Sources/Network/Network.swift').read_text()
    assert 'automaticFloodWait: Bool = true' in block(network,'    func request<T>(').split('{',1)[0]
    upload=(source/'submodules/TelegramCore/Sources/Network/MultipartUpload.swift').read_text()
    assert 'case data(Data)' in block(upload,'public enum MultipartUploadSource')
    assert 'forceNoBigParts: Bool' in block(upload,'func multipartUpload(').split('{',1)[0]
    return {'native_schema_git_blob':meta['schema_git_blob'],'actual_generator_sources':len(files),'generated_swift_files':len(texts),'actual_generated_rpc_matches_fixture':True,'real_input_file_cases':meta['native_input_file_cases'],'native_upload_and_network_signatures':'checked','server_availability':'not_tested','whole_app_sdk':'not_run'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='premium-file-native-api-') as d:r=check(a.source,a.swiftc,Path(d))
    if a.report:a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
